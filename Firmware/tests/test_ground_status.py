import csv
from itertools import combinations
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

FIRMWARE_DIR = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(FIRMWARE_DIR))

import ground_status as gs
from ground_status import GroundStatus, load_model, minimal_diagnoses, parse_gain_entry, signature


class Clock:
    def __init__(self, now=0.0):
        self.now = now

    def __call__(self):
        return self.now


NOMINAL_ENV = "ENV,0.000000,0.000000,212.3,2"


def board():
    clock = Clock()
    return GroundStatus(clock=clock), clock


def sample(status, clock, roll=1.0, rate=2.0, output=0, state="IDLE", kp="0.50", kd="0.20", device_ms=None):
    device_ms = int(clock.now * 1000) if device_ms is None else device_ms
    status.observe(f"T,{device_ms},{roll},{rate},{output}")
    status.observe(f"STATUS:{state},{kp},{kd},1.30")


def healthy_launcher(status, env=NOMINAL_ENV):
    status.observe(env)
    status.observe("[FUSION] Hdg: 141.0 | Pitch: +0.4")


def run(status, clock, seconds, *, rocket=True, launcher=True, state="IDLE", **kwargs):
    """Advance time while the named sources keep reporting at their firmware rates."""
    end = clock.now + seconds
    jitter = 0
    while clock.now < end:
        clock.now += 0.05
        jitter += 1
        if rocket:
            sample(status, clock, rate=2.0 + (jitter % 7) / 100, state=state, **kwargs)
        if launcher and jitter % 10 == 0:
            healthy_launcher(status)


def ids(snapshot):
    return [advisory["id"] for advisory in snapshot["advisories"]]


