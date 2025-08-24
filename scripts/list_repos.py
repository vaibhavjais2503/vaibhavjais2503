import os, re, requests, sys
from datetime import datetime, timezone

USER = os.getenv("GH_USER", "vaibhavjais2503")
TOKEN = os.getenv("GITHUB_TOKEN", "")

API = f"https://api.github.com/users/{USER}/repos?per_page=100&type=owner&sort=updated"

headers = {"Accept": "application/vnd.github+json"}
if TOKEN:
    headers["Authorization"] = f"Bearer {TOKEN}"

repos = []
url = API
while url:
    r = requests.get(url, headers=headers, timeout=30)
    r.raise_for_status()
    repos.extend(r.json())
    # pagination
    nxt = None
    if "link" in r.headers:
        for part in r.headers["link"].split(","):
            seg, rel = part.split(";")
            if 'rel="next"' in rel:
                nxt = seg.strip()[1:-1]
    url = nxt

# Sort: stars desc, then recently updated
repos.sort(key=lambda x: (x.get("stargazers_count", 0), x.get("updated_at", "")), reverse=True)

def row(r):
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

table_header = (
    "| Repository | Language | Stars | Last Update | Description |\n"
    "|---|---:|---:|---:|---|\n"
)
table_rows = "\n".join(row(r) for r in repos)

generated = table_header + table_rows if repos else "_No public repositories found._"

readme_path = "README.md"
with open(readme_path, "r", encoding="utf-8") as f:
    readme = f.read()

start = "<!--AUTO-REPO-LIST:START-->"
end = "<!--AUTO-REPO-LIST:END-->"
import re as _re
pattern = _re.compile(_re.escape(start) + r".*?" + _re.escape(end), _re.S)
replacement = start + "\n" + generated + "\n" + end

if not pattern.search(readme):
    print("Markers not found in README.md; make sure they exist.", file=sys.stderr)
    sys.exit(1)

readme = pattern.sub(replacement, readme)

with open(readme_path, "w", encoding="utf-8") as f:
    f.write(readme)

print(f"Updated README with {len(repos)} repositories.")
