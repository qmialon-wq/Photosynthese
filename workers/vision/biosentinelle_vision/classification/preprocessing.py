from typing import Any


def build_transform(image_size: int, *, training: bool = False) -> Any:
    """Import torchvision différé ; aucun poids téléchargé par les transformations."""
    from torchvision import transforms

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
