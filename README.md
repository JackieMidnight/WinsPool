# Philly Wins Pool

The website for the Philly Wins Pool 2026 season.

| Page | File |
| --- | --- |
| This week (phone; screens 1024px and wider go to the desktop layout) | `index.html` |
| Standings and results for past weeks (`week.html?w=1`, `?w=2`, …) | `week.html` |
| This week (desktop) | `desktop.html` |
| Season and archive | `season.html` |
| Coach page | `coaches.html` |
| All 32 teams + pace vs Vegas | `teams.html` |
| Rosters and draft board | `rosters.html` |
| Start here and rules | `rules.html` |
| Playoff bonus tracker | `playoffs.html` |
| Group-text standings image | `share.html` |

`item.html` is the older standings page and is unchanged.

## How the pages work

Each page keeps its markup in a `<template id="dc-template">` and its data and logic in the
`<script type="text/x-dc" data-dc-script>` block at the bottom. `support.js` fills the template's
`{{holes}}` from that script's `renderVals()`, repeats `<sc-for>` blocks, and wires up buttons.
To update the weekly results, edit the data inside each page's script block. Past-week pages are calculated from the scores in `RESULTS` inside `week.html`: add each new week's games there, and its headline to `INFO`.

The light/dark choice is remembered across pages. On screens 1024px and wider, `support.js` gives every page a desktop layout (menu in the header, sections in two columns); each section's `data-wide` attribute says where it goes.

## Publishing with GitHub Pages

In the repository on GitHub: **Settings → Pages → Build and deployment → Source: Deploy from a branch**,
pick the branch and `/ (root)`, then save. The site appears at
`https://<your-username>.github.io/WinsPool/` a minute or two later.

Browsers keep a copy of `support.js` for about 10 minutes. Whenever you change it, bump the `?v=` number on its
`<script src="support.js?v=…">` line in every page so visitors get the new version along with the new pages.

To preview locally: `python3 -m http.server` in this folder, then open http://localhost:8000.
