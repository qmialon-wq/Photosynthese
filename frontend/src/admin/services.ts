import { watch } from "vue";
import type { Router } from "vue-router";
import { auth } from "../auth-state";
import { ApiError, configureApi } from "../api";
import type { DataModeStore } from "../data/data-mode";
import { AdminDemoProvider } from "./demo-provider";
import { closeAdminConfirmation, confirmAdminAction } from "./confirmation";

export function installAdminServices(store: DataModeStore, router: Router) {
  const demo = new AdminDemoProvider(store);
  let epoch = 0;
  const uploads = new Set<string>();
  watch(
    [() => store.mode.value, () => auth.user?.id, () => auth.user?.role],
    () => {
      epoch++;
      uploads.clear();
      demo.reset();
      closeAdminConfirmation();
    },
    { flush: "sync" },
  );
  configureApi(
    async (path, options) => {
      if (path.startsWith("/auth/")) return { handled: false };
      const captured = epoch,
        account = auth.user?.id;
      const current = () => captured === epoch && account === auth.user?.id;
      if (store.isDemo.value) {
        if (
          !router.currentRoute.value.path.startsWith("/admin") ||
          auth.user?.role !== "admin"
        )
          throw new ApiError(
            "Ce service métier est réservé à l’espace administrateur authentifié.",
            403,
          );
        const value = await demo.request(path, options);
        if (!current()) throw new DOMException("Source changée", "AbortError");
        return { handled: true, value };
      }
      if (!router.currentRoute.value.path.startsWith("/admin"))
        return { handled: false, current };
      if (auth.user?.role !== "admin")
        throw new ApiError("Accès administrateur requis.", 403);
      const method = (options.method || "GET").toUpperCase();
      const upload = path.match(/^\/console\/uploads\/([^/]+)/)?.[1];
      // Cet endpoint POST consulte le suivi des imports ; il ne crée aucun travail.
      const readsImportStatus =
        path === "/parcels/import-status" && method === "POST";
      if (
        !["GET", "HEAD"].includes(method) &&
        !readsImportStatus &&
        !(upload && uploads.has(upload))
      ) {
        const allowed = await confirmAdminAction(path, method);
        if (!allowed || !current())
          throw new ApiError(
            "Action annulée. Aucune requête de modification n’a été envoyée.",
            409,
          );
      }
      return {
        handled: false,
        current,
        received:
          path === "/console/uploads" && method === "POST"
            ? (value) => {
                const id = (value as { id?: string })?.id;
                if (id) uploads.add(id);
              }
            : undefined,
      };
    },
    (path) =>
      store.isDemo.value &&
      router.currentRoute.value.path.startsWith("/admin") &&
      !path.startsWith("/auth/")
        ? demo.url(path)
        : null,
  );
  return demo;
}
