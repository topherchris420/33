#ifndef GUIDANCE_H
#define GUIDANCE_H

/*
 * Phase 3 terminal guidance (docs/MILITARY/GUIDANCE.md).
 *
 * Replaces the Phase 1 roll-only PID with three-axis canard control using
 * proportional navigation toward a designated target point.
 *
 * Navigation: GPS-aided IMU. The rocket carries its own GPS (UART1, see
 * docs/WIRING.md); position is GPS, attitude is gyro-integrated with accel
 * gravity correction, velocity blends GPS course/speed with IMU integration.
 *
 * Engagement modes (design_point.json / MILITARY tree):
 *   MITL   (default) - operator designates the target point pre-launch and
 *                      commands the launch; guidance steers to that point.
 *   AUTO   fire-and-forget on a locked target point - accepted only while the
 *          rocket is IDLE/ARMED, i.e. an explicit pre-launch mode selection
 *          by the operator (the arm-mode toggle).
 *
 * All arithmetic in double precision where the ESP32 allows; ENU frame in
 * meters, Earth-radius sphere for geodetic conversion.
 */

#include <Arduino.h>
#include <math.h>

struct GuidanceTarget {
    bool valid = false;
    double lat_deg = 0.0;
    double lon_deg = 0.0;
    double alt_m = 0.0;
    // ENU offset from the launch point, filled at launch
    double e = 0.0;
    double n = 0.0;
    double u = 0.0;
};

struct NavState {
    // position (ENU from launch point, m)
    double pos_e = 0.0, pos_n = 0.0, pos_u = 0.0;
    // velocity (ENU, m/s)
    double vel_e = 0.0, vel_n = 0.0, vel_u = 0.0;
    // attitude (deg): yaw about U (0 = east), pitch above horizon, roll
    double yaw_deg = 0.0, pitch_deg = 0.0, roll_deg = 0.0;
    bool gps_fix = false;
    unsigned long gps_age_ms = 0;
};

class Guidance {
public:
    static constexpr double EARTH_RADIUS_M = 6371000.0;
    static constexpr double PN_GAIN = 3.0;             // navigation constant
    static constexpr double MAX_CANARD_DEG = 12.0;    // airframe limit
    static constexpr double MIN_GUIDE_SPEED_MPS = 15.0;

    // Geodetic target + launch point -> ENU offset.
    static void setTargetFromGeo(GuidanceTarget &tgt, double tgt_lat, double tgt_lon,
                                 double tgt_alt, double launch_lat, double launch_lon,
                                 double launch_alt) {
        tgt.lat_deg = tgt_lat;
        tgt.lon_deg = tgt_lon;
        tgt.alt_m = tgt_alt;
        const double d2r = M_PI / 180.0;
        const double dlat = (tgt_lat - launch_lat) * d2r;
        const double dlon = (tgt_lon - launch_lon) * d2r;
        const double lat0 = launch_lat * d2r;
        tgt.e = EARTH_RADIUS_M * dlon * cos(lat0);
        tgt.n = EARTH_RADIUS_M * dlat;
        tgt.u = tgt_alt - launch_alt;
        tgt.valid = (fabs(tgt.e) > 0.5 || fabs(tgt.n) > 0.5 || fabs(tgt.u) > 0.5);
    }

