"""Checks for tools/odds.py. Run: python3 tools/test_odds.py"""
import pathlib, sys
sys.path.insert(0, str(pathlib.Path(__file__).parent))
import odds

roster, results, vegas = odds.site_data()
n = len(results)
r = odds.simulate(roster, results, vegas, n, n + 1, sims=3000, raw=True)
C = odds.COACHES

# 1. Every simulated season hands out 272 regular-season wins + 31 playoff bonus points.
totals = {sum(r["finals"][c][i] for c in C) for i in range(3000)}
assert totals == {272 + 31}, totals
# 2. Title odds add up to 100% (allowing for rounding).
assert abs(sum(r["win"]) - 100) < 0.5, sum(r["win"])
# 3. Nobody finishes below the points already banked.
pts = {c: 0 for c in C}
own = {t: c for c, ts in roster.items() for t in ts}
for w in results:
    for a, h, sa, sh in w:
        pts[own[a if sa > sh else h]] += 1
assert all(min(r["finals"][c]) >= pts[c] for c in C)
# 4. Rooting guide points the right way: a coach's odds are higher when their own team wins
#    a game against another coach (checked for every such game next week).
checked = 0
for (a, h), (if_away, if_home) in zip(r["next"], r["lev"]):
    ca, ch = own[a], own[h]
    if ca == ch:
        continue
    i, j = C.index(ca), C.index(ch)
    if if_away[i] + if_home[i] > 2 and if_away[j] + if_home[j] > 2:  # skip coaches with ~0% where noise dominates
        assert if_away[i] >= if_home[i] - 0.5, (a, h, ca, if_away[i], if_home[i])
        assert if_home[j] >= if_away[j] - 0.5, (a, h, ch, if_away[j], if_home[j])
        checked += 1
print(f"odds model OK: every season totals 303 points, odds sum to {sum(r['win']):.1f}%, banked points respected, rooting direction right in {checked} games")
