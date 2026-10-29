# Cadence frontend

The public status page: a Next.js (App Router) app in TypeScript with Tailwind and hand-written SVG charts. See the
[root README](../README.md) for the whole project.

## Run it

```bash
cp .env.example .env.local    # NEXT_PUBLIC_API_URL=http://localhost:8000
npm install
npm run dev                   # http://localhost:3000
```

The backend must be running for data to appear; without it the page shows its error state with a retry button.

## Scripts

| Command | What it does |
| --- | --- |
| `npm run dev` | Dev server |
| `npm run build` / `npm start` | Production build and server |
| `npm run lint` | ESLint (`eslint.config.mjs`, Next's core-web-vitals and TypeScript rules) |
| `npm run gen:types` | Regenerate `lib/api-types.ts` from the running backend's `/openapi.json` (`API_URL` selects the backend) |

CI runs `npm run lint`, `npx tsc --noEmit` and `npm run build` on every push and pull request. The build does not need
a backend: the page catches the failed fetch and builds its empty state.

## Configuration

| Variable | Purpose |
| --- | --- |
| `NEXT_PUBLIC_API_URL` | Base URL of the API (defaults to `http://localhost:8000`) |
| `API_URL` | Only for `npm run gen:types`: where to read the OpenAPI schema |

## How the data flows

1. `app/page.tsx` is server-rendered with `revalidate = 60` and loads everything through `loadDashboard` (`lib/api.ts`). If the API is asleep or down, it renders without data instead of failing.
2. `components/Dashboard.tsx` (a client component) takes that as its initial state, then refreshes every 60 seconds.
3. Once the "next sweep" countdown reaches zero it checks every 10 seconds for the new sweep, and gives up after 2 minutes so a dead scheduler does not cause endless polling.
4. Loading, empty, error and incident states live in `components/States.tsx` and `IncidentPanel.tsx`.

## Layout

```
app/          layout, the page, global styles
components/   Dashboard and its sections: Header, KpiStrip, LatencyChart, HistoryBars, CheckLog,
              IncidentPanel, Leaderboard, Achievements, Footer, plus small pieces (Blocks: HP and
              streak bars, Marker: status text with a coloured square, PixelIcon, States,
              SweepButton: the countdown tag; runs a sweep on click, and by itself when one is due)
lib/          api.ts (typed client), api-types.ts (generated, do not edit), format.ts, useNow.ts
```

## Design notes

- No chart library: the charts are small SVG components.
- Small status text is charcoal with a coloured square beside it, because the teal and orange fall below 4.5:1 contrast on the panel colour at that size (see `components/Marker.tsx` and the bug journal).
