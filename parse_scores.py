#!/usr/bin/env python3
"""
Step 2 of 3: read the fork-rating tables out of the downloaded wiki pages.

Reads:   doughboys_pages.json (from scrape_wiki.py)
         doughboys_side_shows.json (optional; those pages are skipped)
Writes:  doughboys_forks.csv        one row per episode
         doughboys_forks_long.csv   one row per person per episode
         doughboys_unparsed.csv     pages left out, with the reason

How a page is read
  * The score section is the first section whose heading mentions "rating", "fork"
    or "score" ("Fork rating", "Spoon rating", "Pitchfork rating", ...).
  * Inside it, the table header ends with a "rating" cell. Every later cell that looks
    like "<number> <unit>" (4 forks, 2.5 spoons, 3 Morts) is a score, where the unit
    must be fork/spoon/knife/claw or a word from the section heading.
  * The person for a score is found in the cells since the previous score: an exact
    host or guest name first, then a fuzzy match on the episode's listed guests.
  * Nick is listed first and Mitch second; that order is used when Mitch appears
    under a persona ("Mr. Slice", "The Batspoonman").
  * People not listed as the episode's guest (producers, walk-ons) get role "Other"
    and are left out of the guest stats.

Episodes are kept when both Nick and Mitch have exactly one score. Scores above 5
are kept when the scale is forks; other scales above 5 (shopping carts) are dropped.

Setup:  pip install pandas
Run:    python parse_scores.py
"""
import collections, difflib, json, os, re

import pandas as pd

PAGES = "doughboys_pages.json"
SIDE = "doughboys_side_shows.json"
CREW = {"Emma Erdbrink", "Amelia Marino"}  # producers who sometimes score

RATING = re.compile(r"^(\d+(?:\.\d+)?)\s+([A-Za-z' ]{2,30}?)\s*\**$")


def lines(text):
    return [l.strip() for l in text.split("\n") if l.strip()]


def headings(L):
    # section headings render as "Heading", "[", "]" (the edit link)
    return [i for i in range(len(L) - 2) if L[i + 1] == "[" and L[i + 2] == "]"]


def info(L, key):
    """Value next to a label in the episode infobox (Episode Number, Release Date, Guest)."""
    for i, l in enumerate(L[:80]):
        if l == key:
            return L[i + 1]


def split_names(s):
    return [p.strip() for p in re.split(r",|&| and ", s or "") if p.strip()]


def role_of(name):
    if re.search(r"\bnick\b|wiger", name, re.I):
        return "Nick"
    if re.search(r"\bmitch|mike mitchell", name, re.I):
        return "Mitch"
    return "Guest"


def parse_page(text):
    L = lines(text)
    guests = split_names(info(L, "Guest") or info(L, "Guests"))
    known = [k.lower() for k in ["Nick Wiger", "Mike Mitchell"] + guests]
    gl = [g.lower() for g in guests]

    def is_guest(n):
        ws = re.findall(r"[a-z']+", n.lower())
        return any(difflib.SequenceMatcher(None, w, gw).ratio() >= 0.75
                   for g in gl for gw in g.split() for w in ws if len(w) > 2 and len(gw) > 2)

    H = headings(L)
    for j, i in enumerate(H):
        if re.search(r"rating|fork|score", L[i], re.I) and not re.search(r"non-canon|sleep", L[i], re.I):
            end = H[j + 1] if j + 1 < len(H) else len(L)
            head, S = L[i], L[i + 3:end]
            break
    else:
        return None, "no rating section", guests

    try:
        k = next(i for i, l in enumerate(S) if l.lower() in ("rating", "ratings", "score"))
    except StopIteration:
        return None, "no rating table", guests

    head_words = [w[:4] for w in re.findall(r"[a-z]{3,}", head.lower())
                  if w not in ("rating", "ratings", "and", "the", "with")]
    rows, start = [], k + 1
    for i in range(k + 1, len(S)):
        m = RATING.match(S[i])
        if not m:
            continue
        unit = m.group(2).lower()
        if not (re.search(r"fork|spoon|knife|knives|claw", unit) or any(w in unit for w in head_words)):
            continue
        span, start = S[start:i], i + 1
        name = next((l for l in span if l.lower() in known or (role_of(l) != "Guest" and len(l) < 25)), None)
        if name is None:
            name = next((l for l in span if len(l) < 40 and
                         any(set(l.lower().split()) & set(g.split()) for g in gl)), None)
        if name is None and span:
            name = span[0]
        if name:
            rows.append([name, role_of(name), float(m.group(1)), m.group(2)])

    taken = {r[1] for r in rows}
    for pos, want in ((0, "Nick"), (1, "Mitch")):
        if (len(rows) > pos and rows[pos][1] == "Guest" and want not in taken
                and not is_guest(rows[pos][0]) and rows[pos][0] not in CREW):
            rows[pos][1] = want
            taken.add(want)
    for r in rows:
        if r[1] == "Guest" and not is_guest(r[0]):
            r[1] = "Other"
    return {"head": head, "rows": rows}, None, guests


