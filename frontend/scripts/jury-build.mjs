import { readFile, writeFile, stat, readdir } from "node:fs/promises";
import path from "node:path";
import { createHash } from "node:crypto";
import { rangeResponse } from "./offline-range.mjs";

export function juryBuild() {
  let directory,
    configuredMedia = [];
  return {
    name: "symbiose-jury-offline",
    apply: "build",
    configResolved(config) {
      directory = path.resolve(config.root, config.build.outDir);
      configuredMedia = [
        { url: config.env.VITE_SYMBIOSE_DEMO_URL, video: true },
        { url: config.env.VITE_SYMBIOSE_DEMO_CAPTIONS_URL, video: false },
      ].filter((item) => item.url?.trim());
    },
    async closeBundle() {
      const manifest = JSON.parse(
        await readFile(path.join(directory, ".vite/manifest.json"), "utf8"),
      );
      const inventory = JSON.parse(
        await readFile(
          path.join(directory, "experience-art/runtime-assets.json"),
          "utf8",
        ),
      );
      const files = new Set([
        "/jury/index.html",
        "/favicon.ico",
        "/experience-art/runtime-assets.json",
        "/experience-art/shared/symbiose-logo.png",
        inventory.poster.url,
      ]);
      const visited = new Set();
      function collect(id) {
        if (visited.has(id)) return;
        visited.add(id);
        const entry = manifest[id];
        if (!entry) throw new Error(`Missing jury build entry ${id}`);
        files.add("/" + entry.file);
        for (const file of [...(entry.css || []), ...(entry.assets || [])])
          files.add("/" + file);
        for (const dependency of [
          ...(entry.imports || []),
          ...(entry.dynamicImports || []),
        ])
          collect(dependency);
      }
      collect("jury/index.html");
      const spatial = JSON.parse(
        await readFile(
          path.join(directory, "experience-models/inventory.json"),
          "utf8",
        ),
      );
      files.add("/experience-models/inventory.json");
      for (const asset of Object.values(spatial.assets)) files.add(asset.url);
      for (const scene of Object.values(inventory.scenes))
        files.add(scene.primary.url);
      const media = await readdir(path.join(directory, "experience-media"));
      const demos = media
        .filter((name) => /^demo\.(mp4|webm)$/.test(name))
        .map((name) => `/experience-media/${name}`);
      for (const item of configuredMedia) {
        const url = item.url.trim();
        if (!/^\/(?![\/\\])/.test(url) || /[\\?#\s]/.test(url))
          throw new Error("Jury media must be a local absolute URL: " + url);
        const file = path.resolve(directory, "." + decodeURIComponent(url));
        if (!file.startsWith(directory + path.sep))
          throw new Error("Jury media outside build directory");
        await stat(file); // Explicit configuration errors fail the build, never silently break offline mode.
        files.add(url);
        if (item.video && !demos.includes(url)) demos.push(url);
      }
      for (const file of media.filter((name) =>
        /^demo(?:\.fr)?\.vtt$/.test(name),
      ))
        files.add(`/experience-media/${file}`);
      demos.forEach((file) => files.add(file));
      const records = await Promise.all(
        [...files].sort().map(async (url) => {
          const location = path.join(
            directory,
            decodeURIComponent(url.slice(1)),
          );
          const bytes = await readFile(location);
          return {
            url,
            bytes: (await stat(location)).size,
            sha256: createHash("sha256").update(bytes).digest("hex"),
          };
        }),
      );
      const revision = createHash("sha256")
        .update(JSON.stringify(records))
        .digest("hex")
        .slice(0, 16);
      const report = {
        revision,
        entry: "/jury/",
        totalBytes: records.reduce((sum, file) => sum + file.bytes, 0),
        files: records,
        demo: { available: demos.length > 0, files: demos },
      };
      await writeFile(
        path.join(directory, "jury/offline-manifest.json"),
        JSON.stringify(report, null, 2),
      );
      const worker = `/* Generated for this production build. Scope: /jury/ only. */
const CACHE = ${JSON.stringify("symbiose-jury-" + revision)};
const FILES = ${JSON.stringify([...files, "/jury/offline-manifest.json"])};
const ALLOWED = new Set(FILES);
${rangeResponse.toString()}
self.addEventListener('install', event => event.waitUntil((async () => {
  const cache = await caches.open(CACHE);
  try {
    // Bounded concurrency avoids decoding/downloading all images simultaneously.
    for(let i=0;i<FILES.length;i+=4) await Promise.all(FILES.slice(i,i+4).map(async url => {
      const response = await fetch(url,{cache:'reload',credentials:'omit'});
      if(!response.ok) throw new Error('Unavailable local asset: '+url);
      await cache.put(url,response);
    }));
    await self.skipWaiting();
  } catch(error) { await caches.delete(CACHE);throw error; }
})()));
self.addEventListener('activate', event => event.waitUntil((async () => {
  for(const name of await caches.keys()) if(name.startsWith('symbiose-jury-') && name!==CACHE) await caches.delete(name);
  await self.clients.claim();
})()));
self.addEventListener('fetch', event => {
  const url=new URL(event.request.url);
  if(url.origin!==self.location.origin || event.request.method!=='GET')return;
  const navigation=event.request.mode==='navigate' && url.pathname.startsWith('/jury/');
  const key=navigation ? '/jury/index.html' : url.pathname;
  if(!navigation && !ALLOWED.has(key))return;
  event.respondWith((async () => {
    const cached=await (await caches.open(CACHE)).match(key);
    if(cached)return event.request.headers.has('range') ? rangeResponse(event.request,cached) : cached;
    return fetch(event.request);
  })());
});
`;
      await writeFile(path.join(directory, "jury/sw.js"), worker);
      console.log(
        `Jury offline: ${records.length} assets, ${(report.totalBytes / 1024 / 1024).toFixed(2)} MiB; product demo ${report.demo.available ? "present" : "MISSING"}.`,
      );
    },
  };
}
