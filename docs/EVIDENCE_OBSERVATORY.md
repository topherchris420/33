# Evidence Observatory

Project 33's review workflow answers four questions: what is being claimed, which
exact files support it, what those files cannot establish, and which claims need
another review after evidence changes. It operates on local files and never
opens a command or hardware connection.

The catalog currently traces eight claims to 32 artifacts. There are no declared
physical artifacts. C2, C6, C7, and C8 carry explicit unresolved questions; the
remaining claims have limited analytical or software support, not a physical
validation verdict. The classifications and scientific interpretation are
authored declarations that still require independent review.

## Build a Portable Review

Run from the repository root with Python 3.11 or later. No packages are required.

```bash
python -m evidence build --output build/review
python -m evidence verify build/review
```

Open `build/review/index.html`. The report works without a server, internet access,
or JavaScript; JavaScript adds search and filters. The equivalent Make target is
`make review`. Existing outputs are never overwritten; choose a new directory for
the next review, such as `make review REVIEW_OUTPUT=build/review-02`.

| Bundle file | Meaning |
|---|---|
| `index.html` | Searchable claim explorer with limitations and source links |
| `assessment.json` | Structured artifact observations and authored claim records |
| `catalog.json` | Exact input catalog |
| `artifacts/` | Byte-for-byte copies of all referenced artifacts |
| `reviewer/evidence/` | Included standard-library reviewer implementation |
| `manifest.json` | SHA-256, byte count, and relative path for every included file |
| `manifest.sha256` | Digest of the manifest itself |
| `README.txt` | Verification instructions and interpretation boundary |

For a standalone check, enter the bundle's `reviewer` directory and run
`python -B -m evidence verify ..`. For independent review, prefer the verifier from
a trusted checkout. Pin the manifest digest through an independently trusted
channel when identity matters:

```bash
python -m evidence verify build/review --expected-sha256 YOUR_TRUSTED_DIGEST
```

Hashes detect changes relative to that reference; they do not authenticate an
author. Anyone can replace both a manifest and its accompanying digest. A valid
bundle is not a signature, a qualification result, or a readiness approval.

## Trace the Effect of a Change

```bash
python -m evidence compare build/review build/review-02
```

Both bundles are verified before comparison. The output identifies changed source
bytes, changed artifact classifications/descriptions, and the affected claim IDs.
Claim wording and assumption changes also trigger review even when the underlying
files are identical. Changes to the overall scope or the included reviewer code
mark all claims for another review. This compares evidence dependencies, not
physical performance.

## Audit a Captured Session

Close the dashboard before auditing so the capture is complete. Use its existing
CSV directly:

```bash
python -m evidence audit Firmware/TestSessions/bench_EXAMPLE/telemetry.csv \
  --origin bench --gap-ms 500 --output build/session-review
python -m evidence verify build/session-review
```

Open `build/session-review/index.html`. The original CSV is included unchanged,
along with `audit.json`, the portable verifier, and a manifest. The origin defaults
to `unknown`; `bench` and `synthetic` are explicit operator declarations, not
automatically established facts. A declared bench origin does not promote a
research claim to physically validated status.

| Check | Interpretation |
|---|---|
| Non-finite or malformed sample | Error; recorded and excluded, never replaced with zero |
| Device timestamp outside unsigned 32-bit integer range | Error |
| Receive timestamp missing its timezone | Error |
| Same device timestamp with different sample values | Error; conflicting evidence |
| Exact repeated sample at the same timestamp within a stream segment | Warning; retained and counted |
| Decreasing device timestamp | Warning; starts a new segment without guessing reset, reorder, or rollover |
| Positive interval above the chosen threshold | Warning; does not imply a packet-loss count |
| Empty capture / no valid telemetry | Error |
| Missing or malformed CSV columns | Input error; no partial bundle published |

Streams are separated by both `source` and `message_type`. `T` packets and recovered
`LOG` rows never share timing statistics. Valid sample counts retain duplicates;
positive-interval statistics use successive valid samples within a segment.
Invalid rows can therefore span a measured interval. `STATUS`, `ENV`, and `RAW`
rows have their receive timestamp checked, but their payload values are not
numerically audited. Findings retain accurate totals; detailed row locations are
limited to the first 100 findings.

The current protocol contains no sequence number or boot identity. This tool
cannot recover either fact from timestamps and cannot establish true packet loss,
elapsed time across a clock regression, or physical test completion.

## Try the Synthetic Fault Example

```bash
python -m evidence demo --output build/demo
python -m evidence verify build/demo/review
```

The eight-row fixture deliberately contains one duplicate, one non-finite sample,
one gap, one clock regression, and separate live/recovered streams. Its expected
quality is `error`. The demo succeeds when it creates that illustrative bundle;
it is never counted as physical evidence. No random seed, network, GUI, or hardware
is needed to reproduce the example.

## Command Results and Input Contract

| Exit code | Meaning |
|---|---|
| `0` | Command completed; an audit may still contain warnings |
| `1` | Audit produced a report containing data-quality errors |
| `2` | Invalid input, failed integrity verification, or an existing output directory |

Build success means the referenced files exist and pass their declared structural
checks. It does **not** mean all claims are resolved. JSON output contains the
unresolved count, and each report keeps the gaps visible. JSON/CSV schema errors,
duplicate IDs or keys, unknown references, path traversal, symlink inputs, missing
files, and non-finite JSON values are rejected. Inputs are limited to 64 MiB per
file and 250,000 CSV data rows. Catalogs allow at most 1,000 claims and 1,000
artifacts. The verifier also rejects extra unlisted files; Python bytecode cache
files are ignored because running the included verifier can create them.

The catalog is [evidence/catalog.json](../evidence/catalog.json). CSV artifacts
must declare their columns and minimum row count. A zero minimum is intentional
for the C7 failure-only log: the report displays zero rows and its denominator
limitation. Model outputs are not recomputed by this command, and file hashes do
not prove that a particular program generated a particular output.

## Reproducibility and CI

For identical inputs, reviewer code, Python version, commit, and working-tree
state, report and manifest bytes are deterministic. There is no generated wall
clock timestamp or machine-specific absolute path. Provenance records the current
commit and whether the source tree contains changes; the manifest captures the
actual file bytes even when the tree is dirty.

The `Portable evidence review` CI job uses only Python's standard library. It
snapshots committed artifacts independently of the numerical-model job so model
regeneration cannot silently substitute for committed evidence. Download the
`project33-evidence-<commit>` artifact from the workflow run to inspect both the
claim review and synthetic telemetry example. Retention is 30 days.

Regression tests cover deterministic builds, relocated/offline verification,
tampering, source symlinks, malformed inputs, HTML escaping, evidence-change
mapping, stream separation, invalid numerics, clock ambiguity, and the synthetic
example's exact findings.
