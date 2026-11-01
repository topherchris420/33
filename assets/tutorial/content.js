/* V3D-TO-33-1 — the bench manual's text. Single source for the film pages,
 * the page-by-page manual view, and the copy panel.
 * Every command and number below was re-checked against commit 217696a
 * (README, docs/SAFETY.md, docs/USER_GUIDE.md, docs/WIRING.md,
 * docs/BENCH_SESSIONS.md, docs/PID_TUNING.md, docs/GROUND_STATUS.md,
 * docs/DEGRADED_MODES.md, docs/PROJECT_STATUS.md, docs/claims/, and the live
 * output of `python -m evidence status`). The repository governs. */
(function () {
  "use strict";
  var PUB = "V3D-TO-33-1";

  var pages = {
    cover: {
      lines: [
        "V3D-TO-33-1",
        "UTILITY BENCH MANUAL",
        "PROJECT 33 FOLDING-FIN ROCKET",
        "INERT BENCH SUPPLEMENT",
        "",
        "DISTRIBUTION: UNLIMITED. MIT LICENSE.",
        "PUBLISHED UNDER THE AUTHORITY OF THE EVIDENCE RECORD.",
      ],
      footer: "VERS3DYNAMICS · AN OPEN EXPERIMENT",
    },

    scope: {
      section: "SCOPE", pageNo: "A",
      blocks: [
        { t: "h", text: "SCOPE" },
        { t: "text", text: "This manual covers offline review and inert bench validation. It authorizes no ignition, propulsion or flight." },
        { t: "gap" },
        { t: "h2", text: "SUPPLEMENTAL NOTICE" },
        { t: "text", text: "This film is incomplete without the repository. Where they differ, the repository governs." },
        { t: "gap" },
        { t: "h2", text: "SAFETY SUPPLEMENT SUMMARY" },
        { t: "toc", label: "G-01", title: "PHYSICAL ARMING SWITCH", page: "NOT MEASURED" },
        { t: "toc", label: "G-02", title: "ROCKET READINESS HANDSHAKE", page: "NOT MEASURED" },
        { t: "toc", label: "G-03", title: "HEARTBEAT TIMEOUT", page: "NOT MEASURED" },
        { t: "toc", label: "G-04", title: "DASHBOARD LAUNCH DISABLED BY DEFAULT", page: "NOT MEASURED" },
        { t: "toc", label: "G-05", title: "DASHBOARD LAUNCH REQUIRES READY", page: "NOT MEASURED" },
        { t: "toc", label: "G-06", title: "DASHBOARD SOURCE CHECK", page: "NOT MEASURED" },
        { t: "toc", label: "G-07", title: "PHYSICAL LAUNCH HOLD", page: "NOT MEASURED" },
        { t: "toc", label: "G-08", title: "ROCKET ARM REQUIRES IDLE AND A HEALTHY IMU", page: "NOT MEASURED" },
        { t: "toc", label: "G-09", title: "ROCKET IGNITE REQUIRES ARMED AND A HEALTHY IMU", page: "NOT MEASURED" },
        { t: "toc", label: "G-10", title: "ROCKET IGNITE REQUIRES THE DEPLOY FLAG", page: "NOT MEASURED" },
        { t: "toc", label: "G-11", title: "DEPLOY TRIGGER REQUIRES A NON-IDLE STATE", page: "NOT MEASURED" },
        { t: "toc", label: "G-12", title: "FORCED IGNITION IS BENCH-BUILD ONLY", page: "NOT MEASURED" },
        { t: "toc", label: "G-13", title: "REFUSALS AND ABORTS ARE LOGGED", page: "NOT MEASURED" },
        { t: "toc", label: "G-14", title: "BOUNDED CONTROLLER GAINS", page: "NOT MEASURED" },
        { t: "small", text: "Gates are checked in source by tests. Source inspection does not show the hardware behaves that way. See docs/SAFETY.md." },
      ],
    },

    toc: {
      section: "CONTENTS", pageNo: "i",
      blocks: [
        { t: "h", text: "TABLE OF CONTENTS" },
        { t: "gap" },
        { t: "toc", id: "t1", label: "SECTION I", title: "DESCRIPTION", page: "1-1" },
        { t: "toc", id: "t2", label: "SECTION II", title: "NORMAL PROCEDURES (INERT BENCH)", page: "2-1" },
        { t: "toc", id: "t3", label: "SECTION III", title: "ABNORMAL OPERATIONS", page: "3-1" },
        { t: "toc", id: "t4", label: "SECTION IV", title: "AUXILIARY EQUIPMENT", page: "4-1" },
        { t: "toc", id: "t5", label: "SECTION V", title: "OPERATING LIMITATIONS", page: "5-1" },
        { t: "toc", id: "t6", label: "SECTION VI", title: "FLIGHT CHARACTERISTICS", page: "NOT MEASURED" },
        { t: "toc", id: "t7", label: "SECTION VII", title: "ADVERSE WEATHER OPERATION", page: "OUTSIDE VALIDATION BOUNDARY" },
        { t: "toc", id: "t8", label: "APPENDIX A", title: "PERFORMANCE DATA", page: "NOT MEASURED" },
        { t: "toc", id: "t9", label: "FOLDOUT", title: "WIRING AND DATA PATH", page: "FO-1" },
      ],
    },

    div1: {
      tab: "I", tabColor: "teal", section: "SECTION I", title: "DESCRIPTION",
      blocks: [
        { t: "toc", label: "FIGURE 1-1", title: "EXPLODED SYSTEM", page: "1-2" },
        { t: "toc", label: "FOLDOUT", title: "WIRING AND DATA PATH", page: "FO-1" },
        { t: "toc", label: "VIEW A-A", title: "ROLL CONTROL, LOOKING AFT", page: "1-4" },
      ],
      intro: "This section describes the bench system as it exists in source and CAD.",
    },

    fig11: {
      section: "SECTION I", pageNo: "1-2", figure: "FIGURE 1-1. EXPLODED SYSTEM (CLAY, NOT TO SCALE)",
      callouts: [
        "NOSE", "BODY", "CANARDS (4)", "FOLDING FINS", "ROCKET ESP32",
        "MPU6050 IMU", "CANARD SERVOS (4)", "IGNITION SERVO (HORN REMOVED)",
      ],
    },

    fo1: {
      section: "FOLDOUT", pageNo: "FO-1", figure: "FO-1. WIRING AND DATA PATH",
      lines: [
        "DASHBOARD  <-- Wi-Fi UDP 4444 -->  LAUNCHER ESP32  <-- UART2 115200 -->  ROCKET ESP32",
        "                                   GPS · COMPASS · BAROMETER             MPU6050 IMU",
        "                                   ARM SWITCH · BUTTON · LED · BUZZER    4 CANARD SERVOS",
      ],
    },

    div2: {
      tab: "II", tabColor: "teal", section: "SECTION II", title: "NORMAL PROCEDURES (INERT BENCH)",
      blocks: [
        { t: "toc", label: "II-A", title: "OFFLINE REVIEW (NO HARDWARE)", page: "2-1" },
        { t: "toc", label: "II-B", title: "INERT BENCH PREFLIGHT", page: "2-3" },
        { t: "toc", label: "II-C", title: "CANARD CENTERING AND GAIN WINDOWS", page: "2-6" },
        { t: "toc", label: "II-D", title: "SESSION PASSPORT", page: "2-8" },
      ],
      intro: "These procedures use inert loads only. No energetic material is present during any repository test.",
    },

    p21: {
      section: "SECTION II", pageNo: "2-1",
      blocks: [
        { t: "h", text: "II-A  OFFLINE REVIEW (NO HARDWARE)" },
        { t: "step", id: "a1", n: "1.", item: "PYTHON", state: "3.11 OR NEWER, VERIFY" },
        { t: "step", id: "a2", n: "2.", cmd: "python -m evidence status", state: "RUN" },
        { t: "step", id: "a3", n: "3.", cmd: "python -m evidence check", state: "RUN" },
        { t: "note", id: "nb", text: "If the output folder already exists, choose a fresh path. The packet builder does not overwrite." },
        { t: "step", id: "a4", n: "4.", cmd: "python -m evidence build --output build/review", state: "RUN" },
        { t: "note", id: "nv", text: "Verification confirms packet integrity, not scientific validity or physical performance." },
        { t: "step", id: "a5", n: "5.", cmd: "python -m evidence verify build/review", state: "RUN" },
        { t: "step", id: "a6", n: "6.", cmd: "build/review/index.html", state: "OPEN" },
      ],
    },

    p23: {
      section: "SECTION II", pageNo: "2-3",
      blocks: [
        { t: "h", text: "II-B  INERT BENCH PREFLIGHT" },
        { t: "warning", id: "w1", text: "No energetic material is present during any repository test." },
        { t: "step", id: "b0", n: "", item: "IGNITION SERVO", state: "MECHANICALLY DISCONNECTED" },
        { t: "caution", id: "c1", text: "Power servos from a supply sized for stall current, not from a weak USB port or an ESP32 GPIO." },
        { t: "step", id: "b1", n: "1.", item: "WIRING", state: "VERIFY AGAINST WIRING.md" },
        { t: "step", id: "b2", n: "2.", item: "FIRMWARE", state: "BUILD BOTH PROJECTS FROM A RECORDED COMMIT" },
        { t: "step", id: "b3", n: "3.", item: "LAUNCHER ACCESS POINT", state: "CONNECT" },
        { t: "step", id: "b4", n: "4.", item: "DASHBOARD", state: "START" },
        { t: "sub", id: "b4s", text: "Session ID, RAW SESSION and data-quality line – VERIFY" },
        { t: "step", id: "b5", n: "5.", item: "GPS STATUS, ALTITUDE (OR \"NOT REPORTED\"), HEARTBEAT", state: "VERIFY UPDATING" },
        { t: "step", id: "b6", n: "6.", item: "ARM SWITCH", state: "ARM. LAUNCHER – VERIFY READY" },
        { t: "step", id: "b7", n: "7.", item: "ARM SWITCH", state: "SAFE. LAUNCHER – VERIFY SAFE, ABORT: ROW LOGGED" },
        { t: "note", id: "n8", text: "Firmware does not acknowledge calibration." },
        { t: "step", id: "b8", n: "8.", item: "ROCKET", state: "HOLD STILL. CALIBRATE – SEND" },
        { t: "step", id: "b9", n: "9.", item: "DASHBOARD LAUNCH", state: "VERIFY REJECTED" },
        { t: "sub", id: "b9s", text: "CMD_REJECT:dashboard_launch_disabled – VERIFY LOGGED" },
        { t: "step", id: "b10", n: "10.", item: "DASHBOARD", state: "CLOSE CLEANLY" },
      ],
    },

    p26: {
      section: "SECTION II", pageNo: "2-6",
      blocks: [
        { t: "h", text: "II-C  CANARD CENTERING AND GAIN WINDOWS" },
        { t: "table", id: "fig22", caption: "FIGURE 2-2. CANARD CENTERS (Firmware/Rocket/src/main.cpp, WIRING.md)",
          cols: ["CANARD", "GPIO", "CENTER", "MAX DEFLECTION"], widths: [9, 7, 9, 14],
          rows: [["LEFT", "26", "115°", "±12°"], ["RIGHT", "25", "80°", "±12°"], ["UP", "27", "80°", "±12°"], ["DOWN", "14", "115°", "±12°"]] },
        { t: "caution", id: "c6", text: "A setting that saturates the servos is not a better tune because it briefly lowers roll error." },
        { t: "note", id: "n6", text: "One session per setting. Same fixture motion. Comparison rule pre-registered before the runs." },
        { t: "table", id: "gains", caption: "GAIN WINDOWS (docs/PID_TUNING.md)",
          cols: ["RUN", "Kp", "Kd"], widths: [29, 7, 6],
          rows: [["Baseline", "0.50", "0.20"], ["Higher damping", "0.50", "0.30"], ["More proportional authority", "0.80", "0.20"], ["Conservative", "0.35", "0.15"]] },
      ],
    },

    p28: {
      section: "SECTION II", pageNo: "2-8",
      blocks: [
        { t: "h", text: "II-D  SESSION PASSPORT" },
        { t: "note", id: "nd", text: "Never edit telemetry.csv, session.json or commands.csv." },
        { t: "step", id: "d1", n: "1.", item: "DASHBOARD", state: "CLOSE CLEANLY" },
        { t: "step", id: "d2", n: "2.", cmd: "python -m evidence session declare …", state: "RUN (operator)" },
        { t: "step", id: "d3", n: "3.", cmd: "python -m evidence session passport …", state: "RUN" },
        { t: "step", id: "d4", n: "4.", cmd: "python -m evidence verify …", state: "RUN" },
        { t: "note", id: "na", text: "Automated tools, including AI assistants, never run session accept." },
        { t: "step", id: "d5", n: "5.", item: "NAMED HUMAN REVIEWER", state: "ACCEPT OR REJECT" },
      ],
    },

    div3: {
      tab: "III", tabColor: "mustard", section: "SECTIONS III AND IV", title: "ABNORMAL OPERATIONS · AUXILIARY EQUIPMENT",
      blocks: [
        { t: "toc", label: "III", title: "LOSS OF ROCKET TELEMETRY", page: "3-1" },
        { t: "toc", label: "FIGURE 3-1", title: "DEGRADED MODES", page: "3-2" },
        { t: "toc", label: "IV", title: "STATUS BOARD", page: "4-1" },
        { t: "toc", label: "IV", title: "EVIDENCE OBSERVATORY", page: "4-2" },
      ],
      intro: "The status board reads packets and suggests. It cannot send anything, and it is not evidence.",
    },

    p31: {
      section: "SECTION III", pageNo: "3-1",
      blocks: [
        { t: "h", text: "LOSS OF ROCKET TELEMETRY (LAUNCHER STILL REPORTING)" },
        { t: "small", text: "Indication: C-ROCKET-TELEMETRY-LOST (CAUTION)" },
        { t: "step", id: "e1", n: "1.", item: "STATUS BOARD", state: "OPEN" },
        { t: "note", id: "ne", text: "The board suggests. The operator presses. dumplog reads the onboard log and moves no actuator." },
        { t: "step", id: "e2", n: "2.", item: "DUMP LOG", state: "PRESS" },
        { t: "cond", id: "ey", text: "If a reply arrives:" },
        { t: "step", id: "e3", n: "3.", item: "UART AND ROCKET", state: "CLEARED. IMU – SUSPECT" },
        { t: "cond", id: "en", text: "If silence:" },
        { t: "step", id: "e3a", n: "3a.", item: "UART OR ROCKET", state: "SUSPECT" },
      ],
    },

    fig31: {
      section: "SECTION III", pageNo: "3-2",
      figure: "FIGURE 3-1. DEGRADED MODES (ANALYTICAL. NO FAULT INJECTED ON HARDWARE.)",
      root: "ALL UNITS WORKING — 12 OF 12 CAPABILITIES",
      rows: [
        ["RESULT AFTER LINK FAILS", "4 OF 12"],
        ["RESULT AFTER LAUNCHER FAILS", "1 OF 12"],
        ["RESULT AFTER UART FAILS", "7 OF 12"],
        ["RESULT AFTER ROCKET FAILS", "6 OF 12"],
        ["RESULT AFTER IMU FAILS", "9 OF 12"],
        ["RESULT AFTER GPS / BARO / COMPASS FAILS", "11 OF 12"],
      ],
      source: "Generated from protocol/ground_status_model.json (docs/DEGRADED_MODES.md).",
    },

    div5: {
      tab: "V", tabColor: "sage", section: "SECTION V", title: "OPERATING LIMITATIONS",
      blocks: [
        { t: "toc", label: "5-1", title: "RECORD STATE", page: "5-1" },
        { t: "toc", label: "5-1", title: "CLAIM LEDGER", page: "5-1" },
      ],
      intro: "Limits are read from the evidence record: python -m evidence status.",
    },

    p51: {
      section: "SECTION V", pageNo: "5-1",
      blocks: [
        { t: "h", text: "OPERATING LIMITATIONS" },
        { t: "text", id: "rs", text: "RECORD STATE: 8 claims · 3 contradicted · 4 unresolved · 1 supported within stated limits · 0 accepted physical measurements" },
        { t: "gap" },
        { t: "toc", id: "l1", label: "C1", labelW: 4, title: "FOLDING-FIN MECHANISM", page: "CONTRADICTED (linkage does not close)" },
        { t: "toc", id: "l6", label: "C6", labelW: 4, title: "SPRING MARGIN", page: "CONTRADICTED (19% vs 20% required)" },
        { t: "toc", id: "l8", label: "C8", labelW: 4, title: "STRUCTURAL BOUNDARIES", page: "CONTRADICTED (modulus below comparison)" },
        { t: "toc", id: "l5", label: "C5", labelW: 4, title: "STATIC STABILITY", page: "UNRESOLVED (two models disagree)" },
        { t: "gap" },
        { t: "toc", id: "lp", label: "", title: "PHYSICAL PERFORMANCE", page: "NOT ESTABLISHED" },
        { t: "toc", id: "lf", label: "", title: "FLIGHT READINESS", page: "NOT ASSESSED" },
        { t: "small", text: "Source: python -m evidence status at commit 217696a. If the record changes, the record governs." },
      ],
    },

    cds: {
      section: "CHANGE DATA SUMMARY", pageNo: "C-1",
      title: "CHANGE DATA SUMMARY: VALIDATION GATES",
      gates: [
        "ANALYTICAL MODEL", "SOFTWARE REPRODUCTION", "SYNTHETIC TEST",
        "INERT BENCH SETUP", "INERT PHYSICAL MEASUREMENT",
        "REPEATED MEASUREMENT", "INDEPENDENT REVIEW",
      ],
      /* Gate reached per claim passport at 217696a. */
      claims: { C1: 0, C2: 2, C3: 1, C4: 1, C5: 1, C6: 1, C7: 1, C8: 1 },
      humanFrom: 3,
      note: "Gates from INERT BENCH SETUP onward need a human-registered pre-registration or a human-accepted measurement. No AI model, CI run or repository setting can move a claim across them.",
    },

    endcard: {
      lines: [
        "THE ROCKET IS THE SPECIMEN. THE RECORD IS THE EXPERIMENT.",
        "RUN THE REVIEW",
        "python -m evidence status",
        "github.com/topherchris420/33 · topherchris420.github.io/33",
        "An open experiment by Vers3Dynamics.",
      ],
    },
  };

  var glossary = [
    ["ESP32", "Microcontroller board. One in the rocket, one in the launcher."],
    ["IMU", "Inertial measurement unit: the rocket's MPU6050 motion sensor."],
    ["UART", "Serial wire between launcher and rocket (UART2, 115200 baud)."],
    ["UDP", "Network messages between dashboard and launcher (port 4444)."],
    ["AP", "The launcher's Wi-Fi access point (192.168.4.1)."],
    ["PID / Kp / Kd", "The roll controller and its proportional and derivative gains."],
    ["CP / CG", "Centre of pressure and centre of gravity; their spacing sets static margin."],
    ["CMD_REJECT", "A logged refusal, e.g. CMD_REJECT:dashboard_launch_disabled."],
    ["RAW SESSION", "A dashboard capture before audit, declaration and human acceptance."],
    ["PASSPORT", "A verifiable summary of a session: digests, audit, warnings, limits."],
    ["NOT MEASURED", "A quantity with no accepted measurement. Never read as zero."],
  ];

  var disclaimer = "Claymation tutorial. Not a flight test, physical assembly record, or evidence of deployment. Procedures are summarized from the Project 33 repository, which is authoritative. This film supplies no engineering evidence and changes no claim status.";

  /* Copy panel: exact commands from the repository, keyed by chapter. */
  var commands = {
    cover: [
      { label: "Run the review", cmd: "python -m evidence status", src: "README.md" },
    ],
    toc: [
      { label: "Claim table and scopes", cmd: "python -m evidence status", src: "README.md" },
    ],
    desc: [
      { label: "Status board demo (invented packets, no hardware)", cmd: "python Firmware/status_panel.py --demo", src: "docs/GROUND_STATUS.md" },
    ],
    offline: [
      { label: "1 · Claim table, requirement results, scopes", cmd: "python -m evidence status", src: "README.md" },
      { label: "2 · Strict check", cmd: "python -m evidence check", src: "README.md" },
      { label: "3 · Build a portable packet", cmd: "python -m evidence build --output build/review", src: "README.md" },
      { label: "4 · Integrity only, not scientific validity", cmd: "python -m evidence verify build/review", src: "README.md" },
      { label: "5 · Open in a browser", cmd: "build/review/index.html", src: "README.md" },
    ],
    preflight: [
      { label: "Firmware: create the local WiFi header (git-ignored)", cmd: "cp Firmware/Launcher/src/wifi_config.h.example Firmware/Launcher/src/wifi_config.h", src: "README.md" },
      { label: "Firmware: build the rocket project", cmd: "pio run -d Firmware/Rocket", src: "README.md" },
      { label: "Firmware: build the launcher project", cmd: "pio run -d Firmware/Launcher", src: "README.md" },
      { label: "Dashboard dependencies", cmd: "python -m pip install -r Firmware/requirements.txt", src: "docs/USER_GUIDE.md" },
      { label: "Start the dashboard", cmd: "python Firmware/dashboard.py", src: "docs/USER_GUIDE.md" },
    ],
    canards: [
      { label: "Gain-window report from a session", cmd: "python Firmware/analyze_pid.py Firmware/TestSessions/<session>/telemetry.csv -o Firmware/TestSessions/<session>/pid-comparison.md", src: "docs/PID_TUNING.md" },
    ],
    passport: [
      { label: "Declare (operator; example from the docs)", cmd: "python -m evidence session declare Firmware/TestSessions/bench_EXAMPLE \\\n  --operator \"Your Name\" --origin bench --purpose \"Stationary roll drift, 600 s\" \\\n  --tests gyro_drift --firmware-commit $(git rev-parse HEAD) --hardware-revision \"proto-1\" \\\n  --inert-configuration \"No energetic material; ignition servo horn removed\" \\\n  --ignition-servo-disconnected true --calibration \"CALIBRATE sent at start, rocket on level fixture\" \\\n  --measurement-equipment \"none (telemetry only)\" --preregistration P-003", src: "docs/BENCH_SESSIONS.md" },
      { label: "Build the passport", cmd: "python -m evidence session passport Firmware/TestSessions/bench_EXAMPLE --output build/bench_EXAMPLE-passport", src: "docs/BENCH_SESSIONS.md" },
      { label: "Verify it", cmd: "python -m evidence verify build/bench_EXAMPLE-passport", src: "docs/BENCH_SESSIONS.md" },
    ],
    abnormal: [
      { label: "Status board demo (invented packets, no hardware)", cmd: "python Firmware/status_panel.py --demo", src: "docs/GROUND_STATUS.md" },
      { label: "Replay a recorded session as text", cmd: "python Firmware/ground_status.py SESSION_FOLDER", src: "docs/GROUND_STATUS.md" },
      { label: "Is the failure analysis current?", cmd: "python tools/generate_degraded_modes.py --check", src: "docs/GROUND_STATUS.md" },
    ],
    limits: [
      { label: "Read the record yourself", cmd: "python -m evidence status", src: "README.md" },
      { label: "What a change would affect", cmd: "python -m evidence impact mechanism/spring_sizing.py", src: "README.md" },
    ],
    gates: [
      { label: "Run the review", cmd: "python -m evidence status", src: "README.md" },
    ],
  };

  window.P33T_CONTENT = {
    pub: PUB, pages: pages, glossary: glossary, disclaimer: disclaimer, commands: commands,
    repo: "https://github.com/topherchris420/33", site: "https://topherchris420.github.io/33/",
    commit: "217696a",
  };
})();
