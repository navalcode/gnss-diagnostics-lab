# Verification

Checked on 30 October 2026 on macOS with Python 3.14.2 and the host C compiler.

```sh
python3 tools/build_native.py
python3 -m unittest discover -s tests -v
python3 -m gnss_lab --backend python --format text --language en
python3 -m gnss_lab --backend native --format text --language es
```

All 28 tests pass, including raw C ABI checks and Python/C distance comparisons. The native library is built locally from the reviewed source; no compiled library is exported.

Both backends process the bundled data in English and Spanish. Their parsed JSON results were compared separately with the pre-edit results and remained equal. The deliberately poor capture still exits 0; its reference p95 remains about 104.52 m. An all-no-fix capture keeps unavailable statistics null rather than zero.

Failure checks cover an invalid `fix` value with a row-specific recovery message, unreadable input and a missing native library. Each exits 2 with empty stdout. A source-only export first demonstrates the missing-library recovery, then builds the native library and processes the same capture successfully. Tests also inject a native loader failure and verify that private loader details are not printed.

The [checks workflow](https://github.com/navalcode/gnss-diagnostics-lab/actions/workflows/checks.yml) builds C and tests Python on Linux and macOS. Its run history records hosted results. Host compilation and analytical fixtures do not demonstrate Android integration, real receiver performance, field accuracy or navigation safety.
