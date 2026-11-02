// Materials for the laboratory's five renderings of the same geometry:
// CLAY (handcrafted, stop-motion), SOLID CAD, WIREFRAME (display tessellation),
// BLUEPRINT (feature edges with hidden lines), and X-RAY. Plus section hatching.
// The clay shader also carries the cinematic "scan" that turns clay into linework.
import { THREE } from "./three-kit.js";

const NOISE_GLSL = /* glsl */`
float p33hash(vec3 p) { p = fract(p * 0.3183099 + 0.1); p *= 17.0; return fract(p.x * p.y * p.z * (p.x + p.y + p.z)); }
float p33noise(vec3 x) {
  vec3 i = floor(x); vec3 f = fract(x); f = f * f * (3.0 - 2.0 * f);
  return mix(mix(mix(p33hash(i), p33hash(i + vec3(1,0,0)), f.x), mix(p33hash(i + vec3(0,1,0)), p33hash(i + vec3(1,1,0)), f.x), f.y),
             mix(mix(p33hash(i + vec3(0,0,1)), p33hash(i + vec3(1,0,1)), f.x), mix(p33hash(i + vec3(0,1,1)), p33hash(i + vec3(1,1,1)), f.x), f.y), f.z);
}
float p33fbm(vec3 p) { float a = 0.5, s = 0.0; for (int i = 0; i < 4; i++) { s += a * p33noise(p); p *= 2.07; a *= 0.5; } return s; }
`;

/**
 * Handcrafted clay. Object-space noise so the surface does not swim when parts move.
 * uniforms: uStep (stop-motion frame index), uBoil (mm of per-frame jitter), uScan* (scan reveal).
 */
export function clayMaterial({ color = 0xc9a27e, bump = 0.9, scale = 0.09, boil = 0.0, roughness = 0.86 } = {}) {
  const material = new THREE.MeshStandardMaterial({ color, roughness, metalness: 0.0 });
  const uniforms = {
    uStep: { value: 0 }, uBoil: { value: boil }, uBump: { value: bump }, uClayScale: { value: scale },
    uScanOn: { value: 0 }, uScanOrigin: { value: new THREE.Vector3() }, uScanDir: { value: new THREE.Vector3(1, 0, 0) },
    uScanGlow: { value: new THREE.Color(0x67d8cf) }, uScanWidth: { value: 18 },
  };
  material.userData.uniforms = uniforms;
  material.onBeforeCompile = (shader) => {
    Object.assign(shader.uniforms, uniforms);
    shader.vertexShader = shader.vertexShader
      .replace("#include <common>", `#include <common>\n${NOISE_GLSL}\nuniform float uStep; uniform float uBoil; uniform float uClayScale;\nvarying vec3 vClayPos; varying vec3 vScanWorld;`)
      .replace("#include <begin_vertex>", `#include <begin_vertex>
        vClayPos = position;
        if (uBoil > 0.0) { transformed += normal * uBoil * (p33noise(position * uClayScale * 1.7 + vec3(uStep * 7.13, uStep * 3.71, uStep * 5.37)) - 0.5); }`)
      .replace("#include <worldpos_vertex>", `#include <worldpos_vertex>\n vScanWorld = (modelMatrix * vec4(transformed, 1.0)).xyz;`);
    shader.fragmentShader = shader.fragmentShader
      .replace("#include <common>", `#include <common>\n${NOISE_GLSL}
        uniform float uBump; uniform float uClayScale; uniform float uScanOn; uniform vec3 uScanOrigin; uniform vec3 uScanDir; uniform vec3 uScanGlow; uniform float uScanWidth;
        varying vec3 vClayPos; varying vec3 vScanWorld;
        vec3 p33perturb(vec3 surf_pos, vec3 surf_norm, vec2 dHdxy, float faceDir) {
          vec3 sx = normalize(dFdx(surf_pos)); vec3 sy = normalize(dFdy(surf_pos));
          vec3 r1 = cross(sy, surf_norm); vec3 r2 = cross(surf_norm, sx);
          float det = dot(sx, r1) * faceDir;
          vec3 g = sign(det) * (dHdxy.x * r1 + dHdxy.y * r2);
          return normalize(abs(det) * surf_norm - g);
        }`)
      .replace("#include <clipping_planes_fragment>", `#include <clipping_planes_fragment>
        float p33scan = dot(vScanWorld - uScanOrigin, uScanDir);
        if (uScanOn > 0.5 && p33scan < 0.0) discard;`)
      .replace("#include <color_fragment>", `#include <color_fragment>
        vec3 p33cp = vClayPos * uClayScale;
        float p33n = p33fbm(p33cp);
        float p33streak = p33noise(vec3(p33cp.x * 0.6, p33cp.y * 6.0, p33cp.z * 0.6));
        diffuseColor.rgb *= 0.86 + 0.22 * p33n - 0.05 * p33streak;`)
      .replace("#include <roughnessmap_fragment>", `#include <roughnessmap_fragment>\n roughnessFactor = clamp(roughnessFactor + 0.12 * (p33n - 0.5), 0.55, 1.0);`)
      .replace("#include <normal_fragment_maps>", `#include <normal_fragment_maps>
        float p33h = p33fbm(p33cp * 2.3) + 0.35 * sin(length(p33cp.xz * 7.0 + p33n * 3.0) * 6.0) * p33noise(p33cp * 0.7);
        normal = p33perturb(-vViewPosition, normal, vec2(dFdx(p33h), dFdy(p33h)) * uBump, faceDirection);`)
      .replace("#include <emissivemap_fragment>", `#include <emissivemap_fragment>
        if (uScanOn > 0.5) { totalEmissiveRadiance += uScanGlow * 2.2 * (1.0 - smoothstep(0.0, uScanWidth, p33scan)); }`);
  };
  material.customProgramCacheKey = () => "p33-clay-v1";
  return material;
}

