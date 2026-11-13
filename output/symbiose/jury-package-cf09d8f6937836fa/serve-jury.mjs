import { createServer } from "node:http";
import { createReadStream, existsSync } from "node:fs";
import { stat } from "node:fs/promises";
import path from "node:path";

const root = path.resolve(process.argv[2] || "frontend/dist");
const port = Number(process.argv[3] || 8088);
if (
  !existsSync(path.join(root, "jury/index.html")) ||
  !existsSync(path.join(root, "jury/offline-manifest.json"))
)
  throw new Error("Point this server at a built Symbiose jury package.");
if (!Number.isInteger(port) || port < 1024 || port > 65535)
  throw new Error("Invalid local port");
const types = {
  ".html": "text/html; charset=utf-8",
  ".js": "application/javascript; charset=utf-8",
  ".css": "text/css; charset=utf-8",
  ".json": "application/json; charset=utf-8",
  ".webp": "image/webp",
  ".png": "image/png",
  ".ico": "image/x-icon",
  ".svg": "image/svg+xml",
  ".mp4": "video/mp4",
  ".webm": "video/webm",
  ".vtt": "text/vtt; charset=utf-8",
  ".woff2": "font/woff2",
};
const server = createServer(async (request, response) => {
  if (!["GET", "HEAD"].includes(request.method)) {
    response.writeHead(405);
    response.end();
    return;
  }
  try {
    const pathname = decodeURIComponent(
      new URL(request.url, "http://localhost").pathname,
    );
    let file = path.resolve(root, "." + pathname);
    if (!file.startsWith(root + path.sep) && file !== root) {
      response.writeHead(403);
      response.end();
      return;
    }
    let info = await stat(file);
    if (info.isDirectory()) {
      file = path.join(file, "index.html");
      info = await stat(file);
    }
    let start = 0,
      end = info.size - 1,
      status = 200;
    const headers = {
      "Content-Type": types[path.extname(file)] || "application/octet-stream",
      "Accept-Ranges": "bytes",
      "Cache-Control": "no-cache",
      "X-Content-Type-Options": "nosniff",
    };
    if (request.headers.range) {
      const match = /^bytes=(\d*)-(\d*)$/.exec(request.headers.range);
      if (!match || (!match[1] && !match[2])) throw new RangeError();
      start = match[1]
        ? Number(match[1])
        : Math.max(0, info.size - Number(match[2]));
      end = match[1] && match[2] ? Math.min(Number(match[2]), end) : end;
      if (start > end || start >= info.size) {
        response.writeHead(416, { "Content-Range": `bytes */${info.size}` });
        response.end();
        return;
      }
      status = 206;
      headers["Content-Range"] = `bytes ${start}-${end}/${info.size}`;
    }
    headers["Content-Length"] = String(end - start + 1);
    if (info.size === 0) {
      response.writeHead(200, headers);
      response.end();
      return;
    }
    response.writeHead(status, headers);
    if (request.method === "HEAD") response.end();
    else
      createReadStream(file, { start, end })
        .on("error", () => response.destroy())
        .pipe(response);
  } catch (error) {
    response.writeHead(error instanceof RangeError ? 416 : 404);
    response.end("Local file unavailable");
  }
});
server.listen(port, "127.0.0.1", () =>
  console.log(
    `Symbiose jury: http://localhost:${port}/jury/\nLocal files only. Ctrl+C stops the server.`,
  ),
);
