# Terminal presentation

The product is a local diagnostic CLI with JSON and plain-text output. It inherits terminal font, contrast and wrapping; no custom font, color, ANSI, animation or graphical shell is imposed.

The human report has three open groups: capture, continuity and comparison against supplied reference. Labels carry units and strict gap/speed thresholds. Reference error and declared uncertainty are adjacent but distinct. Exact matches and unmatched fixes remain visible; unavailable statistics say “No data” / “Sin datos”, never zero. Two decimal places are a presentation choice in text only; JSON keeps numeric precision.

Text supports EN/ES; validation messages remain English. Exit 0 means the analysis ran, including poor results. It is not a quality verdict or a statement about receiver accuracy. JSON schema, input bounds, pairing semantics and native boundary remain unchanged.

Verification exercises both languages, synthetic outliers, missing fixes/pairs, native/Python parity and invalid-input exit behavior. Command transcripts are actual executions. No generated map or fake field trace is used.
