#!/usr/bin/env python3
"""Generate the terminal-style card used by the GitHub profile README."""

from __future__ import annotations

import base64
import json
import os
import time
from calendar import monthrange
from datetime import UTC, date, datetime
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.parse import quote
from urllib.request import Request, urlopen
from xml.sax.saxutils import escape


ROOT = Path(__file__).resolve().parents[1]
USERNAME = "dat-hoangnguyentuandat"
API_ROOT = "https://api.github.com"
STATS_CACHE = ROOT / "assets" / "profile-stats.json"
ACCOUNT_CREATED = date(2021, 6, 27)


def github_get(path: str, retries: int = 0):
    headers = {
        "Accept": "application/vnd.github+json",
        "User-Agent": f"{USERNAME}-profile-readme",
        "X-GitHub-Api-Version": "2022-11-28",
    }
    if token := os.environ.get("GITHUB_TOKEN"):
        headers["Authorization"] = f"Bearer {token}"

    for attempt in range(retries + 1):
        request = Request(f"{API_ROOT}{path}", headers=headers)
        with urlopen(request, timeout=20) as response:
            data = json.load(response)
            if response.status != 202 or attempt == retries:
                return data
        time.sleep(3)
    return {}


def public_stats() -> dict[str, int]:
    user = github_get(f"/users/{USERNAME}")
    repos = github_get(f"/users/{USERNAME}/repos?per_page=100&type=owner")
    commit_search = github_get(f"/search/commits?q={quote(f'author:{USERNAME}')}&per_page=1")
    pr_search = github_get(
        f"/search/issues?q={quote(f'type:pr author:{USERNAME} -user:{USERNAME}')}&per_page=100"
    )

    additions = 0
    deletions = 0
    for repo in repos:
        if repo["fork"] or repo["size"] == 0:
            continue
        contributors = github_get(f"/repos/{repo['full_name']}/stats/contributors", retries=4)
        if not isinstance(contributors, list):
            continue
        for contributor in contributors:
            author = contributor.get("author") or {}
            if author.get("login") != USERNAME:
                continue
            additions += sum(week["a"] for week in contributor["weeks"])
            deletions += sum(week["d"] for week in contributor["weeks"])

    contributed_repos = {
        item["repository_url"]
        for item in pr_search.get("items", [])
    }
    return {
        "repos": user["public_repos"],
        "followers": user["followers"],
        "stars": sum(repo["stargazers_count"] for repo in repos),
        "forks": sum(repo["forks_count"] for repo in repos),
        "commits": commit_search.get("total_count", 0),
        "contributed": len(contributed_repos),
        "additions": additions,
        "deletions": deletions,
        "lines": additions - deletions,
    }


def github_uptime() -> str:
    today = datetime.now(UTC).date()
    years = today.year - ACCOUNT_CREATED.year
    if (today.month, today.day) < (ACCOUNT_CREATED.month, ACCOUNT_CREATED.day):
        years -= 1

    anniversary = ACCOUNT_CREATED.replace(year=ACCOUNT_CREATED.year + years)
    months = (today.year - anniversary.year) * 12 + today.month - anniversary.month
    if today.day < anniversary.day:
        months -= 1

    month_index = anniversary.year * 12 + anniversary.month - 1 + months
    anchor_year, zero_based_month = divmod(month_index, 12)
    anchor_month = zero_based_month + 1
    anchor_day = min(anniversary.day, monthrange(anchor_year, anchor_month)[1])
    days = (today - date(anchor_year, anchor_month, anchor_day)).days

    def unit(value: int, singular: str) -> str:
        return f"{value} {singular}{'' if value == 1 else 's'}"

    return ", ".join(
        (unit(years, "year"), unit(months, "month"), unit(days, "day"))
    )


def current_stats() -> dict[str, int]:
    try:
        stats = public_stats()
        STATS_CACHE.write_text(json.dumps(stats, indent=2) + "\n", encoding="utf-8")
        return stats
    except (HTTPError, URLError, TimeoutError) as error:
        if not STATS_CACHE.exists():
            raise
        print(f"GitHub API unavailable ({error}); using cached statistics.")
        return json.loads(STATS_CACHE.read_text(encoding="utf-8"))


def portrait_data_uri() -> str:
    encoded = base64.b64encode((ROOT / "assets" / "portrait-ascii.gif").read_bytes()).decode("ascii")
    return f"data:image/gif;base64,{encoded}"


def text(x: int, y: int, value: str, css_class: str = "value") -> str:
    return f'<text x="{x}" y="{y}" class="{css_class}">{escape(value)}</text>'


