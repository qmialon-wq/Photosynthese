class VisionError(Exception):
    """Erreur exploitable par la CLI et par un worker."""


class VideoError(VisionError):
    pass


class ModelError(VisionError):
    pass


class GpuBusyError(ModelError):
    pass


class ManifestError(VisionError):
    pass


class TrainingInterrupted(VisionError):
    """Arrêt demandé ; le dernier checkpoint d'époque reste reprenable."""
