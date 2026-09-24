#!/usr/bin/env python3
"""Bump waterfox-bin PKGBUILD to latest upstream stable.

- Source of truth: GitHub releases API BrowserWorks/waterfox (latest stable)
  fallback: CDN listing https://cdn.waterfox.com/waterfox/releases/
- Updates pkgver, resets pkgrel=1, recomputes sha512 for tarball,
  preserves desktop file checksum, regenerates .SRCINFO.
- Usage: python3 scripts/bump.py [--check-only] [--version X.Y.Z]
"""
import hashlib
import json
import re
import sys
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
PKGBUILD = ROOT / "PKGBUILD"
SRCINFO = ROOT / ".SRCINFO"

GITHUB_LATEST_API = "https://api.github.com/repos/BrowserWorks/waterfox/releases/latest"
GITHUB_RELEASES_API = "https://api.github.com/repos/BrowserWorks/waterfox/releases?per_page=20"
CDN_TPL = "https://cdn.waterfox.com/waterfox/releases/{ver}/Linux_x86_64/waterfox-{ver}.tar.bz2"

STABLE_RE = re.compile(r"^6\.\d+(\.\d+)*$")


def http_json(url: str):
    req = urllib.request.Request(url, headers={"User-Agent": "wtrfx-bump/1.0", "Accept": "application/vnd.github+json"})
    with urllib.request.urlopen(req, timeout=30) as r:
        return json.loads(r.read().decode())


def get_latest_github() -> str:
    try:
        data = http_json(GITHUB_LATEST_API)
        tag = data.get("tag_name", "").strip()
        if tag and not data.get("prerelease") and not data.get("draft"):
            return tag.lstrip("v")
    except Exception as e:
        print(f"latest API failed: {e}", file=sys.stderr)
    # fallback: scan recent releases for stable 6.x
    data = http_json(GITHUB_RELEASES_API)
    for rel in data:
        if rel.get("prerelease") or rel.get("draft"):
            continue
        tag = rel.get("tag_name", "").strip().lstrip("v")
        if STABLE_RE.match(tag):
            return tag
    raise RuntimeError("could not determine latest stable version")


def get_current() -> str:
    m = re.search(r"^pkgver=(.+)$", PKGBUILD.read_text(), re.M)
    assert m, "pkgver not found in PKGBUILD"
    return m.group(1).strip()


def sha512_of_url(url: str) -> str:
    print(f"downloading {url} ...", flush=True)
    h = hashlib.sha512()
    req = urllib.request.Request(url, headers={"User-Agent": "wtrfx-bump/1.0"})
    with urllib.request.urlopen(req, timeout=120) as r:
        while True:
            chunk = r.read(1 << 20)
            if not chunk:
                break
            h.update(chunk)
    return h.hexdigest()


def expected_sha512(url: str) -> str:
    """Fetch upstream <tarball>.sha512 sidecar published by Waterfox.

    e.g. https://cdn.waterfox.com/.../waterfox-6.7.4.tar.bz2.sha512
    contains "<hex>  waterfox-6.7.4.tar.bz2". Fail closed if missing.
    """
    sidecar = url + ".sha512"
    print(f"fetching {sidecar} ...", flush=True)
    req = urllib.request.Request(sidecar, headers={"User-Agent": "wtrfx-bump/1.0"})
    with urllib.request.urlopen(req, timeout=30) as r:
        body = r.read().decode().strip()
    m = re.search(r"\b([0-9a-fA-F]{128})\b", body)
    if not m:
        raise RuntimeError(f"no sha512 found in {sidecar}: {body[:200]!r}")
    return m.group(1).lower()


def update_pkgbuild(new_ver: str, new_sum: str):
    text = PKGBUILD.read_text()
    text = re.sub(r"^pkgver=.*$", f"pkgver={new_ver}", text, count=1, flags=re.M)
    text = re.sub(r"^pkgrel=.*$", "pkgrel=1", text, count=1, flags=re.M)
    # replace first sha512 entry (tarball), keep second (desktop)
    # matches: sha512sums=('xxx'\n  'yyy')
    m = re.search(r"sha512sums=\(\s*'[^']+'", text)
    assert m, "sha512sums not found"
    text = re.sub(r"sha512sums=\(\s*'[^']+'", f"sha512sums=('{new_sum}'", text, count=1)
    PKGBUILD.write_text(text)