class DiagnosisTests(unittest.TestCase):
    def test_minimal_diagnoses_are_minimal_hitting_sets(self):
        order = ["A", "B", "C", "D"]
        self.assertEqual(minimal_diagnoses([{"A", "B"}, {"B", "C"}], order), [["B"], ["A", "C"]])
        self.assertEqual(minimal_diagnoses([], order), [])

    def test_no_packets_at_all_points_at_link_or_launcher(self):
        status, clock = board()
        clock.now = 10
        snapshot = status.snapshot()
        self.assertEqual(snapshot["diagnoses"], [["LINK"], ["LAUNCHER"]])
        self.assertIn("C-NO-PACKETS", ids(snapshot))
        self.assertEqual(snapshot["attitude"]["valid"], False)

    def test_startup_grace_does_not_raise_a_fault(self):
        status, clock = board()
        clock.now = 1
        snapshot = status.snapshot()
        self.assertEqual(snapshot["diagnoses"], [])
        self.assertNotIn("C-NO-PACKETS", ids(snapshot))

    def test_launcher_without_rocket_suggests_the_log_dump_probe(self):
        status, clock = board()
        run(status, clock, 5, rocket=False)
        snapshot = status.snapshot()
        self.assertEqual(snapshot["diagnoses"], [["UART"], ["ROCKET"], ["IMU"]])
        self.assertEqual(snapshot["next_test"]["command"], "dumplog")
        self.assertEqual(snapshot["next_test"]["if_reply"], [["IMU"]])
        self.assertEqual(snapshot["next_test"]["if_silent"], [["UART"], ["ROCKET"]])
        self.assertIn("DUMP LOG", snapshot["isolation"])
        self.assertEqual(snapshot["units"]["LAUNCHER"], gs.SEEN)
        self.assertEqual(snapshot["units"]["IMU"], gs.SUSPECT)

    def test_log_reply_isolates_a_failed_imu(self):
        status, clock = board()
        run(status, clock, 5, rocket=False)
        status.command_sent("dumplog")
        clock.now += 0.1
        status.observe("LOG_START,0")
        status.observe("LOG_END")
        snapshot = status.snapshot()
        self.assertEqual(snapshot["diagnoses"], [["IMU"]])
        self.assertEqual(snapshot["units"]["ROCKET"], gs.SEEN)
        self.assertEqual(snapshot["capabilities"]["live_telemetry"], gs.LOST)
        self.assertEqual(snapshot["capabilities"]["log_recovery"], gs.SUPPORTED)
        self.assertEqual(snapshot["capabilities"]["arm_handshake"], gs.LOST)

    def test_silence_after_the_probe_leaves_uart_or_rocket_and_says_so(self):
        status, clock = board()
        run(status, clock, 5, rocket=False)
        status.command_sent("dumplog")
        clock.now += 0.5
        self.assertEqual(status.snapshot()["isolation"], "Waiting for the log-dump reply.")
        run(status, clock, 2.5, rocket=False)
        snapshot = status.snapshot()
        self.assertEqual(snapshot["diagnoses"], [["UART"], ["ROCKET"]])
        self.assertIsNone(snapshot["next_test"])
        self.assertIn("inspect the hardware", snapshot["isolation"])
        self.assertEqual(snapshot["units"]["IMU"], gs.NOT_SEEN)

    def test_probe_result_expires_and_can_be_repeated(self):
        status, clock = board()
        run(status, clock, 5, rocket=False)
        status.command_sent("dumplog")
        run(status, clock, 31, rocket=False)
        self.assertEqual(status.snapshot()["next_test"]["command"], "dumplog")

    def test_every_failure_combination_is_explained_and_never_marked_seen(self):
        """Exhaustive over the model, through the real packet path. Software only."""
        model = load_model()
        units = [unit["id"] for unit in model["units"]]
        for size in range(len(units) + 1):
            for failed in combinations(units, size):
                for probe in (False, True):
                    failed_set = set(failed)
                    snapshot = self._steady_state(failed_set, probe, model)
                    for unit in failed_set:
                        self.assertNotEqual(snapshot["units"][unit], gs.SEEN, (failed, probe))
                    if snapshot["diagnoses"]:
                        self.assertTrue(any(set(item) <= failed_set for item in snapshot["diagnoses"]), (failed, probe))
                    if not failed_set:
                        self.assertEqual(snapshot["diagnoses"], [])

    def _steady_state(self, failed, probe, model):
        expected = signature(failed, model, probe=probe)
        clock = Clock()
        status = GroundStatus(model=model, clock=clock)
        reaches_dashboard = not failed & {"LINK", "LAUNCHER"}
        telemetry = expected["rocket_telemetry"] == gs.PRESENT
        gps = "GPS" not in failed
        baro = "BARO" not in failed
        compass = "COMPASS" not in failed
        env = f"ENV,0.0,0.0,{'212.0' if baro else 'nan'},{2 if gps else 0}"
        for step in range(1, 101):
            clock.now = step * 0.05
            if telemetry:
                sample(status, clock, rate=2.0 + (step % 5) / 100)
            if reaches_dashboard and step % 20 == 0:
                status.observe(env)
            if reaches_dashboard and compass and step % 10 == 0:
                status.observe("[FUSION] Hdg: 1.0 | Pitch: +0.1")
        if probe:
            status.command_sent("dumplog")
            if expected["log_reply"] == gs.PRESENT:
                status.observe("LOG_START,0")
                status.observe("LOG_END")
            else:
                for step in range(101, 150):
                    clock.now = step * 0.05
                    if telemetry:
                        sample(status, clock, rate=2.0 + (step % 5) / 100)
                    if reaches_dashboard and step % 20 == 0:
                        status.observe(env)
                    if reaches_dashboard and compass and step % 10 == 0:
                        status.observe("[FUSION] Hdg: 1.0 | Pitch: +0.1")
        return status.snapshot()


