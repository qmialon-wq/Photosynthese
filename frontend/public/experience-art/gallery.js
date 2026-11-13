// The review runs in its own document. It never installs listeners in the Vue application.
const byId = (id) => document.getElementById(id);
const image = byId("scene-image");
const roleNames = {
  primary: "Plan principal",
  foreground: "Premier plan détouré",
  background: "Fond reconstruit",
  depth: "Profondeur calibrée",
  atmosphere: "Passe atmosphérique",
  geometry: "Géométrie et occlusions",
  motion: "Séquence pré-rendue",
  "product-video": "Vidéo réelle du produit · 90 s",
};
let manifest,
  index = 0,
  representation = "primary";
const text = (id, value) => {
  byId(id).textContent = value;
};
const node = (tag, value, className) => {
  const element = document.createElement(tag);
  if (value) element.textContent = value;
  if (className) element.className = className;
  return element;
};
const clock = (seconds) =>
  `${Math.floor(seconds / 60)}:${String(seconds % 60).padStart(2, "0")}`;
const isPresent = (resource) =>
  resource.status === "present-review-required" && Boolean(resource.path);

function render() {
  const scene = manifest.scenes[index];
  const resource = scene.resources.find((item) => item.role === representation);
  text(
    "scene-status",
    `${String(scene.index).padStart(2, "0")} / 08 · ${scene.name} · revue artistique requise`,
  );
  text("scene-index", String(scene.index).padStart(2, "0"));
  text("scene-title", scene.name);
  text(
    "scene-time",
    `${clock(scene.time.start)} — ${clock(scene.time.end)} · ${scene.time.duration} s prévues`,
  );
  text("disclosure", scene.disclosure);
  text("capability", scene.capability ?? "");
  byId("capability").hidden = !scene.capability;
  byId("viewer").dataset.representation = representation;
  byId("image-failure").hidden = true;
  image.hidden = false;
  if (resource && isPresent(resource)) {
    image.src = `./${resource.path}`;
    image.alt = `${scene.name} — ${representation === "primary" ? scene.planes.main : scene.planes.foreground} ${scene.disclosure}`;
    byId("image-link").href = `./${resource.path}`;
    byId("image-link").download =
      `${scene.id}-generated-${representation}-v1.png`;
  } else {
    image.removeAttribute("src");
    image.hidden = true;
    byId("image-failure").hidden = false;
  }
  byId("show-primary").setAttribute(
    "aria-pressed",
    String(representation === "primary"),
  );
  byId("show-foreground").setAttribute(
    "aria-pressed",
    String(representation === "foreground"),
  );
  byId("show-foreground").disabled = !scene.resources.some(
    (item) => item.role === "foreground" && isPresent(item),
  );
  byId("previous").disabled = index === 0;
  byId("next").disabled = index === manifest.scenes.length - 1;
  document
    .querySelectorAll("#scene-rail button")
    .forEach((button, i) =>
      button.setAttribute("aria-pressed", String(i === index)),
    );
  const rows = [
    ["Plan principal", scene.planes.main],
    ["Premier plan", scene.planes.foreground],
    ["Arrière-plan", scene.planes.background],
    ["Profondeur", scene.planes.depth],
    ["Atmosphère", scene.atmosphere],
    ["Éléments animés", scene.animated],
    ["Caméra prévue", scene.camera.trajectory],
    ["Entrée", scene.camera.entry],
    ["Sortie", scene.camera.exit],
    ["Ressources de raccord", scene.transitionNeeds],
  ];
  byId("storyboard").replaceChildren(
    ...rows.map(([title, value]) => {
      const row = node("div", null, "story-row");
      row.append(node("dt", title), node("dd", value));
      return row;
    }),
  );
  byId("palette").replaceChildren(
    ...scene.palette.map((color) => {
      const swatch = node("span", color, "swatch"),
        chip = node("i");
      chip.style.backgroundColor = color;
      chip.setAttribute("aria-hidden", "true");
      swatch.prepend(chip);
      return swatch;
    }),
  );
  byId("inventory").replaceChildren(
    ...scene.resources.map((item) => {
      const li = node("li"),
        heading = node("div", null, "resource-heading");
      li.dataset.status = item.status;
      heading.append(
        node("strong", roleNames[item.role]),
        node(
          "span",
          isPresent(item) ? "Produit · à revoir" : "Absent · à produire",
        ),
      );
      li.append(heading, node("p", item.description));
      if (isPresent(item)) {
        const metadata = node(
          "p",
          `${item.dimensions.width} × ${item.dimensions.height} · ${(item.bytes / 1048576).toFixed(2)} Mio${item.alpha?.min === 0 ? " · alpha mesuré" : ""}`,
        );
        const link = node("a", "Ouvrir la ressource ↗");
        link.href = `./${item.path}`;
        li.append(metadata, link);
      } else li.append(node("p", `Emplacement attendu : ${item.expectedPath}`));
      return li;
    }),
  );
  text("transition-needs", `Raccord non produit. ${scene.transitionNeeds}`);
  byId("scene-manifest-link").href = `./${scene.id}/manifest.json`;
  byId("prompt-link").href =
    `./${scene.id}/prompts/${representation === "primary" ? "primary" : "foreground"}.txt`;
  byId("missing-link").href = `./${scene.id}/prompts/missing.json`;
}
function select(next) {
  index = Math.max(0, Math.min(manifest.scenes.length - 1, next));
  representation = "primary";
  history.replaceState(null, "", `#${manifest.scenes[index].id}`);
  render();
}

