# Bug journal

Real problems hit while building Cadence, and what they taught.

## 1. HP was off by one block: floating point
**Symptom:** a test expecting 99.85% uptime to give HP 9 got 8.
**Cause:** `(99.85 - 99.0) / 0.1` evaluates to 8.4999999..., not 8.5, so half-up rounding went down. Python's `round()` also uses banker's rounding, so it was not an option either.
**Fix:** round away the float noise first, then add 0.5 and floor (`backend/app/game.py`).
**Lesson:** tests on boundary values catch what the happy path hides.

## 2. Neon's connection string does not work with asyncpg
**Symptom (would-be):** `postgresql://...?sslmode=require&channel_binding=require` fails with SQLAlchemy + asyncpg.
**Cause:** asyncpg wants the `postgresql+asyncpg://` scheme, calls the option `ssl`, and does not know `channel_binding`.
**Fix:** a Pydantic validator rewrites the URL (`backend/app/config.py`), unit-tested.

## 3. Tailwind silently stopped working after I simplified the Next config
**Symptom:** build warned `Unknown at rule: @theme`.
**Cause:** this Next version wires Tailwind through a Turbopack loader in `next.config.ts`; I had deleted it along with options I did not need.
**Fix:** restore only the loader rule. **Lesson:** read the build warnings, and remove config deliberately.

## 4. Stale data after the backend went down
**Symptom:** with the API stopped, the page still showed data instead of the error state.
**Cause:** Next's persistent fetch cache served the previous result.
**Fix/lesson:** this is the intended `revalidate: 60` behaviour. A clean rebuild confirmed the error state.

## 5. Red text failed the contrast check on failed rows
**Symptom:** Lighthouse accessibility 95, not 100.
**Cause:** `#b3392a` on the 7% red tint is 4.41:1, just under 4.5:1.
**Fix:** on tinted rows the text is charcoal with a red square. The same reasoning applies to teal and orange small text.

## 6. Container ignored shutdown signals
**Symptom:** `podman stop` took 10 s then force-killed.
**Cause:** `sh -c "... && uvicorn ..."` kept the shell as PID 1.
**Fix:** `exec uvicorn`, so the server receives SIGTERM.

## Interview Q&A
- **Why a cron from GitHub instead of an in-process scheduler?** The free API sleeps; an in-process timer sleeps with it. See the README trade-offs.
- **Why two failures to open an incident?** Fewer false alarms for at most 5 minutes of detection delay.
- **Why compute uptime and percentiles in SQL?** The database does it in one pass over an index; no rows are pulled into Python.
- **Why no chart library?** Four small SVG charts do not justify a dependency.
- **How do you know the achievements are not fake?** Each is a rule over real checks; only the first unlock time is stored.
