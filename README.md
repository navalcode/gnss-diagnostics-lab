# GNSS Diagnostics Lab

[Español](README.es.md) · [![CI](https://github.com/navalcode/gnss-diagnostics-lab/actions/workflows/checks.yml/badge.svg)](https://github.com/navalcode/gnss-diagnostics-lab/actions/workflows/checks.yml)

A Python/C tool for comparing position samples with a supplied reference. It reports the first fix, samples without a position, gaps, apparent jumps and reference error. Pairing uses identical elapsed times; there is no interpolation or automatic clock alignment.

The bundled CSV files are synthetic and deliberately include a late first fix, missing positions and an outlier. You can also select your own local files. The program does not acquire device location. A small C distance function, called through `ctypes`, can be compared with the Python implementation.

## Run

Python 3.11+; no Python packages required. The native backend additionally needs a host C compiler (`cc`) on macOS or Linux.

```sh
python3 -m gnss_lab
python3 -m gnss_lab --format text --language es
python3 tools/build_native.py
python3 -m gnss_lab --backend native
python3 -m unittest discover -s tests -v
```

Run from the repository root. Tests require the native build and fail if it is missing; native checks are not silently skipped. The build script compiles only `native/distance.c`. No binary is shipped. The Python backend runs without a compiler or library.

Expected bundled results: **3 fixes, 4 no-fix samples, first fix at 2000 ms, one interval exceeding 2500 ms and one apparent speed jump exceeding 10 m/s**. Supplied-reference p95 is about 104.52 m, while reported uncertainty is 3 m. That mismatch is deliberate and does not certify a real device's accuracy.

Exit 0 means the capture was processed successfully, including captures with poor diagnostic results. Invalid input or unavailable native backend exits 2 and emits no JSON. No pass/fail quality certification is produced.

## Input contract

```csv
elapsed_ms,fix,latitude_deg,longitude_deg,horizontal_accuracy_m
0,0,,,
2000,1,0,0.00003,3
```

| Field | Rule |
|---|---|
| `elapsed_ms` | Integer since declared session start at 0; 0 ≤ value < 10¹⁵; strictly increasing, no duplicates or sorting. |
| `fix` | Exactly 0 or 1. |
| No fix | All three position fields must be empty. |
| Valid fix | Finite latitude −90…90, longitude −180…180 and reported horizontal uncertainty 0…1,000,000 m. This upper bound belongs to the parser contract. |

Exact header order, UTF-8 (optional BOM), at most 1 MiB and 10,000 samples per capture. Missing/extra columns, nonfinite values and partial fixes fail. The examples are generated mathematical paths near (0,0), not recorded journeys or real ground truth.

Provide your own explicitly selected files with `--samples file.csv --reference reference.csv`. The program reads them locally, writes reports to stdout and makes no network requests. The reference uses the same schema. Only exact `elapsed_ms` matches with fixes in both captures contribute to error; there is no interpolation or automatic clock alignment.

## Report semantics

- TTFF is the first valid elapsed time from declared zero, not a hardware acquisition benchmark.
- Gaps count intervals **between consecutive valid fixes** strictly greater than `--max-gap-ms`; the trailing no-fix duration is separate. A missing first fix is null, never zero.
- Apparent speed is spherical displacement divided by actual elapsed time; `--jump-mps` is a demo diagnostic threshold, not a universal physical limit.
- Error mean, arithmetic median/p50, nearest-rank p95 and RMSE use matched valid pairs only. Missing pairs are counted explicitly. No pairs produce null error statistics.
- `mean_reported_accuracy_m` is supplied uncertainty, separate from reference error. The tool does not infer a confidence level, calibrate uncertainty or treat it as a guarantee.
- JSON keys remain English and include units; human summaries support English/Spanish. Recovery messages support both languages; CSV field names and argparse usage stay in English.

## Read the implementation

| File | Purpose |
|---|---|
| [`capture.py`](gnss_lab/capture.py) | Bounded parser, immutable samples and schema validation. |
| [`diagnostics.py`](gnss_lab/diagnostics.py) | Explicit matching, gaps, jumps and statistics. |
| [`distance.py`](gnss_lab/distance.py) | Python model and typed native ABI adapter. |
| [`distance.c`](native/distance.c) | Original C kernel with validated inputs and status/result contract. |
| [`test_diagnostics.py`](tests/test_diagnostics.py) | Parser failures, known analytical distances, report semantics, CLI and C ABI tests. |

The kernel uses a sphere of radius **6,371,000 m**, a chosen model parameter. It is not an ellipsoidal geodesic solution. Python/C parity checks exercise zero distance, equator, poles, antimeridian and antipodes; parity is not independent proof of physical accuracy. The C ABI rejects null output pointers and invalid coordinates without overwriting the output.

Only the project's own compiled `build/libgnss_distance.so` or `.dylib` is loaded when `--backend native` is explicitly requested. Capture content cannot choose a library or execute a command. This host-side `ctypes` boundary is not Android JNI or a GNSS receiver driver.

## Checks and limits

The suite has **28 tests** covering parser failures, report semantics, Python/C parity, the raw C ABI and CLI recovery. [Verification](docs/VERIFICATION.md) records the current native build, CLI examples and Linux/macOS CI separately. An unavailable native backend exits 2 and suggests `python3 tools/build_native.py` or `--backend python`; unreadable input points to `--samples` and `--reference`.

No Android acquisition, NMEA/raw measurements, field validation, receiver certification or navigation use is claimed. Physical measurements would require capture provenance, clock definitions, a defensible reference and uncertainty analysis.

## License

Original code, documentation and synthetic fixtures: [MIT](LICENSE), Manuel Naval, 2026. Python, the host C toolchain and system libraries retain their own licenses; their source/binaries are not redistributed here.
