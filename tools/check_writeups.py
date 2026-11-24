#!/usr/bin/env python3
"""Recompute every write-up number from RESULTS and report mismatches.

Checks weeks 1-11, phone and desktop pages, plus share pages:
  weekly records, season totals, ranks, rank moves,
  "from X to Y" / "up from" rank claims, leads, best and worst weeks,
  and that every ledger score is a real result.
  Also checks his/her/my before a team name: the pronoun has to be that
  team's owner, and in a preview the owner's name has to be in the sentence.
"""
import re, sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
ROSTER = {
    "Nicole": ["LAR", "CHI", "DAL", "ARI"], "Luke": ["PHI", "JAX", "PIT", "TEN"],
    "Virginia": ["BUF", "CIN", "TB", "CLE"], "Jack": ["SEA", "GB", "IND", "LV"],
    "Caleb": ["DEN", "NE", "NO", "NYJ"], "Court": ["SF", "LAC", "WAS", "MIA"],
    "Drew": ["BAL", "DET", "MIN", "ATL"], "Mike": ["HOU", "KC", "NYG", "CAR"],
}
OWN = {t: c for c, ts in ROSTER.items() for t in ts}
C = list(ROSTER)
ORDS = {"first": 1, "second": 2, "third": 3, "fourth": 4, "fifth": 5, "sixth": 6, "seventh": 7, "eighth": 8}
LEAD_WORDS = {
    "a game and a half": 1.5, "half a point": 0.5, "a point": 1.0,
    "one": 1, "two": 2, "three": 3, "four": 4, "1.5": 1.5,
}

def results():
    text = (ROOT / "week.html").read_text()
    raw = "".join(re.findall(r"'([^']*)'", text.split("var RESULTS = ")[1].split(";")[0]))
    weeks = []
    for w in raw.split("/"):
        games = []
        for g in w.split(","):
            if not g.strip():
                continue
            a, h, sa, sh = g.split()
            games.append((a, h, int(sa), int(sh)))
        weeks.append(games)
    return weeks

def compute(weeks):
    pts = {c: 0.0 for c in C}
    out = []
    prev = None
    for games in weeks:
        rec = {c: [0, 0, 0] for c in C}
        for a, h, sa, sh in games:
            oa, oh = OWN[a], OWN[h]
            if sa == sh:
                pts[oa] += 0.5; pts[oh] += 0.5; rec[oa][2] += 1; rec[oh][2] += 1
            elif sa > sh:
                pts[oa] += 1; rec[oa][0] += 1; rec[oh][1] += 1
            else:
                pts[oh] += 1; rec[oh][0] += 1; rec[oa][1] += 1
        rank = {c: 1 + sum(pts[d] > pts[c] for d in C) for c in C}
        order = sorted(C, key=lambda c: (-pts[c], c))
        def fmt(r):
            return f"{r[0]}-{r[1]}" + (f"-{r[2]}" if r[2] else "")
        wk = {c: rec[c][0] + rec[c][2] / 2 for c in C}
        leaders = [c for c in order if rank[c] == 1]
        rest = [pts[c] for c in C if rank[c] > 1]
        lead = (pts[leaders[0]] - max(rest)) if rest else 0
        out.append({
            "pts": dict(pts), "rec": {c: fmt(rec[c]) for c in C}, "rank": rank, "prev": prev,
            "order": order, "wkpts": wk, "lead": lead, "best": max(wk.values()), "worst": min(wk.values()),
            "games": games,
        })
        prev = rank
    return out

def parse_rows(text):
    m = re.search(r"var standings = \[(.*?)\]", text, re.S)
    if not m:
        return None
    rows = []
    for row in re.findall(r"\[(.*?)\]", m.group(1)):
        parts = [p.strip().strip('"').strip("'") for p in row.split(",")]
        if len(parts) >= 6 and parts[1][:1].isalpha():
            rows.append(parts[:6])
    return rows

def parse_ledger(text):
    m = re.search(r"var ledger = \[(.*?)\]", text, re.S)
    if not m:
        return []
    games = []
    for row in re.findall(r"\[(.*?)\]", m.group(1)):
        parts = [p.strip().strip('"').strip("'") for p in row.split(",")]
        if len(parts) >= 7 and parts[1] in OWN:
            games.append((parts[1], parts[4], int(parts[3]), int(parts[6])))
    return games

def strip(html):
    body = re.split(r"<script type=\"text/x-dc\"", html)[0]
    body = re.sub(r"<script[\s\S]*?</script>", " ", body)
    text = re.sub(r"<[^>]+>", " ", body)
    return re.sub(r"\s+", " ", text)

