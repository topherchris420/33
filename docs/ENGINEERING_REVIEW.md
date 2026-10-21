# Engineering review: define a testable product

**Disposition: the review tooling is useful; the hardware design is not complete.**
This is an engineering assessment of the inert educational testbed, not a completed
redesign or a company review. The current release cannot demonstrate its physical
claims. Improving documentation and builds does not resolve that limitation.

The recommended next product is a stationary, instrumented educational
demonstrator with recorded observations. Its intended user must be able to tell
which specimen was observed, what an instrument actually measured, what was
commanded, and what remains unknown. Operational propulsion, flight and targeting
are outside this design scope, consistent with [Paper Alignment](PAPER_ALIGNMENT.md).

## Decisions that precede another hardware revision

| Decision | Why the current record is insufficient | Reviewable outcome |
|---|---|---|
| Define the intended demonstration | The request mixes electrical timing, mechanical completion, material properties and system tracking. They are different functions with different evidence needs. | One bounded statement of intended use, environment and observable outcome for each demonstration. |
| Establish one configuration baseline | CAD, model assumptions and the BOM describe different configurations (D-005, D-010, D-021). | A revision-controlled list of specimen/part identifiers, drawings, material sources and software revisions, with unknowns explicitly recorded. |
| Validate each requirement | A numerical target alone does not establish that the right property is being specified. | Each requirement identifies the quantity, units, conditions, tolerance, verification method and source of the limit. |
| Establish measurement provenance | Commanded state and telemetry estimates are being asked to stand in for independent physical observations. | Recorded instrument identity, calibration status, timebase, uncertainty, raw observations and acceptance responsibility. |
| Separate software verification from hardware acceptance | Passing tests currently establishes several software facts but no accepted physical measurements. | Separate decisions for software review completeness and each physical claim, with explicit evidence references. |

This ordering follows the distinction between requirements, design definition,
verification and validation in the public [NASA Systems Engineering Handbook](https://www.nasa.gov/reference/4-0-system-design-processes/).
Configuration control makes it possible to determine which design a result
actually describes; see [NASA configuration management guidance](https://www.nasa.gov/reference/6-5-configuration-management/).
These references supply a review framework, not agency or company approval.

## Findings that must remain visible

The [readiness assessment](RELEASE_READINESS.md) contains the underlying values
and artifact references. The engineering implications are:

- **C1:** the current modeled linkage cannot assemble. A report claiming a
  closed physical state would contradict the current inputs. Model closure,
  tolerance compatibility and physical locking are distinct questions.
- **C6:** the spring calculation needs dimensional review before its numerical
  margin can be interpreted. Selecting a larger number is not a characterized
  component or a validated load model.
- **C8:** material modulus, section stiffness and mass are different quantities.
  Changing density cannot resolve a requirement on elastic modulus.
- **C5:** the independent calculations and saved simulation do not establish a
  common, traceable configuration. A cached result is not independent validation
  of the current geometry.
- **C7:** a simulation whose success condition cannot fail is not a useful
  discriminator of design reliability. Repeated software success does not supply
  physical reliability evidence.
- **Measurement coverage:** P-001 concerns an electrical timing observation;
  it does not measure completion of mechanical motion. P-003 is exploratory,
  and P-006 is not registered. There is no basis for assigning their requested
  physical pass results.

None of these findings has been closed by this review.

## Recommended review sequence

1. Review intended use and requirements for the stationary demonstrator. Record
   any requirement changes and their rationale before collecting results.
2. Review the selected configuration and the sources of its inputs. Keep
   alternatives as proposed configurations until a responsible engineer adopts
   one; retain the earlier records.
3. Review an inert measurement plan against that exact configuration. Define
   what the observation can establish and how uncertainty and incomplete data
   will affect the decision. Review expected failure conditions as well as the
   nominal demonstration.
4. Have a qualified person perform and document the approved physical work.
   Preserve raw data and discrepancies; obtain an independent review of each
   applicable claim.
5. Decide readiness only for the demonstrated scope. A stationary demonstration
   does not establish flight or field readiness.

The next useful milestone is one independently accepted physical observation
of a defined specimen. A global “100% verified” label would hide the missing
design and measurement work.

The [bench configuration workflow](BENCH_CONFIGURATION.md) now implements
configuration snapshots, typed measurement records, provenance checks and
portable readiness packets for this sequence. Physical identities, instrument
records and human registration remain inputs supplied from actual reviewed work.

## Software corrections from this review

The distribution audit now requires every named check exactly once and a
successful exit code; a nonempty software test record without failures; and
exactly one current reproduction result for each declared model output.
Missing, partial, duplicate, stale or failed records produce blockers.

A build's artifact directory is published only after every expected file has
been read and found nonempty. A missing final file cannot leave the preceding
files packaged as a partial build. Regression tests exercise these failure
conditions using synthetic software fixtures.

These changes improve the audit's reliability. They do not change any design
dimensions, hardware behavior, physical evidence, purchase record or human
approval. See [Release Readiness](RELEASE_READINESS.md) for the outstanding work.