def clean_name(n):
    n = re.sub(r'"[^"]*"', "", n)              # Matt "The Tinefather" Selman -> Matt Selman
    n = re.sub(r"[^\w\s.'\-&]", "", n)         # drop emoji
    return re.sub(r"\s+", " ", n).strip()


def restaurant_of(title):
    r = re.split(r" with | vs\.? | v\. ", re.sub(r"^[^:]+: ", "", title))[0]
    r = re.sub(r"\s+\d+$|\s+(II|III|IV|IX|XVIII)$", "", r).replace("’", "'").replace("‘", "'")
    fix = {"Popeyes Louisiana Kitchen": "Popeyes", "Panera Bread": "Panera", "The Olive Garden": "Olive Garden",
           "Fat Burger": "Fatburger", "Habit Burger": "The Habit", "Dunkin' Donuts": "Dunkin'",
           "Chuck E. Cheese's": "Chuck E. Cheese"}
    return fix.get(r, r)


def main():
    pages = json.load(open(PAGES))
    side = set(json.load(open(SIDE))) if os.path.exists(SIDE) else set()
    wide, long, skipped = [], [], []
    for title, text in pages.items():
        if title in side:
            skipped.append((title, "side show")); continue
        L = lines(text)
        r, why, _ = parse_page(text)
        if r is None or not r["rows"]:
            skipped.append((title, why or "no scores")); continue
        roles = collections.Counter(x[1] for x in r["rows"])
        if roles["Nick"] != 1 or roles["Mitch"] != 1:
            skipped.append((title, "missing or multiple host scores")); continue
        if any(x[2] > 5 for x in r["rows"]) and not re.search(r"fork", r["head"], re.I):
            skipped.append((title, "non-fork scale above 5")); continue
        ep = info(L, "Episode Number") or ""
        if re.match(r"\s*[A-Za-z]", ep):   # "DD27" etc. = Doughboys Double
            skipped.append((title, "side-show episode number")); continue
        ep = int(re.match(r"\d+", ep).group()) if re.match(r"\d+", ep) else None
        date = pd.to_datetime(info(L, "Release Date"), errors="coerce")
        get = lambda k: [x for x in r["rows"] if x[1] == k]
        g = get("Guest")
        wide.append(dict(episode=title, ep_num=ep, date=date, restaurant=restaurant_of(title),
                         scale=r["head"], nick=get("Nick")[0][2], mitch=get("Mitch")[0][2],
                         guest_avg=sum(x[2] for x in g) / len(g) if g else None, n_guests=len(g),
                         guests="; ".join(clean_name(x[0]) for x in g), live="live" in title.lower()))
        for x in r["rows"]:
            long.append(dict(episode=title, ep_num=ep, date=date, person=clean_name(x[0]),
                             role=x[1], forks=x[2]))
    df = pd.DataFrame(wide).sort_values(["date", "ep_num"])
    pd.DataFrame(long).to_csv("doughboys_forks_long.csv", index=False)
    df.to_csv("doughboys_forks.csv", index=False)
    pd.DataFrame(skipped, columns=["page", "reason"]).to_csv("doughboys_unparsed.csv", index=False)
    print(f"{len(df)} episodes -> doughboys_forks.csv")
    print(pd.Series([s[1] for s in skipped]).value_counts().to_string())


if __name__ == "__main__":
    main()
