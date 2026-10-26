# Deploying Cadence

Do the steps in order: each needs a value from the one before. Everything runs on free tiers.

## 1. Neon (database)
1. Sign up at https://neon.tech and create a project in the same region as Render. `render.yaml` uses
   **Singapore**, so pick AWS Asia Pacific (Singapore).
2. Copy the connection string (`postgresql://...`). Use it as-is: the app converts it for asyncpg.

## 2. Cron secret
Run `openssl rand -hex 32`. You will paste the same value into Render and into GitHub. It is required: without it the
API refuses to run sweeps.

## 3. Render (API)
1. https://dashboard.render.com, New, Blueprint, pick this repo (it reads `render.yaml`).
2. Set `DATABASE_URL` (Neon string), `CRON_SECRET`, and `CORS_ORIGIN` (any placeholder for now).
3. Deploy. On every start the container runs migrations, upserts the seed monitors, then serves.
4. Check `<render-url>/health` returns `{"status":"ok"}`.
5. Check the service's **Settings** page shows region **Singapore**. Render sets the region only when a service is
   created, so if it shows another region, delete the service and create the Blueprint again.

## 4. Vercel (web)
1. https://vercel.com, import the repo, Root Directory `frontend`.
2. Env var `NEXT_PUBLIC_API_URL` = the Render URL. Deploy.

## 5. Fix CORS
In Render set `CORS_ORIGIN` to the Vercel URL (no trailing slash) and redeploy.

## 6. GitHub Actions secrets
Repo, Settings, Secrets and variables, Actions: add `API_URL` (Render URL) and `CRON_SECRET`.
Run the **Sweep** workflow once from the Actions tab and check the response.

## Optional: a steadier scheduler
GitHub's cron can run hours apart on a quiet repo. For timing closer to every 5 minutes, add an external pinger such as
cron-job.org (free) and keep the GitHub workflow as a backup. The API's lock and 2-minute minimum gap make it safe for
both to call:
- URL: `<render-url>/internal/run-sweep`, method **POST**, schedule every 5 minutes.
- Header: `X-Cron-Secret: <your secret>`. The secret then also lives in that service's settings.
- Timeout: as long as the service allows; Render's cold start can take about a minute.

## Notes and limitations
- Render's free tier sleeps when idle; the first request after a pause can take about a minute. The sweep workflow allows 150 s and retries once.
- GitHub's cron is best-effort and was observed running hours apart on this repo.
- GitHub disables scheduled workflows after 60 days without repository activity; re-enable **Sweep** in the Actions tab.
- Until the two GitHub secrets exist, the Sweep workflow logs a warning and does nothing.
- Changing monitored URLs: edit `backend/seed/monitors.json` and redeploy (the seed updates by `short_code`).
