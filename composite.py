
from PIL import Image
import glob, os
d="C:/Users/PRATHAM/AppData/Local/hermes/cache/scratch/readme/png/"
for f in glob.glob(d+"raw-*.png"):
    n=os.path.basename(f)[4:-4]
    im=Image.open(f).convert("RGBA")
    bg=(13,17,23,255) if n.endswith("-dark") else (255,255,255,255)
    canvas=Image.new("RGBA", im.size, bg)
    canvas.alpha_composite(im)
    canvas.convert("RGB").save(d+n+".png")
    os.remove(f)
    print(n, canvas.size)
