#!/usr/bin/env python3
"""Render an ASCII art panel with the languages I use most and inject it
into README.md between the ASCII-STATS markers.

Env vars:
  GITHUB_TOKEN    token used for the GitHub API (required in CI)
  GH_USER         profile owner (default: dryingcore)
  TOP_N           how many languages to list before grouping into "Other"
  EXCLUDE_LANGS   comma separated languages to ignore (e.g. "HTML,CSS")
  README_PATH     file to update (default: README.md)
  STATS_JSON      optional path to a JSON file with fake data, for local tests
"""
import json
import os
import re
import sys
import urllib.request
from datetime import datetime, timezone

USER = os.environ.get("GH_USER", "dryingcore")
TOKEN = os.environ.get("GITHUB_TOKEN", "")
TOP_N = int(os.environ.get("TOP_N", "8"))
EXCLUDE = {l.strip().lower() for l in os.environ.get("EXCLUDE_LANGS", "").split(",") if l.strip()}
README = os.environ.get("README_PATH", "README.md")

START = "<!-- ASCII-STATS:START -->"
END = "<!-- ASCII-STATS:END -->"

WIDTH = 58


def api(path):
    req = urllib.request.Request(f"https://api.github.com{path}")
    req.add_header("Accept", "application/vnd.github+json")
    if TOKEN:
        req.add_header("Authorization", f"Bearer {TOKEN}")
    with urllib.request.urlopen(req) as res:
        return json.load(res)


def collect():
    user = api(f"/users/{USER}")
    repos, page = [], 1
    while True:
        batch = api(f"/users/{USER}/repos?per_page=100&type=owner&page={page}")
        repos += batch
        if len(batch) < 100:
            break
        page += 1

    own = [r for r in repos if not r["fork"] and not r.get("archived")]
    langs = {}
    for r in own:
        for lang, size in api(f"/repos/{USER}/{r['name']}/languages").items():
            langs[lang] = langs.get(lang, 0) + size

    return {
        "langs": langs,
        "repos": len(own),
        "stars": sum(r["stargazers_count"] for r in own),
        "followers": user.get("followers", 0),
        "since": user.get("created_at", "")[:4],
    }


def banner(text):
    try:
        import pyfiglet
        art = pyfiglet.figlet_format(text, font="small", width=WIDTH)
    except Exception:
        art = f"[ {text} ]\n"
    return [line.rstrip() for line in art.rstrip("\n").split("\n")]


def box(lines):
    top = "+" + "-" * (WIDTH + 2) + "+"
    body = [f"| {line[:WIDTH].ljust(WIDTH)} |" for line in lines]
    return [top, *body, top]


def render(data):
    langs = {k: v for k, v in data["langs"].items() if k.lower() not in EXCLUDE}
    total = sum(langs.values()) or 1
    ranked = sorted(langs.items(), key=lambda kv: kv[1], reverse=True)
    top, rest = ranked[:TOP_N], ranked[TOP_N:]
    if rest:
        top.append(("Other", sum(v for _, v in rest)))

    fav = ranked[0][0] if ranked else "Hello"
    lines = [*banner(fav), "", f"> linguagem mais usada: {fav}", ""]

    name_w = max([len(n) for n, _ in top] + [5])
    bar_w = WIDTH - name_w - 9
    for name, size in top:
        pct = size / total * 100
        filled = round(pct / 100 * bar_w)
        bar = "█" * filled + "░" * (bar_w - filled)
        lines.append(f"{name.ljust(name_w)}  {bar} {pct:5.1f}%")

    lines += [
        "",
        f"repos: {data['repos']}   stars: {data['stars']}   "
        f"followers: {data['followers']}   since: {data['since']}",
    ]

    updated = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    footer = f"  updated {updated} · {USER}@github:~$ _"
    return "\n".join(["```text", *box(lines), footer, "```"])


def main():
    if os.environ.get("STATS_JSON"):
        with open(os.environ["STATS_JSON"]) as f:
            data = json.load(f)
    else:
        data = collect()

    block = render(data)
    with open(README) as f:
        readme = f.read()

    pattern = re.compile(re.escape(START) + r".*?" + re.escape(END), re.S)
    if not pattern.search(readme):
        sys.exit(f"markers {START} / {END} not found in {README}")

    new = pattern.sub(lambda _: f"{START}\n{block}\n{END}", readme)
    with open(README, "w") as f:
        f.write(new)
    print(block)


if __name__ == "__main__":
    main()
