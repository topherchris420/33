// 3D systems architecture of Project 33, drawn from docs/ARCHITECTURE.md and docs/WIRING.md.
// A diagram only: nodes, links, and animated telemetry pulses. Command-direction links are
// drawn dashed and labelled "exists in firmware — not exposed here"; nothing in this module
// can transmit, and no node offers a control.
import { THREE, createRenderer, CameraRig, studioLights, label3D, autoResize, loop } from "../core/three-kit.js";
import { clayMaterial } from "../core/materials.js";
import { h, clear, announce, reducedMotion } from "../core/dom.js";
import { categoryBadge } from "../core/taxonomy.js";
import { repoLink, docLink, discrepancyLink } from "../core/data.js";

const ROCKET_SRC = "Firmware/Rocket/src/main.cpp";
const LAUNCHER_SRC = "Firmware/Launcher/src/main.cpp";

export const NODES = [
  { id: "dashboard", name: "Python dashboard", zone: "ground", kind: "software", pos: [-380, 0, 0], size: [92, 16, 62],
    iface: "UDP 4444 over the launcher's Wi-Fi access point (192.168.4.1)",
    duties: ["Live plot of roll, rate, and servo output", "Automatic raw CSV logging per session with metadata and command log", "PID comparison, graph export, onboard log-dump request"],
    sources: ["Firmware/dashboard.py", "Firmware/telemetry_log.py", "Firmware/session_artifacts.py", "Firmware/analyze_pid.py"],
    gates: ["G-04", "G-05", "G-06", "G-13"], units: ["LINK"] },
  { id: "status", name: "Status board (read-only)", zone: "ground", kind: "software", pos: [-380, 0, 122], size: [80, 12, 44],
    iface: "Reads packets the dashboard already received; no socket of its own",
    duties: ["Fault isolation against a source-pinned dependency model", "Attitude, gain confirmation, advisories, session replay", "No command path"],
    sources: ["Firmware/ground_status.py", "Firmware/status_panel.py", "protocol/ground_status_model.json"], gates: [], units: [] },
  { id: "observatory", name: "Evidence Observatory (offline)", short: "Evidence Observatory · offline", zone: "ground", kind: "software", pos: [-380, 0, -126], size: [80, 12, 44],
    iface: "Reads committed files and completed captures; standard library only; no network",
    duties: ["Claim passports, requirement evaluation, discrepancy register", "Portable review packets with SHA-256 digests", "Never talks to firmware"],
    sources: ["evidence/__main__.py", "evidence/telemetry.py", "docs/EVIDENCE_OBSERVATORY.md"], gates: [], units: [] },
  { id: "launcher", name: "Launcher ESP32", zone: "launcher", kind: "board", pos: [-60, 0, 0], size: [70, 12, 34],
    iface: "Wi-Fi AP + UDP 4444 · UART2 (TX 17 / RX 16, 115200) · I²C (SDA 21 / SCL 22) · Serial1 RX 4",
    duties: ["Wi-Fi access point and dashboard UDP link", "UART relay to the rocket; stamps T packets with its own millis()", "GPS, barometer, compass telemetry", "Physical launch interlock and SAFE → ARMING → READY → IGNITING state machine"],
    sources: [LAUNCHER_SRC, "docs/ARCHITECTURE.md", "docs/WIRING.md"],
    gates: ["G-01", "G-02", "G-03", "G-04", "G-05", "G-06", "G-07", "G-13", "G-14"], units: ["LAUNCHER"] },
  { id: "gps", name: "GPS module", zone: "launcher", kind: "sensor", pos: [-175, 0, 126], size: [34, 8, 26], iface: "Serial1 RX1 on GPIO 4, 9600 baud (receive only)", duties: ["NMEA position for the ENV packet"], sources: ["docs/WIRING.md", LAUNCHER_SRC], gates: [], units: ["GPS"] },
  { id: "baro", name: "BMP180 barometer", zone: "launcher", kind: "sensor", pos: [-62, 0, 136], size: [28, 8, 24], iface: "I²C address 0x77", duties: ["Barometric altitude for ENV (NaN when missing, see D-019)"], sources: ["docs/WIRING.md", LAUNCHER_SRC], gates: [], units: ["BARO"] },
  { id: "compass", name: "QMC5883L compass", zone: "launcher", kind: "sensor", pos: [52, 0, 126], size: [28, 8, 24], iface: "I²C address 0x0D", duties: ["Launcher heading ([FUSION] lines)"], sources: ["docs/WIRING.md", LAUNCHER_SRC], gates: [], units: ["COMPASS"] },
  { id: "armswitch", name: "Arm switch", zone: "launcher", kind: "interlock", pos: [-205, 0, -122], size: [22, 10, 22], iface: "GPIO 5, INPUT_PULLUP, active LOW (toggle)", duties: ["Physical gate: leaving SAFE requires it; releasing it aborts to SAFE"], sources: ["docs/WIRING.md", "docs/SAFETY.md"], gates: ["G-01", "G-07"], units: [] },
  { id: "button", name: "Launch button", zone: "launcher", kind: "interlock", pos: [-145, 0, -156], size: [22, 10, 22], iface: "GPIO 18, momentary normally open", duties: ["Physical hold requirement with the switch still armed"], sources: ["docs/WIRING.md", "docs/SAFETY.md"], gates: ["G-07"], units: [] },
  { id: "led", name: "Status LED", zone: "launcher", kind: "indicator", pos: [-85, 0, -122], size: [18, 8, 18], iface: "GPIO 23 (HIGH = on)", duties: ["Indicator output"], sources: ["docs/WIRING.md"], gates: [], units: [] },
  { id: "buzzer", name: "Buzzer", zone: "launcher", kind: "indicator", pos: [-25, 0, -156], size: [18, 8, 18], iface: "GPIO 2, LOW-trigger", duties: ["Indicator output"], sources: ["docs/WIRING.md"], gates: [], units: [] },
  { id: "lservo", name: "Launcher-side servo (interlock)", short: "Launcher servo", zone: "launcher", kind: "actuator", pos: [50, 0, -118], size: [26, 12, 18], iface: "GPIO 19, SG90", duties: ["Launcher-side interlock actuator — not controllable from this page"], sources: ["docs/WIRING.md"], gates: [], units: [] },
  { id: "rocket", name: "Rocket ESP32 flight computer", short: "Rocket ESP32", zone: "rocket", kind: "board", pos: [262, 0, 0], size: [70, 12, 34],
    iface: "UART2 (TX 17 / RX 16, 115200) · I²C (SDA 21 / SCL 22) · servo PWM · GPIO 33 deploy output",
    duties: ["IMU roll integration and PID output", "Canard servo control; canards centred until FLIGHT", "Rocket-side arming state; refusals reported as CMD_REJECT", "240-sample RAM ring buffer returned by DUMPLOG"],
    sources: [ROCKET_SRC, "Firmware/Rocket/src/deploy_isr.cpp", "docs/ARCHITECTURE.md"],
    gates: ["G-02", "G-08", "G-09", "G-10", "G-11", "G-12", "G-13", "G-14"], units: ["ROCKET"] },
  { id: "imu", name: "MPU6050 IMU", zone: "rocket", kind: "sensor", pos: [262, 0, 132], size: [28, 8, 22], iface: "I²C (SDA 21 / SCL 22)", duties: ["Roll rate for integration; health checked only at boot (not_modeled)"], sources: ["docs/WIRING.md", ROCKET_SRC], gates: ["G-08", "G-09"], units: ["IMU"] },
  { id: "canards", name: "Canard servos ×4", zone: "rocket", kind: "actuator", pos: [396, 0, 0], size: [24, 12, 18], group: 4, iface: "GPIO 26 left, 25 right, 27 up, 14 down; ±12° maximum deflection", duties: ["Roll control surfaces — not controllable from this page"], sources: ["docs/WIRING.md", ROCKET_SRC], gates: [], units: [] },
  { id: "iservo", name: "Rocket ignition servo", short: "Ignition servo", zone: "rocket", kind: "actuator", pos: [262, 0, -124], size: [26, 12, 18], iface: "GPIO 5 (motor bay)", duties: ["Not controllable from this page; gated by G-09, G-10, G-12"], sources: ["docs/WIRING.md", ROCKET_SRC], gates: ["G-09", "G-10", "G-12"], units: [] },
];

