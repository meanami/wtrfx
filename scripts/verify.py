#!/usr/bin/env python3
"""Independently re-verify a waterfox-bin bump PR.

Checks (fail closed, non-zero exit on any mismatch):
 1. PKGBUILD pkgver is stable 6.x, pkgrel reset to 1, tarball URL consistent.
 2. Upstream `<tarball>.sha512` sidecar matches the recorded hash.
 3. Full re-download + re-hash matches (second hash, independent of bump job).
 4. `.SRCINFO` consistent: pkgver/pkgrel/epoch, both hashes, source URL.

Usage: python3 scripts/verify.py
Must run from the repo root (or anywhere — paths resolve relative to this file).
"""
import hashlib
import re
import sys
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
PKGBUILD = ROOT / "PKGBUILD"
SRCINFO = ROOT / ".SRCINFO"

STABLE_RE = re.compile(r"^6\.\d+(\.\d+)*$")


def fail(msg: str):
    print(f"VERIFY FAILED: {msg}", file=sys.stderr)
    raise SystemExit(1)


def main() -> int:
    pkg = PKGBUILD.read_text()
    srcinfo = SRCINFO.read_text()

    ver_m = re.search(r"^pkgver=(.+)$", pkg, re.M)
    rel_m = re.search(r"^pkgrel=(.+)$", pkg, re.M)
    epoch_m = re.search(r"^epoch=(.+)$", pkg, re.M)
    if not (ver_m and rel_m and epoch_m):
        fail("pkgver/pkgrel/epoch not found in PKGBUILD")
    ver, rel, epoch = ver_m.group(1).strip(), rel_m.group(1).strip(), epoch_m.group(1).strip()

    sums = re.findall(r"'([0-9a-fA-F]{128})'", pkg)
    if not sums:
        fail("no sha512 in PKGBUILD")
    recorded = sums[0].lower()

    m = re.search(r"sources?=.*?(https?://\S+waterfox-\S+\.tar\.bz2)", pkg, re.S)
    if not m:
        m = re.search(r"(https://cdn\.waterfox\.com/\S+\.tar\.bz2)", pkg)
    if not m:
        fail("tarball URL not found in PKGBUILD")
    url = m.group(1).rstrip("'\"")
    # PKGBUILD uses $pkgver/${pkgver} variables — expand them
    url = url.replace("${pkgver}", ver).replace("$pkgver", ver)
    url = url.replace("${pkgrel}", rel).replace("$pkgrel", rel)

    if ver not in url:
        fail(f"pkgver {ver} not in URL {url}")
    if not STABLE_RE.match(ver):
        fail(f"version {ver!r} not stable 6.x")
    if rel != "1":
        fail(f"pkgrel should reset to 1 on bump, got {rel}")

    # 1) upstream sidecar (small, cheap)
    sidecar = url + ".sha512"
    print(f"fetching sidecar {sidecar}", flush=True)
    req = urllib.request.Request(sidecar, headers={"User-Agent": "wtrfx-verify/1.0"})
    with urllib.request.urlopen(req, timeout=30) as r:
        body = r.read().decode().strip()
    sm = re.search(r"\b([0-9a-fA-F]{128})\b", body)
    if not sm:
        fail(f"no sha512 in sidecar: {body[:200]!r}")
    upstream = sm.group(1).lower()
    print(f"PKGBUILD: {recorded}\nupstream: {upstream}", flush=True)
    if upstream != recorded:
        fail("PKGBUILD hash != upstream .sha512 sidecar")

    # 2) full re-download + re-hash (second hash, independent of bump job)
    print(f"downloading {url}", flush=True)
    h = hashlib.sha512()
    req = urllib.request.Request(url, headers={"User-Agent": "wtrfx-verify/1.0"})
    with urllib.request.urlopen(req, timeout=300) as r:
        while True:
            chunk = r.read(1 << 20)
            if not chunk:
                break
            h.update(chunk)
    computed = h.hexdigest()
    print(f"computed: {computed}", flush=True)
    if not (computed == recorded == upstream):
        fail("re-hash mismatch")

    # 3) .SRCINFO consistency
    for key, want in (("pkgver", ver), ("pkgrel", rel), ("epoch", epoch)):
        mm = re.search(rf"^\s*{key}\s*=\s*(\S+)", srcinfo, re.M)
        if not mm:
            fail(f".SRCINFO missing {key}")
        if mm.group(1) != want:
            fail(f".SRCINFO {key} {mm.group(1)} != PKGBUILD {want}")
    if recorded not in srcinfo.lower():
        fail(".SRCINFO missing tarball hash")
    if len(sums) >= 2 and sums[1].lower() not in srcinfo.lower():
        fail(".SRCINFO missing desktop file hash")
    prov = re.search(r"^\s*provides\s*=\s*waterfox=(\S+)", srcinfo, re.M)
    if prov and prov.group(1) != ver:
        fail(f".SRCINFO provides {prov.group(1)} != {ver}")
    if ver not in srcinfo:
        fail(".SRCINFO source URL missing version")

    print(f"OK: {ver}-{rel} (epoch {epoch}) re-hash matches, .SRCINFO consistent")
    return 0


if __name__ == "__main__":
    sys.exit(main())
