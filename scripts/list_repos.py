import os, re, requests, sys
from datetime import datetime, timezone

USER = os.getenv("GH_USER", "vaibhavjais2503")
TOKEN = os.getenv("GITHUB_TOKEN", "")

# -------- settings you can tweak ----------
CARDS_PER_ROW = 2             # 2 big cards per row (nice and bold)
MAX_CARDS = None              # set to an int (e.g., 24) to limit, or None for ALL
PIN_THEME = "tokyonight"      # dark theme for cards
# -----------------------------------------

API = f"https://api.github.com/users/{USER}/repos?per_page=100&type=owner&sort=updated"

headers = {"Accept": "application/vnd.github+json"}
if TOKEN:
    headers["Authorization"] = f"Bearer {TOKEN}"

# fetch all repos (with pagination)
repos = []
url = API
while url:
    r = requests.get(url, headers=headers, timeout=30)
    r.raise_for_status()
    repos.extend(r.json())
    nxt = None
    if "link" in r.headers:
        for part in r.headers["link"].split(","):
            seg, rel = part.split(";")
            if 'rel="next"' in rel:
                nxt = seg.strip()[1:-1]
    url = nxt

# sort: stars desc, then recent update
repos.sort(key=lambda x: (x.get("stargazers_count", 0), x.get("updated_at", "")), reverse=True)

if MAX_CARDS is not None:
    repos_for_cards = repos[:MAX_CARDS]
else:
    repos_for_cards = repos

def table_row(r):
    name = r["name"]
    html = r["html_url"]
    desc = (r.get("description") or "").strip()
    if len(desc) > 80:
        desc = desc[:77] + "..."
    stars = r.get("stargazers_count", 0)
    lang = r.get("language") or "-"
    updated = r.get("updated_at")
    if updated:
        try:
            dt = datetime.fromisoformat(updated.replace("Z", "+00:00")).astimezone(timezone.utc)
            updated = dt.strftime("%Y-%m-%d")
        except Exception:
            pass
    return f"| [{name}]({html}) | {lang} | ⭐ {stars} | {updated} | {desc} |"

def make_cards_grid(rs):
    if not rs:
        return "_No public repositories found._"
    cards = []
    for r in rs:
        name = r["name"]
        html = r["html_url"]
        img = f"https://github-readme-stats.vercel.app/api/pin/?username={USER}&repo={name}&theme={PIN_THEME}&hide_border=true"
        cards.append(f'<a href="{html}"><img src="{img}" /></a>')
    # group into rows
    rows = []
    for i in range(0, len(cards), CARDS_PER_ROW):
        rows.append('<p align="center">\n  ' + "\n  ".join(cards[i:i+CARDS_PER_ROW]) + "\n</p>")
    return "\n".join(rows)

# build outputs
table_header = (
    "| Repository | Language | Stars | Last Update | Description |\n"
    "|---|---:|---:|---:|---|\n"
)
table_rows = "\n".join(table_row(r) for r in repos)
table_md = table_header + table_rows if repos else "_No public repositories found._"
cards_md = make_cards_grid(repos_for_cards)

# replace in README
readme_path = "README.md"
with open(readme_path, "r", encoding="utf-8") as f:
    readme = f.read()

def replace_block(text, start, end, content, required=True):
    pat = re.compile(re.escape(start) + r".*?" + re.escape(end), re.S)
    if not pat.search(text):
        if required:
            print(f"Markers not found: {start} ... {end}", file=sys.stderr)
            sys.exit(1)
        return text
    return pat.sub(start + "\n" + content + "\n" + end, text)

# cards
readme = replace_block(
    readme,
    "<!--AUTO-PIN-CARDS:START-->",
    "<!--AUTO-PIN-CARDS:END-->",
    cards_md,
    required=True,
)
# table
readme = replace_block(
    readme,
    "<!--AUTO-REPO-LIST:START-->",
    "<!--AUTO-REPO-LIST:END-->",
    table_md,
    required=True,
)

with open(readme_path, "w", encoding="utf-8") as f:
    f.write(readme)

print(f"Updated README with {len(repos)} repositories and {len(repos_for_cards)} cards.")

