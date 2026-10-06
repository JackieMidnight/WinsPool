"""Sanity checks for tools/schedule_2026.py. Run: python3 tools/check_schedule.py"""
import collections, pathlib, re, sys
sys.path.insert(0, str(pathlib.Path(__file__).parent))
from schedule_2026 import WEEKS, DIVISIONS, NEUTRAL, games

site = (pathlib.Path(__file__).parent.parent / "coaches.html").read_text()
BYE = {t: int(w) for t, w in re.findall(r"(\w+): (\d+)", site.split("var BYE = {")[1].split("}")[0])}
teams = {t for d in DIVISIONS.values() for t in d}
div_of = {t: d for d, ts in DIVISIONS.items() for t in ts}
assert len(teams) == 32 and set(BYE) == teams, "bye map should cover all 32 teams"
G = games()
errors = []
for w in range(1, 19):
    wk = [t for (gw, a, h) in G if gw == w for t in (a, h)]
    dup = [t for t, n in collections.Counter(wk).items() if n > 1]
    if dup: errors.append(f"week {w}: plays twice {dup}")
    off = sorted(teams - set(wk))
    want = sorted(t for t, b in BYE.items() if b == w)
    if off != want: errors.append(f"week {w}: off {off}, bye map says {want}")
for t in sorted(teams):
    mine = [(w, a, h) for (w, a, h) in G if t in (a, h)]
    if len(mine) != 17: errors.append(f"{t}: {len(mine)} games")
    home = sum(1 for (w, a, h) in mine if h == t)
    if home not in (8, 9): errors.append(f"{t}: {home} home games")
    for r in DIVISIONS[div_of[t]]:
        if r == t: continue
        vs = [(w, a, h) for (w, a, h) in mine if r in (a, h)]
        if len(vs) != 2 or {vs[0][2], vs[1][2]} != {t, r}:
            errors.append(f"{t} vs {r}: {vs}")
    opps = collections.Counter(a if h == t else h for (w, a, h) in mine)
    if any(n > 1 and div_of[o] != div_of[t] for o, n in opps.items()):
        errors.append(f"{t}: non-division opponent twice {opps}")
for w, gs in NEUTRAL.items():
    for g in gs:
        if (w, *g) not in G: errors.append(f"neutral game not in schedule: week {w} {g}")
print("272 games" if len(G) == 272 else f"{len(G)} games (expected 272)")
print("\n".join(errors) if errors else "schedule OK: 17 games each, byes match the site, division rivals home and away, no repeats")
sys.exit(1 if errors else 0)