class AdvisoryTests(unittest.TestCase):
    def test_nominal_session_raises_nothing(self):
        status, clock = board()
        run(status, clock, 6)
        snapshot = status.snapshot()
        self.assertEqual(snapshot["advisories"], [])
        self.assertTrue(all(state == gs.SEEN for state in snapshot["units"].values()))
        self.assertEqual(snapshot["capabilities"]["switch_abort"], gs.SUPPORTED)

    def test_rocket_left_armed_by_a_launcher_abort_is_a_warning(self):
        status, clock = board()
        run(status, clock, 3, state="ARMED")
        status.observe("ABORT:Arming switch flipped OFF.")
        run(status, clock, 1, state="ARMED", launcher=False)
        snapshot = status.snapshot()
        self.assertIn("W-ARMED-AFTER-ABORT", ids(snapshot))
        self.assertEqual(snapshot["advisories"][0]["level"], gs.WARNING)
        self.assertIn("D-025", snapshot["advisories"][0]["detail"])

    def test_abort_with_the_rocket_still_idle_is_not_that_warning(self):
        status, clock = board()
        run(status, clock, 3)
        status.observe("ABORT:Rocket Timeout.")
        run(status, clock, 1, launcher=False)
        snapshot = status.snapshot()
        self.assertNotIn("W-ARMED-AFTER-ABORT", ids(snapshot))
        self.assertIn("C-LAUNCHER-ABORT", ids(snapshot))

    def test_rocket_restart_clears_the_warning_and_is_inferred(self):
        status, clock = board()
        run(status, clock, 3, state="ARMED")
        status.observe("ABORT:Lost heartbeat from Rocket!")
        run(status, clock, 1, state="ARMED")
        run(status, clock, 1, state="IDLE")
        snapshot = status.snapshot()
        self.assertNotIn("W-ARMED-AFTER-ABORT", ids(snapshot))
        self.assertIn("C-ROCKET-RESTART", ids(snapshot))

    def test_loss_of_telemetry_while_armed_is_not_shown_as_safe(self):
        status, clock = board()
        run(status, clock, 3, state="ARMED")
        run(status, clock, 3, rocket=False)
        snapshot = status.snapshot()
        self.assertIn("W-ACTIVE-STATE-STALE", ids(snapshot))
        self.assertTrue(snapshot["rocket"]["stale"])
        self.assertIn("STALE", snapshot["rocket"]["display"])

    def test_stale_idle_rocket_is_not_a_warning(self):
        status, clock = board()
        run(status, clock, 3)
        run(status, clock, 3, rocket=False)
        self.assertNotIn("W-ACTIVE-STATE-STALE", ids(status.snapshot()))

    def test_ignition_actuation_is_announced_with_its_limits(self):
        status, clock = board()
        run(status, clock, 1, state="FLIGHT")
        snapshot = status.snapshot()
        advisory = next(a for a in snapshot["advisories"] if a["id"] == "W-IGNITION-ACTUATION")
        self.assertIn("does not confirm ignition", advisory["detail"])

    def test_launcher_wait_is_not_read_as_a_compass_or_gps_fault(self):
        status, clock = board()
        run(status, clock, 3)
        previous = []
        for _ in range(80):
            run(status, clock, 0.1, launcher=False)
            previous.append(status.snapshot())
        for snapshot in previous:
            self.assertNotIn("A-COMPASS-SILENT", ids(snapshot))
            self.assertNotIn("A-GPS-NO-NMEA", ids(snapshot))
            self.assertEqual(snapshot["diagnoses"], [])
        self.assertIn("A-LAUNCHER-HELD", ids(previous[-1]))

    def test_launcher_resuming_does_not_flash_a_compass_fault(self):
        status, clock = board()
        run(status, clock, 3)
        run(status, clock, 6, launcher=False)
        status.observe(NOMINAL_ENV)
        self.assertNotIn("A-COMPASS-SILENT", ids(status.snapshot()))

    def test_compass_silence_with_env_flowing_is_flagged(self):
        status, clock = board()
        end = clock.now + 6
        tick = 0
        while clock.now < end:
            clock.now += 0.05
            tick += 1
            sample(status, clock, rate=2.0 + (tick % 7) / 100)
            if tick % 20 == 0:
                status.observe(NOMINAL_ENV)
        snapshot = status.snapshot()
        self.assertIn("A-COMPASS-SILENT", ids(snapshot))
        self.assertEqual(snapshot["diagnoses"], [["COMPASS"]])

    def test_output_is_paired_with_the_status_from_the_same_data_line(self):
        status, clock = board()
        run(status, clock, 1, state="IGNITING")
        # The first FLIGHT sample: T arrives before the STATUS that names its state.
        clock.now += 0.05
        status.observe("T,9000,1.0,2.0,5")
        status.observe("STATUS:FLIGHT,0.50,0.20,1.30")
        self.assertNotIn("C-OUTPUT-OUTSIDE-FLIGHT", ids(status.snapshot()))
        status, clock = board()
        run(status, clock, 1, state="ARMED")
        clock.now += 0.05
        status.observe("T,9000,1.0,2.0,5")
        status.observe("STATUS:ARMED,0.50,0.20,1.30")
        self.assertIn("C-OUTPUT-OUTSIDE-FLIGHT", ids(status.snapshot()))

    def test_frozen_imu_is_a_heuristic_advisory(self):
        status, clock = board()
        for _ in range(60):
            clock.now += 0.05
            status.observe(f"T,{int(clock.now * 1000)},1.00,0.00,0")
            status.observe("STATUS:IDLE,0.50,0.20,1.30")
        advisory = next(a for a in status.snapshot()["advisories"] if a["id"] == "A-IMU-FROZEN")
        self.assertEqual(advisory["level"], gs.ADVISORY)
        self.assertIn("heuristic", advisory["detail"])

    def test_launcher_clock_regression_is_inferred_as_restart(self):
        status, clock = board()
        status.observe("T,50000,1.0,2.0,0")
        status.observe("T,100,1.0,2.0,0")
        self.assertIn("C-LAUNCHER-RESTART", ids(status.snapshot()))

    def test_unknown_state_and_refusals_are_reported_not_guessed(self):
        status, clock = board()
        status.observe("STATUS:COAST,0.50,0.20,1.30")
        status.observe("CMD_REJECT:dashboard_launch_disabled")
        status.observe("CMD_REJECT:unknown_command")
        snapshot = status.snapshot()
        self.assertIn("C-STATE-UNKNOWN", ids(snapshot))
        self.assertIn("A-COMMAND-REFUSED", ids(snapshot))
        self.assertIn("C-UNKNOWN-COMMAND", ids(snapshot))
        self.assertEqual(snapshot["rocket"]["display"], "NOT RECEIVED")

    def test_one_shot_events_expire(self):
        status, clock = board()
        status.observe("CMD_REJECT:dashboard_launch_disabled")
        self.assertIn("A-COMMAND-REFUSED", ids(status.snapshot()))
        clock.now += gs.EVENT_HOLD_S + 1
        self.assertNotIn("A-COMMAND-REFUSED", ids(status.snapshot()))

    def test_partial_log_dump_is_flagged(self):
        status, clock = board()
        status.observe("LOG_START,3")
        status.observe("LOG,1,1.0,2.0,0,IDLE,0.50,0.20,1.30")
        status.observe("LOG_END")
        self.assertIn("A-LOG-PARTIAL", ids(status.snapshot()))

    def test_advisories_are_ordered_by_severity(self):
        status, clock = board()
        run(status, clock, 2, state="FLIGHT", output=12)
        levels = [advisory["level"] for advisory in status.snapshot()["advisories"]]
        self.assertEqual(levels, sorted(levels, key=gs.LEVEL_ORDER.get))
        self.assertIn(gs.ADVISORY, levels)


