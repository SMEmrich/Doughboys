#!/usr/bin/env python3
"""
Step 1 of 3: download every Doughboys episode page from the fandom wiki.

Writes:
  doughboys_pages.json        page title -> plain text of the page
  doughboys_side_shows.json   titles filed under Doughboys Double / Bread Cast etc.

Re-running only downloads pages that aren't already in doughboys_pages.json.

Setup:  pip install requests beautifulsoup4
Run:    python scrape_wiki.py
"""
import json, os, re, sys, time

import requests
from bs4 import BeautifulSoup

API = "https://doughboys.fandom.com/api.php"
LIST_PAGE = "Doughboys_Episode_List"
CACHE = "doughboys_pages.json"
SIDE_CACHE = "doughboys_side_shows.json"
HEADERS = {"User-Agent": "doughboys-fork-stats/1.0 (personal fan analysis)"}



def api(session, **params):
    params.update(format="json", formatversion=2)
    for attempt in range(4):
        r = session.get(API, params=params, headers=HEADERS, timeout=30)
        if r.status_code == 200:
            return r.json()
        time.sleep(2 * (attempt + 1))
    r.raise_for_status()


def list_page_links(session, page):
    data = api(session, action="parse", page=page, prop="links")
    return [l["title"] for l in data["parse"]["links"] if l.get("ns") == 0 and l.get("exists", True)]


def category_members(session, cat):
    out, cont = [], {}
    while True:
        d = api(session, action="query", list="categorymembers", cmtitle=cat, cmlimit=500,
                cmnamespace=0, **cont)
        out += [m["title"] for m in d["query"]["categorymembers"]]
        if "continue" not in d:
            return out
        cont = {"cmcontinue": d["continue"]["cmcontinue"]}


def episode_titles(session):
    """Every candidate episode page: links from the episode list (and any sub-lists it
    links to), plus members of every wiki category with 'episode' in its name.
    Pages without both host scores just land in the unparsed file."""
    titles = set(list_page_links(session, LIST_PAGE))
    for sub in [t for t in titles if re.search(r"episode|list|season|\b20\d\d\b", t, re.I)]:
        try:
            titles |= set(list_page_links(session, sub))
        except Exception:
            pass
    cats, cont = [], {}
    while True:
        d = api(session, action="query", list="allcategories", aclimit=500, **cont)
        cats += [c["category"] for c in d["query"]["allcategories"]]
        if "continue" not in d:
            break
        cont = {"accontinue": d["continue"]["accontinue"]}
    ep_cats = [c for c in cats if re.search(r"episode", c, re.I)]
    print(f"  episode categories found: {', '.join(ep_cats) or 'none'}")
    side = set()  # Doughboys Double / Bread Cast / other non-main-feed shows
    for c in ep_cats:
        members = set(category_members(session, "Category:" + c))
        titles |= members
        if re.search(r"double|bread|patreon|bonus|spoonfed", c, re.I):
            side |= members
    for c in cats:  # also tag side-show pages that sit in non-"episode" categories
        if re.search(r"doughboys double|bread ?cast", c, re.I) and c not in ep_cats:
            side |= set(category_members(session, "Category:" + c))
    json.dump(sorted(side), open(SIDE_CACHE, "w"))
    print(f"  {len(side)} pages tagged as side shows (Double / Bread Cast etc.), excluded unless --all-feeds")
    return sorted(titles)


def fetch_pages(titles):
    cache = {}
    if os.path.exists(CACHE):
        cache = json.load(open(CACHE))
    s = requests.Session()
    todo = [t for t in titles if t not in cache]
    for i, t in enumerate(todo, 1):
        try:
            html = api(s, action="parse", page=t, prop="text")["parse"]["text"]
            cache[t] = BeautifulSoup(html, "html.parser").get_text("\n")
        except Exception as e:
            print(f"  ! {t}: {e}", file=sys.stderr)
        if i % 25 == 0:
            print(f"  fetched {i}/{len(todo)}")
            json.dump(cache, open(CACHE, "w"))
        time.sleep(0.4)  # be polite to Fandom
    json.dump(cache, open(CACHE, "w"))
    return cache



if __name__ == "__main__":
    s = requests.Session()
    print("Reading episode list and episode categories…")
    titles = episode_titles(s)
    print(f"{len(titles)} candidate pages; downloading (cached in {CACHE})…")
    pages = fetch_pages(titles)
    print(f"Done: {len(pages)} pages in {CACHE}")
