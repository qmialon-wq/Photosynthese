import random
from collections import defaultdict
from collections.abc import Mapping

from ..config import SplitConfig
from ..errors import ManifestError
from ..schemas import Inventory, Split


def split_videos(
    source: Inventory,
    config: SplitConfig,
    seed: int = 42,
    sequence_groups: Mapping[str, str] | None = None,
) -> Inventory:
    """Stratifie des groupes, jamais des images. Les candidats ne sont pas des vérités."""
    groups: dict[str, list[int]] = defaultdict(list)
    # Union des groupes explicites et des contenus identiques, même transitivement.
    parents = list(range(len(source.videos)))

    def find(index: int) -> int:
        while parents[index] != index:
            parents[index] = parents[parents[index]]
            index = parents[index]
        return index

    seen: dict[tuple[str, str], int] = {}
    for i, video in enumerate(source.videos):
        explicit = (sequence_groups or {}).get(video.video_id, video.group_id)
        for kind, key in (("content", video.content_hash), ("sequence", explicit)):
            if key is not None:
                previous = seen.setdefault((kind, key), i)
                parents[find(i)] = find(previous)
    for i in range(len(source.videos)):
        groups[str(find(i))].append(i)
    strata: dict[str, list[str]] = defaultdict(list)
    for group, indices in groups.items():
        labels = {source.videos[i].species_candidate for i in indices} - {None}
        if len(labels) > 1:
            raise ManifestError("Un groupe contient des candidats contradictoires : revue requise")
        strata[next(iter(labels), "unknown")].append(group)
    assignments: dict[int, tuple[Split, str]] = {}
    for label, keys in sorted(strata.items()):
        keys.sort(key=lambda key: min(source.videos[i].video_id for i in groups[key]))
        random.Random(f"{seed}:{label}").shuffle(keys)
        count = len(keys)
        nt = (
            min(count - 1, max(1, round(count * config.test_fraction)))
            if count >= 2 and config.test_fraction
            else 0
        )
        nv = (
            min(count - nt - 1, max(1, round(count * config.validation_fraction)))
            if count >= 3 and config.validation_fraction
            else 0
        )
        for position, key in enumerate(keys):
            split: Split = "test" if position < nt else "val" if position < nt + nv else "train"
            group_id = min(source.videos[i].video_id for i in groups[key])
            for index in groups[key]:
                assignments[index] = split, group_id
    return source.model_copy(
        update={
            "videos": tuple(
                video.model_copy(update={"split": assignments[i][0], "group_id": assignments[i][1]})
                for i, video in enumerate(source.videos)
            )
        }
    )
