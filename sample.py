
from PIL import Image
for t in ("light","dark"):
    im=Image.open(f"C:/Users/PRATHAM/AppData/Local/hermes/cache/scratch/readme/render-{t}.png").convert("RGB")
    w,h=im.size
    print(t, w, h)
    # sample: hero card bg, tile1, tile2, tile3, repo card, code block
    pts={"hero-bg":(60,60),"tile1":(160,1700),"tile2":(620,1700),"tile3":(1080,1700)}
    for k,(x,y) in pts.items():
        try: print("  ",k, im.getpixel((x,y)))
        except Exception as e: print("  ",k,"oob")
