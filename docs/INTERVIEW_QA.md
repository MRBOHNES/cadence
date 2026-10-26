# Interview Q&A

Short answers about how Cadence is built. The reasoning is in [`ARCHITECTURE.md`](ARCHITECTURE.md); the failures that
shaped it are in [`BUG_JOURNAL.md`](BUG_JOURNAL.md).

**Why a cron from GitHub instead of an in-process scheduler?**
The free API sleeps, and an in-process timer sleeps with it. GitHub's cron wakes it from outside, costs nothing and every run is visible. The price is timing: on this repo it ran hours apart, so the page shows when data is stale and the docs describe an external pinger as the upgrade.

**Why two failures to open an incident?**
Fewer false alarms for at most 5 minutes of detection delay. The incident's start is backdated to the first failure so its duration is still honest.

**What counts as down, and what is "slow"?**
Down is a timeout, a connection error or a 5xx. Slow is a successful response over 500 ms: a warning, still up.

**Why compute uptime and percentiles in SQL?**
The database does it in one pass over an index, so no rows are pulled into Python. p50/p95 use `percentile_cont`.

**Why no chart library?**
Four small SVG charts do not justify a dependency, and hand-written SVG matches the design exactly.

**How do you know the achievements are not fake?**
Each is a rule over real checks, and only the first unlock time is stored. Windowed achievements stay locked until the data actually spans the window.

**Why server-render the page if the data changes every five minutes?**
So visitors see the last results immediately even while the sleeping API wakes up. The server caches for 60 seconds and the browser refreshes every 60 seconds; if the API is down the page shows an error state with a retry.

**How do you run many checks without one slow site blocking the rest?**
They run concurrently with `asyncio.gather`, each with its own 10 second timeout, and a failed check returns a result instead of raising.

**What did floating point teach you here?**
`(99.85 - 99.0) / 0.1` is 8.4999999..., so HP rounded down a block. Round away the noise first, then add 0.5 and floor. Boundary tests found it.

**How does the Neon connection string work with asyncpg?**
It does not as-is: asyncpg needs the `postgresql+asyncpg://` scheme, calls the SSL option `ssl`, and rejects `channel_binding`. A Pydantic validator rewrites the URL, with a unit test.

**Why does the Sweep workflow not fail when secrets are missing?**
So an unconfigured repo does not create a red run every five minutes. It logs a warning annotation and exits; once `API_URL` and `CRON_SECRET` exist it fails normally on any real error.

**What stops two sweeps from running at once?**
A Postgres advisory lock taken inside the sweep's transaction, so it is released on commit or rollback. A sweep is also skipped if the previous one started under 2 minutes ago, which keeps a retried request from counting one outage twice.

**What happens if `CRON_SECRET` is not set?**
The endpoint refuses with 503. An earlier version defaulted to a placeholder, which would have let anyone trigger sweeps; security settings should fail closed.

