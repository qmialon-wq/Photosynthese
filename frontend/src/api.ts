import { onBeforeUnmount, onMounted, ref, watch } from "vue";
import { auth, clearSession } from "./auth-state";

export const apiUrl = (path: string): string => `/api${path}`;
const taskLabels: Record<string, string> = {
  analysis: "Analyse vidéo",
  training: "Entraînement du classificateur",
  evaluation: "Évaluation",
  classification_dataset: "Préparation du dataset commun",
  classifiers_compare: "Benchmark des classificateurs",
  import_upload: "Import vidéo",
  import_local: "Indexation vidéo",
  register_model: "Vérification du modèle",
  prepare_review: "Préparation des recadrages",
};
export const taskLabel = (kind: string): string => taskLabels[kind] ?? kind;

export class ApiError extends Error {
  constructor(
    message: string,
    readonly status: number,
  ) {
    super(message);
  }
}

export async function api<T>(
  path: string,
  options: RequestInit = {},
): Promise<T> {
  const headers = new Headers(options.headers);
  if (
    auth.csrf &&
    !["GET", "HEAD"].includes((options.method ?? "GET").toUpperCase())
  )
    headers.set("X-CSRF-Token", auth.csrf);
  if (typeof options.body === "string")
    headers.set("Content-Type", "application/json");
  const response = await fetch(apiUrl(path), {
    ...options,
    credentials: "same-origin",
    headers,
  });
  if (!response.ok) {
    if (response.status === 401 && auth.user) {
      clearSession();
      window.dispatchEvent(new Event("auth-expired"));
    }
    let message = `Erreur HTTP ${response.status}`;
    try {
      const body = await response.json();
      message = Array.isArray(body.detail)
        ? body.detail.map((item: { msg: string }) => item.msg).join(" · ")
        : (body.detail ?? message);
    } catch {
      /* Conserver le code HTTP si le proxy ne renvoie pas de JSON. */
    }
    throw new ApiError(message, response.status);
  }
  return response.status === 204
    ? (undefined as T)
    : ((await response.json()) as T);
}
export const post = <T>(path: string, body: unknown = {}): Promise<T> =>
  api<T>(path, { method: "POST", body: JSON.stringify(body) });
export const message = (error: unknown): string =>
  error instanceof Error ? error.message : String(error);
export const percent = (value?: number | null): string =>
  value == null ? "Non mesuré" : `${(value * 100).toFixed(1)} %`;
export const date = (value: string): string =>
  new Intl.DateTimeFormat("fr-FR", {
    dateStyle: "medium",
    timeStyle: "short",
  }).format(new Date(value));

export function useResource<T>(url: () => string | null, interval = 0) {
  const data = ref<T | null>(null);
  const loading = ref(false);
  const error = ref("");
  let controller: AbortController | null = null;
  let timer: ReturnType<typeof setInterval> | undefined;
  let disposed = false;
  async function refresh(): Promise<void> {
    const path = url();
    if (!path || loading.value) return;
    const current = new AbortController();
    controller = current;
    loading.value = true;
    error.value = "";
    try {
      const result = await api<T>(path, { signal: current.signal });
      if (!disposed && controller === current) data.value = result;
    } catch (reason) {
      if (!current.signal.aborted && !disposed && controller === current)
        error.value = message(reason);
    } finally {
      if (!disposed && controller === current) loading.value = false;
    }
  }
  watch(url, () => {
    controller?.abort();
    loading.value = false;
    data.value = null;
    void refresh();
  });
  onMounted(() => {
    void refresh();
    if (interval)
      timer = setInterval(() => {
        if (!document.hidden) void refresh();
      }, interval);
  });
  onBeforeUnmount(() => {
    disposed = true;
    controller?.abort();
    if (timer) clearInterval(timer);
  });
  return { data, loading, error, refresh };
}