// kind: telemetry (pulses flow along it), input, indicator, files, command (dashed; not exposed)
export const EDGES = [
  { id: "uart", from: "rocket", to: "launcher", kind: "telemetry", label: "UART2 · 115200 baud", unit: "UART", packets: ["DATA", "LOG", "CMD_REJECT"] },
  { id: "link", from: "launcher", to: "dashboard", kind: "telemetry", label: "UDP 4444 · Wi-Fi AP", unit: "LINK", packets: ["T", "STATUS", "ENV"] },
  { id: "imu-bus", from: "imu", to: "rocket", kind: "telemetry", label: "I²C", packets: ["rate"] },
  { id: "gps-bus", from: "gps", to: "launcher", kind: "telemetry", label: "Serial1 · 9600", packets: ["NMEA"] },
  { id: "baro-bus", from: "baro", to: "launcher", kind: "telemetry", label: "I²C 0x77", packets: ["p"] },
  { id: "compass-bus", from: "compass", to: "launcher", kind: "telemetry", label: "I²C 0x0D", packets: ["B"] },
  { id: "status-copy", from: "dashboard", to: "status", kind: "telemetry", label: "read-only copy", packets: ["T"] },
  { id: "files", from: "dashboard", to: "observatory", kind: "files", label: "files, offline · no network" },
  { id: "arm-in", from: "armswitch", to: "launcher", kind: "input", label: "GPIO 5 input" },
  { id: "btn-in", from: "button", to: "launcher", kind: "input", label: "GPIO 18 input" },
  { id: "led-out", from: "launcher", to: "led", kind: "indicator", label: "indicator" },
  { id: "buzz-out", from: "launcher", to: "buzzer", kind: "indicator", label: "indicator" },
  { id: "cmd-udp", from: "dashboard", to: "launcher", kind: "command", label: "commands · not exposed" },
  { id: "cmd-uart", from: "launcher", to: "rocket", kind: "command", label: "commands · not exposed" },
  { id: "pwm-canards", from: "rocket", to: "canards", kind: "command", label: "PWM · not exposed" },
  { id: "pwm-ign", from: "rocket", to: "iservo", kind: "command", label: "PWM · not exposed" },
  { id: "pwm-lservo", from: "launcher", to: "lservo", kind: "command", label: "PWM · not exposed" },
];

