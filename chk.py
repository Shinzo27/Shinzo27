
from PIL import Image
im=Image.open("C:/Users/PRATHAM/AppData/Local/hermes/cache/scratch/readme/page-light.png").convert("L")
w,h=im.size; print("page", w, h)
