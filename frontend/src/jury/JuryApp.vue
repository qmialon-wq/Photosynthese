<script setup lang="ts">
import { computed, onMounted, ref } from "vue";
import LandingPage from "../pages/LandingPage.vue";
import { applicationUrl } from "../experience/pitch";
const busy = ref(false),
  status = ref("Installation hors ligne à préparer"),
  installed = ref(false),
  demoMissing = ref(false);
const installedRevision = ref("");
const appHref = applicationUrl(
  import.meta.env.VITE_SYMBIOSE_APP_URL ||
    (location.port === "8080"
      ? "/connexion"
      : "http://localhost:8080/connexion"),
);
const installationText = computed(() =>
  installed.value
    ? "Vérifier / actualiser l’installation"
    : "Installer hors ligne",
);
async function readStatus() {
  if (!("caches" in window)) return;
  const response = await caches.match("/jury/offline-manifest.json");
  if (!response) return;
  const manifest = await response.json();
  const cache = await caches.open(`symbiose-jury-${manifest.revision}`);
  for (const file of manifest.files)
    if (!(await cache.match(file.url))) {
      installed.value = false;
      status.value =
        "Installation locale incomplète ; relancez l’installation avant le pitch.";
      return;
    }
  installed.value = true;
  installedRevision.value = manifest.revision;
  demoMissing.value = !manifest.demo.available;
  status.value = `Installation locale prête · ${(manifest.totalBytes / 1024 / 1024).toFixed(1)} Mio${demoMissing.value ? " · vidéo produit à ajouter" : " · vidéo incluse"}`;
}
async function install() {
  if (!navigator.serviceWorker || !window.isSecureContext) {
    status.value =
      "Installation indisponible : servir sur localhost ou HTTPS. Le secours 2D reste accessible.";
    return;
  }
  busy.value = true;
  status.value = "Installation locale des paysages, du récit et des sources…";
  try {
    await readStatus();
    const previousRevision = installedRevision.value;
    const registration = await navigator.serviceWorker.register("/jury/sw.js", {
      scope: "/jury/",
      updateViaCache: "none",
    });
    const worker =
      registration.installing || registration.waiting || registration.active;
    if (!worker) throw new Error("Aucun service worker disponible");
    if (worker.state !== "activated")
      await new Promise<void>((resolve, reject) => {
        const timeout = setTimeout(() => {
          worker.removeEventListener("statechange", changed);
          reject(new Error("Installation trop longue ou stockage insuffisant"));
        }, 60000);
        function changed() {
          if (worker!.state === "activated" || worker!.state === "redundant") {
            clearTimeout(timeout);
            worker!.removeEventListener("statechange", changed);
            worker!.state === "activated"
              ? resolve()
              : reject(
                  new Error(
                    "Un fichier manque ou le stockage local est insuffisant",
                  ),
                );
          }
        }
        worker.addEventListener("statechange", changed);
        changed();
      });
    await readStatus();
    if (!installed.value)
      throw new Error("L’installation locale n’a pas pu être vérifiée");
    if (previousRevision && previousRevision !== installedRevision.value)
      location.reload();
  } catch (error) {
    status.value = `Installation non terminée : ${error instanceof Error ? error.message : String(error)}. Gardez le serveur local actif.`;
  } finally {
    busy.value = false;
  }
}
onMounted(() => {
  void readStatus().catch(() => {
    status.value = "Stockage local indisponible ; utiliser le serveur local.";
  });
});
</script>
<template>
  <a href="#main-content" class="jury-skip">Aller au récit</a>
  <LandingPage jury :application-href="appHref" />
  <details class="jury-installation">
    <summary>
      Préparation du jury <span>{{ installed ? "●" : "○" }}</span>
    </summary>
    <p role="status">{{ status }}</p>
    <p>
      Après installation, cette adresse fonctionne sans backend ni Internet.
      Conservez ce profil de navigateur et n’effacez pas ses données avant le
      pitch.
    </p>
    <button :disabled="busy" @click="install">
      {{ busy ? "Installation en cours…" : installationText }}
    </button>
    <p v-if="demoMissing">
      Le fichier de démonstration de 90 s est absent de ce build. Une capture le
      remplace ; aucun parcours produit complet n’est revendiqué.
    </p>
    <a href="?render=2d">Ouvrir le secours sans WebGL</a>
  </details>
</template>
