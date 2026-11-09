/** Zone réellement occupée par un média en mode contain, en coordonnées normalisées. */
export function containedMedia(
  frameWidth: number,
  frameHeight: number,
  mediaWidth: number,
  mediaHeight: number,
) {
  if (
    ![frameWidth, frameHeight, mediaWidth, mediaHeight].every(
      (value) => Number.isFinite(value) && value > 0,
    )
  )
    return { x: 0, y: 0, width: 1, height: 1 };
  const frameRatio = frameWidth / frameHeight,
    mediaRatio = mediaWidth / mediaHeight;
  if (mediaRatio < frameRatio) {
    const width = mediaRatio / frameRatio;
    return { x: (1 - width) / 2, y: 0, width, height: 1 };
  }
  const height = frameRatio / mediaRatio;
  return { x: 0, y: (1 - height) / 2, width: 1, height };
}
export function playbackTime(seconds: number | null) {
  if (seconds == null) return "?";
  const value = Number.isFinite(seconds) ? Math.max(0, Math.floor(seconds)) : 0;
  return `${Math.floor(value / 60)}:${String(value % 60).padStart(2, "0")}`;
}
