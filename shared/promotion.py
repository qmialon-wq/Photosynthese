"""Règles de promotion : validation humaine, gain et bootstrap groupé par vidéo."""

import hashlib
import json
import random
from collections import defaultdict
from typing import Any
from uuid import uuid4

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict

from .review.database import ReviewError, jsonb, transaction


class PromotionPolicy(BaseSettings):
    model_config = SettingsConfigDict(env_prefix="BIOSENTINELLE_PROMOTION_", extra="forbid")
    min_macro_f1_gain: float = Field(default=0.01, ge=0, le=1)
    max_recall_drop: float = Field(default=0.05, ge=0, le=1)
    max_coverage_drop: float = Field(default=0.02, ge=0, le=1)
    max_latency_ratio: float = Field(default=1.5, ge=1)
    min_samples: int = Field(default=200, ge=1)
    min_videos_per_class: int = Field(default=3, ge=1)
    bootstrap_samples: int = Field(default=500, ge=50, le=10000)
    seed: int = 42


def macro_f1(rows: list[dict[str, Any]], classes: list[str]) -> float:
    support, predicted, correct = defaultdict(int), defaultdict(int), defaultdict(int)
    for row in rows:
        support[row["truth"]] += 1
        predicted[row.get("predicted")] += 1
        if row["truth"] == row.get("predicted"):
            correct[row["truth"]] += 1
    return sum(
        2 * correct[c] / (support[c] + predicted[c]) if support[c] + predicted[c] else 0
        for c in classes
    ) / len(classes)


def assess(
    report: dict[str, Any], champion: str, candidate: str, policy: PromotionPolicy
) -> dict[str, Any]:
    reasons = []
    if report.get("schema_version") != "classifier-comparison-1" or not report.get(
        "human_validated"
    ):
        return {
            "status": "rejected",
            "reasons": ["Validation humaine requise"],
            "policy": policy.model_dump(),
        }
    if report.get("protocol", {}).get("split") != "val":
        return {
            "status": "rejected",
            "reasons": ["La promotion ne peut être optimisée sur test"],
            "policy": policy.model_dump(),
        }
    models = {r["model"]["model_id"]: r for r in report["models"]}
    if champion not in models or candidate not in models or champion == candidate:
        raise ReviewError("Comparaison sans champion et candidat distincts", 422)
    baseline, challenger = models[champion], models[candidate]
    base_rows, new_rows = baseline["predictions"], challenger["predictions"]
    if [(r["crop_id"], r["truth"], r["video_id"]) for r in base_rows] != [
        (r["crop_id"], r["truth"], r["video_id"]) for r in new_rows
    ]:
        raise ReviewError("Prédictions non appariées", 422)
    gain = challenger["metrics"]["macro_f1"] - baseline["metrics"]["macro_f1"]
    if gain <= policy.min_macro_f1_gain:
        reasons.append("Gain de macro-F1 insuffisant")
    if challenger["coverage"] < baseline["coverage"] - policy.max_coverage_drop:
        reasons.append("Régression de couverture")
    latency, reference = challenger["mean_inference_ms"], baseline["mean_inference_ms"]
    if (
        latency is None
        or reference is None
        or latency > max(reference, 1e-6) * policy.max_latency_ratio
    ):
        reasons.append("Latence absente ou trop élevée")
    if challenger["failure_rate"] > baseline["failure_rate"] or challenger.get("error"):
        reasons.append("Régression du taux d'échec")
    for name, metric in baseline["metrics"]["per_class"].items():
        if (
            challenger["metrics"]["per_class"][name]["recall"]
            < metric["recall"] - policy.max_recall_drop
        ):
            reasons.append(f"Régression du rappel : {name}")
    if reasons:
        return {
            "status": "rejected",
            "reasons": reasons,
            "gain": gain,
            "policy": policy.model_dump(),
        }
    names = [row["name"] for row in report["classes"]["classes"]]
    actual_support = {
        name: len({row["video_id"] for row in base_rows if row["truth"] == name}) for name in names
    }
    insufficient = len(base_rows) < policy.min_samples or any(
        min(actual_support[name], report["video_support"].get(name, 0))
        < policy.min_videos_per_class
        for name in names
    )
    if insufficient:
        return {
            "status": "manual_required",
            "reasons": ["Nombre d'exemples ou de vidéos insuffisant"],
            "gain": gain,
            "policy": policy.model_dump(),
        }
    by_video: dict[str, list[int]] = defaultdict(list)
    for i, row in enumerate(base_rows):
        by_video[row["video_id"]].append(i)
    video_ids = sorted(by_video)
    rng, differences = random.Random(policy.seed), []
    for _ in range(policy.bootstrap_samples):
        indices = [i for video in rng.choices(video_ids, k=len(video_ids)) for i in by_video[video]]
        differences.append(
            macro_f1([new_rows[i] for i in indices], names)
            - macro_f1([base_rows[i] for i in indices], names)
        )
    differences.sort()
    lower = differences[int(0.025 * (len(differences) - 1))]
    return {
        "status": "approved" if lower > 0 else "manual_required",
        "reasons": [] if lower > 0 else ["Gain non établi par bootstrap de vidéos"],
        "gain": gain,
        "bootstrap_lower_95": lower,
        "policy": policy.model_dump(),
    }