def notes_of(html):
    """coach -> prose, from phone articles or desktop notesText. Awards are (who, text)."""
    out = {}
    if "var notesText" in html:
        m = re.search(r"var notesText = \{(.*?)\n    \};", html, re.S)
        if m:
            for name, text in re.findall(r"(\w+): \"(.*?)\"", m.group(1)):
                out[name] = text
        m = re.search(r"var awards = \[(.*?)\]", html, re.S)
        if m:
            for who, title, text in re.findall(r"\[\s*\"(\w+)\"\s*,\s*\"(.*?)\"\s*,\s*\"(.*?)\"\s*\]", m.group(1)):
                out.setdefault("_awards", []).append((who, title + " " + text))
    else:
        for art in re.findall(r"<article[\s\S]*?</article>", html):
            name = re.search(r"<b[^>]*>([^<]+)</b>", art)
            who = re.search(r'color: var\(--gold\)">([^<]+)</span>', art)
            paras = re.findall(r"<p[^>]*>(.*?)</p>", art, re.S)
            h3 = re.search(r"<h3[^>]*>(.*?)</h3>", art, re.S)
            blob = " ".join(re.sub(r"<[^>]+>", "", p) for p in paras)
            if h3 and who:
                out.setdefault("_awards", []).append((who.group(1), re.sub(r"<[^>]+>", "", h3.group(1)) + " " + blob))
            elif name and not h3:
                out[name.group(1)] = blob
    # The hero summary is its own blob, checked sentence by sentence.
    sm = re.search(r'text-wrap: pretty">(.*?)</p>', html)
    if sm:
        out["_summary"] = re.sub(r"<[^>]+>", "", sm.group(1))
    return out

RANK_RE = re.compile(
    r"(?:from|up from|climbed from|jumped from|dropped from)\s+"
    r"(?:an?\s+)?(?:tie for\s+)?(first|second|third|fourth|fifth|sixth|seventh|eighth)"
    r"\s+to\s+(?:an?\s+)?(?:tie for\s+)?(first|second|third|fourth|fifth|sixth|seventh|eighth)",
    re.I,
)
# "Second to third", "Second to a tie for third"
SHORT_RE = re.compile(
    r"\b(First|Second|Third|Fourth|Fifth|Sixth|Seventh|Eighth)\s+to\s+(?:a tie for\s+)?"
    r"(first|second|third|fourth|fifth|sixth|seventh|eighth)\b",
    re.I,
)

def check_file(path, truth, errors):
    html = path.read_text()
    m = re.search(r"Week (\d+)", path.name)
    # share pages and week pages
    wk = None
    km = re.search(r"Week (\d+) ·", html) or re.search(r"AFTER WEEK (\d+)", html)
    if km:
        wk = int(km.group(1))
    elif m:
        wk = int(m.group(1))
    if not wk or wk > len(truth):
        errors.append(f"{path.name}: could not tell which week")
        return
    T = truth[wk - 1]
    rows = parse_rows(html)
    if rows:
        for rk, name, teams, rec, pts, mv in rows:
            pts, mv = float(pts), int(mv)
            tied = any(d != name and T["rank"][d] == T["rank"][name] for d in C)
            exp_rk = ("T" if tied else "") + str(T["rank"][name])
            exp_mv = 0 if not T["prev"] else T["prev"][name] - T["rank"][name]
            if rk != exp_rk or rec != T["rec"][name] or abs(pts - T["pts"][name]) > 1e-9 or mv != exp_mv:
                errors.append(f"{path.name}: {name} row {rk} {rec} {pts} mv {mv} != {exp_rk} {T['rec'][name]} {T['pts'][name]} mv {exp_mv}")
            if teams.replace(" · ", " ") != " ".join(ROSTER[name]) and teams != " ".join(ROSTER[name]):
                errors.append(f"{path.name}: {name} teams {teams!r}")
    ledger = parse_ledger(html)
    if ledger:
        got = {(a, h, sa, sh) for a, h, sa, sh in ledger}
        exp = {(a, h, sa, sh) for a, h, sa, sh in T["games"]}
        if got != exp:
            errors.append(f"{path.name}: ledger games differ: missing {sorted(exp-got)} extra {sorted(got-exp)}")
    # rank phrases inside each coach note and award
    notes = notes_of(html)
    hero = strip(html)
    blobs = []
    for name, text in notes.items():
        if name == "_awards":
            for who, text in text:
                blobs.append((who if who != "Me" else "Jack", text, True))
        elif name == "_summary":
            blobs.append((None, text, False))
        else:
            blobs.append((name, text, True))
    for coach, text, owned in blobs:
        for rx in (RANK_RE, SHORT_RE):
            for m in rx.finditer(text):
                a, b = ORDS[m.group(1).lower()], ORDS[m.group(2).lower()]
                who = coach
                if not owned:
                    sent = text[max(0, text.rfind(".", 0, m.start()) + 1): text.find(".", m.end()) if text.find(".", m.end()) != -1 else m.end()]
                    names = [c for c in C if re.search(r"\b" + c + r"\b", sent)]
                    who = names[0] if len(names) == 1 else None
                if not who or who not in T["rank"]:
                    continue
                prev = T["prev"][who] if T["prev"] else None
                cur = T["rank"][who]
                if prev is None:
                    errors.append(f"{path.name}: rank phrase for {who} before any prior week: {m.group(0)}")
                elif prev != a or cur != b:
                    errors.append(f"{path.name}: {who} {m.group(0)!r} but moved {prev} -> {cur}")
    # best / worst
    low = hero.lower()
    if "worst week" in low:
        # the coach whose note says it, if any, should have the worst weekly points
        for name, text in notes.items():
            if name in T["wkpts"] and "worst week" in text.lower():
                if T["wkpts"][name] != T["worst"]:
                    errors.append(f"{path.name}: {name} called worst but week points {T['wkpts'][name]} best-or-worst range {T['worst']}-{T['best']}")
    if "best week" in low:
        for name, text in notes.items():
            if name in T["wkpts"] and "best week" in text.lower():
                if T["wkpts"][name] != T["best"]:
                    errors.append(f"{path.name}: {name} called best but week points {T['wkpts'][name]} != {T['best']}")
        for who, text in notes.get("_awards", []):
            who = "Jack" if who == "Me" else who
            if "best week" in text.lower() and who in T["wkpts"] and T["wkpts"][who] != T["best"]:
                errors.append(f"{path.name}: award calls {who} best but {T['wkpts'][who]} != {T['best']}")