def field(y: int, label: str, value: str) -> str:
    dots = "·" * max(2, 28 - len(label))
    return (
        f'<text x="500" y="{y}">'
        f'<tspan class="label">{escape(label)}:</tspan> '
        f'<tspan class="dots">{dots}</tspan> '
        f'<tspan class="value">{escape(value)}</tspan>'
        "</text>"
    )


def build_svg(stats: dict[str, int], portrait_uri: str) -> str:
    parts = [
        '<svg xmlns="http://www.w3.org/2000/svg" width="1200" height="640" viewBox="0 0 1200 640" role="img" aria-labelledby="title desc">',
        "<title id=\"title\">Tuấn Đạt's developer profile</title>",
        '<desc id="desc">A neofetch-style developer profile with an ASCII portrait, systems, languages, hobbies, contact links, and GitHub contribution statistics.</desc>',
        '<defs><clipPath id="portrait-clip"><rect x="20" y="20" width="445" height="600" rx="5"/></clipPath></defs>',
        "<style>",
        "text { font-family: ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, 'Liberation Mono', monospace; font-size: 18px; letter-spacing: 0; }",
        ".title { fill: #e6edf3; font-size: 22px; font-weight: 700; }",
        ".section { fill: #e6edf3; font-size: 19px; }",
        ".label { fill: #f0a866; font-weight: 700; }",
        ".value { fill: #b7d8f7; }",
        ".dots { fill: #56616e; }",
        ".muted { fill: #8b949e; font-size: 15px; }",
        ".green { fill: #7ee787; }",
        ".red { fill: #ff7b72; }",
        "</style>",
        '<rect x="1" y="1" width="1198" height="638" rx="6" fill="#0d1117" stroke="#30363d" stroke-width="2"/>',
        '<rect x="20" y="20" width="1160" height="600" rx="5" fill="#090d12" stroke="#161b22"/>',
        f'<image x="20" y="20" width="445" height="600" href="{portrait_uri}" preserveAspectRatio="xMidYMid slice" clip-path="url(#portrait-clip)"/>',
        '<line x1="465" y1="34" x2="465" y2="606" stroke="#30363d"/>',
        text(500, 54, "dat@github", "title"),
        '<line x1="650" y1="48" x2="1140" y2="48" stroke="#8b949e" stroke-width="2"/>',
        field(86, "OS", "Windows 11, Android 16, Linux"),
        field(114, "Uptime", github_uptime()),
        field(142, "IDE", "Visual Studio 2026"),
        field(190, "Languages.Programming", "C#, Java"),
        field(218, "Languages.Frameworks", "ASP.NET Core, EF Core, WinUI 3"),
        field(246, "Languages.Data", "SQL Server, MySQL, REST, gRPC"),
        field(294, "Hobbies.Software", "Open source, API design, AI tooling"),
        field(322, "Hobbies.Hardware", "Windows apps, Bluetooth, system tools"),
        text(500, 368, "— Contact", "section"),
        '<line x1="620" y1="362" x2="1140" y2="362" stroke="#8b949e" stroke-width="2"/>',
        field(402, "Email.Personal", "hoangdatlnbp@gmail.com"),
        field(430, "Discord", "tdat_zo4"),
        field(458, "Telegram", "@dat_hoangnguyentuan"),
        text(500, 504, "— GitHub Stats", "section"),
        '<line x1="670" y1="498" x2="1140" y2="498" stroke="#8b949e" stroke-width="2"/>',
        text(500, 538, "Repos:", "label"),
        text(610, 538, f"{stats['repos']:,}", "value"),
        text(670, 538, f"{{Contributed: {stats['contributed']:,}}}", "value"),
        text(870, 538, "|", "label"),
        text(900, 538, "Stars:", "label"),
        text(1035, 538, f"{stats['stars']:,}", "value"),
        text(500, 566, "Commits:", "label"),
        text(610, 566, f"{stats['commits']:,}", "value"),
        text(870, 566, "|", "label"),
        text(900, 566, "Followers:", "label"),
        text(1035, 566, f"{stats['followers']:,}", "value"),
        text(500, 594, "Lines of Code on GitHub:", "label"),
        text(775, 594, f"{stats['lines']:,}", "value"),
        text(900, 594, f"( {stats['additions']:,}++", "green"),
        text(1045, 594, f"{stats['deletions']:,}-- )", "red"),
        "</svg>",
    ]
    return "\n".join(parts) + "\n"


if __name__ == "__main__":
    output = ROOT / "assets" / "profile-terminal.svg"
    output.write_text(build_svg(current_stats(), portrait_data_uri()), encoding="utf-8")
    print(f"Generated {output.relative_to(ROOT)}")
