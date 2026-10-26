# Bug journal

Real problems hit while building Cadence, and what they taught. For short answers about the design, see
[`INTERVIEW_QA.md`](INTERVIEW_QA.md).

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

## 7. The sweep workflow failed before anything was deployed
**Symptom:** a red `Sweep` run in the Actions tab on each scheduled trigger, ending in `curl: (3) URL rejected: No host part in the URL`.
**Cause:** the `API_URL` and `CRON_SECRET` repository secrets did not exist yet, so both expanded to empty strings.
**Fix:** the workflow now checks for them first and exits with a warning annotation ("no sweep was triggered, see docs/DEPLOY.md step 6") instead of failing.
**Lesson:** a scheduled job should say "not configured" rather than fail loudly forever; but keep the message visible, or a real misconfiguration hides.

## 8. "Every 5 minutes" turned out to be every few hours
**Symptom:** after deploying, the live page showed one sweep for hours, and the countdown sat at `00:00`.
**Cause:** GitHub's scheduled workflows are best-effort. On this new, low-activity repo the `*/5` schedule ran twice in about five hours.
**Fix:** not fixable from the repo. The page now tells the truth (`DUE`, the last sweep's age, charts that end at load time), the docs describe the real behaviour, and `DEPLOY.md` documents an external pinger.
**Lesson:** test the scheduler you will actually run in production; the documented behaviour was optimistic.

## 9. A missing secret would have opened the sweep endpoint (found in review)
**Symptom:** none in production; found while auditing the code.
**Cause:** `cron_secret` defaulted to `"change-me"`, so a deploy without `CRON_SECRET` would accept a value anyone can read in the repo.
**Fix:** no default. With the secret unset the endpoint returns 503, and a test pins that.
**Lesson:** security settings should fail closed.

## 10. A retried request could count one outage twice (found in review)
**Symptom:** none observed; found while auditing the cron retry.
**Cause:** the workflow retries once after a 150 s client timeout. If the first request had in fact completed, the retry ran a second sweep about 2.5 minutes later, so two failures could open an incident sooner than the 2-failure rule intends. A manual run overlapping the cron had the same effect.
**Fix:** a Postgres advisory lock allows one sweep at a time, and a sweep that starts under 2 minutes after the previous one is skipped with a reason, with tests for both.

