"""Phase 6.1 fuze S&A software-in-the-loop harness.

A faithful Python port of the rocket's launch-detection, fuze S&A, and
DISARM logic from Firmware/Rocket/src/main.cpp, with an event-injection API
so the Phase 6.1 bench matrix can be driven today (software-in-the-loop)
and on hardware tomorrow (the same harness drives the ESP32 over UART).

Fidelity is enforced by tests/test_sa_harness.py, which asserts this
module's constants against the firmware source text — if the firmware
changes, the harness fails until it is re-ported.

Phase 6.1 items covered at the LOGIC level (all still PENDING on hardware):
  1.1 no-fire checks (drop, static acceleration, handling)
  1.2 single-event arming attempts (each alone leaves the fuze SAFE)
  1.3 arm-in-order (all three events in sequence)
  1.4 impact function and selectable PD delay
Everything here is IMPLEMENTATION-VERIFIED LOGIC, not a hardware record.
"""

import json
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]

# --- constants mirrored from the firmware (test-enforced) -------------------
DEPLOY_ACCEL_THRESHOLD_MS2 = 2.0 * 9.80665      # 2 g launch detection
DEPLOY_ACCEL_SUSTAIN_MS = 150                     # ms the event must hold
FUZE_IMPACT_THRESHOLD_MS2 = -8.0 * 9.80665        # -8 g impact detection
FUZE_FLIGHT_TIME_GATE_MS = 2600                   # motor burn + 0.5 s
FUZE_FIRE_DELAY_OPTIONS_MS = (0, 5, 10, 20)        # PD delay set


class SaHarness:
    """Event-driven model of the rocket's S&A chain.

    Events (each a call, in bench or simulated time):
      set_state('IDLE' | 'ARMED' | 'FLIGHT')   -- rocket state machine
      accel(x_ms2, duration_ms)               -- feed an acceleration event
      deploy_fins(deployed: bool)            -- canard-deployment latch
      time_advance(ms)                        -- advance the rocket clock
      disarm()                                -- MIL-DEV-011 DISARM command

    Observables:
      fuze_state       'SAFE' | 'ARMED' | 'FUNCTION'
      fire_pin         bool (HIGH only after the PD delay post-impact)
      launch_detected  bool
    """

    def __init__(self):
        self.state = 'IDLE'
        self.fuze_state = 'SAFE'
        self.launch_detected = False
        self.fins_deployed = False
        self.fire_pin = False
        self.fuze_delay_ms = 0
        self.clock_ms = 0
        self._flight_start_ms = None
        self._launch_detect_start_ms = None
        self._launch_detect_active = False
        self._impact_ms = None
        self.events = []          # audit trail for the bench log

    # -- commands ---------------------------------------------------------
    def command(self, cmd):
        """Serial commands the rocket accepts (subset relevant to 6.1)."""
        if cmd == 'ARM' and self.state == 'IDLE':
            self.state = 'ARMED'
            self._log('ARM -> ARMED')
        elif cmd == 'DISARM':
            if self.state == 'ARMED':
                self.state = 'IDLE'
                self._launch_detect_active = False
                self.launch_detected = False
                self.fins_deployed = False
                self._log('DISARM -> IDLE (safed)')
            elif self.state != 'IDLE':
                return False  # refused outside ARMED/IDLE (never in FLIGHT)
        elif cmd.startswith('FUZEDELAY,'):
            if self.state in ('IDLE', 'ARMED'):
                value = int(cmd.split(',')[1])
                if value in FUZE_FIRE_DELAY_OPTIONS_MS:
                    self.fuze_delay_ms = value
                    self._log(f'FUZEDELAY {value} ms')
        return True

    def set_state(self, state):
        if state == 'FLIGHT' and self._flight_start_ms is None:
            self._flight_start_ms = self.clock_ms
        self.state = state

    def deploy_fins(self, deployed):
        self.fins_deployed = deployed

    def accel(self, x_ms2, duration_ms=0):
        """Feed an acceleration reading; models the sustained-detection rule
        exactly: above threshold continuously for the sustain time, checked
        on every loop iteration (1 ms effective step in the harness)."""
        self._log(f'accel {x_ms2:.1f} m/s2 for {duration_ms} ms')
        elapsed = 0
        while elapsed <= duration_ms:
            self._tick_accel(x_ms2)
            self.time_advance(1)
            elapsed += 1

    def _tick_accel(self, x_ms2):
        if self.state != 'IDLE':
            if x_ms2 > DEPLOY_ACCEL_THRESHOLD_MS2:
                if not self._launch_detect_active:
                    self._launch_detect_active = True
                    self._launch_detect_start_ms = self.clock_ms
                elif (self.clock_ms - self._launch_detect_start_ms
                      >= DEPLOY_ACCEL_SUSTAIN_MS
                      and not self.launch_detected):
                    self.launch_detected = True
            else:
                self._launch_detect_active = False

    def time_advance(self, ms):
        self.clock_ms += ms
        self._update_fuze()

    def impact(self, x_ms2):
        """An impact deceleration event (only meaningful in FLIGHT)."""
        self._log(f'impact reading {x_ms2:.1f} m/s2')
        if (self.fuze_state == 'ARMED' and self.state == 'FLIGHT'
                and x_ms2 < FUZE_IMPACT_THRESHOLD_MS2):
            self.fuze_state = 'FUNCTION'
            self._impact_ms = self.clock_ms
            self._log('FUZE FUNCTION')
        self._update_fuze()

    # -- S&A core -----------------------------------------------------------
    def _update_fuze(self):
        if self.fuze_state == 'SAFE' and self.state == 'FLIGHT':
            armed_by_time = (self._flight_start_ms is not None
                             and self.clock_ms - self._flight_start_ms
                             >= FUZE_FLIGHT_TIME_GATE_MS)
            if self.fins_deployed and self.launch_detected and armed_by_time:
                self.fuze_state = 'ARMED'
                self._log('FUZE ARMED (launch-g AND canard-deploy AND burn-time)')
        if (self.fuze_state == 'FUNCTION' and self._impact_ms is not None
                and self.clock_ms - self._impact_ms >= self.fuze_delay_ms):
            self.fire_pin = True

    def _log(self, text):
        self.events.append({'clock_ms': self.clock_ms, 'text': text})