NICK = {
    "Ravens": "Drew", "Lions": "Drew", "Vikings": "Drew", "Falcons": "Drew",
    "Texans": "Mike", "Chiefs": "Mike", "Giants": "Mike", "Panthers": "Mike",
    "Bills": "Virginia", "Bengals": "Virginia", "Buccaneers": "Virginia", "Bucs": "Virginia", "Browns": "Virginia",
    "Broncos": "Caleb", "Patriots": "Caleb", "Saints": "Caleb", "Jets": "Caleb",
    "Seahawks": "Jack", "Packers": "Jack", "Colts": "Jack", "Raiders": "Jack",
    "Eagles": "Luke", "Jaguars": "Luke", "Steelers": "Luke", "Titans": "Luke",
    "Rams": "Nicole", "Bears": "Nicole", "Cowboys": "Nicole", "Cardinals": "Nicole",
    "49ers": "Court", "Chargers": "Court", "Commanders": "Court", "Dolphins": "Court",
}
WOMEN = {"Virginia", "Nicole", "Court"}
POSS = re.compile(
    r"\b((?:his|her|my)(?: own)?)\s+(" + "|".join(sorted(NICK, key=len, reverse=True)) + r")\b",
    re.I,
)

def sentence_around(body, pos):
    prev = 0
    for m in re.finditer(r"\.(?!\d)\s+", body[:pos]):
        prev = m.end()
    nxt = re.search(r"\.(?!\d)", body[pos:])
    end = pos + nxt.start() if nxt else len(body)
    return body[prev:end].strip()

def prose_chunks(html):
    """(section coach or None, text). Section is the coach a note or award is about."""
    chunks = []
    if "var notesText" in html:
        m = re.search(r"var notesText = \{(.*?)\n    \};", html, re.S)
        if m:
            for name, body in re.findall(r'(\w+): "(.*?)"', m.group(1)):
                chunks.append((name, body))
        m = re.search(r"var awards = \[(.*?)\]\.map", html, re.S)
        if m:
            for who, title, body in re.findall(r'\[\s*"(\w+)"\s*,\s*"(.*?)"\s*,\s*"(.*?)"\s*\]', m.group(1)):
                chunks.append(("Jack" if who == "Me" else who, title + " " + body))
        for body in re.findall(r'line-height: 1\.5">(.*?)</span>', html):
            chunks.append((None, re.sub(r"<[^>]+>", "", body)))
    else:
        for art in re.findall(r"<article[\s\S]*?</article>", html):
            b = re.search(r"<b[^>]*>([^<]+)</b>", art)
            who = re.search(r'color: var\(--gold\)">([^<]+)</span>', art)
            h3 = re.search(r"<h3[^>]*>(.*?)</h3>", art)
            paras = " ".join(re.sub(r"<[^>]+>", "", x) for x in re.findall(r"<p[^>]*>(.*?)</p>", art, re.S))
            if h3 and who:
                w = who.group(1)
                chunks.append(("Jack" if w == "Me" else w, re.sub(r"<[^>]+>", "", h3.group(1)) + " " + paras))
            elif b:
                chunks.append((b.group(1).replace(" (me)", ""), paras))
        for body in re.findall(r'line-height: 1\.45">(.*?)</span>', html):
            chunks.append((None, re.sub(r"<[^>]+>", "", body)))
        sm = re.search(r'text-wrap: pretty">(.*?)</p>', html)
        if sm:
            chunks.append((None, re.sub(r"<[^>]+>", "", sm.group(1))))
    return chunks