def promote(
    candidate: str, comparison_id: str, actor: str, *, manual_reason: str = ""
) -> dict[str, Any]:
    # Évaluation hors transaction ; revalidation du champion et des empreintes au commit.
    with transaction() as connection:
        champion = connection.execute("SELECT * FROM console_models WHERE active").fetchone()
        comparison = connection.execute(
            "SELECT * FROM classifier_comparisons WHERE id=%s", (comparison_id,)
        ).fetchone()
        target = connection.execute(
            "SELECT * FROM console_models WHERE id=%s", (candidate,)
        ).fetchone()
    if not champion or not comparison or not target:
        raise ReviewError("Champion, candidat ou comparaison absent", 404)
    report = comparison["report"]
    digest = hashlib.sha256(
        json.dumps(
            report, sort_keys=True, separators=(",", ":"), ensure_ascii=False, allow_nan=False
        ).encode()
    ).hexdigest()
    if digest != comparison["report_sha256"]:
        raise ReviewError("Rapport de comparaison corrompu")
    if report.get("classes") != champion["metadata"].get("classes") or report.get(
        "classes"
    ) != target["metadata"].get("classes"):
        raise ReviewError("Référentiels de comparaison incompatibles")
    if target["status"] == "archived":
        raise ReviewError("Modèle archivé")
    decision = assess(report, str(champion["id"]), candidate, PromotionPolicy())
    for row in (champion, target):
        evaluated = next(
            (m for m in report["models"] if m["model"]["model_id"] == str(row["id"])), None
        )
        if not evaluated or evaluated["checkpoint_sha256"] != row["sha256"]:
            raise ReviewError("Le checkpoint évalué ne correspond plus au registre")
    accepted = (
        decision["status"] == "approved"
        or decision["status"] == "manual_required"
        and bool(manual_reason.strip())
    )
    with transaction(write=True) as connection:
        current = connection.execute("SELECT id FROM console_models WHERE active").fetchone()
        if not current or current["id"] != champion["id"]:
            raise ReviewError("Le champion a changé depuis la comparaison")
        if accepted:
            connection.execute(
                "UPDATE console_models SET active=false,status='validated' WHERE active"
            )
            connection.execute(
                "UPDATE console_models SET active=true,status='active' WHERE id=%s", (candidate,)
            )
        connection.execute(
            """INSERT INTO model_promotions
            (id,model_id,previous_model_id,comparison_id,action,actor,justification)
            VALUES(%s,%s,%s,%s,%s,%s,%s)""",
            (
                str(uuid4()),
                candidate,
                champion["id"],
                comparison_id,
                "promotion" if accepted else "rejected",
                actor,
                jsonb({**decision, "manual_reason": manual_reason}),
            ),
        )
    return {**decision, "activated": accepted, "model_id": candidate}


def rollback(identifier: str, actor: str, reason: str) -> dict[str, Any]:
    if not reason.strip():
        raise ReviewError("Justification du rollback requise", 422)
    with transaction(write=True) as connection:
        previous = connection.execute("SELECT id FROM console_models WHERE active").fetchone()
        known = connection.execute(
            """SELECT 1 FROM model_promotions WHERE
          (model_id=%s OR previous_model_id=%s)
          AND action IN ('bootstrap','promotion','rollback')""",
            (identifier, identifier),
        ).fetchone()
        if not known:
            raise ReviewError("Seul un ancien champion peut être restauré")
        connection.execute("UPDATE console_models SET active=false,status='validated' WHERE active")
        connection.execute(
            "UPDATE console_models SET active=true,status='active' WHERE id=%s", (identifier,)
        )
        connection.execute(
            """INSERT INTO model_promotions
          (id,model_id,previous_model_id,action,actor,justification)
          VALUES(%s,%s,%s,'rollback',%s,%s)""",
            (
                str(uuid4()),
                identifier,
                previous["id"] if previous else None,
                actor,
                jsonb({"reason": reason}),
            ),
        )
    return {"model_id": identifier, "active": True}