# --- the Phase 6.1 bench matrix, as runnable scenarios --------------------

def scenario_drop_test():
    """6.1.1 logic half: a 1.5 m drop gives a short, hard transient that
    must never sustain long enough to detect launch."""
    h = SaHarness()
    h.command('ARM')
    h.state = 'ARMED'
    # a 40 g, 20 ms drop transient (far above the 2 g threshold, far below
    # the 150 ms sustain requirement)
    h.accel(40 * 9.80665, duration_ms=20)
    h.time_advance(2000)
    return h


def scenario_static_acceleration():
    """6.1.1 logic half: 8 g static for 5 s arms the launch detector but the
    rocket never enters FLIGHT, so the fuze cannot arm."""
    h = SaHarness()
    h.command('ARM')
    h.state = 'ARMED'
    h.accel(8 * 9.80665, duration_ms=5000)
    h.time_advance(2000)
    return h


def scenario_single_event_launch_only():
    """6.1.2: launch detection without canard deployment."""
    h = SaHarness()
    h.command('ARM')
    h.set_state('FLIGHT')
    h.accel(3 * 9.80665, duration_ms=400)
    h.time_advance(4000)
    return h


def scenario_single_event_fins_only():
    """6.1.2: canard deployment without launch acceleration."""
    h = SaHarness()
    h.command('ARM')
    h.set_state('FLIGHT')
    h.deploy_fins(True)
    h.time_advance(4000)
    return h


def scenario_single_event_time_only():
    """6.1.2: flight time passing with no launch detection and no fins."""
    h = SaHarness()
    h.command('ARM')
    h.set_state('FLIGHT')
    h.time_advance(5000)
    return h


def scenario_arm_in_order():
    """6.1.3: all three events in the intended sequence."""
    h = SaHarness()
    h.command('ARM')
    h.set_state('FLIGHT')
    h.accel(3 * 9.80665, duration_ms=400)   # event 1: sustained launch g
    h.deploy_fins(True)                     # event 2: canard confirmation
    h.time_advance(3000)                    # event 3: burn-time gate
    return h


def scenario_impact_function(delay_ms=0):
    """6.1.4: an armed fuze meets a -20 g impact and fires after the delay."""
    h = scenario_arm_in_order()
    h.impact(-20 * 9.80665)
    h.time_advance(delay_ms + 5)
    return h


def scenario_disarm_after_abort():
    """MIL-DEV-011: an aborted round can be safed without restart."""
    h = SaHarness()
    h.command('ARM')
    h.accel(3 * 9.80665, duration_ms=400)    # launch detected during the abort
    ok = h.command('DISARM')
    return h, ok


SCENARIOS = {
    'drop_test': scenario_drop_test,
    'static_acceleration': scenario_static_acceleration,
    'single_event_launch_only': scenario_single_event_launch_only,
    'single_event_fins_only': scenario_single_event_fins_only,
    'single_event_time_only': scenario_single_event_time_only,
    'arm_in_order': scenario_arm_in_order,
    'impact_function': scenario_impact_function,
}


def run_matrix():
    """The full 6.1 logic matrix with expected outcomes."""
    results = {}
    drop = scenario_drop_test()
    results['drop_test'] = {'fuze': drop.fuze_state,
                            'launch_detected': drop.launch_detected,
                            'expect': 'SAFE, no launch detect'}
    static = scenario_static_acceleration()
    results['static_acceleration'] = {'fuze': static.fuze_state,
                                      'launch_detected': static.launch_detected,
                                      'expect': 'SAFE (no FLIGHT state), launch detected'}
    for name in ('single_event_launch_only', 'single_event_fins_only',
                'single_event_time_only'):
        h = SCENARIOS[name]()
        results[name] = {'fuze': h.fuze_state, 'expect': 'SAFE'}
    armed = scenario_arm_in_order()
    results['arm_in_order'] = {'fuze': armed.fuze_state, 'expect': 'ARMED'}
    for delay in FUZE_FIRE_DELAY_OPTIONS_MS:
        h = scenario_impact_function(delay)
        results[f'impact_function_{delay}ms'] = {
            'fuze': h.fuze_state, 'fire_pin': h.fire_pin,
            'fired_within_delay_plus_5ms': h.fire_pin, 'delay_ms': delay,
            'expect': 'FUNCTION, fire pin HIGH after the delay'}
    h, ok = scenario_disarm_after_abort()
    results['disarm_after_abort'] = {'fuze': h.fuze_state, 'state': h.state,
                                     'command_accepted': ok,
                                     'launch_detected_after': h.launch_detected,
                                     'expect': 'IDLE, launch detect cleared'}
    return results


if __name__ == '__main__':
    print(json.dumps(run_matrix(), indent=2))
