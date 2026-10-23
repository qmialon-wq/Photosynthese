from typing import Literal

from pydantic import Field

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


class Profile(Body):
    area_m2: float = Field(gt=0, le=1_000_000_000)
    land_type: Literal["woodland", "pasture", "fallow", "buildable", "artificial"]
    project_type: Literal["housing", "crops", "livestock", "park", "other"]
    locality: str = Field(default="", max_length=200)
    details: str = Field(default="", max_length=1000)
    expected_revision: int = Field(default=0, ge=0)
