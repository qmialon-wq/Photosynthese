"""Create bounded WebP delivery copies; preserve the supplied PNG masters."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path

from PIL import Image

FRONTEND = Path(__file__).resolve().parents[1]
PUBLIC = FRONTEND / "public"
SCENES = ("forest", "sky", "rivers", "underwater", "wetland", "meadow", "coast", "night-forest")


def convert(source: Path, target: Path, width: int, quality: int) -> dict:
    with Image.open(source) as original:
        image = original.convert("RGBA" if "A" in original.getbands() else "RGB")
        image.thumbnail((width, width), Image.Resampling.LANCZOS)
        image.save(target, "WEBP", quality=quality, method=6, exact=True)
        with Image.open(target) as decoded:
            alpha_exact = (
                "A" not in image.getbands()
                or decoded.getchannel("A").tobytes() == image.getchannel("A").tobytes()
            )
        if not alpha_exact:
            raise ValueError(f"WebP alpha changed: {target}")
        return {
            "url": "/" + target.relative_to(PUBLIC).as_posix(),
            "source": "/" + source.relative_to(PUBLIC).as_posix(),
            "sourceBytes": source.stat().st_size,
            "bytes": target.stat().st_size,
            "sha256": hashlib.sha256(target.read_bytes()).hexdigest(),
            "width": image.width,
            "height": image.height,
            "estimatedRgbaMipBytes": round(image.width * image.height * 4 * 4 / 3),
            "alphaExactAtDeliveryResolution": alpha_exact,
            "quality": quality,
        }


def main() -> None:
    scenes = {}
    for scene in SCENES:
        root = PUBLIC / "experience-art" / scene
        scenes[scene] = {
            role: convert(root / f"{role}-v1.png", root / f"{role}-runtime.webp", width, quality)
            for role, width, quality in (("foreground", 1280, 88), ("primary", 1920, 88))
        }
    media = PUBLIC / "experience-media"
    poster = convert(media / "manifesto-review.png", media / "manifesto-review.webp", 1440, 90)
    inventory = {
        "version": 1,
        "method": "Pillow WebP, original masters unchanged; alpha preserved at delivery resolution",
        "scenes": scenes,
        "poster": poster,
    }
    encoded = json.dumps(inventory, ensure_ascii=False, indent=2) + "\n"
    (PUBLIC / "experience-art" / "runtime-assets.json").write_text(encoded, encoding="utf-8")
    (FRONTEND / "src" / "experience" / "content" / "runtime-assets.json").write_text(
        encoded, encoding="utf-8"
    )
    records = [resource for scene in scenes.values() for resource in scene.values()] + [poster]
    print(
        json.dumps(
            {
                "resources": len(records),
                "sourceBytes": sum(r["sourceBytes"] for r in records),
                "deliveryBytes": sum(r["bytes"] for r in records),
            },
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
