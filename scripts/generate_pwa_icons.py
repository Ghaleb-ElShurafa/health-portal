"""Generates simple PWA icon PNGs (192x192 and 512x512) for the portal.
Run once; output is committed to pwa/ so it doesn't need Pillow at runtime.
"""

from PIL import Image, ImageDraw, ImageFont

BG_COLOR = (14, 90, 92)  # dark teal, matches a clinical/health tone
FG_COLOR = (255, 255, 255)


def make_icon(size, out_path):
    img = Image.new("RGB", (size, size), BG_COLOR)
    draw = ImageDraw.Draw(img)

    # Simple cross (medical) glyph, drawn as two rectangles.
    bar_w = size * 0.18
    bar_len = size * 0.56
    cx, cy = size / 2, size / 2
    draw.rectangle(
        [cx - bar_w / 2, cy - bar_len / 2, cx + bar_w / 2, cy + bar_len / 2],
        fill=FG_COLOR,
    )
    draw.rectangle(
        [cx - bar_len / 2, cy - bar_w / 2, cx + bar_len / 2, cy + bar_w / 2],
        fill=FG_COLOR,
    )

    img.save(out_path)
    print(f"wrote {out_path}")


if __name__ == "__main__":
    make_icon(192, "pwa/icon-192.png")
    make_icon(512, "pwa/icon-512.png")