def check_possessives(path, errors):
    """his/her/my before a team must be that team's owner.

    Inside a coach's note, the pronoun has to be that coach (or "my" for Jack).
    In a summary or preview, the owner's name has to be in the same sentence.
    """
    if not re.match(r"week\d+", path.name):
        return
    for sec, body in prose_chunks(path.read_text()):
        for m in POSS.finditer(body):
            pron, team = m.group(1).lower(), m.group(2)
            team = next(k for k in NICK if k.lower() == team.lower())
            owner = NICK[team]
            sent = sentence_around(body, m.start())
            if pron == "my" or pron == "my own":
                if owner != "Jack":
                    errors.append(f"{path.name}: “my {team}” but {team} is {owner}'s ({sent})")
                continue
            expect = "her" if owner in WOMEN else "his"
            if not pron.startswith(expect):
                errors.append(f"{path.name}: “{m.group(1)} {team}” should be {expect}, {owner} owns the {team} ({sent})")
                continue
            if sec:
                if owner != sec:
                    errors.append(f"{path.name}: {sec}'s note says “{m.group(1)} {team}”, which is {owner}'s ({sent})")
            else:
                names = re.findall(r"\b(Nicole|Luke|Virginia|Jack|Caleb|Court|Drew|Mike)\b", sent)
                if owner not in names:
                    errors.append(f"{path.name}: “{m.group(1)} {team}” with no {owner} in the sentence ({sent})")

def main():
    weeks = results()
    if len(weeks) < 11 or len(weeks[10]) != 13:
        print(f"FAIL results: {len(weeks)} weeks, week 11 has {len(weeks[10]) if len(weeks)>10 else 0} games (want 13, including CIN-WAS)")
        return 1
    truth = compute(weeks)
    errors = []
    pages = []
    for n in range(1, 12):
        for suffix in (f"week{n}.html", f"week{n}-desktop.html"):
            p = ROOT / suffix
            if not p.exists():
                errors.append(f"missing {suffix}")
            else:
                pages.append(p)
    for name in ("share.html", "share-week10.html", "share-week9.html", "share-week8.html",
                 "share-week7.html", "share-week6.html", "share-week5.html", "share-week4.html",
                 "share-week3.html", "share-week2.html", "share-week1.html"):
        p = ROOT / name
        if p.exists():
            pages.append(p)
        elif name in ("share.html", "share-week10.html", "share-week1.html", "share-week2.html"):
            errors.append(f"missing {name}")
    for p in pages:
        check_file(p, truth, errors)
        check_possessives(p, errors)
    # headlines in week.html INFO vs h1
    info = re.findall(r"headline: '([^']*)'", (ROOT / "week.html").read_text())
    for n in range(1, 12):
        h = re.search(r"<h1[^>]*>(.*?)</h1>", (ROOT / f"week{n}.html").read_text(), re.S)
        h1 = re.sub(r"<[^>]+>", "", h.group(1)).strip() if h else ""
        if n - 1 < len(info) and info[n - 1] != h1:
            errors.append(f"week.html INFO[{n}] {info[n-1]!r} != h1 {h1!r}")
    posted = re.search(r"var POSTED = (\d+)", (ROOT / "week.html").read_text())
    if not posted or posted.group(1) != "11":
        errors.append(f"POSTED is {posted.group(1) if posted else '?'}, want 11")
    if errors:
        print(f"FAIL {len(errors)}")
        for e in errors:
            print(" -", e)
        return 1
    print("OK", len(pages), "pages match RESULTS through week", len(weeks))
    # print the table so a reader can see what was checked
    for i, T in enumerate(truth, 1):
        top = T["order"][0]
        print(f"  week {i}: lead {T['lead']} ({', '.join(c for c in T['order'] if T['rank'][c]==1)} {T['pts'][top]}) best {T['best']} worst {T['worst']}")
    return 0

if __name__ == "__main__":
    sys.exit(main())
