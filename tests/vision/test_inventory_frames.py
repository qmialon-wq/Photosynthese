from collections.abc import Callable
from pathlib import Path

import pytest
from biosentinelle_vision.classes import ClassManifest
from biosentinelle_vision.cli import main
from biosentinelle_vision.config import FramesConfig, SplitConfig
from biosentinelle_vision.datasets.frames import extract_frames, sample_indices
from biosentinelle_vision.datasets.inventory import inventory, species_candidates
from biosentinelle_vision.datasets.split import split_videos
from biosentinelle_vision.errors import ManifestError, VideoError
from biosentinelle_vision.schemas import FramesManifest, Inventory, VideoRecord
from biosentinelle_vision.storage import LocalStorage
from PIL import Image


@pytest.mark.parametrize(
    "filename,expected",
    [
        ("PIgeons-Scene-020.mp4", ("pigeons",)),
        ("Chouette_hulotte.mp4", ("chouette",)),
        ("faisan-01.MP4", ("faisans",)),
        ("renard_et_sangliers.mp4", ("sanglier", "renards")),
        ("inconnu.mp4", ()),
        ("martre.mp4", ("martres",)),
        ("geais.avi", ("geai",)),
        ("chevreuil001.mp4", ("chevreuil",)),
    ],
)
def test_filename_aliases(filename: str, expected: tuple[str, ...], classes: ClassManifest) -> None:
    assert species_candidates(Path(filename), classes) == expected
    assert species_candidates(Path("renards") / "inconnu.mp4", classes) == ()


def test_inventory_reports_bad_and_unknown_videos(
    make_video: Callable, classes: ClassManifest
) -> None:
    video = make_video()
    make_video("inconnu.avi", shade=80)
    (video.parent / "buse.mp4").write_bytes(b"not a video")
    result = inventory(video.parent, classes)
    assert len(result.videos) == 3
    assert next(v for v in result.videos if v.relative_path == "buse.mp4").error
    unknown = next(v for v in result.videos if v.relative_path == "inconnu.avi")
    assert unknown.species_candidate is None and unknown.error is None
    with pytest.raises(VideoError):
        inventory(video.parent / "absent", classes)


def make_inventory(classes: ClassManifest, count: int) -> Inventory:
    return Inventory(
        class_manifest_version=classes.version,
        dataset_root=".",
        videos=tuple(
            VideoRecord(
                video_id=str(i),
                relative_path=f"renard-{i}.avi",
                content_hash=f"content-{i}",
                species_candidate="renards",
            )
            for i in range(count)
        ),
    )


@pytest.mark.parametrize(
    "count,expected", [(1, {"train"}), (2, {"train", "test"}), (3, {"train", "val", "test"})]
)
def test_split_small_classes(count: int, expected: set[str], classes: ClassManifest) -> None:
    source = make_inventory(classes, count)
    result = split_videos(source, SplitConfig())
    assert {v.split for v in result.videos} == expected
    assert result == split_videos(source, SplitConfig())


def test_split_groups_duplicates_and_explicit_sequences(classes: ClassManifest) -> None:
    source = make_inventory(classes, 6)
    videos = list(source.videos)
    videos[1] = videos[1].model_copy(update={"content_hash": "content-0"})
    source = source.model_copy(update={"videos": tuple(videos)})
    result = split_videos(source, SplitConfig(), sequence_groups={"1": "sequence", "2": "sequence"})
    assert len({result.videos[i].split for i in (0, 1, 2)}) == 1
    assert len({result.videos[i].group_id for i in (0, 1, 2)}) == 1
    videos[1] = videos[1].model_copy(update={"species_candidate": "buse"})
    with pytest.raises(ManifestError, match="contradictoires"):
        split_videos(source.model_copy(update={"videos": tuple(videos)}), SplitConfig())


def test_sampling_respects_minimum_spacing() -> None:
    config = FramesConfig(max_per_video=24, min_seconds_between=0.8)
    samples = sample_indices(20, 10, config)
    assert samples == (0, 8, 16)
    assert sample_indices(1, 30, config) == (0,)
    assert len(sample_indices(10000, 25, config)) == 24
    with pytest.raises(VideoError):
        sample_indices(20, float("nan"), config)


def test_extraction_real_jpeg_and_manifest(
    make_video: Callable,
    classes: ClassManifest,
    tmp_path: Path,
) -> None:
    video = make_video()
    source = split_videos(inventory(video.parent, classes), SplitConfig())
    storage = LocalStorage(tmp_path / "results")
    result = extract_frames(source, storage, FramesConfig())
    assert len(result.frames) == 3 and not result.issues
    assert result == FramesManifest.model_validate_json(storage.read_bytes("frames.json"))
    for record in result.frames:
        with Image.open(storage.path(record.image_key)) as image:
            assert image.size == (64, 48)
            assert image.format == "JPEG"
        assert record.species_candidate == "renards" and record.split == "train"
    video.write_bytes(b"changed")
    changed = extract_frames(source, storage, FramesConfig())
    assert not changed.frames and "modifiée" in changed.issues[0].message


def test_cli_inventory_and_extract(make_video: Callable, tmp_path: Path) -> None:
    video = make_video()
    index = tmp_path / "inventory.json"
    assert main(["inventory", str(video.parent), "--output", str(index)]) == 0
    assert (
        main(["extract-frames", "--inventory", str(index), "--output-dir", str(tmp_path / "out")])
        == 0
    )
    assert (tmp_path / "out/frames.json").is_file()
    assert main(["inventory", str(tmp_path / "absent"), "--output", str(index)]) == 1
    (video.parent / "buse.mp4").write_bytes(b"broken")
    assert main(["inventory", str(video.parent), "--output", str(index)]) == 2
