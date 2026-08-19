from pathlib import Path

from PIL import Image, ImageDraw, ImageFont


HERE = Path(__file__).resolve().parent
PAGES = sorted((HERE / "render" / "pages").glob("page-*.png"))
OUT = HERE / "render" / "sheets"
OUT.mkdir(parents=True, exist_ok=True)

font = ImageFont.load_default(size=24)
for sheet_no, offset in enumerate(range(0, len(PAGES), 4), start=1):
    group = PAGES[offset : offset + 4]
    images = [Image.open(path).convert("RGB") for path in group]
    page_w = max(im.width for im in images)
    page_h = max(im.height for im in images)
    gutter = 30
    label_h = 42
    canvas = Image.new("RGB", (page_w * 2 + gutter * 3, (page_h + label_h) * 2 + gutter * 3), "#d0d0d0")
    draw = ImageDraw.Draw(canvas)
    for slot, (path, im) in enumerate(zip(group, images)):
        row, col = divmod(slot, 2)
        x = gutter + col * (page_w + gutter)
        y = gutter + row * (page_h + label_h + gutter)
        draw.text((x, y), path.stem.replace("page-", "Page "), fill="black", font=font)
        canvas.paste(im, (x, y + label_h))
    canvas.save(OUT / f"sheet-{sheet_no:02d}.jpg", quality=88, optimize=True)

print(f"pages={len(PAGES)} sheets={len(list(OUT.glob('sheet-*.jpg')))}")
