#!/usr/bin/env python3
"""Every image referenced by an HTML page must exist. Run before every push."""
import re, os, glob, sys
missing = []
for f in ["index.html", "insights/index.html"] + sorted(glob.glob("insights/*/index.html")):
    for m in re.finditer(r'(?:src|href)="(/?assets/[^"]+)"', open(f).read()):
        p = m.group(1).lstrip("/")
        if not os.path.exists(p):
            missing.append((f, p))
for f, p in missing:
    print(f"MISSING  {p}   (referenced by {f})")
print(f"{'FAIL' if missing else 'OK'}: {len(missing)} missing asset(s)")
sys.exit(1 if missing else 0)