const PACKET_COLORS = { T: 0x67d8cf, STATUS: 0xe3c27a, ENV: 0xb49ad8, DATA: 0x67d8cf, LOG: 0xf1e9d6, CMD_REJECT: 0xe07650, rate: 0x4cc9bb, NMEA: 0xb49ad8, p: 0xb49ad8, B: 0xb49ad8 };
export const PACKET_LEGEND = [
  ["- - - copper", "#c47a45", "command path: exists in firmware, not exposed here"],
  ["T / DATA", "#67d8cf", "roll, rate, servo output (T is stamped with the launcher's clock at relay — D-018)"],
  ["STATUS", "#e3c27a", "rocket state and gains"],
  ["ENV / sensors", "#b49ad8", "launcher position, altitude, heading"],
  ["LOG", "#f1e9d6", "recovered ring-buffer rows (rocket clock)"],
  ["CMD_REJECT", "#e07650", "refusals forwarded into the session record"],
];

const KIND_COLORS = { software: 0x2fb3ae, board: 0x0f6a70, sensor: 0x5b6b78, interlock: 0xc47a45, indicator: 0x8a7a5a, actuator: 0x3a4652 };

export function mountArchitecture({ viewport, inspector, nodeList, toggles, safetyGates, groundStatus }) {
  const gateById = new Map(safetyGates.gates.map((g) => [g.id, g]));
  const scene = new THREE.Scene();
  scene.background = new THREE.Color(0x08111a);
  scene.fog = new THREE.Fog(0x08111a, 900, 1800);
  const { renderer, labels } = createRenderer(viewport);
  renderer.shadowMap.enabled = false; // a schematic: shadows cost frames and add nothing
  const rig = new CameraRig(renderer.domElement, { fov: 32 });
  let onScreen = false;
  new IntersectionObserver((entries) => { onScreen = entries.some((e) => e.isIntersecting); }).observe(viewport);
  rig.controls.maxPolarAngle = Math.PI * 0.47;
  studioLights(scene, { intensity: 0.9 });

  // Ground plinth, zones, and grid
  const floor = new THREE.Mesh(new THREE.BoxGeometry(1020, 6, 420), new THREE.MeshStandardMaterial({ color: 0x0c1621, roughness: 0.9 }));
  floor.position.set(-20, -6, 0); floor.receiveShadow = true;
  scene.add(floor);
  const grid = new THREE.GridHelper(1020, 51, 0x67d8cf, 0x67d8cf);
  grid.material.transparent = true; grid.material.opacity = 0.06; grid.position.set(-20, -2.9, 0);
  scene.add(grid);
  const zones = [
    { id: "ground", label: "GROUND SOFTWARE · laptop", x: -380, w: 150, color: 0x2fb3ae },
    { id: "launcher", label: "LAUNCHER GROUND STATION", x: -66, w: 330, color: 0xc47a45 },
    { id: "rocket", label: "ROCKET FLIGHT COMPUTER", x: 318, w: 230, color: 0x67d8cf },
  ];
  for (const z of zones) {
    const pts = [[-z.w / 2, -170], [z.w / 2, -170], [z.w / 2, 170], [-z.w / 2, 170], [-z.w / 2, -170]].map(([x, y]) => new THREE.Vector3(z.x + x, -2.5, y));
    const line = new THREE.Line(new THREE.BufferGeometry().setFromPoints(pts), new THREE.LineDashedMaterial({ color: z.color, dashSize: 6, gapSize: 5, transparent: true, opacity: 0.5 }));
    line.computeLineDistances();
    scene.add(line);
    const tag = label3D(z.label, { className: "css2d-label dim arch-zone" });
    tag.position.set(z.x, 0, 182);
    scene.add(tag);
  }

  const nodeMeshes = new Map();
  const pickables = [];
  const nodeById = new Map(NODES.map((n) => [n.id, n]));
  for (const n of NODES) {
    const group = new THREE.Group();
    group.position.set(...n.pos);
    const count = n.group || 1;
    const meshes = [];
    for (let i = 0; i < count; i++) {
      const [sx, sy, sz] = n.size;
      const geo = new THREE.RoundedBoxGeometry(sx, sy, sz, 3, Math.min(sy, sx, sz) * 0.22);
      let mat;
      if (n.kind === "software") {
        mat = new THREE.MeshStandardMaterial({ color: KIND_COLORS.software, roughness: 0.18, metalness: 0.1, transparent: true, opacity: 0.72, emissive: 0x0b5d63, emissiveIntensity: 0.45 });
      } else {
        mat = clayMaterial({ color: KIND_COLORS[n.kind] ?? 0x5b6b78, bump: 0.7, scale: 0.12 });
      }
      const m = new THREE.Mesh(geo, mat);
      m.castShadow = true; m.receiveShadow = true;
      m.position.y = sy / 2;
      if (count > 1) m.position.z = (i - (count - 1) / 2) * (sz + 8);
      m.userData.nodeId = n.id;
      group.add(m); meshes.push(m); pickables.push(m);
      if (n.kind === "board") {
        // header pins as small clay studs so boards read as boards
        for (let k = 0; k < 10; k++) for (const side of [-1, 1]) {
          const pin = new THREE.Mesh(new THREE.BoxGeometry(2.2, 3, 2.2), clayMaterial({ color: 0x1d1a17, bump: 0.2 }));
          pin.position.set(-sx / 2 + 8 + k * ((sx - 16) / 9), sy + 1.2, side * (sz / 2 - 4));
          group.add(pin);
        }
      }
    }
    const ring = new THREE.Mesh(new THREE.RingGeometry(Math.max(...n.size) * 0.62, Math.max(...n.size) * 0.66 + 2, 48), new THREE.MeshBasicMaterial({ color: 0xe0a274, transparent: true, opacity: 0, side: THREE.DoubleSide }));
    ring.rotation.x = -Math.PI / 2; ring.position.y = -1.8;
    if (count > 1) ring.scale.set(1, 1, 2.2);
    group.add(ring);
    const minor = ["armswitch", "button", "led", "buzzer", "lservo"].includes(n.id);
    const tag = label3D(n.short || n.name, { className: `css2d-label arch-node${minor ? " minor" : ""}` });
    tag.element.style.pointerEvents = "auto";
    tag.element.style.cursor = "pointer";
    tag.element.tabIndex = -1;
    tag.element.addEventListener("click", () => select(n.id));
    tag.position.set(0, n.size[1] + 14, 0);
    group.add(tag);
    scene.add(group);
    nodeMeshes.set(n.id, { group, meshes, ring, tag });
  }

  // Edges
  const edgeObjects = [];
  const resolution = new THREE.Vector2(1, 1);
  for (const e of EDGES) {
    const a = new THREE.Vector3(...nodeById.get(e.from).pos), b = new THREE.Vector3(...nodeById.get(e.to).pos);
    const lift = e.kind === "command" ? 26 : e.kind === "telemetry" ? 14 : 8;
    const offset = e.kind === "command" ? 18 : 0;
    a.y += nodeById.get(e.from).size[1] * 0.6; b.y += nodeById.get(e.to).size[1] * 0.6;
    const dir = new THREE.Vector3().subVectors(b, a);
    const side = new THREE.Vector3(-dir.z, 0, dir.x).normalize().multiplyScalar(offset);
    const mid = a.clone().add(b).multiplyScalar(0.5).add(new THREE.Vector3(0, lift + dir.length() * 0.08, 0)).add(side);
    const curve = new THREE.QuadraticBezierCurve3(a.clone().add(side), mid, b.clone().add(side));
    const pts = curve.getPoints(48);
    const geo = new THREE.LineGeometry();
    geo.setPositions(pts.flatMap((p) => [p.x, p.y, p.z]));
    const style = {
      telemetry: { color: 0x67d8cf, linewidth: 2.4, dashed: false, opacity: 0.9 },
      input: { color: 0xe0a274, linewidth: 1.6, dashed: false, opacity: 0.75 },
      indicator: { color: 0x8fa2ad, linewidth: 1.2, dashed: false, opacity: 0.6 },
      files: { color: 0xf1e9d6, linewidth: 1.4, dashed: true, dashSize: 3, gapSize: 4, opacity: 0.7 },
      command: { color: 0xc47a45, linewidth: 1.6, dashed: true, dashSize: 7, gapSize: 6, opacity: 0.8 },
    }[e.kind];
    const mat = new THREE.LineMaterial({ color: style.color, linewidth: style.linewidth, dashed: style.dashed, dashSize: style.dashSize || 1, gapSize: style.gapSize || 1, transparent: true, opacity: style.opacity, worldUnits: false });
    mat.resolution = resolution;
    const line = new THREE.Line2(geo, mat);
    line.computeLineDistances();
    scene.add(line);
    let tag = null;
    if (e.kind === "telemetry" || e.kind === "command" || e.kind === "files") {
      tag = label3D(e.label, { className: `css2d-label arch-edge arch-edge-${e.kind}` });
      tag.position.copy(curve.getPoint(e.kind === "command" ? 0.3 : 0.55)).add(e.kind === "command" ? side.clone().multiplyScalar(1.4) : new THREE.Vector3(0, 6, -10));
      if (e.unit) { tag.element.style.pointerEvents = "auto"; tag.element.style.cursor = "pointer"; tag.element.addEventListener("click", () => selectUnitEdge(e)); }
      scene.add(tag);
    }
    edgeObjects.push({ e, curve, line, tag });
  }

  // Telemetry pulses
  const pulseGroup = new THREE.Group();
  scene.add(pulseGroup);
  const pulses = [];
  for (const eo of edgeObjects.filter((x) => x.e.kind === "telemetry")) {
    const types = eo.e.packets;
    const n = eo.e.id === "link" || eo.e.id === "uart" ? 6 : 3;
    for (let i = 0; i < n; i++) {
      const type = types[i % types.length];
      const m = new THREE.Mesh(new THREE.SphereGeometry(eo.e.id === "link" || eo.e.id === "uart" ? 3.2 : 2.2, 12, 10), new THREE.MeshBasicMaterial({ color: PACKET_COLORS[type] ?? 0x67d8cf }));
      pulseGroup.add(m);
      pulses.push({ mesh: m, curve: eo.curve, phase: i / n, speed: eo.e.id === "status-copy" ? 0.28 : 0.38, type });
    }
  }

  let animate = !reducedMotion();
  let selected = null;

  function selectUnitEdge(e) {
    selected = null;
    dirty = true;
    for (const nm of nodeMeshes.values()) nm.ring.material.opacity = 0;
    renderInspector({ id: e.id, name: e.unit === "LINK" ? "Dashboard Wi-Fi/UDP link" : "Launcher–rocket UART", kind: "link", iface: e.label,
      duties: e.unit === "LINK" ? ["Carries T, STATUS, and ENV to the dashboard and commands from it", "No sequence number or boot identifier in the protocol"] : ["Carries rocket DATA, LOG, and CMD_REJECT lines to the launcher and commands to the rocket"],
      sources: ["docs/WIRING.md", "docs/PROTOCOL.md", "protocol/project33_protocol.json"], gates: e.unit === "LINK" ? ["G-03", "G-06"] : ["G-02", "G-03"], units: [e.unit] });
    announce(`Selected link ${e.label}`);
  }

  function select(id) {
    selected = id;
    dirty = true;
    for (const [nid, nm] of nodeMeshes) nm.ring.material.opacity = nid === id ? 0.95 : 0;
    const node = nodeById.get(id);
    renderInspector(node);
    for (const b of nodeList.querySelectorAll("button")) b.setAttribute("aria-pressed", String(b.dataset.node === id));
    announce(`Selected ${node.name}`);
  }

  function renderInspector(node) {
    const unitIds = node.units || [];
    const channels = groundStatus.channels.filter((c) => unitIds.some((u) => c.requires.includes(u)));
    const caps = groundStatus.capabilities.filter((c) => unitIds.some((u) => c.requires.includes(u)));
    const gates = (node.gates || []).map((g) => gateById.get(g)).filter(Boolean);
    clear(inspector,
      h("div", { class: "panel-head" }, h("h4", {}, "Node inspector"), categoryBadge("research")),
      h("div", { class: "panel-body arch-inspect", "data-selected": node.id },
        h("h3", {}, node.name),
        h("p", { class: "label" }, node.kind === "software" ? "Ground software" : node.kind === "link" ? "Communication link" : `${node.kind} · ${node.zone ?? ""}`),
        h("dl", { class: "kv" }, h("dt", {}, "Interface"), h("dd", {}, node.iface)),
        h("div", { class: "divider-label" }, h("span", { class: "label" }, "Documented responsibilities")),
        h("ul", { class: "arch-list" }, node.duties.map((d) => h("li", {}, d))),
        h("div", { class: "divider-label" }, h("span", { class: "label" }, "Source references")),
        h("ul", { class: "arch-src" }, node.sources.map((s) => h("li", {}, h("a", { class: "src", href: s.endsWith(".md") ? docLink(s) : repoLink(s), target: "_blank", rel: "noopener" }, s)))),
        h("div", { class: "divider-label" }, h("span", { class: "label" }, `Safety gates (${gates.length})`)),
        gates.length ? h("ul", { class: "arch-gates" }, gates.map((g) => h("li", {}, h("b", { class: "mono" }, g.id), " ", h("span", {}, g.gate), h("small", {}, g.behavior))))
          : h("p", { class: "muted" }, "No gate in evidence/safety_gates.json is implemented by this node."),
        unitIds.length ? [
          h("div", { class: "divider-label" }, h("span", { class: "label" }, `Ground-status unit ${unitIds.join(", ")}`)),
          h("p", { class: "muted small" }, "From protocol/ground_status_model.json — what stops being observable if this unit fails:"),
          h("ul", { class: "arch-deps" },
            channels.map((c) => h("li", {}, h("span", { class: "dep-kind" }, "channel"), " ", c.name)),
            caps.map((c) => h("li", { class: c.safety ? "safety" : "" }, h("span", { class: "dep-kind" }, c.safety ? "safety capability" : "capability"), " ", c.name))),
        ] : null,
        node.id === "rocket" || node.id === "launcher" ? [
          h("div", { class: "divider-label" }, h("span", { class: "label" }, "Capabilities the system does not have")),
          h("ul", { class: "arch-deps absent" }, groundStatus.absent_capabilities.map((c) => h("li", {}, c.name, h("small", {}, c.why)))),
        ] : null,
        node.id === "uart" || node.id === "link" || node.id === "launcher" ? h("p", { class: "small" }, "Clock domains: ", h("a", { href: discrepancyLink("D-018") }, "D-018"), " — T packets carry launcher relay time; LOG rows carry rocket time.") : null,
      ));
  }

  // Inspection only: each entry opens the inspector for a node. None of them controls anything.
  nodeList.append(...NODES.map((n) => h("button", { class: "btn ghost", type: "button", "data-node": n.id, "aria-pressed": "false", onclick: () => select(n.id) }, h("span", { class: "insp" }, "Inspect · "), n.name)));

  // Picking
  const ray = new THREE.Raycaster();
  const ndc = new THREE.Vector2();
  let down = null;
  renderer.domElement.addEventListener("pointerdown", (ev) => { down = [ev.clientX, ev.clientY]; });
  renderer.domElement.addEventListener("pointerup", (ev) => {
    if (!down || Math.hypot(ev.clientX - down[0], ev.clientY - down[1]) > 5) return;
    const r = renderer.domElement.getBoundingClientRect();
    ndc.set(((ev.clientX - r.left) / r.width) * 2 - 1, -((ev.clientY - r.top) / r.height) * 2 + 1);
    ray.setFromCamera(ndc, rig.camera);
    const hit = ray.intersectObjects(pickables, false)[0];
    if (hit) select(hit.object.userData.nodeId);
  });

  autoResize(viewport, renderer, labels, rig, (w, hh) => resolution.set(w, hh));
  const box = new THREE.Box3(new THREE.Vector3(-470, 0, -200), new THREE.Vector3(440, 40, 200));
  const HOME_DIR = new THREE.Vector3(0, 1.75, 0.72);
  rig.frame(box, HOME_DIR, { animate: false, margin: 1.02 });

  // Toggles
  const pulseBtn = toggles.pulses, cmdBtn = toggles.commands;
  pulseBtn.setAttribute("aria-pressed", String(animate));
  pulseBtn.addEventListener("click", () => { animate = !animate; pulseBtn.setAttribute("aria-pressed", String(animate)); pulseGroup.visible = animate; announce(animate ? "Telemetry pulses running" : "Telemetry pulses paused"); });
  pulseGroup.visible = animate;
  cmdBtn.addEventListener("click", () => {
    const on = cmdBtn.getAttribute("aria-pressed") !== "true";
    cmdBtn.setAttribute("aria-pressed", String(on));
    for (const eo of edgeObjects) if (eo.e.kind === "command") { eo.line.visible = on; if (eo.tag) eo.tag.visible = on; }
  });
  toggles.reset.addEventListener("click", () => rig.frame(box, HOME_DIR, { margin: 1.02 }));

  let t = 0, lastFrame = 0, dirty = true;
  rig.controls.addEventListener("change", () => { dirty = true; });
  const markDirty = () => { dirty = true; };
  for (const b of [toggles.pulses, toggles.commands, toggles.reset]) b.addEventListener("click", markDirty);
  nodeList.addEventListener("click", markDirty);
  renderer.domElement.addEventListener("pointerup", markDirty);
  // Compile shaders off the main thread where the browser supports it, then render.
  let compiled = false;
  viewport.dataset.compiled = "false";
  Promise.resolve(renderer.compileAsync ? renderer.compileAsync(scene, rig.camera) : null).catch(() => {}).finally(() => { compiled = true; dirty = true; viewport.dataset.compiled = "true"; });
  loop((now) => {
    if (!compiled || !onScreen || document.hidden) { lastFrame = now; return; }
    if (now - lastFrame < 40) return; // ≤25 fps is plenty for a schematic
    const step = Math.min((now - lastFrame) / 1000, 0.1);
    lastFrame = now;
    const moving = !!rig.tween;
    if (animate) { t += step; dirty = true; }
    if (moving) dirty = true;
    for (const p of pulses) {
      const u = (p.phase + t * p.speed) % 1;
      p.mesh.position.copy(p.curve.getPoint(u));
    }
    rig.update(now);
    if (!dirty) return;
    dirty = false;
    renderer.render(scene, rig.camera);
    labels.render(scene, rig.camera);
  });
  select("launcher");
  return { select, scene, state: () => ({ selected, animate }) };
}
