from pathlib import Path

from PIL import Image, ImageDraw, ImageFont


ROOT = Path(__file__).resolve().parent.parent
ASSETS = ROOT / "assets"
ASSETS.mkdir(parents=True, exist_ok=True)

png_path = ASSETS / "windic.png"
ico_path = ASSETS / "windic.ico"

size = 256
img = Image.new("RGBA", (size, size), (0, 0, 0, 0))
draw = ImageDraw.Draw(img)

# Soft rounded square background.
draw.rounded_rectangle(
    (18, 18, size - 18, size - 18),
    radius=52,
    fill=(236, 244, 255, 255),
    outline=(127, 163, 219, 255),
    width=4,
)

# Two compact cards to hint two side-by-side translation boxes.
draw.rounded_rectangle((48, 78, 118, 178), radius=18, fill=(255, 255, 255, 255), outline=(167, 188, 216, 255), width=3)
draw.rounded_rectangle((138, 78, 208, 178), radius=18, fill=(255, 255, 255, 255), outline=(167, 188, 216, 255), width=3)

try:
    font = ImageFont.truetype("segoeuib.ttf", 42)
except Exception:
    font = ImageFont.load_default()

draw.text((84, 23), "W", font=font, fill=(34, 58, 94, 255))

img.save(png_path)
img.save(ico_path, sizes=[(256, 256), (128, 128), (64, 64), (48, 48), (32, 32), (16, 16)])
print(f"Created: {png_path}")
print(f"Created: {ico_path}")
