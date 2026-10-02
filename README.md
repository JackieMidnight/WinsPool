# Philly Wins Pool

The website for the Philly Wins Pool 2026 season.

| Page | File |
| --- | --- |
| This week (phone; wide screens go to the desktop layout) | `index.html` |
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
To update the weekly results, edit the data inside each page's script block.

The light/dark choice is remembered across pages.

## Publishing with GitHub Pages

In the repository on GitHub: **Settings → Pages → Build and deployment → Source: Deploy from a branch**,
pick the branch and `/ (root)`, then save. The site appears at
`https://<your-username>.github.io/WinsPool/` a minute or two later.

To preview locally: `python3 -m http.server` in this folder, then open http://localhost:8000.