    // Proportional navigation: lateral acceleration command (ENU, m/s^2)
    // toward the target, magnitude-limited by the airframe's usable
    // lateral acceleration.
    static void pnCommand(const NavState &nav, const GuidanceTarget &tgt,
                          double max_lat_accel, double &a_e, double &a_n, double &a_u) {
        a_e = a_n = a_u = 0.0;
        if (!tgt.valid) return;
        const double speed = sqrt(nav.vel_e * nav.vel_e + nav.vel_n * nav.vel_n + nav.vel_u * nav.vel_u);
        if (speed < MIN_GUIDE_SPEED_MPS) return;

        // Line-of-sight vector and its rate: Ldot = -V (target static)
        const double l_e = tgt.e - nav.pos_e;
        const double l_n = tgt.n - nav.pos_n;
        const double l_u = tgt.u - nav.pos_u;
        const double l2 = l_e * l_e + l_n * l_n + l_u * l_u;
        if (l2 < 25.0) return;  // terminal: within 5 m, hold

        // LOS rate omega = (L x Ldot) / |L|^2, Ldot = -V
        const double ld_e = -nav.vel_e, ld_n = -nav.vel_n, ld_u = -nav.vel_u;
        const double w_e = (l_n * ld_u - l_u * ld_n) / l2;
        const double w_n = (l_u * ld_e - l_e * ld_u) / l2;
        const double w_u = (l_e * ld_n - l_n * ld_e) / l2;

        // a_cmd = N * (omega x V): proportional navigation, applied
        // perpendicular to the velocity. (The cross order matters: omega x V,
        // not V x omega — the Python CEP cross-check caught this sign error.)
        a_e = PN_GAIN * (w_n * nav.vel_u - w_u * nav.vel_n);
        a_n = PN_GAIN * (w_u * nav.vel_e - w_e * nav.vel_u);
        a_u = PN_GAIN * (w_e * nav.vel_n - w_n * nav.vel_e);

        // limit
        const double mag = sqrt(a_e * a_e + a_n * a_n + a_u * a_u);
        if (mag > max_lat_accel && mag > 0) {
            const double s = max_lat_accel / mag;
            a_e *= s; a_n *= s; a_u *= s;
        }
    }

    // Map an ENU acceleration command to canard deflections, given the
    // estimated attitude. Pitch canards (up/down pair) steer in the
    // vertical plane; yaw canards (left/right) in the horizontal plane;
    // roll is compensated by rotating the command into the rolled body frame.
    // deflection conventions: +pitch_cmd -> nose up (climb), +yaw_cmd ->
    // nose right (turn south-to-north heading increases).
    static void canardMix(const NavState &nav, double a_e, double a_n, double a_u,
                          double accel_per_deg, double &pitch_deg, double &yaw_deg) {
        // Body-frame directions from attitude.
        const double d2r = M_PI / 180.0;
        const double yaw = nav.yaw_deg * d2r;
        const double pitch = nav.pitch_deg * d2r;
        const double roll = nav.roll_deg * d2r;

        // Rotate ENU accel into the rolled body frame.
        // Body axes: x_b = velocity direction (approx), y_b = right, z_b = up.
        const double ch = cos(pitch);
        const double bx = ch * cos(yaw), by = ch * sin(yaw), bz = sin(pitch);  // heading unit
        const double ux = -sin(pitch) * cos(yaw), uy = -sin(pitch) * sin(yaw), uz = ch;  // body up (no roll)
        // Apply roll about the heading axis.
        const double su = sin(roll), cu = cos(roll);
        // right = heading x up (approx, roll applied)
        const double rx = by * uz - bz * uy, ry = bz * ux - bx * uz, rz = bx * uy - by * ux;
        const double ux2 = ux * cu + rx * su, uy2 = uy * cu + ry * su, uz2 = uz * cu + rz * su;

        // vertical-plane command: component along body-up
        const double a_vert = a_e * ux2 + a_n * uy2 + a_u * uz2;
        // horizontal-plane command: component along body-right
        const double a_hor = a_e * rx + a_n * ry + a_u * rz;

        const double deg_v = (accel_per_deg > 0.0) ? a_vert / accel_per_deg : 0.0;
        const double deg_h = (accel_per_deg > 0.0) ? a_hor / accel_per_deg : 0.0;
        pitch_deg = constrain(deg_v, -MAX_CANARD_DEG, MAX_CANARD_DEG);
        yaw_deg = constrain(deg_h, -MAX_CANARD_DEG, MAX_CANARD_DEG);
    }
};

#endif // GUIDANCE_H
