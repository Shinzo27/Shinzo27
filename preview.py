
import sys
from PIL import Image
ramp=" .:-=+*#%@"
def show(path, cols=110, box=None):
    im=Image.open(path).convert("L")
    if box:
        x,y,w,h=box; im=im.crop((x,y,x+w,y+h))
    w,h=im.size; rows=max(1,int(cols*h/w*0.46))
    im=im.resize((cols,rows), Image.LANCZOS)
    px=list(im.get_flattened_data())
    print(f"--- {path} {w}x{h}")
    for r in range(rows):
        print("".join(ramp[9-min(9, px[r*cols+c]*10//256)] for c in range(cols)))
p=sys.argv[1]; cols=int(sys.argv[2]) if len(sys.argv)>2 else 110
box=None
if len(sys.argv)>6: box=tuple(int(x) for x in sys.argv[3:7])
show(p, cols, box)
