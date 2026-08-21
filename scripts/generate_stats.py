#!/usr/bin/env python3
"""
Fetches live GitHub stats (repos, commits, followers, stars) for a user
and renders them into the custom dark-tech themed stats.svg template.

Requires:
  - env var GH_USERNAME   -> your GitHub username
  - env var GH_TOKEN      -> a token with `read:user` + `repo` scope
                             (repo scope needed to count private commits too;
                              use `public_repo` if you only want public stats)
"""

import os
import sys
import datetime
import requests

GITHUB_API = "https://api.github.com/graphql"
USERNAME = os.environ["GH_USERNAME"]
TOKEN = os.environ["GH_TOKEN"]

HEADERS = {
    "Authorization": f"bearer {TOKEN}",
    "Content-Type": "application/json",
}


def gql(query: str, variables: dict) -> dict:
    resp = requests.post(
        GITHUB_API,
        json={"query": query, "variables": variables},
        headers=HEADERS,
        timeout=30,
    )
    resp.raise_for_status()
    data = resp.json()
    if "errors" in data:
        raise RuntimeError(data["errors"])
    return data["data"]


# ---- 1. Basic profile info: repos, followers, join year ----------------
PROFILE_QUERY = """
query($login: String!) {
  user(login: $login) {
    createdAt
    followers { totalCount }
    repositories(ownerAffiliations: OWNER, isFork: false) {
      totalCount
    }
  }
}
"""

profile = gql(PROFILE_QUERY, {"login": USERNAME})["user"]
followers = profile["followers"]["totalCount"]
repo_count = profile["repositories"]["totalCount"]
created_year = int(profile["createdAt"][:4])
current_year = datetime.datetime.utcnow().year


# ---- 2. Total stars across all owned, non-fork repos --------------------
STARS_QUERY = """
query($login: String!, $after: String) {
  user(login: $login) {
    repositories(first: 100, after: $after, ownerAffiliations: OWNER, isFork: false) {
      nodes { stargazerCount }
      pageInfo { hasNextPage endCursor }
    }
  }
}
"""

total_stars = 0
after = None
while True:
    data = gql(STARS_QUERY, {"login": USERNAME, "after": after})["user"]["repositories"]
    total_stars += sum(n["stargazerCount"] for n in data["nodes"])
    if not data["pageInfo"]["hasNextPage"]:
        break
    after = data["pageInfo"]["endCursor"]


# ---- 3. Total commit contributions (all years, public + private) --------
COMMITS_QUERY = """
query($login: String!, $from: DateTime!, $to: DateTime!) {
  user(login: $login) {
    contributionsCollection(from: $from, to: $to) {
      totalCommitContributions
      restrictedContributionsCount
    }
  }
}
"""

total_commits = 0
for year in range(created_year, current_year + 1):
    from_dt = f"{year}-01-01T00:00:00Z"
    to_dt = f"{year}-12-31T23:59:59Z"
    cc = gql(COMMITS_QUERY, {"login": USERNAME, "from": from_dt, "to": to_dt})["user"][
        "contributionsCollection"
    ]
    total_commits += cc["totalCommitContributions"] + cc["restrictedContributionsCount"]


print(f"repos={repo_count} commits={total_commits} followers={followers} stars={total_stars}")


