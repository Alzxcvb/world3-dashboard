# Static Dashboard (web/)

Pure static build of the World3 dashboard — same charts, same data, no
running server required. Deployed to Vercel.

## Layout

```
web/
├── build_data.py        # runs World3 + bundles real-world data → public/data.json
├── public/              # what Vercel serves
│   ├── index.html       # single-page UI
│   ├── styles.css
│   ├── app.js           # client-side Plotly rendering
│   └── data.json        # generated, ~160 KB
└── vercel.json          # static deploy config
```

## Local rebuild

From the repo root:

```bash
python3 web/build_data.py
```

This re-runs all 4 World3 scenarios (BAU, BAU2, CT, SW), normalizes them to
1970 = 1.0, joins with `data/real_world_data.csv`, computes per-variable RMSE
against real data, and writes `web/public/data.json`.

## Local preview

```bash
cd web/public && python3 -m http.server 8000
# open http://localhost:8000
```

## Deploy

```bash
cd web && npx vercel@latest deploy --prod --yes
```

Vercel serves `public/` directly — no build step.

## Refresh real-world data

The cron job in `.github/workflows/refresh-data.yml` runs `fetch_real_data.py`
+ `build_data.py` monthly and commits the updated CSV/JSON. To trigger a
refresh manually, run:

```bash
python3 src/fetch_real_data.py
python3 web/build_data.py
git add data/real_world_data.csv data/real_world_data_metadata.json web/public/data.json
git commit -m "Refresh real-world data"
git push
```
