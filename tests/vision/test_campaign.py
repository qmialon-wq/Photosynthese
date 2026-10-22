from threading import Event
from uuid import uuid4

import pytest
from biosentinelle_vision.config import VisionSettings
from biosentinelle_vision.errors import ManifestError
from biosentinelle_vision.training import campaign


def fake_queue(tmp_path, monkeypatch, *, empty_validation=False, fail_model=False):
    target = tmp_path / "version/manifest.json"
    target.parent.mkdir()
    target.write_text("{}")
    target.with_name("training.json").write_text("{}")
    submitted, events, results = [], [], {}

    def submit(kind, payload, actor):
        identifier = str(uuid4())
        submitted.append((kind, payload))
        events.append("submit")
        if kind == "classification_dataset":
            results[identifier] = {
                "manifest": str(target),
                "counts": {
                    "train": {"chevreuil": 1},
                    "val": {} if empty_validation else {"chevreuil": 1},
                },
            }
        elif kind == "training":
            results[identifier] = {"model_id": str(uuid4())}
        else:
            results[identifier] = {"comparison_id": identifier}
        return {"id": identifier}

    def wait(identifier):
        events.append("wait")
        if fail_model and "model_id" in results[identifier]:
            raise ManifestError("Échec synthétique")
        return results[identifier]

    monkeypatch.setattr(campaign.console, "submit", submit)
    monkeypatch.setattr(campaign, "wait_for_task", wait)
    monkeypatch.setattr(campaign, "freeze_comparison", lambda body: body.model_dump(mode="json"))
    return submitted, events


@pytest.mark.parametrize("device", ["cpu", "cuda"])
def test_four_models_then_common_validation_and_resume_without_duplicates(
    tmp_path, monkeypatch, device
):
    submitted, events = fake_queue(tmp_path, monkeypatch)
    state = campaign.run_campaign(tmp_path, device=device, allow_weak_labels=True)
    assert [kind for kind, _ in submitted] == ["classification_dataset"] + ["training"] * 4 + [
        "classifiers_compare"
    ]
    assert events == ["submit", "wait"] * 6
    configs = [payload for kind, payload in submitted if kind == "training"]
    assert [p["model_name"] for p in configs] == list(campaign.ARCHITECTURES)
    assert len({p["snapshot_sha256"] for p in configs}) == 1
    assert all(p["epochs_head"] == 6 and p["epochs_finetune"] == 18 for p in configs)
    assert all(p["amp"] == ("off" if device == "cpu" else "auto") for p in configs)
    benchmark = submitted[-1][1]
    assert benchmark["model_ids"] == state["models"] and benchmark["split"] == "val"
    assert benchmark["allow_weak_labels"] is True
    restored = campaign.run_campaign(
        tmp_path,
        device=device,
        allow_weak_labels=True,
        resume=state["id"],
    )
    assert restored == state and len(submitted) == 6


@pytest.mark.parametrize("empty_validation,fail_model", [(True, False), (False, True)])
def test_no_benchmark_on_empty_validation_or_failed_model(
    tmp_path,
    monkeypatch,
    empty_validation,
    fail_model,
):
    submitted, _ = fake_queue(
        tmp_path,
        monkeypatch,
        empty_validation=empty_validation,
        fail_model=fail_model,
    )
    with pytest.raises(ManifestError):
        campaign.run_campaign(tmp_path, device="cpu", allow_weak_labels=False)
    assert all(kind != "classifiers_compare" for kind, _ in submitted)
    if empty_validation:
        assert len(submitted) == 1


def test_worker_uses_immutable_snapshot_and_keeps_training_registration(
    tmp_path, monkeypatch, classes
):
    from biosentinelle_vision import commands, console_tasks
    from biosentinelle_vision.datasets.inventory import file_hash

    snapshot = tmp_path / "snapshot.json"
    snapshot.write_text("{}")
    seen = []
    monkeypatch.setattr(
        commands, "train_from_manifest", lambda config, *_: seen.append(config) or {}
    )
    monkeypatch.setattr(console_tasks, "register_model", lambda *_: {"model_id": "test-only"})
    settings = VisionSettings(output_root=tmp_path, checkpoint_root=tmp_path / "checkpoints")
    row = {
        "id": str(uuid4()),
        "kind": "training",
        "actor": "test",
        "request": {
            "dataset_id": "base",
            "model_name": "resnet50",
            "snapshot_key": "snapshot.json",
            "snapshot_sha256": file_hash(snapshot),
            "initialization": "pretrained",
        },
    }
    assert console_tasks.perform(row, settings, classes, Event(), lambda *_: None)["model_id"]
    assert seen[0].train_manifest == snapshot and seen[0].training.database_metrics
    snapshot.write_text('{"changed":true}')
    with pytest.raises(ValueError, match="modifié"):
        console_tasks.perform(row, settings, classes, Event(), lambda *_: None)


def test_wait_stops_on_cancelled_task(monkeypatch):
    monkeypatch.setattr(
        campaign.console, "task", lambda _: {"status": "cancelled", "error": "stop"}
    )
    with pytest.raises(ManifestError, match="cancelled"):
        campaign.wait_for_task("test")
