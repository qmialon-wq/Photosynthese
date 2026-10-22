from collections.abc import Callable
from pathlib import Path

import pytest
from biosentinelle_vision.classes import ClassManifest
from biosentinelle_vision.config import SplitConfig
from biosentinelle_vision.datasets.inventory import file_hash
from biosentinelle_vision.datasets.organize import organize_videos
from biosentinelle_vision.errors import ManifestError
from biosentinelle_vision.schemas import Inventory
from biosentinelle_vision.storage import LocalStorage


def test_copy_by_name_and_repeat_without_modifying_sources(
    make_video: Callable,
    tmp_path: Path,
    classes: ClassManifest,
) -> None:
    video = make_video()
    unknown = make_video("inconnu.avi", shade=80)
    digest = file_hash(video)
    destination = tmp_path / "classified"
    reports = LocalStorage(tmp_path / "reports")
    first = organize_videos(video.parent, destination, reports, classes, SplitConfig())
    assert first["total"] == first["copied"] == 2
    assert first["counts"] == {"_a_verifier": 1, "renards": 1}
    assert file_hash(destination / "renards" / video.name) == digest
    assert video.is_file() and unknown.is_file() and file_hash(video) == digest
    assert first["human_validated"] is False
    index = Inventory.model_validate_json(reports.read_bytes("videos.json"))
    assert index.dataset_root == str(destination)
    assert {v.relative_path for v in index.videos} == {
        "renards/Renards-Scene-001.avi",
        "_a_verifier/inconnu.avi",
    }
    repeated = organize_videos(video.parent, destination, reports, classes, SplitConfig())
    assert repeated["copied"] == 0 and repeated["unchanged"] == 2
    assert not reports.path("review.json").exists()


def test_conflicting_destination_is_not_overwritten(
    make_video: Callable,
    tmp_path: Path,
    classes: ClassManifest,
) -> None:
    video = make_video()
    target = tmp_path / "classified/renards" / video.name
    target.parent.mkdir(parents=True)
    target.write_bytes(b"keep existing content")
    result = organize_videos(
        video.parent,
        tmp_path / "classified",
        LocalStorage(tmp_path / "reports"),
        classes,
        SplitConfig(),
    )
    assert result["issues"] and result["total"] == 0
    assert target.read_bytes() == b"keep existing content"
    assert video.is_file()


def test_organize_rejects_recursive_destination(
    make_video: Callable,
    tmp_path: Path,
    classes: ClassManifest,
) -> None:
    video = make_video()
    with pytest.raises(ManifestError, match="non imbriqués"):
        organize_videos(
            video.parent,
            video.parent / "classified",
            LocalStorage(tmp_path / "reports"),
            classes,
            SplitConfig(),
        )
