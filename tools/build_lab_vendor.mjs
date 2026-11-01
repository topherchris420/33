// Rebuild lab/lib/three-lab.min.js: three.js plus the few addons the laboratory uses,
// as one ES module so the static site needs no import map or CDN.
//
//   npm install --no-save three@0.186.1 esbuild@0.25.10
//   node tools/build_lab_vendor.mjs
//
// The output is committed; its SHA-256 and the exact versions are recorded in
// lab/lib/README.md. three.js is MIT licensed (lab/lib/LICENSE-three.txt).
import { build } from "esbuild";
import { writeFileSync, mkdirSync } from "node:fs";
import { dirname, join } from "node:path";
import { fileURLToPath } from "node:url";

const root = join(dirname(fileURLToPath(import.meta.url)), "..");
const entry = `
export * from "three";
export { OrbitControls } from "three/addons/controls/OrbitControls.js";
export { RoomEnvironment } from "three/addons/environments/RoomEnvironment.js";
export { CSS2DRenderer, CSS2DObject } from "three/addons/renderers/CSS2DRenderer.js";
export { mergeVertices, mergeGeometries } from "three/addons/utils/BufferGeometryUtils.js";
export { RoundedBoxGeometry } from "three/addons/geometries/RoundedBoxGeometry.js";
export { Line2 } from "three/addons/lines/Line2.js";
export { LineGeometry } from "three/addons/lines/LineGeometry.js";
export { LineMaterial } from "three/addons/lines/LineMaterial.js";
export { LineSegments2 } from "three/addons/lines/LineSegments2.js";
export { LineSegmentsGeometry } from "three/addons/lines/LineSegmentsGeometry.js";
export { EffectComposer } from "three/addons/postprocessing/EffectComposer.js";
export { RenderPass } from "three/addons/postprocessing/RenderPass.js";
export { UnrealBloomPass } from "three/addons/postprocessing/UnrealBloomPass.js";
export { OutputPass } from "three/addons/postprocessing/OutputPass.js";
`;
mkdirSync(join(root, "lab/lib"), { recursive: true });
const result = await build({
  stdin: { contents: entry, resolveDir: process.cwd(), loader: "js" },
  bundle: true, minify: true, format: "esm", target: "es2020",
  legalComments: "inline", write: false,
});
writeFileSync(join(root, "lab/lib/three-lab.min.js"), result.outputFiles[0].contents);
console.log("wrote lab/lib/three-lab.min.js", result.outputFiles[0].contents.length, "bytes");
