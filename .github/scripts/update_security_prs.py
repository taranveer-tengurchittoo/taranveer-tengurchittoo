"""Fetch PR statuses from GitHub and update the security contributions table in README.md."""

import json
import subprocess
import sys
from pathlib import Path

# Each entry: (owner/repo, PR number, short description)
PRS = [
    ("mervinhemaraju/mauritius-emergency-services", 3, "Remove disabled SSL certificate validation"),
    ("mervinhemaraju/mauritius-emergency-services", 4, "Sanitize phone numbers in tel: URIs"),
    ("querylab/lazywarden", 47, "Prevent vault password exposure via /proc and logs"),
    ("ckreiling/mcp-server-docker", 49, "Block container escape via runtime socket and /proc volume mounts"),
]

STATUS_ICONS = {
    "MERGED": "merged",
    "OPEN": "open",
    "CLOSED": "closed",
}

README = Path("README.md")
START_MARKER = "<!-- SECURITY_CONTRIBUTIONS_START -->"
END_MARKER = "<!-- SECURITY_CONTRIBUTIONS_END -->"


def fetch_pr(repo: str, number: int) -> dict:
    result = subprocess.run(
        ["gh", "api", f"repos/{repo}/pulls/{number}", "--jq",
         '{state: .state, merged: .merged_at, title: .title, html_url: .html_url}'],
        capture_output=True, text=True, check=True,
    )
    return json.loads(result.stdout)


def pr_status(pr: dict) -> str:
    if pr["merged"]:
        return "MERGED"
    return pr["state"].upper()


def badge(status: str) -> str:
    colours = {"MERGED": "8957e5", "OPEN": "238636", "CLOSED": "da3633"}
    label = STATUS_ICONS[status]
    colour = colours[status]
    return f"![{label}](https://img.shields.io/badge/{label}-{colour}?style=flat-square)"


def build_table(rows: list[tuple[str, int, str, str, str]]) -> str:
    lines = [
        "| Project | PR | Finding | Status |",
        "|---------|----|---------|---------|",
    ]
    for repo, number, desc, url, status in rows:
        project = repo.split("/")[1]
        lines.append(f"| [{project}](https://github.com/{repo}) | [#{number}]({url}) | {desc} | {badge(status)} |")
    return "\n".join(lines)


def main() -> None:
    rows = []
    for repo, number, desc in PRS:
        try:
            pr = fetch_pr(repo, number)
            status = pr_status(pr)
            rows.append((repo, number, desc, pr["html_url"], status))
        except Exception as e:
            print(f"warning: could not fetch {repo}#{number}: {e}", file=sys.stderr)
            url = f"https://github.com/{repo}/pull/{number}"
            rows.append((repo, number, desc, url, "OPEN"))

    table = build_table(rows)
    content = README.read_text()

    if START_MARKER not in content:
        print("error: start marker not found in README.md", file=sys.stderr)
        sys.exit(1)

    before = content.split(START_MARKER)[0]
    after = content.split(END_MARKER)[1]
    updated = f"{before}{START_MARKER}\n{table}\n{END_MARKER}{after}"

    if updated != content:
        README.write_text(updated)
        print("README.md updated")
    else:
        print("no changes")


if __name__ == "__main__":
    main()
