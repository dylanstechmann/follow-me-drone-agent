# The website

A static website for the project on GitHub Pages: https://dylanstechmann.github.io/follow-me-drone-agent/ (live since 2026-10-26). It shows what the repo's code and data say, in the browser, with nothing to install. Like the rest of the repo, it was written by AI coding agents at the owner's direction, and it keeps the same framing: a personal hobby and learning project, nothing has flown, and nothing is claimed to be safe, autonomous or ready to fly.

## Pages

| Page | What it shows | Where the data comes from |
|---|---|---|
| `index.html` | The project, the six gates, what exists and how it was built | Hand-written text, plus the README's "Status" and "How this was built" sections, copied in at each build |
| `replay.html` | One tick at a time: each source's reading and uncertainty, attention, trust, the gate's decision, the fused estimate, the mode and the command. For a simulated follow, also the distance to the rider over time and a top-down view of both paths | A trace of [examples/replay.example.json](../examples/replay.example.json) from `python -m follow_me.replay --json`, and a made-up ride run through the kinematic simulation, with the controller as it is and as it was before feed-forward ([simulation.md](simulation.md)) |
| `costs.html` | Each pass's core cost, minimum-order cash and shares; cost per drone by number of drones; price freshness; single-supplier parts | The cost model in `src/follow_me/bom.py`, reading `bom/` |
| `parts.html` | Each printable part in 3D, with sliders that re-render it in the browser, its print card, and STL and OpenSCAD downloads | `cad/*.scad` and `cad/parts.json` through `src/follow_me/parts.py`, with STLs rendered at build time |

The replay viewer can also open a trace file the visitor makes from their own log. The file is read in the browser and is not uploaded anywhere:

```
PYTHONPATH=src python3 -m follow_me.replay --json LOG.json > trace.json
```

A raw log is not enough: the trace carries the council's results, so the page never re-implements the logic.

It can also open a GPX recording from a GPS-logging app. The page runs the repo's own Python in a web worker with Pyodide, which is possible because the package uses only the standard library:
- The worker calls `follow_me.recording.run_gpx`, the same code the tests check and the command line runs, and the viewer draws the trace it returns.
- The file never leaves the tab. The importer keeps only meters and seconds from the first fix.
- Pyodide is about 6.4 MB to download, compressed (13.5 MB unpacked). It is loaded from this site the first time a recording is opened.

## How it is built and published

```
PYTHONPATH=src python3 -m follow_me.website          # build into _site/ (ignored by git)
PYTHONPATH=src python3 -m follow_me.website --render-parts   # also fetch the libraries and render the parts
python3 -m http.server -d _site 8000                 # preview at http://localhost:8000
```

- The pages, styles and scripts live in `site/`. They are plain HTML, CSS and JavaScript modules with no build step. Two pages use libraries. The parts page uses three.js 0.186.1 (MIT) for the 3D view and openscad-wasm-prebuilt 1.2.0, an unmodified WebAssembly build of OpenSCAD 2025.01.19 (GPL-2.0-or-later), for rendering. The replay page uses Pyodide 314.0.7 (MPL-2.0, with CPython 3.14's standard library under the PSF licence), unmodified, to run the package's Python for recordings.
- `follow_me.website` copies `site/` and the `.scad` files, writes `data/costs.json`, `data/replay-example.json`, `data/sim-example.json`, `data/sim-example-before.json`, `data/parts.json` and `data/build.json` (the commit, the build time and whether Pyodide is included), copies the example log and the thirteen modules the browser runs (`PY_MODULES`, under `py/follow_me/` with a manifest), and fills the README sections into `index.html`. It uses only the standard library.
- `--vendor` downloads the three libraries from the npm registry, pinned to exact versions and checked against the registry's sha512 hashes, caches them under `~/.cache/follow-me-site`, and copies only the files the page needs into `assets/vendor/`. No library code is kept in git, and the published site makes no requests to other servers. `--render-parts` (which implies `--vendor`) then runs `tools/render_parts.mjs` with Node.js to render each part's default STL with that same OpenSCAD build. Without these flags the parts page still lists the parts and offers the `.scad` downloads, but has no 3D view, and the replay page points to the command line for recordings.
- The workflow in [.github/workflows/site.yml](../.github/workflows/site.yml) runs the tests and builds the site, with the libraries and the rendered parts, on every push and pull request. On `main` it publishes the site to GitHub Pages. The data is regenerated at every build, so the published site cannot fall behind the repo, and nothing generated is committed.
- **Pages** was turned on on 2026-10-26, with the owner's agreement, with source "GitHub Actions" (Settings, Pages). Turning it off unpublishes the site, and the deploy step then fails while the tests still run. The upload action skips hidden files, so `.nojekyll` is not published; it is not needed, because Pages does not run Jekyll on Actions deploys.
- `tests/test_website.py` builds the site and checks that the data matches the model and the replay, every local link and import resolves, the honesty statements are on every page, there is no email-like or phone-like text, and no place data or coordinates are shipped.

## Rules for the site

- **Privacy.** No analytics, cookies, trackers or third-party requests: the libraries are served from the site itself. The theme choice is kept in the browser's local storage. The parts page renders in the visitor's browser and sends nothing anywhere. Never put real coordinates, routes, names, contact details or order records on the site; the tests check for some of these.
- **Honesty.** Keep the hobby framing, the AI disclosure and "nothing has flown" on every page. Label made-up data as made up. Every price on the site carries the model's cutoff date and its freshness.
- **No money asks.** No donate buttons, sponsorship links or funding appeals.
- **No fleet or product claims.** The drone-count view is for exploring. The owner has not set a number of drones.
- **Parts are unprinted and untested** until a card records a print. Never call a part a flight part, and keep the safety notes on the cards.
- **Licences.** Keep OpenSCAD's GPL licence file next to its build and the links to its source on the parts page. Keep three.js's MIT licence file next to it. Pyodide's package has no licence file, so the replay page names its licence and links to its source.

## Design notes

- Colours are roles defined once in `site/assets/style.css`, with light and dark values. The three source colours, the four status colours for the modes and the four-step freshness ramp come from a colour-blind-checked palette in the data-visualization guidance the coding agent used. The source colours and the ramp were run through its validator for both themes on 2026-10-26. One light-mode source colour is below 3:1 contrast, so the plot labels its readings directly and each chart has a table view.
- Status colours always come with an icon and a label, because colour alone cannot carry meaning, and dead reckoning and hold share a colour.
- Text from data files is inserted with `textContent`, never as HTML, so a trace a visitor opens cannot inject markup.

## Adding a page

1. Write it in `site/` with the same header, footer and honesty lines as the other pages.
2. If it needs data, add a function in `src/follow_me/website.py` that writes it under `data/`, computed by the tested modules rather than in JavaScript.
3. Add the page to `PAGES` in `tests/test_website.py`, build, preview, and look at it at phone width and in both themes before committing.
