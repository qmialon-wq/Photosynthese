from typing import Literal

from pydantic import Field, field_validator

from shared.documents.schemas import Body

LAND_TYPES = {
    "woodland": "Bois",
    "pasture": "Pâturage",
    "fallow": "Friche",
    "buildable": "Terrain constructible",
    "artificial": "Terrain artificialisé",
}
PROJECT_TYPES = {
    "housing": "Habitation",
    "crops": "Culture",
    "livestock": "Élevage",
    "park": "Parc ou jardin",
    "other": "Autre activité",
}


INTERVENTIONS = {
    "earthworks": "Terrassement",
    "vegetation_removal": "Suppression de végétation",
    "fencing": "Clôture",
    "outdoor_lighting": "Éclairage extérieur",
    "soil_sealing": "Imperméabilisation",
}
Intervention = Literal[
    "earthworks", "vegetation_removal", "fencing", "outdoor_lighting", "soil_sealing"
]


class Profile(Body):
    area_m2: float = Field(gt=0, le=1_000_000_000)
    land_type: Literal["woodland", "pasture", "fallow", "buildable", "artificial"]
    project_type: Literal["housing", "crops", "livestock", "park", "other"]
    locality: str = Field(default="", max_length=200)
    details: str = Field(default="", max_length=1000)
    interventions: list[Intervention] = Field(default_factory=list, max_length=5)
    expected_revision: int = Field(default=0, ge=0)

    @field_validator("interventions")
    @classmethod
    def unique_interventions(cls, value: list[Intervention]) -> list[Intervention]:
        return list(dict.fromkeys(value))

    def persisted(self, previous: dict | None = None) -> dict:
        data = self.model_dump(exclude={"expected_revision", "interventions"})
        if "interventions" in self.model_fields_set:
            data["interventions"] = self.interventions
        elif previous is not None and "interventions" in previous:
            data["interventions"] = previous["interventions"]
        return data


class ProfileDraft(Profile):
    """Persist unfinished client forms; scientific generation still requires Profile."""

    area_m2: float | None = Field(default=None, gt=0, le=1_000_000_000)
    land_type: Literal["", "woodland", "pasture", "fallow", "buildable", "artificial"] = ""
    project_type: Literal["", "housing", "crops", "livestock", "park", "other"] = ""


class InterventionsUpdate(Body):
    interventions: list[Intervention] = Field(max_length=5)
    expected_revision: int = Field(ge=0)

    def persisted(self, previous: dict | None = None) -> dict:
        return {**(previous or {}), "interventions": list(dict.fromkeys(self.interventions))}


class CorpusCreate(Body):
    video_ids: list[str] = Field(min_length=1, max_length=1000)


class CorpusRequest(Body):
    profile_revision: int = Field(gt=0)
