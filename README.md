# wtrfx

Waterfox-bin for CachyOS / Arch, auto-updated from upstream.

Based on [CachyOS waterfox-bin](https://github.com/CachyOS/cachyos-aur-derived/tree/master/waterfox-bin).
Upstream: https://github.com/BrowserWorks/waterfox

## Install

Import the repo signing key (verify the fingerprint out-of-band):

```bash
curl -fsSL -O https://meanami.github.io/wtrfx/wtrfx.gpg
gpg --show-keys wtrfx.gpg
# expected: 788231734BB6FBEC7F1E9003F52AE1EDBE75CFA2
sudo pacman-key --add wtrfx.gpg
sudo pacman-key --lsign-key 788231734BB6FBEC7F1E9003F52AE1EDBE75CFA2
```

Add to `/etc/pacman.conf`:

```ini
[wtrfx]
SigLevel = Required DatabaseOptional
Server = https://meanami.github.io/wtrfx/$arch
```

Then:

```bash
sudo pacman -Sy
sudo pacman -S wtrfx/waterfox-bin
```

Octopi reads `pacman.conf` directly, so it will show up there after a refresh.

Manual downloads:
- Repo: https://meanami.github.io/wtrfx/x86_64/
- Releases: https://github.com/meanami/wtrfx/releases

## Details

Same deps and install steps as CachyOS (`gtk3`, `libxt`, `startup-notification`, `mime-types`, `dbus-glib`, `ffmpeg`, `ttf-font`, `hicolor-icon-theme`).

Daily check via `scripts/bump.py` + `.github/workflows/check-update.yml` opens a PR for new upstream versions and auto-merges it.

Pushes to `main` build with `makepkg` in `.github/workflows/build.yml`, publish as a pacman repo via GitHub Pages (Actions deployment, handles 100MB+ packages), and attach the package to a versioned Release.
