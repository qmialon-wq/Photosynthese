import { shallowRef } from "vue";
export const pendingAdminAction = shallowRef<{
  title: string;
  description: string;
  destructive: boolean;
  finish: (confirmed: boolean) => void;
} | null>(null);
export function closeAdminConfirmation() {
  pendingAdminAction.value?.finish(false);
}
export function confirmAdminAction(
  path: string,
  method: string,
): Promise<boolean> {
  closeAdminConfirmation();
  const destructive =
    method === "DELETE" || path.endsWith("/remove") || path.endsWith("/role");
  let description =
    "Cette action modifie les données enregistrées. Le serveur vérifiera vos droits.";
  if (path.includes("/training"))
    description =
      "Démarrer un entraînement réel avec les paramètres saisis ? Cette action utilise le worker et peut mobiliser le GPU.";
  else if (path.endsWith("/evaluate"))
    description =
      "Lancer une évaluation réelle du modèle et du dataset sélectionnés ? Cette action utilise la file du worker.";
  else if (path.endsWith("/analyze"))
    description =
      "Démarrer l’analyse réelle de cette vidéo avec les paramètres saisis ? Cette action utilise le worker de vision.";
  else if (path.endsWith("/activate"))
    description =
      "Activer ce modèle pour les prochaines analyses ? Les analyses déjà lancées conservent leur configuration.";
  else if (path === "/console/uploads")
    description =
      "Transférer et indexer ce fichier vidéo sur le serveur ? Aucun entraînement ne sera démarré automatiquement.";
  else if (path === "/documents/collect")
    description =
      "Lancer une récupération documentaire réelle pour les espèces choisies ? Les services existants téléchargeront les textes accessibles.";
  else if (
    path === "/documents/upload" ||
    path.startsWith("/documents/upload?")
  )
    description =
      "Envoyer ce document au serveur avec la confirmation des droits fournie dans le formulaire ?";
  else if (path === "/documents/remove")
    description =
      "Retirer les documents sélectionnés du corpus de cette espèce ?";
  else if (path.startsWith("/admin/users"))
    description =
      "Confirmer cette modification réelle de compte ? Les protections existantes et la vérification des rôles restent appliquées par le serveur.";
  return new Promise((resolve) => {
    const action = {
      title: destructive
        ? "Confirmer la modification"
        : "Confirmer l’action réelle",
      description,
      destructive,
      finish: (confirmed: boolean) => {
        if (pendingAdminAction.value === action)
          pendingAdminAction.value = null;
        resolve(confirmed);
      },
    };
    pendingAdminAction.value = action;
  });
}
