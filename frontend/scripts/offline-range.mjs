/** Single-byte-range responses for browser seeking in an installed local video. */
export async function rangeResponse(request, response) {
  const range = request.headers.get("range");
  if (!range) return response;
  const bytes = await response.arrayBuffer(),
    size = bytes.byteLength;
  const match = /^bytes=(\d*)-(\d*)$/.exec(range);
  const invalid = () =>
    new Response(null, {
      status: 416,
      headers: { "Content-Range": `bytes */${size}` },
    });
  if (!match || (!match[1] && !match[2])) return invalid();
  const start = match[1]
    ? Number(match[1])
    : Math.max(0, size - Number(match[2]));
  const end =
    match[1] && match[2] ? Math.min(Number(match[2]), size - 1) : size - 1;
  if (
    start >= size ||
    start > end ||
    !Number.isSafeInteger(start) ||
    !Number.isSafeInteger(end)
  )
    return invalid();
  const headers = new Headers(response.headers);
  headers.set("Content-Range", `bytes ${start}-${end}/${size}`);
  headers.set("Content-Length", String(end - start + 1));
  headers.set("Accept-Ranges", "bytes");
  return new Response(bytes.slice(start, end + 1), { status: 206, headers });
}
