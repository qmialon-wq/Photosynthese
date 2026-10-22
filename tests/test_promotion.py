import copy

import pytest

from shared.promotion import PromotionPolicy, assess, macro_f1


def example():
    names = ["species-a", "species-b"]
    base_rows = [
        {"crop_id": str(i), "video_id": f"video-{i}", "truth": names[i % 2], "predicted": names[0]}
        for i in range(40)
    ]
    new_rows = [{**row, "predicted": row["truth"]} for row in base_rows]

    def model(identifier, rows):
        return {
            "model": {"model_id": identifier},
            "predictions": rows,
            "metrics": {
                "macro_f1": macro_f1(rows, names),
                "per_class": {n: {"recall": 0.5} for n in names},
            },
            "coverage": 1.0,
            "mean_inference_ms": 1.0,
            "failure_rate": 0.0,
        }

    return {
        "schema_version": "classifier-comparison-1",
        "human_validated": True,
        "protocol": {"split": "val"},
        "classes": {"classes": [{"name": n} for n in names]},
        "video_support": {n: 20 for n in names},
        "models": [model("champion", base_rows), model("challenger", new_rows)],
    }


def test_grouped_bootstrap_is_reproducible_and_requires_gain():
    policy = PromotionPolicy(min_samples=20, bootstrap_samples=50)
    report = example()
    a = assess(report, "champion", "challenger", policy)
    assert a == assess(report, "champion", "challenger", policy)
    assert a["status"] == "approved" and a["bootstrap_lower_95"] > 0
    report["models"][1]["coverage"] = 0.5
    assert assess(report, "champion", "challenger", policy)["status"] == "rejected"


@pytest.mark.parametrize(
    "change,status",
    [
        ({"human_validated": False}, "rejected"),
        ({"protocol": {"split": "test"}}, "rejected"),
        ({"video_support": {"species-a": 1, "species-b": 1}}, "manual_required"),
    ],
)
def test_no_promotion_on_weak_labels_test_or_insufficient_videos(change, status):
    report = copy.deepcopy(example())
    report.update(change)
    assert (
        assess(
            report, "champion", "challenger", PromotionPolicy(min_samples=20, bootstrap_samples=50)
        )["status"]
        == status
    )