async function load() {
  byId("loading").hidden = false;
  byId("load-error").hidden = true;
  try {
    const response = await fetch("./manifest.json");
    if (!response.ok) throw new Error("Manifest unavailable");
    manifest = await response.json();
    index = Math.max(
      0,
      manifest.scenes.findIndex((scene) => scene.id === location.hash.slice(1)),
    );
    byId("scene-rail").replaceChildren(
      ...manifest.scenes.map((scene, i) => {
        const button = node("button"),
          thumb = node("img"),
          label = node("span", scene.name),
          number = node("small", `0${scene.index}`);
        button.type = "button";
        button.setAttribute("aria-label", `0${scene.index}. ${scene.name}`);
        button.addEventListener("click", () => select(i));
        const primary = scene.resources.find((item) => item.role === "primary");
        thumb.src = `./${primary.path}`;
        thumb.alt = "";
        thumb.loading = "lazy";
        thumb.width = 320;
        thumb.height = 180;
        label.prepend(number);
        button.append(thumb, label);
        return button;
      }),
    );
    byId("contact-sheet").replaceChildren(
      ...manifest.scenes.map((scene) => {
        const figure = node("figure"),
          thumb = node("img"),
          caption = node("figcaption", `0${scene.index} · ${scene.name}`);
        const primary = scene.resources.find((item) => item.role === "primary");
        thumb.src = `./${primary.path}`;
        thumb.alt = scene.planes.main;
        thumb.loading = "lazy";
        thumb.width = 1672;
        thumb.height = 941;
        caption.append(node("small", scene.disclosure));
        figure.append(thumb, caption);
        return figure;
      }),
    );
    const resources = manifest.scenes.flatMap((scene) => scene.resources),
      count = resources.filter(isPresent).length;
    text(
      "asset-count",
      `${count} produits · ${resources.length - count} absents déclarés`,
    );
    byId("review").hidden = false;
    render();
  } catch (error) {
    byId("load-error").hidden = false;
    byId("review").hidden = true;
  } finally {
    byId("loading").hidden = true;
  }
}
byId("show-primary").addEventListener("click", () => {
  representation = "primary";
  render();
});
byId("show-foreground").addEventListener("click", () => {
  representation = "foreground";
  render();
});
byId("previous").addEventListener("click", () => select(index - 1));
byId("next").addEventListener("click", () => select(index + 1));
byId("retry").addEventListener("click", load);
byId("scene-rail").addEventListener("keydown", (event) => {
  if (event.key !== "ArrowLeft" && event.key !== "ArrowRight") return;
  event.preventDefault();
  select(index + (event.key === "ArrowRight" ? 1 : -1));
  byId("scene-rail").children[index].focus();
});
image.addEventListener("error", () => {
  byId("image-failure").hidden = false;
  image.hidden = true;
});
load();
