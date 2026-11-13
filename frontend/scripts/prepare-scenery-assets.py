"""Create self-contained delivery scenery from archived CC0 sources, never download at runtime."""

from __future__ import annotations

import hashlib
import importlib.util
import json
import sys
from pathlib import Path

from PIL import Image

ROOT = Path(__file__).resolve().parents[2]
SOURCE = ROOT / "output/symbiose/scenery-sources"
DEST = ROOT / "frontend/public/experience-models"


def main() -> None:
    spec = importlib.util.spec_from_file_location(
        "spatial", Path(__file__).with_name("prepare-spatial-assets.py")
    )
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    if "--stage-tree" in sys.argv:
        module.bundle(
            SOURCE / "tree_small_02/tree_small_02.gltf", ROOT / "frontend/tools/tree-source.glb"
        )
        return
    frames = sorted((SOURCE / "tree-atlas").glob("[0-3].png"))
    if len(frames) == 4:
        images = [Image.open(frame).convert("RGBA") for frame in frames]
        boxes = [image.getchannel("A").getbbox() for image in images]
        box = (
            min(b[0] for b in boxes),
            min(b[1] for b in boxes),
            max(b[2] for b in boxes),
            max(b[3] for b in boxes),
        )
        atlas = Image.new("RGBA", (2048, 768))
        for index, image in enumerate(images):
            atlas.paste(
                image.crop(box).resize((512, 768), Image.Resampling.LANCZOS), (index * 512, 0)
            )
            image.close()
        atlas.save(SOURCE / "tree-atlas/atlas.webp", "WEBP", quality=92, method=6, exact=True)
        (SOURCE / "tree-atlas/atlas.json").write_text(
            json.dumps({"views": 4, "aspect": (box[2] - box[0]) / (box[3] - box[1])}) + "\n",
            encoding="utf-8",
        )
    inventory = json.loads((DEST / "inventory.json").read_text(encoding="utf-8"))
    assets = inventory["assets"]
    tree = SOURCE / "tree_small_02"
    for unused in ("tree-far", "aerial_grass_rock-nor_gl", "aerial_grass_rock-Rough"):
        assets.pop(unused, None)
    for name, source, original in (
        ("tree-near", tree / "tree-near.gltf", "tree_small_02"),
        ("grass-medium", SOURCE / "grass_medium_01/grass_medium_01.gltf", "grass_medium_01"),
    ):
        assets[name] = module.bundle(source, DEST / (name + ".glb"))
        assets[name].update(
            license="CC0-1.0", role="scenery", sourceUrl="https://polyhaven.com/a/" + original
        )
    for name in ("aerial_grass_rock", "rock_face_02"):
        for kind in ("Diffuse",) if name == "aerial_grass_rock" else ("Diffuse", "nor_gl", "Rough"):
            source = SOURCE / name / (kind + ".jpg")
            if not source.exists():
                continue
            target = DEST / (name + "-" + kind + ".jpg")
            with Image.open(source) as image:
                image.save(target, "JPEG", quality=88, optimize=True)
            assets[name + "-" + kind] = {
                "url": "/experience-models/" + target.name,
                "bytes": target.stat().st_size,
                "sha256": hashlib.sha256(target.read_bytes()).hexdigest(),
                "role": "material",
                "license": "CC0-1.0",
                "sourceUrl": "https://polyhaven.com/a/" + name,
            }
    for name, source in (
        ("tree-atlas", SOURCE / "tree-atlas/atlas.webp"),
        ("tree-atlas-metadata", SOURCE / "tree-atlas/atlas.json"),
    ):
        target = DEST / (name + source.suffix)
        target.write_bytes(source.read_bytes())
        assets[name] = {
            "url": "/experience-models/" + target.name,
            "bytes": target.stat().st_size,
            "sha256": hashlib.sha256(target.read_bytes()).hexdigest(),
            "role": "scenery",
            "license": "CC0-1.0",
            "sourceUrl": "https://polyhaven.com/a/tree_small_02",
        }
    encoded = json.dumps(inventory, ensure_ascii=False, indent=2) + "\n"
    (DEST / "inventory.json").write_text(encoded, encoding="utf-8")
    (ROOT / "frontend/src/experience/content/spatial-assets.json").write_text(
        encoded, encoding="utf-8"
    )
    print(
        json.dumps(
            {name: asset["bytes"] for name, asset in assets.items() if asset["role"] == "scenery"},
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