/** Satin CAD solid. */
export function solidMaterial(color = 0x9fb3bf, { metalness = 0.15, roughness = 0.42 } = {}) {
  return new THREE.MeshStandardMaterial({ color, metalness, roughness, side: THREE.FrontSide });
}

/** Fresnel x-ray: silhouettes glow, interiors stay visible. Respects clipping planes. */
export function xrayMaterial(color = 0x67d8cf) {
  return new THREE.ShaderMaterial({
    uniforms: { uColor: { value: new THREE.Color(color) }, uBase: { value: 0.05 } },
    vertexShader: /* glsl */`
      #include <common>
      #include <clipping_planes_pars_vertex>
      varying vec3 vN; varying vec3 vV;
      void main() {
        #include <begin_vertex>
        #include <project_vertex>
        #include <clipping_planes_vertex>
        vN = normalize(normalMatrix * normal);
        vV = normalize(-mvPosition.xyz);
      }`,
    fragmentShader: /* glsl */`
      #include <common>
      #include <clipping_planes_pars_fragment>
      uniform vec3 uColor; uniform float uBase;
      varying vec3 vN; varying vec3 vV;
      void main() {
        #include <clipping_planes_fragment>
        float f = pow(1.0 - abs(dot(normalize(vN), normalize(vV))), 2.4);
        gl_FragColor = vec4(uColor * (uBase + f * 1.25), uBase + f * 0.85);
      }`,
    transparent: true, depthWrite: false, side: THREE.DoubleSide, blending: THREE.AdditiveBlending, clipping: true,
  });
}

/** Back faces exposed by a section plane, drawn with engineering section hatching. */
export function sectionHatchMaterial(color = 0xc47a45) {
  return new THREE.ShaderMaterial({
    uniforms: { uColor: { value: new THREE.Color(color) } },
    vertexShader: /* glsl */`
      #include <common>
      #include <clipping_planes_pars_vertex>
      void main() {
        #include <begin_vertex>
        #include <project_vertex>
        #include <clipping_planes_vertex>
      }`,
    fragmentShader: /* glsl */`
      #include <common>
      #include <clipping_planes_pars_fragment>
      uniform vec3 uColor;
      void main() {
        #include <clipping_planes_fragment>
        float s = mod(gl_FragCoord.x + gl_FragCoord.y, 9.0);
        float line = step(s, 1.6);
        gl_FragColor = vec4(mix(uColor * 0.32, uColor * 1.1, line), 1.0);
      }`,
    side: THREE.BackSide, clipping: true,
  });
}

export function edgeMaterial(color = 0xeef6f8, opacity = 1) {
  return new THREE.LineBasicMaterial({ color, transparent: opacity < 1, opacity });
}

export function hiddenEdgeMaterial(color = 0x67d8cf) {
  const m = new THREE.LineDashedMaterial({ color, dashSize: 1.6, gapSize: 1.2, transparent: true, opacity: 0.38, depthWrite: false });
  m.depthFunc = THREE.GreaterDepth;
  return m;
}

