"""Title-odds model for the Coaches page.

Simulates the rest of the regular season and the playoffs many times and reports, for
each coach: the chance of winning the pool, the 10th-90th percentile final score, and how
much each of next week's games moves their odds (the rooting guide).

How a game is decided
  Each team's strength starts from its preseason Vegas win total and is blended with its
  record so far (the preseason total counts as PRIOR_GAMES games). The chance that A beats
  B is a logistic function of the difference in strength, plus HOME_EDGE for the home team
  (none at international sites). Every simulated season also shifts each team's strength by
  a random amount (SPREAD), so a team's results within a season move together.

Playoffs (bonus points from the Rules page)
  Seven teams per conference: four division winners seeded by record, then three wild cards.
  Wild Card round 2v7, 3v6, 4v5; the top seed gets the bye; reseed after each round.
  A win is worth +2 (Wild Card), +2 (Divisional), +3 (Conference), +5 (Super Bowl).
  Ties on record are broken at random.

Pool winner: most regular-season points plus bonus points; level coaches go to most
regular-season wins; still level, the title is split.

Run:   python3 tools/odds.py            prints the numbers
       python3 tools/odds.py --write    also writes them into coaches.html
"""
import math, pathlib, random, re, sys

sys.path.insert(0, str(pathlib.Path(__file__).parent))
from schedule_2026 import DIVISIONS, NEUTRAL, games

ROOT = pathlib.Path(__file__).parent.parent
SIMS = 40000
SEED = 2026
PRIOR_GAMES = 8
HOME_EDGE = 0.2
SPREAD = 0.3
BONUS = {"wc": 2, "div": 2, "conf": 3, "sb": 5}

COACHES = ["Nicole", "Luke", "Virginia", "Jack", "Caleb", "Court", "Drew", "Mike"]  # order used in coaches.html


def site_data():
    week = (ROOT / "week.html").read_text()
    roster = {n: re.findall(r"'(\w+)'", t) for n, t in re.findall(r"(\w+): (\[[^\]]+\])", week.split("var ROSTER = ")[1].split("};")[0])}
    raw = "".join(re.findall(r"'([^']*)'", week.split("var RESULTS = ")[1].split(";")[0]))
    results = [[(g.split()[0], g.split()[1], int(g.split()[2]), int(g.split()[3])) for g in w.split(",")] for w in raw.split("/")]
    coaches = (ROOT / "coaches.html").read_text()
    vegas = {t: float(v) for t, v in re.findall(r"(\w+): ([\d.]+)", coaches.split("var VEGAS = {")[1].split("}")[0])}
    return roster, results, vegas


