from typing import Any


def build_transform(
    image_size: int, *, training: bool = False, profile: dict[str, Any] | None = None
) -> Any:
    """Import torchvision différé ; aucun poids téléchargé par les transformations."""
    from torchvision import transforms

    if profile is not None:
        if profile.get("version") != "timm-local-imagenet-v1":
            raise ValueError("Version de prétraitement inconnue")
        interpolation = {
            "bicubic": transforms.InterpolationMode.BICUBIC,
            "bilinear": transforms.InterpolationMode.BILINEAR,
        }.get(profile["interpolation"])
        if (
            interpolation is None
            or len(profile["mean"]) != 3
            or len(profile["std"]) != 3
            or min(profile["std"]) <= 0
        ):
            raise ValueError("Profil de normalisation invalide")
        augmentation = (
            [
                transforms.RandomHorizontalFlip(),
                transforms.RandomAffine(5, translate=(0.02, 0.02)),
                transforms.ColorJitter(0.15, 0.15, 0.1),
                transforms.RandomApply([transforms.GaussianBlur(3)], p=0.1),
            ]
            if training
            else []
        )
        return transforms.Compose(
            [
                transforms.Resize((image_size, image_size), interpolation=interpolation),
                *augmentation,
                transforms.ToTensor(),
                transforms.Normalize(profile["mean"], profile["std"]),
            ]
        )

    operations = (
        [
            transforms.RandomResizedCrop(image_size, scale=(0.72, 1.0)),
            transforms.RandomHorizontalFlip(),
            transforms.ColorJitter(0.2, 0.2, 0.2, 0.05),
            transforms.RandomApply([transforms.GaussianBlur(3)], p=0.12),
        ]
        if training
        else [transforms.Resize((image_size, image_size))]
    )
    return transforms.Compose(
        [
            *operations,
            transforms.ToTensor(),
            transforms.Normalize([0.485, 0.456, 0.406], [0.229, 0.224, 0.225]),
        ]
    )
