import { watch } from "vue";
import type { Router } from "vue-router";
import { auth } from "../auth-state";
import { ApiError, configureApi } from "../api";
import type { DataModeStore } from "../data/data-mode";
import { closeAdminConfirmation, confirmAdminAction } from "./confirmation";

export function installAdminServices(store: DataModeStore, router: Router) {
  let epoch = 0;
  const uploads = new Set<string>();
  watch(
    [() => auth.user?.id, () => auth.user?.role],
    () => {
      epoch++;
      uploads.clear();
      closeAdminConfirmation();
    },
    { flush: "sync" },
  );
  configureApi(async (path, options) => {
    if (path.startsWith("/auth/")) return { handled: false };
    const captured = epoch,
      account = auth.user?.id;
    const current = () => captured === epoch && account === auth.user?.id;
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
  });
}
