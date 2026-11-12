"""Resize the supplied official symbols without tracing or changing their shapes.

Run from any directory with Python and Pillow==11.1.0 installed.
"""

from pathlib import Path

from PIL import Image, ImageOps

FRONTEND = Path(__file__).resolve().parents[1]
SOURCES = FRONTEND / "src" / "assets" / "favicon"
PUBLIC = FRONTEND / "public"


def square_icon(source: Path, size: int) -> Image.Image:
    """Keep the native aspect ratio and leave 1/16 of each side transparent."""
    with Image.open(source) as image:
        symbol = image.convert("RGBA")
    bounds = symbol.getchannel("A").getbbox()
    if bounds is None:
        raise ValueError(f"Empty official symbol: {source}")
    margin = size // 16
    symbol = ImageOps.contain(
        symbol.crop(bounds),
        (size - 2 * margin, size - 2 * margin),
        Image.Resampling.LANCZOS,
    )
    canvas = Image.new("RGBA", (size, size))
    canvas.alpha_composite(symbol, ((size - symbol.width) // 2, (size - symbol.height) // 2))
    return canvas


def main() -> None:
    PUBLIC.mkdir(exist_ok=True)
    black = SOURCES / "symbiose-black.png"
    white = SOURCES / "symbiose-white.png"
    light = square_icon(black, 256)
    # Give both adaptive icons the same small sizes as the fallback: browsers
    # may otherwise prefer the fallback's exact 16/32 px frames over a large PNG.
    for variant, source in (("light", black), ("dark", white)):
        square_icon(source, 256).save(
            PUBLIC / f"favicon-{variant}.ico",
            sizes=[(size, size) for size in (16, 32, 48, 256)],
            append_images=[square_icon(source, size) for size in (16, 32, 48)],
        )
    # Dedicated renders from the originals retain detail at every ICO size.
    light.save(
        PUBLIC / "favicon.ico",
        sizes=[(16, 16), (32, 32), (48, 48)],
        append_images=[square_icon(black, size) for size in (16, 32, 48)],
    )
    square_icon(black, 180).save(PUBLIC / "apple-touch-icon.png", optimize=True)


if __name__ == "__main__":
    main()
