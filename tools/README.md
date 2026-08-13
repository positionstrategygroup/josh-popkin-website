# Site checks

## Before pushing (automatic)
A `pre-push` git hook runs `tools/check.py` and **blocks the push** if anything fails.
After a fresh clone, run `./tools/install-hooks.sh` once to reinstall it.

## Manually
    python3 tools/check.py          # the working copy
    python3 tools/check.py --live   # what joshpopkin.com is actually serving

Run `--live` after every deploy. Local-passing does not mean live-serving.

## What it fails on
- an `<img>`, `og:image`, `twitter:image`, schema image or sitemap image that 404s
- a row thumbnail that doesn't exist
- an `<img>` with no alt text
- JSON-LD that doesn't parse
- unclosed or mismatched HTML tags
- a broken internal link
- a missing `<title>`, meta description, canonical or og:image
- two pages sharing a title or canonical
- a page missing from sitemap.xml, or a sitemap entry with no page
- banned phrases (the Carter-Agency language Josh removed) reappearing

## What it warns on
- an image under 1200px on its long side (too small for Google Images)
- an image over 700 KB
- a meta description under 70 characters

Warnings don't block. Fix them when the source photo allows.
