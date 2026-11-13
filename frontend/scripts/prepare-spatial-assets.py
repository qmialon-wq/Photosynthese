"""Bundle supplied animals and selected CC0 assets; keep source files intact."""

from __future__ import annotations

import hashlib
import io
import json
import struct
from pathlib import Path

from PIL import Image

ROOT = Path(__file__).resolve().parents[2]
DEST = ROOT / "frontend/public/experience-models"
SOURCES = ROOT / "output/symbiose/nature-sources"


def bundle(source: Path, target: Path) -> dict:
    if source.suffix == ".glb":
        raw = source.read_bytes()
        length = struct.unpack_from("<I", raw, 12)[0]
        document = json.loads(raw[20 : 20 + length])
        buffers = [raw[28 + length :]]
    else:
        document = json.loads(source.read_text(encoding="utf-8"))
        buffers = [(source.parent / b["uri"]).read_bytes() for b in document["buffers"]]
    old_views = document.get("bufferViews", [])
    views = [
        buffers[v.get("buffer", 0)][
            v.get("byteOffset", 0) : v.get("byteOffset", 0) + v["byteLength"]
        ]
        for v in old_views
    ]
    for image in document.get("images", []):
        if "uri" in image:
            encoded = (source.parent / image.pop("uri")).read_bytes()
            image["bufferView"] = len(views)
            views.append(encoded)
            old_views.append({"buffer": 0})
        index = image["bufferView"]
        with Image.open(io.BytesIO(views[index])) as original:
            bitmap = original.convert("RGBA" if "A" in original.getbands() else "RGB")
            bitmap.thumbnail((1024, 1024), Image.Resampling.LANCZOS)
            result = io.BytesIO()
            fmt = "PNG" if bitmap.mode == "RGBA" else "JPEG"
            bitmap.save(result, fmt, quality=86, optimize=True)
            image["mimeType"] = "image/png" if fmt == "PNG" else "image/jpeg"
            views[index] = result.getvalue()
    binary = bytearray()
    for view, data in zip(old_views, views, strict=False):
        binary.extend(b"\0" * (-len(binary) % 4))
        view.update(buffer=0, byteOffset=len(binary), byteLength=len(data))
        binary.extend(data)
    document["buffers"] = [{"byteLength": len(binary)}]
    document["bufferViews"] = old_views
    document["animations"] = [
        a for a in document.get("animations", []) if a.get("name") in {"Idle", "Walk", "Eating"}
    ]
    encoded = json.dumps(document, separators=(",", ":")).encode()
    encoded += b" " * (-len(encoded) % 4)
    binary.extend(b"\0" * (-len(binary) % 4))
    glb = (
        struct.pack("<III", 0x46546C67, 2, 28 + len(encoded) + len(binary))
        + struct.pack("<II", len(encoded), 0x4E4F534A)
        + encoded
        + struct.pack("<II", len(binary), 0x004E4942)
        + binary
    )
    target.write_bytes(glb)
    return {
        "url": "/experience-models/" + target.name,
        "bytes": len(glb),
        "sha256": hashlib.sha256(glb).hexdigest(),
        "source": source.relative_to(ROOT).as_posix(),
        "sourceBytes": source.stat().st_size,
    }


def main() -> None:
    DEST.mkdir(parents=True, exist_ok=True)
    # Preserve independently prepared scenery when refreshing supplied animals.
    current = DEST / "inventory.json"
    previous = json.loads(current.read_text(encoding="utf-8"))["assets"] if current.exists() else {}
    assets = {
        key: value
        for key, value in previous.items()
        if value.get("role") == "scenery"
        or any(name in value.get("sourceUrl", "") for name in ("aerial_grass_rock", "rock_face_02"))
    }
    for name in ("buse", "chevreuil", "sanglier", "pigeon", "poisson"):
        assets[name] = bundle(ROOT / "3d assets" / (name + ".glb"), DEST / (name + ".glb"))
        assets[name].update(license="User supplied; original license not provided", role="animal")
    for name in ("fern_02", "rock_moss_set_01", "tree_stump_01"):
        assets[name] = bundle(SOURCES / name / (name + ".gltf"), DEST / (name + ".glb"))
        assets[name].update(
            license="CC0-1.0", sourceUrl="https://polyhaven.com/a/" + name, role="nature"
        )
    for name in ("forest_ground_04", "bark_brown_01"):
        for kind in ("Diffuse", "nor_gl", "Rough"):
            target = DEST / (name + "-" + kind + ".jpg")
            with Image.open(SOURCES / name / (kind + ".jpg")) as image:
                image.save(target, "JPEG", quality=88, optimize=True)
            assets[name + "-" + kind] = {
                "url": "/experience-models/" + target.name,
                "bytes": target.stat().st_size,
                "sha256": hashlib.sha256(target.read_bytes()).hexdigest(),
                "license": "CC0-1.0",
                "sourceUrl": "https://polyhaven.com/a/" + name,
                "role": "material",
            }
    inventory = {"version": 1, "assets": assets}
    candidates = [*ROOT.glob("*.svg"), *(ROOT / "3d assets").glob("*.svg")]
    logos = [p for p in candidates if "symbiose" in p.stem.lower() or "logo" in p.stem.lower()]
    if len(logos) == 1:
        svg = logos[0].read_bytes()
        (DEST / "symbiose-logo.svg").write_bytes(svg)
        assets["logo-svg"] = {
            "url": "/experience-models/symbiose-logo.svg",
            "bytes": len(svg),
            "sha256": hashlib.sha256(svg).hexdigest(),
            "source": logos[0].relative_to(ROOT).as_posix(),
            "role": "brand",
            "license": "User supplied",
        }
    encoded = json.dumps(inventory, ensure_ascii=False, indent=2) + "\n"
    (DEST / "inventory.json").write_text(encoded, encoding="utf-8")
    (ROOT / "frontend/src/experience/content/spatial-assets.json").write_text(
        encoded, encoding="utf-8"
    )
    print(json.dumps({key: a["bytes"] for key, a in assets.items()}, indent=2))


if __name__ == "__main__":
    main()
