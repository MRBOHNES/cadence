# Deploying Cadence

Do the steps in order: each needs a value from the one before. Everything runs on free tiers.

## 1. Neon (database)
1. Sign up at https://neon.tech and create a project.
2. Copy the connection string (`postgresql://...`). Use it as-is: the app converts it for asyncpg.

## 2. Cron secret
Run `openssl rand -hex 32`. You will paste the same value into Render and into GitHub.

## 3. Render (API)
1. https://dashboard.render.com, New, Blueprint, pick this repo (it reads `render.yaml`).
2. Set `DATABASE_URL` (Neon string), `CRON_SECRET`, and `CORS_ORIGIN` (any placeholder for now).
3. Deploy. On every start the container runs migrations, upserts the seed monitors, then serves.
4. Check `<render-url>/health` returns `{"status":"ok"}`.

## 4. Vercel (web)
1. https://vercel.com, import the repo, Root Directory `frontend`.
2. Env var `NEXT_PUBLIC_API_URL` = the Render URL. Deploy.

## 5. Fix CORS
In Render set `CORS_ORIGIN` to the Vercel URL (no trailing slash) and redeploy.

## 6. GitHub Actions secrets
Repo, Settings, Secrets and variables, Actions: add `API_URL` (Render URL) and `CRON_SECRET`.
Run the **Sweep** workflow once from the Actions tab and check the response.

## Notes and limitations
- Render's free tier sleeps when idle; the first request after a pause can take about a minute. The sweep workflow allows 150 s and retries once.
- GitHub cron is best-effort and may start minutes late.
- Until the two GitHub secrets exist, the Sweep workflow fails on every scheduled run.
- Changing monitored URLs: edit `backend/seed/monitors.json` and redeploy (the seed updates by `short_code`).