export function blueprintFillMaterial() {
  return new THREE.MeshBasicMaterial({ color: 0x0a1a28, transparent: true, opacity: 0.55, polygonOffset: true, polygonOffsetFactor: 1, polygonOffsetUnits: 1 });
}

/**
 * Build every representation of one part from a single geometry. The returned group
 * holds children tagged by role; setMode() shows the ones each rendering needs.
 * edgePositions: optional Float32Array of line-segment endpoints (true CAD edges).
 */
export function partVisuals(geometry, { color = 0x9fb3bf, clayColor = 0xc9a27e, edgePositions = null, edgeThreshold = 24, clay } = {}) {
  geometry.computeBoundingBox();
  if (!geometry.attributes.normal) geometry.computeVertexNormals();
  const group = new THREE.Group();
  const solid = new THREE.Mesh(geometry, solidMaterial(color));
  solid.userData.role = "solid"; solid.castShadow = true; solid.receiveShadow = true;
  const clayMesh = new THREE.Mesh(geometry, clay || clayMaterial({ color: clayColor }));
  clayMesh.userData.role = "clay"; clayMesh.castShadow = true; clayMesh.receiveShadow = true;
  const fill = new THREE.Mesh(geometry, blueprintFillMaterial());
  fill.userData.role = "fill";
  const xray = new THREE.Mesh(geometry, xrayMaterial());
  xray.userData.role = "xray"; xray.renderOrder = 2;
  const wire = new THREE.LineSegments(new THREE.WireframeGeometry(geometry), edgeMaterial(0x67d8cf, 0.5));
  wire.userData.role = "wire";
  let edgeGeom;
  if (edgePositions) {
    edgeGeom = new THREE.BufferGeometry();
    edgeGeom.setAttribute("position", new THREE.BufferAttribute(edgePositions, 3));
  } else {
    edgeGeom = new THREE.EdgesGeometry(geometry, edgeThreshold);
  }
  const edges = new THREE.LineSegments(edgeGeom, edgeMaterial(0xeef6f8));
  edges.userData.role = "edges";
  const hidden = new THREE.LineSegments(edgeGeom, hiddenEdgeMaterial());
  hidden.computeLineDistances();
  hidden.userData.role = "hidden"; hidden.renderOrder = 3;
  const hatch = new THREE.Mesh(geometry, sectionHatchMaterial());
  hatch.userData.role = "hatch";
  group.add(solid, clayMesh, fill, xray, wire, edges, hidden, hatch);
  group.userData.visuals = { solid, clay: clayMesh, fill, xray, wire, edges, hidden, hatch };
  return group;
}

export const MODES = {
  clay: ["clay", "hatch"],
  solid: ["solid", "edgesFaint", "hatch"],
  wireframe: ["wire"],
  blueprint: ["fill", "edges", "hidden", "hatch"],
  xray: ["xray", "edgesFaint"],
};

/** Show the representations a rendering mode needs; apply clipping planes to all. */
export function applyMode(group, mode, { clipping = [], ghost = false, highlight = false } = {}) {
  const v = group.userData.visuals;
  if (!v) return;
  const roles = MODES[mode] || MODES.solid;
  const faint = roles.includes("edgesFaint");
  for (const [role, obj] of Object.entries(v)) {
    let visible = roles.includes(role) || (role === "edges" && faint);
    if (role === "hatch") visible = visible && clipping.length > 0;
    obj.visible = visible;
    const mats = Array.isArray(obj.material) ? obj.material : [obj.material];
    for (const m of mats) {
      // Three.js recompiles automatically when the number of clipping planes changes;
      // only a change of the transparent flag needs an explicit update.
      const wasTransparent = m.transparent;
      m.clippingPlanes = clipping.length ? clipping : null;
      if (role === "edges") { m.opacity = faint ? 0.35 : 1; m.transparent = faint || ghost; m.color.set(highlight ? 0xe0a274 : 0xeef6f8); }
      if (role === "solid" || role === "clay") {
        m.transparent = ghost; m.opacity = ghost ? 0.12 : 1; m.depthWrite = !ghost;
        if (m.emissive) m.emissive.set(highlight ? 0x3a1e0c : 0x000000);
      }
      if (role === "fill") { m.opacity = ghost ? 0.08 : 0.55; m.color.set(highlight ? 0x2a1a10 : 0x0a1a28); }
      if (role === "xray") m.uniforms.uColor.value.set(highlight ? 0xe0a274 : 0x67d8cf);
      if (wasTransparent !== m.transparent) m.needsUpdate = true;
    }
  }
}
