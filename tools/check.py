#!/usr/bin/env python3
"""
joshpopkin.com site checker.

  python3 tools/check.py          # check the working copy (run before pushing)
  python3 tools/check.py --live   # check what joshpopkin.com is actually serving

Exits non-zero if anything FAILS. Warnings do not fail the build.
"""
import sys, os, re, io, json, glob, html, urllib.request, urllib.error
from html.parser import HTMLParser

LIVE = "--live" in sys.argv
BASE = "https://joshpopkin.com"
UA   = {"User-Agent": "Mozilla/5.0 (compatible; Googlebot/2.1; +http://www.google.com/bot.html)"}
fails, warns = [], []
def fail(page, msg): fails.append((page, msg))
def warn(page, msg): warns.append((page, msg))

# phrases Josh has explicitly removed — regression guard
BANNED = ["allegation", "accusation", "accused", "substantiated", "scam creators",
          "use aliases", "deeply hurt", "disputes were resolved"]

def pages():
    return ["index.html", "insights/index.html"] + sorted(glob.glob("insights/*/index.html"))

def url_for(p):
    return BASE + "/" + (p.replace("index.html", "") if p.endswith("index.html") else p)

def get(p):
    if LIVE:
        try:
            return urllib.request.urlopen(urllib.request.Request(url_for(p), headers=UA)).read().decode("utf-8", "replace")
        except Exception as e:
            fail(p, f"could not fetch live page: {e}"); return ""
    return open(p, encoding="utf-8").read()

def asset(ref):
    """Return (ok, dims, bytes) for an asset reference."""
    if LIVE or ref.startswith("http"):
        u = ref if ref.startswith("http") else BASE + "/" + ref.lstrip("/")
        try:
            d = urllib.request.urlopen(urllib.request.Request(u, headers=UA)).read()
        except Exception:
            return False, None, 0
    else:
        f = ref.lstrip("/")
        if not os.path.exists(f): return False, None, 0
        d = open(f, "rb").read()
    try:
        from PIL import Image
        return True, Image.open(io.BytesIO(d)).size, len(d)
    except Exception:
        return True, None, len(d)

class Balance(HTMLParser):
    VOID = {"img","br","meta","link","hr","input","source","area","base","col","embed","param","track","wbr"}
    def __init__(self): super().__init__(); self.stack=[]; self.bad=[]
    def handle_starttag(self, t, a):
        if t not in self.VOID: self.stack.append(t)
    def handle_endtag(self, t):
        if self.stack and self.stack[-1]==t: self.stack.pop()
        elif t in self.stack: self.bad.append(t)

titles, canon = {}, {}
print(f"Checking {'LIVE SITE' if LIVE else 'working copy'}\n" + "="*66)

