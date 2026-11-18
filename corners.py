
from PIL import Image
d="C:/Users/PRATHAM/AppData/Local/hermes/cache/scratch/readme/png/"
for n in ("hero-dark","graph-dark","tile-build-dark"):
    im=Image.open(d+n+".png").convert("RGB")
    w,h=im.size
    print(n, "corner", im.getpixel((2,2)), "edge-mid", im.getpixel((w//2,2)), "card", im.getpixel((w//2,20)))
