# 🛺 GalliMaps — Bangalore Inner-Road Navigator

> Skip the arterials. Take the *gallis*.

A small, no-backend web app that routes you across Bangalore on **inner roads**
instead of the traffic-choked main roads Google loves. Google optimizes for ETA,
which almost always dumps you onto Outer Ring Road, Hosur Road, or Old Airport
Road at exactly the wrong time. GalliMaps deliberately does the opposite.

**Everything runs in the browser. No API keys. No server.**

---

## The product idea

Fastest ≠ least stressful. On a bad-traffic day, the arterial that's "fastest"
in free-flow is the one crawling bumper-to-bumper. Locals already know this —
they cut through residential layouts and side streets. GalliMaps turns that
instinct into a tool:

> *"Get me there mostly on small roads, and I'll happily trade some time for it."*

You control that trade-off with a single slider.

## How it actually works

There's no magic "avoid main roads" button in public routing APIs, so GalliMaps
uses a **multi-route + scoring** approach:

1. **Ask for alternatives.** It queries the free [OSRM](https://project-osrm.org)
   public server for up to 3 candidate routes between your two points.
2. **Score "main-road exposure"** for each candidate. A stretch of road counts
   as a *main road* if it is:
   - a **named Bangalore arterial / ring road** (ORR, Hosur Rd, Old Airport Rd,
     Sarjapur Rd, 100 Feet Rd, Bannerghatta Rd, … — the list lives in `app.js`),
   - carrying a **highway reference** (NH / SH / NICE / ORR), or
   - a **long, fast-moving segment** — a speed proxy that catches big roads even
     when we don't recognise the name.
3. **Rank by calmness within your budget.** The route with the *least* main-road
   exposure wins — as long as it isn't slower than the fastest option by more
   than the % you set on the slider.
4. **Show the trade-off honestly.** Each route card shows time, distance, and the
   share of the trip spent on main roads, so you can decide for yourself.

The map is [Leaflet](https://leafletjs.com) + OpenStreetMap tiles; search is
[Nominatim](https://nominatim.org). All free, all client-side.

## Honest limits (read this)

- GalliMaps can only choose among the routes **OSRM proposes**. It can't invent a
  side-street shortcut the router never offered. On short trips OSRM often returns
  just one route — then there's nothing to choose between.
- "Main road" detection is a **heuristic**, not ground truth. The named-arterial
  list is hand-curated for Bangalore and can be extended.
- It uses **historical/free-flow** routing, not live traffic. It avoids roads
  that *tend* to jam, which is a decent proxy, but it isn't reading current jams.

### The "real" upgrade path

For true inner-road routing you want a routing engine whose **cost function**
penalizes high road classes directly, rather than scoring after the fact:

- **Valhalla** — `auto` costing with a low `use_highways` and custom penalties on
  `trunk`/`primary` road classes. Self-host, or via a provider.
- **GraphHopper** — a custom `profile` with `priority` rules that down-weight
  `road_class == primary|trunk|motorway`.

Point the `fetchRoutes()` function in `app.js` at that endpoint and the rest of
the app (scoring, ranking, UI) still applies as a second-pass refinement.

## Run it

It's a static site — no build step.

```bash
# any static server works; pick one
python3 -m http.server 8000
#   or
npx serve .
```

Then open <http://localhost:8000>. (Open via a server, not `file://` — the
geocoding API needs a real origin.)

## Deploy to GitHub Pages

1. Push this branch and merge to your default branch.
2. Repo **Settings → Pages → Source: Deploy from a branch → `main` / root**.
3. Your app is live at `https://<user>.github.io/<repo>/`.

## Files

| File | What it does |
|------|--------------|
| `index.html` | Layout: control panel + map |
| `styles.css` | Dark, map-first theme |
| `app.js` | Map, geocoding, routing, **scoring & ranking** (the interesting bit) |

## Roadmap ideas

- [ ] Perturb routes with random via-points to surface *more* inner-road options
- [ ] Fold in live traffic (a traffic-aware routing provider) as a second signal
- [ ] Crowd-sourced "known bad junction" avoid-list (Silk Board, anyone?)
- [ ] Turn-by-turn directions for the chosen quiet route
- [ ] Save favourite start/destination pairs

---

*Map © OpenStreetMap contributors · Routing by OSRM · Search by Nominatim.*