for p in pages():
    s = get(p)
    if not s: continue

    # --- head essentials ---
    for name, rx in [("<title>", r"<title>(.+?)</title>"),
                     ("meta description", r'<meta name="description" content="(.+?)"'),
                     ("canonical", r'<link rel="canonical" href="(.+?)"'),
                     ("og:image", r'<meta property="og:image" content="(.+?)"')]:
        m = re.search(rx, s, re.S)
        if not m: fail(p, f"missing {name}")
        elif name == "<title>": titles.setdefault(m.group(1), []).append(p)
        elif name == "canonical": canon.setdefault(m.group(1), []).append(p)

    d = re.search(r'<meta name="description" content="(.+?)"', s, re.S)
    if d and len(d.group(1)) < 70: warn(p, f"meta description only {len(d.group(1))} chars")

    # --- structure ---
    b = Balance(); b.feed(s)
    if b.stack: fail(p, f"unclosed tags: {b.stack[:5]}")
    if b.bad:   fail(p, f"mismatched close tags: {b.bad[:5]}")

    # --- structured data ---
    for blk in re.findall(r'<script type="application/ld\+json">(.*?)</script>', s, re.S):
        try:
            g = json.loads(blk)
        except json.JSONDecodeError as e:
            fail(p, f"JSON-LD does not parse: {e}"); continue
        nodes = g.get("@graph", [g])
        for n in nodes:
            for k in ("url", "contentUrl"):
                if isinstance(n.get(k), str) and "/assets/" in n[k]:
                    ok, dims, _ = asset(n[k])
                    if not ok: fail(p, f"schema {k} 404s: {n[k].split('/')[-1]}")
        if not any(n.get("@type") in ("Article","ProfilePage","CollectionPage","WebPage","Blog") for n in nodes) and p != "index.html":
            warn(p, "no Article/ProfilePage node in JSON-LD")

    # --- images ---
    for m in re.finditer(r"<img\b[^>]*>", s):
        tag = m.group(0)
        src = re.search(r'src="([^"]+)"', tag)
        alt = re.search(r'alt="([^"]*)"', tag)
        if not src: fail(p, "img with no src"); continue
        ref = src.group(1)
        if not alt or not alt.group(1).strip():
            fail(p, f"img missing alt: {ref.split('/')[-1]}")
        ok, dims, n = asset(ref)
        if not ok:
            fail(p, f"IMAGE 404: {ref}")
            continue
        is_thumb = "/thumbs/" in ref
        if dims and not is_thumb and max(dims) < 1200:
            warn(p, f"{ref.split('/')[-1]} is {dims[0]}x{dims[1]} — under 1200px for Google Images")
        if not is_thumb and n > 700_000:
            warn(p, f"{ref.split('/')[-1]} is {round(n/1024)} KB — consider recompressing")

    # --- social + schema image URLs resolve ---
    for tag in ("og:image", "twitter:image"):
        m = re.search(rf'(?:property|name)="{tag}" content="([^"]+)"', s)
        if m and not asset(m.group(1))[0]:
            fail(p, f"{tag} 404s: {m.group(1)}")

    # --- internal links resolve ---
    for m in re.finditer(r'href="(/[^"#?]*)"', s):
        h = m.group(1)
        if h.startswith("/assets/") or "." in h.rsplit("/",1)[-1]:
            if not asset(h)[0]: fail(p, f"broken internal link: {h}")
        else:
            target = h.strip("/") + "/index.html" if h != "/" else "index.html"
            if not LIVE and not os.path.exists(target): fail(p, f"broken internal link: {h}")

    # --- banned phrases ---
    low = s.lower()
    for w in BANNED:
        if w in low: fail(p, f"banned phrase present: '{w}'")

# --- cross-page checks ---
for t, ps in titles.items():
    if len(ps) > 1: fail(ps[1], f"duplicate <title> with {ps[0]}: {t[:50]}")
for c, ps in canon.items():
    if len(ps) > 1: fail(ps[1], f"duplicate canonical with {ps[0]}: {c}")

# --- sitemap ---
sm = get("sitemap.xml") if LIVE else open("sitemap.xml").read()
try:
    import xml.dom.minidom; xml.dom.minidom.parseString(sm)
except Exception as e:
    fail("sitemap.xml", f"invalid XML: {e}")
locs = re.findall(r"<loc>([^<]+)</loc>", sm)
for l in locs:
    t = l.replace(BASE, "").strip("/")
    t = (t + "/index.html").lstrip("/") if t else "index.html"
    if not LIVE and not os.path.exists(t): fail("sitemap.xml", f"lists a page that does not exist: {l}")
for il in re.findall(r"<image:loc>([^<]+)</image:loc>", sm):
    if not asset(il)[0]: fail("sitemap.xml", f"image 404s: {il}")
listed = {l.replace(BASE, "").strip("/") for l in locs}
for p in pages():
    slug = p.replace("index.html", "").strip("/")
    if slug not in listed: fail("sitemap.xml", f"page not in sitemap: /{slug}/")

# --- every article image needs a matching row thumbnail ---
home = get("index.html")
for m in re.finditer(r'<img class="thumb"[^>]+src="([^"]+)"', home):
    if not asset(m.group(1))[0]: fail("index.html", f"row thumbnail missing: {m.group(1)}")

# --- report ---
print()
for p, m in fails: print(f"  FAIL  {p:52} {m}")
for p, m in warns: print(f"  warn  {p:52} {m}")
print("\n" + "="*66)
print(f"  {len(fails)} failure(s), {len(warns)} warning(s), {len(pages())} pages checked")
sys.exit(1 if fails else 0)