class AttitudeTests(unittest.TestCase):
    def test_old_samples_are_invalid_not_held(self):
        status, clock = board()
        sample(status, clock, roll=12.5)
        self.assertEqual(status.snapshot()["attitude"]["roll_deg"], 12.5)
        clock.now += gs.ATTITUDE_VALID_S + 0.1
        attitude = status.snapshot()["attitude"]
        self.assertFalse(attitude["valid"])
        self.assertIsNone(attitude["roll_deg"])
        self.assertIn("old", attitude["reason"])

    def test_non_finite_sample_is_not_used(self):
        status, clock = board()
        status.observe("T,100,nan,2.0,0")
        self.assertFalse(status.snapshot()["attitude"]["valid"])

    def test_attitude_states_what_it_does_not_observe(self):
        status, clock = board()
        attitude = status.snapshot()["attitude"]
        self.assertIn("pitch and yaw", attitude["not_observed"])
        self.assertIn("NOT MEASURED", attitude["drift"])


class GainEntryTests(unittest.TestCase):
    def test_limits_match_firmware_and_reject_non_finite(self):
        self.assertEqual(parse_gain_entry("0", "10"), (0.0, 10.0))
        for bad in (("-0.1", "1"), ("1", "10.01"), ("nan", "1"), ("1", "inf"), ("abc", "1"), ("", "1")):
            with self.assertRaises(ValueError):
                parse_gain_entry(*bad)

    def test_sent_gains_confirm_only_from_a_later_status(self):
        status, clock = board()
        run(status, clock, 1)
        status.command_sent("PID,1.0,0.3")
        self.assertEqual(status.snapshot()["gains"]["state"], "SENT")
        run(status, clock, 0.2, kp="1.00", kd="0.30")
        self.assertEqual(status.snapshot()["gains"]["state"], "CONFIRMED")

    def test_resending_current_gains_is_not_confirmed_by_an_older_status(self):
        status, clock = board()
        run(status, clock, 1)
        clock.now += 0.01
        status.command_sent("PID,0.5,0.2")
        self.assertEqual(status.snapshot()["gains"]["state"], "SENT")

    def test_half_cent_values_confirm_despite_rounding_differences(self):
        # Python formats 0.125 as 0.12; firmware String(0.125, 2) reports 0.13.
        status, clock = board()
        run(status, clock, 1)
        status.command_sent("PID,0.125,0.2")
        run(status, clock, 0.2, kp="0.13", kd="0.20")
        self.assertEqual(status.snapshot()["gains"]["state"], "CONFIRMED")

    def test_differing_telemetry_after_the_window_is_no_match(self):
        status, clock = board()
        run(status, clock, 1)
        status.command_sent("PID,1.0,0.3")
        run(status, clock, 1.5)
        snapshot = status.snapshot()
        self.assertEqual(snapshot["gains"]["state"], "NO MATCH")
        self.assertIn("C-GAINS-NO-MATCH", ids(snapshot))

    def test_no_telemetry_after_the_window_is_unconfirmed_not_no_match(self):
        status, clock = board()
        run(status, clock, 1)
        status.command_sent("PID,1.0,0.3")
        run(status, clock, 3, rocket=False)
        snapshot = status.snapshot()
        self.assertEqual(snapshot["gains"]["state"], "UNCONFIRMED")
        self.assertNotIn("C-GAINS-NO-MATCH", ids(snapshot))
        self.assertIn("A-GAINS-UNCONFIRMED", ids(snapshot))

    def test_firmware_rejection_is_reported_and_cleared_by_the_next_send(self):
        status, clock = board()
        status.command_sent("PID,1.0,0.3")
        status.observe("CMD_REJECT:pid_invalid")
        snapshot = status.snapshot()
        self.assertEqual(snapshot["gains"]["state"], "REJECTED")
        self.assertIn("C-GAINS-REJECTED", ids(snapshot))
        status.command_sent("PID,1.0,0.4")
        snapshot = status.snapshot()
        self.assertEqual(snapshot["gains"]["state"], "SENT")
        self.assertNotIn("C-GAINS-REJECTED", ids(snapshot))

    def test_preselect_is_shown_separately_from_active_and_is_not_sent(self):
        status, clock = board()
        run(status, clock, 1)
        status.preselect("0.5", "0.2")
        self.assertIsNone(status.snapshot()["gains"]["preselect"])
        status.preselect("2.5", "0.2")
        gains = status.snapshot()["gains"]
        self.assertEqual(gains["preselect"], (2.5, 0.2))
        line = gs.gains_line(gains)
        self.assertIn("ACTIVE Kp 0.50 / Kd 0.20", line)
        self.assertIn("PRESELECT Kp 2.50 / Kd 0.20 (not sent)", line)
        status.preselect("99", "0.2")
        self.assertIn("ENTRY INVALID", gs.gains_line(status.snapshot()["gains"]))


