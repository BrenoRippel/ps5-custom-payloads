#!/usr/bin/env python3
"""
Rebuilds payloads.json (and mirror/*.elf for zip-packaged releases) from the
live "latest release" of each upstream repo below. Always takes the newest
release regardless of stable/prerelease status, matching how these are being
tracked by hand.

Run locally (needs GITHUB_TOKEN in env to avoid low-volume rate limits/500s)
or via .github/workflows/update.yml on a schedule.
"""
import hashlib
import json
import os
import re
import sys
import urllib.request
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
MIRROR_DIR = ROOT / "mirror"
CATALOG_NAME = "Breno's PS5 Payload Sources"

TOKEN = os.environ.get("GITHUB_TOKEN") or os.environ.get("GH_TOKEN")
REPO_SLUG = os.environ.get("GITHUB_REPOSITORY")  # e.g. "user/repo", set by Actions

# Each entry: display name, upstream repo, category, description override
# (None = use the GitHub repo description), and whether the release ships a
# zip that needs the .elf extracted out of it (mirrored into mirror/).
PAYLOADS = [
    {
        "name": "OnionHEN",
        "repo": "aydencharles/onionHEN",
        "category": "System & Jailbreak",
        "description": None,
    },
    {
        "name": "kstuff-lite (EchoStretch)",
        "repo": "EchoStretch/kstuff-lite",
        "category": "System & Jailbreak",
        "description": "Lite version of kstuff. Also mirrored in the official "
                        "catalog; kept here so all kstuff variants sit side by side.",
    },
    {
        "name": "kstuff-lite (drakmor fork)",
        "repo": "drakmor/kstuff-lite",
        "category": "System & Jailbreak",
        "description": "drakmor's fork/test branch of kstuff-lite.",
    },
    {
        "name": "ShadowMountPlus (prerelease)",
        "repo": "drakmor/ShadowMountPlus",
        "category": "Utilities & Tools",
        "description": None,
        "zip_inner_elf": "shadowmountplus.elf",
        "mirror_as": "ShadowMountPlus.elf",
    },
    {
        "name": "APR Emu Updater",
        "repo": "tsuramatsu1/apr-emu-updater",
        "category": "Utilities & Tools",
        "description": None,
    },
    {
        "name": "ProsperoMgr",
        "repo": "notmaj0r/ProsperoMgr",
        "category": "Utilities & Tools",
        "description": None,
    },
]


def api_get(path):
    req = urllib.request.Request(f"https://api.github.com{path}")
    req.add_header("Accept", "application/vnd.github+json")
    req.add_header("User-Agent", "ps5-custom-payloads-updater")
    if TOKEN:
        req.add_header("Authorization", f"Bearer {TOKEN}")
    with urllib.request.urlopen(req, timeout=30) as resp:
        return json.load(resp)


def download_asset(repo, asset_id, out_path):
    req = urllib.request.Request(
        f"https://api.github.com/repos/{repo}/releases/assets/{asset_id}"
    )
    req.add_header("Accept", "application/octet-stream")
    req.add_header("User-Agent", "ps5-custom-payloads-updater")
    if TOKEN:
        req.add_header("Authorization", f"Bearer {TOKEN}")
    with urllib.request.urlopen(req, timeout=60) as resp:
        out_path.write_bytes(resp.read())


def sha256_of(path):
    h = hashlib.sha256()
    h.update(path.read_bytes())
    return h.hexdigest()


def raw_url_for(rel_path):
    slug = REPO_SLUG or "YOUR_GITHUB_USERNAME/YOUR_REPO_NAME"
    return f"https://raw.githubusercontent.com/{slug}/main/{rel_path}"


def build_entry(cfg, tmp_dir):
    repo = cfg["repo"]
    releases = api_get(f"/repos/{repo}/releases")
    if not releases:
        print(f"!! {repo}: no releases found, skipping", file=sys.stderr)
        return None
    release = releases[0]  # newest by publish date, stable or not
    assets = release.get("assets", [])
    if not assets:
        print(f"!! {repo}: latest release {release.get('tag_name')} has no assets, skipping",
              file=sys.stderr)
        return None

    description = cfg["description"]
    if description is None:
        description = api_get(f"/repos/{repo}").get("description") or ""

    tag = release.get("tag_name", "")
    published = (release.get("published_at") or "")[:10]

    if "zip_inner_elf" in cfg:
        zip_asset = next((a for a in assets if a["name"].lower().endswith(".zip")), assets[0])
        zip_path = tmp_dir / zip_asset["name"]
        download_asset(repo, zip_asset["id"], zip_path)
        with zipfile.ZipFile(zip_path) as zf:
            inner_name = cfg["zip_inner_elf"]
            matches = [n for n in zf.namelist() if n.lower().endswith(inner_name.lower())]
            if not matches:
                print(f"!! {repo}: {inner_name} not found in {zip_asset['name']}", file=sys.stderr)
                return None
            elf_bytes = zf.read(matches[0])
        MIRROR_DIR.mkdir(exist_ok=True)
        mirror_path = MIRROR_DIR / cfg["mirror_as"]
        mirror_path.write_bytes(elf_bytes)
        checksum = sha256_of(mirror_path)
        url = raw_url_for(f"mirror/{cfg['mirror_as']}")
        source_direct = zip_asset["browser_download_url"]
        filename = f"{cfg['mirror_as'].removesuffix('.elf')}_{tag}.elf"
    else:
        elf_asset = next((a for a in assets if a["name"].lower().endswith(".elf")), assets[0])
        local_path = tmp_dir / elf_asset["name"]
        download_asset(repo, elf_asset["id"], local_path)
        checksum = sha256_of(local_path)
        url = elf_asset["browser_download_url"]
        source_direct = url
        base = re.sub(r"\.elf$", "", elf_asset["name"], flags=re.IGNORECASE)
        filename = elf_asset["name"] if tag in base else f"{base}_{tag}.elf"

    return {
        "name": cfg["name"],
        "filename": filename,
        "url": url,
        "source": f"https://github.com/{repo}/releases",
        "source_direct": source_direct,
        "description": description,
        "last_update": published,
        "version": tag,
        "category": cfg["category"],
        "checksum": checksum,
    }


def main():
    tmp_dir = ROOT / ".tmp_downloads"
    tmp_dir.mkdir(exist_ok=True)
    entries = []
    for cfg in PAYLOADS:
        try:
            entry = build_entry(cfg, tmp_dir)
        except Exception as exc:  # noqa: BLE001
            print(f"!! {cfg['repo']}: {exc}", file=sys.stderr)
            entry = None
        if entry:
            entries.append(entry)

    for f in tmp_dir.glob("*"):
        f.unlink()
    tmp_dir.rmdir()

    catalog = {"name": CATALOG_NAME, "payloads": entries}
    out_path = ROOT / "payloads.json"
    out_path.write_text(json.dumps(catalog, indent=2) + "\n")
    print(f"Wrote {out_path} with {len(entries)} payload(s)")


if __name__ == "__main__":
    main()