def write_srcinfo(new_ver: str, new_sum: str):
    desktop_sum = "d0237cffceb1f22bcef3479ee192360c069052534cbe6f452bf88e671ba26b7d8d04f6cdbb4f34647277b64136093d703b5f9ac8071fe0d3c80d70b1e1395a84"
    # try to preserve desktop checksum from PKGBUILD if it changed
    m = re.findall(r"'([0-9a-f]{128})'", PKGBUILD.read_text())
    if len(m) >= 2:
        desktop_sum = m[1]
    content = f"""pkgbase = waterfox-bin
\tpkgdesc = Current/modern generation of customizable privacy-conscious web browser.
\tpkgver = {new_ver}
\tpkgrel = 1
\tepoch = 1
\turl = https://www.waterfox.net
\tarch = x86_64
\tlicense = MPL-2.0
\tdepends = gtk3
\tdepends = libxt
\tdepends = startup-notification
\tdepends = mime-types
\tdepends = dbus-glib
\tdepends = ffmpeg
\tdepends = ttf-font
\tdepends = hicolor-icon-theme
\toptdepends = networkmanager: Location detection via available WiFi networks
\toptdepends = libnotify: Notification integration
\toptdepends = pulseaudio: Audio support
\toptdepends = alsa-lib: Audio support
\toptdepends = speech-dispatcher: Text-to-Speech
\toptdepends = hunspell-en_US: Spell checking, American English
\tprovides = waterfox={new_ver}
\tconflicts = waterfox
\toptions = !debug
\toptions = !strip
\tsource = waterfox-{new_ver}-1.tar.bz2::https://cdn.waterfox.com/waterfox/releases/{new_ver}/Linux_x86_64/waterfox-{new_ver}.tar.bz2
\tsource = waterfox.desktop
\tsha512sums = {new_sum}
\tsha512sums = {desktop_sum}

pkgname = waterfox-bin
"""
    SRCINFO.write_text(content)


def main():
    forced = None
    check_only = False
    for a in sys.argv[1:]:
        if a == "--check-only":
            check_only = True
        elif a.startswith("--version="):
            forced = a.split("=", 1)[1]
        elif not a.startswith("-"):
            forced = a

    latest = forced or get_latest_github()
    if not STABLE_RE.match(latest):
        print(f"version {latest!r} does not look stable (want 6.x), aborting", file=sys.stderr)
        sys.exit(1)
    current = get_current()
    print(f"current={current} latest={latest}")
    if current == latest:
        print("already up to date")
        return 0
    if check_only:
        print(f"update available: {current} -> {latest}")
        return 10
    url = CDN_TPL.format(ver=latest)
    # verify URL exists
    req = urllib.request.Request(url, method="HEAD", headers={"User-Agent": "wtrfx-bump/1.0"})
    try:
        with urllib.request.urlopen(req, timeout=30) as r:
            if r.status >= 400:
                raise RuntimeError(f"CDN HEAD failed: {r.status}")
    except Exception as e:
        print(f"CDN check failed for {url}: {e}", file=sys.stderr)
        sys.exit(1)
    new_sum = sha512_of_url(url)
    print(f"sha512={new_sum}")
    try:
        want = expected_sha512(url)
    except Exception as e:
        print(f"upstream .sha512 check failed for {url}: {e}", file=sys.stderr)
        sys.exit(1)
    if want != new_sum.lower():
        print(f"sha512 mismatch: computed {new_sum} != upstream {want}", file=sys.stderr)
        sys.exit(1)
    print("sha512 matches upstream .sha512 sidecar")
    update_pkgbuild(latest, new_sum)
    write_srcinfo(latest, new_sum)
    print(f"bumped {current} -> {latest}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