# ---- 4. Render into the SVG template -------------------------------------
SVG_TEMPLATE = """<?xml version="1.0" encoding="UTF-8"?>
<svg xmlns="http://www.w3.org/2000/svg" width="900" height="520" viewBox="0 0 900 520">
<defs>
<linearGradient id="bg" x1="0" y1="0" x2="1" y2="1">
<stop offset="0%" stop-color="#0a0a0a"/><stop offset="100%" stop-color="#131418"/>
</linearGradient>
<linearGradient id="accent" x1="0" y1="0" x2="1" y2="0">
<stop offset="0%" stop-color="#38bdf8"/><stop offset="100%" stop-color="#0ea5e9"/>
</linearGradient>
<pattern id="grid" width="30" height="30" patternUnits="userSpaceOnUse">
<path d="M30 0H0V30" fill="none" stroke="#1a1c22" stroke-width="1"/>
</pattern>
</defs>

<rect width="900" height="520" rx="20" fill="url(#bg)" stroke="#26292f" stroke-width="1.5"/>
<rect x="1" y="1" width="898" height="518" rx="19" fill="url(#grid)" opacity=".3"/>
<rect width="900" height="520" rx="20" fill="none" stroke="url(#accent)" stroke-width="1" opacity=".4"/>

<circle cx="52" cy="48" r="5" fill="#22c55e">
<animate attributeName="opacity" values="1;.35;1" dur="1.8s" repeatCount="indefinite"/>
</circle>
<text x="40" y="60" fill="#f5f5f5" font-size="26" font-family="'Inter','Segoe UI',sans-serif" font-weight="700">GitHub Stats</text>
<text x="40" y="88" fill="#6b7280" font-size="14" font-family="'JetBrains Mono', monospace" letter-spacing="1">SYSTEM METRICS</text>
<rect x="40" y="105" width="820" height="1.5" fill="#26292f"/>

<rect x="40" y="140" width="390" height="110" rx="14" fill="#111318" stroke="#26292f" stroke-width="1.5"/>
<rect x="40" y="140" width="390" height="110" rx="14" fill="none" stroke="url(#accent)" stroke-width="1" opacity=".35"/>
<text x="60" y="177" fill="#6b7280" font-size="14" font-family="'JetBrains Mono', monospace" letter-spacing=".5">REPOSITORIES</text>
<text x="60" y="222" fill="#f5f5f5" font-size="38" font-family="'Inter','Segoe UI',sans-serif" font-weight="700">{repos}</text>

<rect x="470" y="140" width="390" height="110" rx="14" fill="#111318" stroke="#26292f" stroke-width="1.5"/>
<rect x="470" y="140" width="390" height="110" rx="14" fill="none" stroke="url(#accent)" stroke-width="1" opacity=".35"/>
<text x="490" y="177" fill="#6b7280" font-size="14" font-family="'JetBrains Mono', monospace" letter-spacing=".5">COMMITS</text>
<text x="490" y="222" fill="#f5f5f5" font-size="38" font-family="'Inter','Segoe UI',sans-serif" font-weight="700">{commits}</text>

<rect x="40" y="270" width="390" height="110" rx="14" fill="#111318" stroke="#26292f" stroke-width="1.5"/>
<rect x="40" y="270" width="390" height="110" rx="14" fill="none" stroke="url(#accent)" stroke-width="1" opacity=".35"/>
<text x="60" y="307" fill="#6b7280" font-size="14" font-family="'JetBrains Mono', monospace" letter-spacing=".5">FOLLOWERS</text>
<text x="60" y="352" fill="#f5f5f5" font-size="38" font-family="'Inter','Segoe UI',sans-serif" font-weight="700">{followers}</text>

<rect x="470" y="270" width="390" height="110" rx="14" fill="#111318" stroke="#26292f" stroke-width="1.5"/>
<rect x="470" y="270" width="390" height="110" rx="14" fill="none" stroke="url(#accent)" stroke-width="1" opacity=".35"/>
<text x="490" y="307" fill="#6b7280" font-size="14" font-family="'JetBrains Mono', monospace" letter-spacing=".5">STARS EARNED</text>
<text x="490" y="352" fill="#f5f5f5" font-size="38" font-family="'Inter','Segoe UI',sans-serif" font-weight="700">{stars}</text>

<rect x="40" y="410" width="820" height="1.5" fill="#26292f"/>
<text x="40" y="452" fill="#38bdf8" font-family="'JetBrains Mono', monospace" font-size="18">CURRENTLY BUILDING: FROST</text>

<circle cx="800" cy="447" r="5" fill="#22c55e">
<animate attributeName="opacity" values="1;.35;1" dur="1.8s" repeatCount="indefinite"/>
</circle>
<text x="815" y="452" fill="#9ca3af" font-family="'JetBrains Mono', monospace" font-size="15">AVAILABLE</text>

</svg>
"""

svg_output = SVG_TEMPLATE.format(
    repos=repo_count,
    commits=total_commits,
    followers=followers,
    stars=total_stars,
)

out_path = sys.argv[1] if len(sys.argv) > 1 else "assets/stats.svg"
os.makedirs(os.path.dirname(out_path) or ".", exist_ok=True)
with open(out_path, "w") as f:
    f.write(svg_output)

print(f"Written to {out_path}")
