from collections.abc import Sequence
from typing import TYPE_CHECKING

from PIL import ImageDraw
from PIL.Image import Image

from ..schemas import Detection
from ..tracking.base import TrackedObservation

if TYPE_CHECKING:
    from numpy.typing import NDArray


def draw_detections(image: Image, detections: Sequence[Detection]) -> Image:
    output = image.convert("RGB").copy()
    draw = ImageDraw.Draw(output)
    width, height = image.size
    for detection in detections:
        box = detection.box
        bounds = (box.x * width, box.y * height, (box.x + box.w) * width, (box.y + box.h) * height)
        draw.rectangle(bounds, outline="lime", width=3)
        draw.text(
            (bounds[0], max(0, bounds[1] - 16)), f"Animal {detection.confidence:.2f}", fill="lime"
        )
    return output


def draw_tracks(frame: "NDArray", observations: Sequence[TrackedObservation]) -> None:
    import cv2

    height, width = frame.shape[:2]
    for item in observations:
        box, prediction = item.observation.detection.box, item.observation.prediction
        left, top = int(box.x * width), int(box.y * height)
        right, bottom = int((box.x + box.w) * width), int((box.y + box.h) * height)
        color = (0, 210, 0) if prediction.label is not None else (0, 180, 255)
        cv2.rectangle(frame, (left, top), (right, bottom), color, 2)
        label = prediction.label or "incertain"
        cv2.putText(
            frame,
            f"#{item.track_id} {label} {max(prediction.probabilities):.2f}",
            (left, max(18, top - 7)),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.55,
            color,
            2,
        )