class ReplayTests(unittest.TestCase):
    def _session(self, root, rows, commands=()):
        directory = Path(root) / "session"
        directory.mkdir()
        with (directory / "telemetry.csv").open("w", newline="", encoding="utf-8") as handle:
            writer = csv.DictWriter(handle, fieldnames=["received_at_iso", "raw", "origin"], lineterminator="\n")
            writer.writeheader()
            for second, raw in rows:
                writer.writerow({"received_at_iso": f"2000-01-01T00:{second // 60:02d}:{second % 60:02d}.000+00:00", "raw": raw, "origin": "synthetic"})
        with (directory / "commands.csv").open("w", newline="", encoding="utf-8") as handle:
            writer = csv.DictWriter(handle, fieldnames=["sent_utc", "command", "outcome"], lineterminator="\n")
            writer.writeheader()
            for second, command, outcome in commands:
                writer.writerow({"sent_utc": f"2000-01-01T00:00:{second:02d}.000+00:00", "command": command, "outcome": outcome})
        return directory

    def test_replay_reports_stale_warning_in_a_silent_gap_and_keeps_origin(self):
        rows = []
        for second in range(0, 5):
            rows += [(second, f"T,{second * 1000},1.{second},2.{second},0"), (second, "STATUS:ARMED,0.50,0.20,1.30"), (second, NOMINAL_ENV)]
        rows += [(40, NOMINAL_ENV)]
        with tempfile.TemporaryDirectory() as tmp:
            report = gs.build_report(self._session(tmp, rows))
        self.assertEqual(report["origins"], ["synthetic"])
        self.assertIn("Not evidence", report["stage"])
        warning = next(entry for entry in report["timeline"] if entry["id"] == "W-ACTIVE-STATE-STALE")
        self.assertAlmostEqual(warning["start"], 6.0, delta=0.5)

    def test_replay_applies_only_commands_that_were_sent(self):
        rows = [(0, "STATUS:IDLE,0.50,0.20,1.30"), (5, "STATUS:IDLE,0.50,0.20,1.30")]
        with tempfile.TemporaryDirectory() as tmp:
            report = gs.build_report(self._session(tmp, rows, [(1, "PID,1.0,0.3", "send_failed: x"), (2, "calibrate", "sent")]))
        self.assertIsNone(report["final"]["gains"]["commanded"])
        self.assertIsNotNone(report["final"]["attitude"]["calibration_age_s"])

    def test_cli_refuses_to_write_inside_the_session_and_never_changes_it(self):
        with tempfile.TemporaryDirectory() as tmp:
            session = self._session(tmp, [(0, "STATUS:IDLE,0.50,0.20,1.30")])
            before = {path.name: path.read_bytes() for path in session.iterdir()}
            script = str(FIRMWARE_DIR / "ground_status.py")
            refused = subprocess.run([sys.executable, script, str(session), "--output", str(session / "report.txt")],
                                     capture_output=True, text=True)
            self.assertNotEqual(refused.returncode, 0)
            self.assertIn("raw capture", refused.stderr)
            printed = subprocess.run([sys.executable, script, str(session), "--json"], capture_output=True, text=True, check=True)
            self.assertEqual(json.loads(printed.stdout)["session"], "session")
            self.assertEqual({path.name: path.read_bytes() for path in session.iterdir()}, before)

    def test_synthetic_demo_shows_the_abort_warning_and_the_isolation_limit(self):
        report = gs.replay(gs.synthetic_demo_events())
        seen = {entry["id"] for entry in report["timeline"]}
        self.assertLessEqual({"W-ARMED-AFTER-ABORT", "W-ACTIVE-STATE-STALE", "A-LAUNCHER-HELD"}, seen)
        self.assertNotIn("A-COMPASS-SILENT", seen)
        self.assertEqual(report["final"]["diagnoses"], [["UART"], ["ROCKET"]])


if __name__ == "__main__":
    unittest.main()
