import json
import urllib.request

GITHUB_API_URL = "https://api.github.com/repos/{repo}/releases/latest"


def check_for_update(current_version: str, repo: str = "GZPavlov23/getclip"):
    url = GITHUB_API_URL.format(repo=repo)
    request = urllib.request.Request(url, headers={"Accept": "application/vnd.github+json"})

    with urllib.request.urlopen(request, timeout=10) as response:
        data = json.load(response)

    latest_tag = data.get("tag_name", "").lstrip("v")
    release_url = data.get("html_url", "")

    is_newer = _is_newer(latest_tag, current_version)
    return is_newer, latest_tag, release_url


def _is_newer(latest: str, current: str) -> bool:
    def parts(version: str):
        return tuple(int(p) for p in version.split(".") if p.isdigit())
    return parts(latest) > parts(current)