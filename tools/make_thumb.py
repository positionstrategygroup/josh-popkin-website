#!/usr/bin/env python3
"""
Square row thumbnails, framed by measurement rather than by eye.

Give it where the face actually is and it computes the crop:
  - the head (hairline to chin) fills HEAD_FRACTION of the square
  - the eyes sit EYE_LINE down from the top

    python3 tools/make_thumb.py SOURCE OUT.jpg --eyes Y --hair Y --chin Y --cx X

Measure those four numbers off a gridded copy of the source; don't guess them.
"""
import sys, argparse, os
import numpy as np, cv2
from PIL import Image, ImageOps

HEAD_FRACTION = 0.55   # hairline-to-chin as a share of the square's height
EYE_LINE      = 0.40   # eyes this far down from the top of the square

ap = argparse.ArgumentParser()
ap.add_argument("source"); ap.add_argument("out")
ap.add_argument("--eyes", type=int, required=True)
ap.add_argument("--hair", type=int, required=True)
ap.add_argument("--chin", type=int, required=True)
ap.add_argument("--cx",   type=int, required=True)
ap.add_argument("--size", type=int, default=160)
ap.add_argument("--desc", default="Josh Popkin")
a = ap.parse_args()

pil = ImageOps.exif_transpose(Image.open(a.source).convert("RGB"))
src = cv2.cvtColor(np.array(pil), cv2.COLOR_RGB2BGR)
H, W = src.shape[:2]

side = int(round((a.chin - a.hair) / HEAD_FRACTION))
side = min(side, H, W)
top  = int(round(a.eyes - EYE_LINE * side))
left = int(round(a.cx - side / 2))
top  = max(0, min(top,  H - side))
left = max(0, min(left, W - side))
crop = src[top:top+side, left:left+side]

lab = cv2.cvtColor(crop, cv2.COLOR_BGR2LAB).astype(np.float32); L = lab[...,0]/255.0
o = np.clip((L-.82)/.18, 0, 1); L = L - o*o*.09
L = .012 + L*(1-.012)
L = np.clip(L + .075*np.sin(np.pi*np.clip(L,0,1))*(L-0.5)*2, 0, 1)
lab[...,0] = L*255
out = cv2.cvtColor(np.clip(lab,0,255).astype(np.uint8), cv2.COLOR_LAB2BGR)
out = cv2.resize(out, (a.size, a.size), interpolation=cv2.INTER_AREA)
out = cv2.addWeighted(out, 1.18, cv2.GaussianBlur(out,(0,0),1.1), -0.18, 0)

img = Image.fromarray(cv2.cvtColor(out, cv2.COLOR_BGR2RGB))
ex = Image.Exif(); ex[270] = a.desc; ex[315] = "Josh Popkin"
img.save(a.out, quality=84, optimize=True, exif=ex.tobytes())

eye_pct  = (a.eyes - top) / side
head_pct = (a.chin - a.hair) / side
print(f"  crop {side}x{side} at ({left},{top})  ->  {a.out}")
print(f"  eyes {eye_pct:.0%} down (target {EYE_LINE:.0%})   head fills {head_pct:.0%} (target {HEAD_FRACTION:.0%})")
