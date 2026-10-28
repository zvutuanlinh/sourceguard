# E46 — ExamTrust AI organizer replay

This is an **additive** checkpoint on `sourceguard` branch `competition/khkt-hanoi-2026-2027-sourceguard`; it does not overwrite E44/E45 or historical rules.

## Run offline

```bash
python run.py --mode offline --archive E45_REPLAY.zip --output E46_OUTPUT_OFFLINE
```

After a successful run, open `E46_OUTPUT_OFFLINE/RESULT.html`; the question, A–D answers, explanation and source images are visible. A fresh invocation requires a new output directory. `RUN_REPORT.json` records PASS/HOLD; `VERIFICATION.json` comes from the original engine, not a fabricated status.

**Portability caveat:** The original frozen index contains absolute source-page paths. The runner verifies the archived source-page SHA256 as well as those paths. It refuses to rewrite the immutable frozen index. If the environment lacks those paths, the runner produces HOLD. Restoring the path using a controlled copy or link to the SHA-matched page is required before running; this means the current checkpoint is **not yet certified for arbitrary clean-machine reproduction**.

## Run online (optional, not approved automatically)

```bash
GEMINI_API_KEY=... python run.py --mode online --archive E45_REPLAY.zip --output E46_OUTPUT_ONLINE
```

The online workflow requires a real saved pre-generation engine runtime (`REPLAY/online_grounding_pass_run`) with the original `GROUNDING_PASSED` state; it executes the original grounding gate and will not call Gemini if the gate does not PASS. Available models are queried from Google's models list. Gemini results remain `REVIEW_ONLY` and require teacher approval; a new model call need not reproduce the historical question. Never put an API key in Git, Drive, or a report.

## Limitations

- Offline is **original-engine post-generation re-verification**, not raw-to-question Gemini regeneration.
- No historical teacher approval is recomputed or manufactured.
- Do not treat one BIO12 and one PHY12 case as a statistical benchmark.
- E44 archive is the source for historical teacher approval.
- The installer must successfully test the runner before Git push.
