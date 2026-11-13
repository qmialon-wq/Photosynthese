/* Generated for this production build. Scope: /jury/ only. */
const CACHE = "symbiose-jury-ac657de1abda1830";
const FILES = ["/jury/index.html","/favicon.ico","/experience-art/runtime-assets.json","/experience-art/shared/symbiose-logo.png","/experience-media/manifesto-review.webp","/assets/jury-CUo4wTC9.js","/assets/jury-DfVSCK7Z.css","/assets/symbiose-logo-CX_rJBaj.js","/assets/symbiose-logo-BTPSrkyB.png","/assets/LandingPage.vue_vue_type_script_setup_true_lang-BaCr2eoJ.js","/assets/LandingPage-Dx2GMp5i.css","/assets/ExperienceCanvas-Dar4CtSY.js","/assets/CameraController-7ikOnsvg.js","/assets/DebugControls-BjOPpx0g.js","/assets/PitchSources-DQvGmtX3.js","/experience-models/inventory.json","/experience-models/buse.glb","/experience-models/chevreuil.glb","/experience-models/sanglier.glb","/experience-models/pigeon.glb","/experience-models/poisson.glb","/experience-models/fern_02.glb","/experience-models/rock_moss_set_01.glb","/experience-models/tree_stump_01.glb","/experience-models/forest_ground_04-Diffuse.jpg","/experience-models/forest_ground_04-nor_gl.jpg","/experience-models/forest_ground_04-Rough.jpg","/experience-models/bark_brown_01-Diffuse.jpg","/experience-models/bark_brown_01-nor_gl.jpg","/experience-models/bark_brown_01-Rough.jpg","/experience-art/forest/foreground-runtime.webp","/experience-art/forest/primary-runtime.webp","/experience-art/sky/foreground-runtime.webp","/experience-art/sky/primary-runtime.webp","/experience-art/rivers/foreground-runtime.webp","/experience-art/rivers/primary-runtime.webp","/experience-art/underwater/foreground-runtime.webp","/experience-art/underwater/primary-runtime.webp","/experience-art/wetland/foreground-runtime.webp","/experience-art/wetland/primary-runtime.webp","/experience-art/meadow/foreground-runtime.webp","/experience-art/meadow/primary-runtime.webp","/experience-art/coast/foreground-runtime.webp","/experience-art/coast/primary-runtime.webp","/experience-art/night-forest/foreground-runtime.webp","/experience-art/night-forest/primary-runtime.webp","/jury/offline-manifest.json"];
const ALLOWED = new Set(FILES);
async function rangeResponse(request, response) {
  const range = request.headers.get("range");
  if (!range) return response;
  const bytes = await response.arrayBuffer(), size = bytes.byteLength;
  const match = /^bytes=(\d*)-(\d*)$/.exec(range);
  const invalid = () => new Response(null, {
    status: 416,
    headers: { "Content-Range": `bytes */${size}` }
  });
  if (!match || !match[1] && !match[2]) return invalid();
  const start = match[1] ? Number(match[1]) : Math.max(0, size - Number(match[2]));
  const end = match[1] && match[2] ? Math.min(Number(match[2]), size - 1) : size - 1;
  if (start >= size || start > end || !Number.isSafeInteger(start) || !Number.isSafeInteger(end))
    return invalid();
  const headers = new Headers(response.headers);
  headers.set("Content-Range", `bytes ${start}-${end}/${size}`);
  headers.set("Content-Length", String(end - start + 1));
  headers.set("Accept-Ranges", "bytes");
  return new Response(bytes.slice(start, end + 1), { status: 206, headers });
}
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
