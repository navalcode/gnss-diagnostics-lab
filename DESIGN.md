# Terminal presentation

The text report groups capture, continuity and comparison with the supplied reference. Each metric includes its unit or threshold. Reference error and reported uncertainty remain distinct. Paired and unmatched positions are explicit; unavailable statistics read “No data” / “Sin datos”. Two decimal places make text easier to scan; JSON retains numeric precision.

Spanish wording uses “muestras con posición” and “muestras sin posición”; CSV fields such as `fix` and machine keys stay unchanged. The heading describes a capture report, since the program can also read user-selected files. Only the bundled captures are asserted to be synthetic.

Recovery messages support English and Spanish. They identify a malformed row or required option without echoing file paths. An unavailable native library points to the build command and Python fallback; unreadable captures point to the two file options. Validation still exits 2 with no report on stdout. Error classification affects presentation only; parser rules, exact pairing and distance calculations are unchanged.

The report describes the supplied samples and does not validate a receiver. Exit 0 means processing completed, including reports with poor metrics. [Verification](docs/VERIFICATION.md) separates unit/native tests, executed CLI cases and machine-output comparisons. Font, contrast and wrapping belong to the terminal; the report uses plain text without mandatory color.
