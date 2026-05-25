from PIL import Image
import numpy as np

img = Image.open('docs/images/hero_banner.png').convert('RGB')
arr = np.array(img)
# Find background color from top-left pixel
bg_color = arr[0, 0]
# Find rows that are not entirely background
mask = ~np.all(arr == bg_color, axis=-1)
rows = np.any(mask, axis=1)
if np.any(rows):
    top = np.argmax(rows)
    bottom = len(rows) - np.argmax(rows[::-1])
    print(f"Crop top: {top}, bottom: {bottom}, height: {bottom - top}")
else:
    print("Empty image")
