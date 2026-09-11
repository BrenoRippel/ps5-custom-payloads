# PS5 Payload Manager - custom source

A third-party catalog for [ps5-payload-manager](https://github.com/itsPLK/ps5-payload-manager),
following its [custom repository spec](https://github.com/itsPLK/ps5-payload-manager/blob/main/CUSTOM_REPOSITORIES.md).

Tracks, and auto-updates to, the newest release (stable or not) of:

- [OnionHEN](https://github.com/aydencharles/onionHEN)
- [kstuff-lite (EchoStretch)](https://github.com/EchoStretch/kstuff-lite)
- [kstuff-lite (drakmor fork)](https://github.com/drakmor/kstuff-lite)
- [ShadowMountPlus (drakmor prerelease branch)](https://github.com/drakmor/ShadowMountPlus) - latest alpha, not the official stable one
- [APR Emu Updater](https://github.com/tsuramatsu1/apr-emu-updater)
- [ProsperoMgr](https://github.com/notmaj0r/ProsperoMgr)

## Setup

1. Create a new **public** GitHub repo (the PS5 needs to reach it unauthenticated) and push
   everything in this folder to its `main` branch.
2. Push once manually so `payloads.json` exists, then let the workflow take over — see below.
   Or just let the first scheduled/dispatched Action run regenerate it.
3. In Payload Manager: **Settings → Manage Sources → Enable Multiple Payload Sources → Add Source**,
   paste:
   ```
   https://raw.githubusercontent.com/<your-username>/<your-repo>/main/payloads.json
   ```
4. Payloads from this catalog show up grouped under "Breno's PS5 Payload Sources" in the Manage tab,
   alongside the official one.

## Keeping it updated

`.github/workflows/update.yml` runs `scripts/update_payloads.py` every 6 hours (and on manual
dispatch from the Actions tab). It:

- Checks each repo's newest release via the GitHub API (no "stable-only" filtering, per your ask).
- For repos that ship a raw `.elf` release asset, links directly to that asset.
- For **ShadowMountPlus**, whose releases ship a `.zip`, downloads it, extracts `shadowmountplus.elf`,
  and commits it to `mirror/ShadowMountPlus.elf` (a stable path — only the *content* changes on
  updates, so `payloads.json`'s `url` field never needs editing).
- Recomputes the SHA-256 `checksum` for every entry, which Payload Manager verifies after download.
- Commits `payloads.json` (and `mirror/`) back to the repo only if something actually changed.

No secrets needed — it uses the repo's built-in `GITHUB_TOKEN` to read the GitHub API and to push.

To update immediately instead of waiting for the schedule: **Actions → Update payload catalog →
Run workflow**.

## Notes

- ShadowMountPlus here tracks drakmor's *prerelease* alpha branch, separate from the stable
  `1.6betaXX` build in the official repository — expect occasional breakage, that's the nature of
  an alpha channel.
- Same goes for the drakmor `kstuff-lite` fork: its latest tag is a test build (`-dr-test*`), not a
  vetted stable release.
- Run `python3 scripts/update_payloads.py` locally any time to regenerate `payloads.json` by hand
  (set `GITHUB_TOKEN` in your env first to avoid low unauthenticated GitHub API rate limits).
