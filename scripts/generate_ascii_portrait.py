#!/usr/bin/env python3
"""Generate the animated ASCII portrait embedded in the profile card."""

from __future__ import annotations

from pathlib import Path

from PIL import Image, ImageDraw, ImageEnhance, ImageFont, ImageOps


ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / "assets" / "portrait-ascii.png"
OUTPUT = ROOT / "assets" / "portrait-ascii.gif"
GLYPH_GROUPS = (".,`'", "-_:;", "irs!|", "xXA+=", "253hM", "HGS#9", "B&@%")
CELL_WIDTH = 3
CELL_HEIGHT = 5
FRAME_COUNT = 10


def monospace_font() -> ImageFont.FreeTypeFont | ImageFont.ImageFont:
    # Pillow's bundled font keeps animation output deterministic across runners.
    return ImageFont.load_default(size=5)


def generate() -> None:
    with Image.open(SOURCE) as source:
        gray = source.convert("L")

    columns = gray.width // CELL_WIDTH
    rows = gray.height // CELL_HEIGHT
    sample = gray.resize((columns, rows), Image.Resampling.BOX)
    sample = ImageOps.autocontrast(sample, cutoff=1)
    sample = ImageEnhance.Contrast(sample).enhance(1.15)
    cells: list[tuple[int, int, float, str]] = []
    for row in range(rows):
        for column in range(columns):
            level = (sample.getpixel((column, row)) / 255) ** 0.62
            if level < 0.14:
                continue
            group_index = min(len(GLYPH_GROUPS) - 1, int(level * len(GLYPH_GROUPS)))
            cells.append((column, row, level, GLYPH_GROUPS[group_index]))

    font = monospace_font()
    frames: list[Image.Image] = []

    for frame_index in range(FRAME_COUNT):
        frame = Image.new(
            "RGB",
            (columns * CELL_WIDTH, rows * CELL_HEIGHT),
            "#090d12",
        )
        draw = ImageDraw.Draw(frame)
        for column, row, level, group in cells:
            cell_index = row * columns + column
            glyph = group[(cell_index + frame_index) % len(group)]
            brightness = round(135 + level * 115)
            draw.text(
                (column * CELL_WIDTH, row * CELL_HEIGHT - 1),
                glyph,
                font=font,
                fill=(brightness, brightness, brightness),
            )
        frames.append(frame.quantize(colors=96, method=Image.Quantize.MEDIANCUT))

    frames[0].save(
        OUTPUT,
        save_all=True,
        append_images=frames[1:],
        duration=380,
        loop=0,
        optimize=True,
        disposal=2,
    )
    print(
        f"Generated {OUTPUT.relative_to(ROOT)} "
        f"({len(frames)} frames, {len(cells)} animated glyphs)"
    )


if __name__ == "__main__":
    generate()
