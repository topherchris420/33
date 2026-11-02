# Vendored libraries

The laboratory is a static site with no build step and no CDN dependency. These files are
committed exactly as produced below; `tests/test_lab_data.py` checks the digests.

| File | Source | Licence | SHA-256 |
|---|---|---|---|
| `three-lab.min.js` | three.js 0.186.1 plus the addons listed in `tools/build_lab_vendor.mjs`, bundled with esbuild 0.25.10 | MIT (`LICENSE-three.txt`) | `07fe0fd24ff12f159522d4f6b9a1c0b5a2e4ec84a01008edccc07b81fa56c822` |
| `katex/katex.mjs`, `katex/katex.min.css`, `katex/fonts/*.woff2` | KaTeX 0.16.22 `dist/` | MIT (`katex/LICENSE`) | `7af1aa5e484a4ae881e181ff97ddffdce2deabef42596d2679658b9fe4cd4615` (mjs) |
| `fonts/fraunces-latin-full-*.woff2` | `@fontsource-variable/fraunces` 5.3.0 | SIL OFL 1.1 (`fonts/LICENSE-Fraunces-OFL.txt`) | — |
| `fonts/ibm-plex-*.woff2` | `@fontsource/ibm-plex-sans` and `@fontsource/ibm-plex-mono` 5.3.0 | SIL OFL 1.1 (`fonts/LICENSE-IBM-Plex-OFL.txt`) | — |

Rebuild the three.js bundle with:

```bash
npm install --no-save three@0.186.1 esbuild@0.25.10
node tools/build_lab_vendor.mjs
```
