# The website

A static website for the project on GitHub Pages: https://dylanstechmann.github.io/follow-me-drone-agent/ (live once Pages is turned on for the repo, see below). It shows what the repo's code and data say, in the browser, with nothing to install. Like the rest of the repo, it was written by AI coding agents at the owner's direction, and it keeps the same framing: a personal hobby and learning project, nothing has flown, and nothing is claimed to be safe, autonomous or ready to fly.

## Pages

| Page | What it shows | Where the data comes from |
|---|---|---|
| `index.html` | The project, the six gates, what exists and how it was built | Hand-written text, plus the README's "Status" and "How this was built" sections, copied in at each build |
| `replay.html` | One tick at a time: each source's reading and uncertainty, attention, trust, the gate's decision, the fused estimate, the mode and the command | A trace of [examples/replay.example.json](../examples/replay.example.json) from `python -m follow_me.replay --json` |
| `costs.html` | Each pass's core cost, minimum-order cash and shares; cost per drone by number of drones; price freshness; single-supplier parts | The cost model in `src/follow_me/bom.py`, reading `bom/` |

The replay viewer can also open a trace file the visitor makes from their own log. The file is read in the browser and is not uploaded anywhere:

```
PYTHONPATH=src python3 -m follow_me.replay --json LOG.json > trace.json
```

A raw log is not enough: the trace carries the council's results, so the page never re-implements the logic. A later page could run the Python itself in the browser (Pyodide), since the package uses only the standard library.

## How it is built and published

```
PYTHONPATH=src python3 -m follow_me.website          # build into _site/ (ignored by git)
python3 -m http.server -d _site 8000                 # preview at http://localhost:8000
```

- The pages, styles and scripts live in `site/`. They are plain HTML, CSS and JavaScript modules with no libraries and no build step.
- `follow_me.website` copies `site/`, writes `data/costs.json`, `data/replay-example.json` and `data/build.json` (the commit and build time), copies the example log, and fills the README sections into `index.html`. It uses only the standard library.
- The workflow in [.github/workflows/site.yml](../.github/workflows/site.yml) runs the tests on every push and pull request. On `main` it builds the site and publishes it to GitHub Pages. The data is regenerated at every build, so the published site cannot fall behind the repo, and nothing generated is committed.
- **Turning Pages on** is a one-time repo setting: Settings, Pages, Source "GitHub Actions" (or `gh api -X POST repos/dylanstechmann/follow-me-drone-agent/pages -f build_type=workflow`). It publishes the site, so it is the owner's call. Until then the deploy step fails and the tests still run.
- `tests/test_website.py` builds the site and checks that the data matches the model and the replay, every local link and import resolves, the honesty statements are on every page, there is no email-like or phone-like text, and no place data or coordinates are shipped.

## Rules for the site

- **Privacy.** No analytics, cookies, trackers or third-party requests. The theme choice is kept in the browser's local storage. Never put real coordinates, routes, names, contact details or order records on the site; the tests check for some of these.
- **Honesty.** Keep the hobby framing, the AI disclosure and "nothing has flown" on every page. Label made-up data as made up. Every price on the site carries the model's cutoff date and its freshness.
- **No money asks.** No donate buttons, sponsorship links or funding appeals.
- **No fleet or product claims.** The drone-count view is for exploring. The owner has not set a number of drones.

## Design notes

- Colours are roles defined once in `site/assets/style.css`, with light and dark values. The three source colours, the four status colours for the modes and the four-step freshness ramp come from a colour-blind-checked palette in the data-visualization guidance the coding agent used. The source colours and the ramp were run through its validator for both themes on 2026-10-26. One light-mode source colour is below 3:1 contrast, so the plot labels its readings directly and each chart has a table view.
- Status colours always come with an icon and a label, because colour alone cannot carry meaning, and dead reckoning and hold share a colour.
- Text from data files is inserted with `textContent`, never as HTML, so a trace a visitor opens cannot inject markup.

## Adding a page

1. Write it in `site/` with the same header, footer and honesty lines as the other pages.
2. If it needs data, add a function in `src/follow_me/website.py` that writes it under `data/`, computed by the tested modules rather than in JavaScript.
3. Add the page to `PAGES` in `tests/test_website.py`, build, preview, and look at it at phone width and in both themes before committing.
