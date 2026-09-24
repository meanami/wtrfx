# wtrfx

Waterfox-bin for CachyOS / Arch, auto-updated from upstream.

Based on [CachyOS waterfox-bin](https://github.com/CachyOS/cachyos-aur-derived/tree/master/waterfox-bin).
Upstream: https://github.com/BrowserWorks/waterfox

## Install

Add to `/etc/pacman.conf`:

```ini
[wtrfx]
SigLevel = Optional TrustAll
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

Pushes to `main` build with `makepkg` in `.github/workflows/build.yml`, publish to the `gh-pages` branch as a pacman repo, and attach the package to a versioned Release.