def simulate(roster, results, vegas, weeks_played, next_week, sims=SIMS, seed=SEED, raw=False):
    own = {t: c for c, ts in roster.items() for t in ts}
    conf = {t: d.split()[0] for d, ts in DIVISIONS.items() for t in ts}
    div = {t: d for d, ts in DIVISIONS.items() for t in ts}
    neutral = {(w, a, h) for w, gs in NEUTRAL.items() for a, h in gs}
    played = results[:weeks_played]
    wins0 = {t: 0 for t in own}; games0 = {t: 0 for t in own}
    for w in played:
        for a, h, sa, sh in w:
            games0[a] += 1; games0[h] += 1
            wins0[a if sa > sh else h] += 1
    base = {}
    for t in own:
        p = (vegas[t] / 17 * PRIOR_GAMES + wins0[t]) / (PRIOR_GAMES + games0[t])
        p = min(max(p, 0.03), 0.97)
        base[t] = math.log(p / (1 - p))
    remaining = [(w, a, h) for (w, a, h) in games() if w > weeks_played]
    next_games = [(a, h) for (w, a, h) in remaining if w == next_week]
    rng = random.Random(seed)

    def beat(r, a, h, neutral_site):
        edge = r[h] - r[a] + (0 if neutral_site else HOME_EDGE)
        return h if rng.random() < 1 / (1 + math.exp(-edge)) else a

    titles = {c: 0.0 for c in COACHES}
    finals = {c: [] for c in COACHES}
    cond = [[{c: 0.0 for c in COACHES}, {c: 0.0 for c in COACHES}] for _ in next_games]  # [away won, home won]
    cond_n = [[0, 0] for _ in next_games]
    for _ in range(sims):
        r = {t: base[t] + rng.gauss(0, SPREAD) for t in own}
        wins = dict(wins0)
        nxt = []
        for (w, a, h) in remaining:
            win = beat(r, a, h, (w, a, h) in neutral)
            wins[win] += 1
            if w == next_week:
                nxt.append(1 if win == h else 0)
        bonus = {t: 0 for t in own}
        for cf in ("AFC", "NFC"):
            teams = [t for t in own if conf[t] == cf]
            key = lambda t: (wins[t], rng.random())
            leaders = sorted((max((t for t in teams if div[t] == d), key=key) for d in sorted({div[t] for t in teams})), key=key, reverse=True)
            wild = sorted((t for t in teams if t not in leaders), key=key, reverse=True)[:3]
            seeds = leaders + wild  # seed 1..7
            # Wild Card: 2v7, 3v6, 4v5 (higher seed at home)
            survivors = [seeds[0]]
            for hi, lo in ((1, 6), (2, 5), (3, 4)):
                wnr = beat(r, seeds[lo], seeds[hi], False); bonus[wnr] += BONUS["wc"]; survivors.append(wnr)
            # Divisional: top seed hosts the lowest seed left
            survivors.sort(key=seeds.index)
            d1 = beat(r, survivors[3], survivors[0], False); d2 = beat(r, survivors[2], survivors[1], False)
            bonus[d1] += BONUS["div"]; bonus[d2] += BONUS["div"]
            hi, lo = sorted((d1, d2), key=seeds.index)
            champ = beat(r, lo, hi, False); bonus[champ] += BONUS["conf"]
            if cf == "AFC": afc = champ
            else: nfc = champ
        sb = beat(r, afc, nfc, True); bonus[sb] += BONUS["sb"]
        reg = {c: 0 for c in COACHES}; tot = {c: 0 for c in COACHES}
        for t, c in own.items():
            reg[c] += wins[t]; tot[c] += wins[t] + bonus[t]
        best = max(tot.values())
        top = [c for c in COACHES if tot[c] == best]
        if len(top) > 1:
            most = max(reg[c] for c in top); top = [c for c in top if reg[c] == most]
        share = 1 / len(top)
        for c in COACHES:
            finals[c].append(tot[c])
        for c in top:
            titles[c] += share
        for i, o in enumerate(nxt):
            cond_n[i][o] += 1
            for c in top:
                cond[i][o][c] += share
    pct = lambda x, n: round(100 * x / n, 1)
    out = {"win": [pct(titles[c], sims) for c in COACHES]}
    for q, name in ((0.1, "p10"), (0.9, "p90")):
        out[name] = [sorted(finals[c])[int(q * sims)] for c in COACHES]
    out["lev"] = [[[pct(cond[i][o][c], cond_n[i][o]) for c in COACHES] for o in (0, 1)] for i in range(len(next_games))]
    out["next"] = next_games
    if raw:
        out["finals"] = finals
    return out


def js(v):
    return str(v).replace("'", "")


if __name__ == "__main__":
    roster, results, vegas = site_data()
    n = len(results)
    now = simulate(roster, results, vegas, n, n + 1)
    before = simulate(roster, results, vegas, n - 1, n)
    for c, w, b, lo, hi in zip(COACHES, now["win"], before["win"], now["p10"], now["p90"]):
        print(f"{c:9} {w:5.1f}%  (a week ago {b:5.1f}%)  likely final {lo}-{hi}")
    print("sum", round(sum(now["win"]), 1))
    if "--write" in sys.argv:
        p = ROOT / "coaches.html"; s = p.read_text()
        page_next = [tuple(g.split("|")[1:]) for g in re.search(r"var NEXT = '([^']*)'", s).group(1).split(",")]
        assert page_next == now["next"], ("NEXT in coaches.html must list next week's games in schedule order", page_next, now["next"])
        s, k1 = re.subn(r"var WIN = \[[^\]]*\], W2 = \[[^\]]*\];", "var WIN = %s, W2 = %s;" % (now["win"], before["win"]), s)
        s, k2 = re.subn(r"var P10 = \[[^\]]*\], P90 = \[[^\]]*\];", "var P10 = %s, P90 = %s;" % (now["p10"], now["p90"]), s)
        s, k3 = re.subn(r"var LEV = \[\[\[.*?\]\]\];", "var LEV = %s;" % js(now["lev"]).replace(" ", ""), s, flags=re.S)
        assert (k1, k2, k3) == (1, 1, 1), (k1, k2, k3)
        p.write_text(s)
        print("wrote coaches.html")
