import {
  computed,
  inject,
  reactive,
  readonly,
  ref,
  watch,
  type InjectionKey,
} from "vue";
import { auth } from "../auth-state";
import { summarize } from "./summary";
import { RealDataProvider } from "./real-provider";
import {
  emptySnapshot,
  resource,
  type Collections,
  type DataProvider,
  type Snapshot,
} from "./contracts";

export const DATA_MODE_KEY = "symbiose:data-mode:v1";
function browserStorage() {
  try {
    return globalThis.localStorage;
  } catch {
    return undefined;
  }
}
export function createDataModeStore(
  storage: Pick<Storage, "getItem" | "setItem"> | undefined = browserStorage(),
  provider: DataProvider = new RealDataProvider(),
) {
  // Migration des navigateurs ayant conservé l'ancien choix de démonstration.
  try {
    storage?.setItem(DATA_MODE_KEY, "real");
  } catch {
    /* Navigation privée : le mode reste utilisable sans persistance. */
  }
  const active = ref(false),
    revision = ref(0);
  const data = reactive<Snapshot>(emptySnapshot());
  let controller: AbortController | undefined,
    reportController: AbortController | undefined,
    generation = 0;
  const sourceId = computed(
    () => `${provider.id}:${auth.user?.id || "anonymous"}`,
  );
  function cancel() {
    controller?.abort();
    reportController?.abort();
    generation++;
  }
  async function load(resetView: boolean) {
    cancel();
    Object.assign(data, emptySnapshot());
    if (resetView) revision.value++;
    if (!active.value || !auth.user) return;
    const current = new AbortController();
    controller = current;
    const run = generation;
    await provider.load(current.signal, (key, value) => {
      if (generation === run && !current.signal.aborted && active.value)
        Object.assign(data, { [key]: value });
    });
  }
  const refresh = () => load(true);
  const refreshInPlace = () => load(false);
  function setActive(value: boolean) {
    if (active.value === value) return;
    active.value = value;
    if (value) void refresh();
    else {
      cancel();
      Object.assign(data, emptySnapshot());
    }
  }
  // Un changement de compte invalide immédiatement les données du compte précédent.
  const stopAuthWatch = watch(
    () => `${auth.user?.id || ""}:${auth.user?.role || ""}`,
    (id, previous) => {
      if (active.value && id !== previous) void refresh();
    },
    { flush: "sync" },
  );
  async function report(id: string) {
    reportController?.abort();
    const current = new AbortController();
    reportController = current;
    const run = generation;
    const loader = provider.report;
    if (!loader)
      return resource<import("./contracts").Detection>([], "unconnected");
    try {
      const result = await loader.call(provider, id, current.signal);
      return generation === run && !current.signal.aborted
        ? resource(result)
        : null;
    } catch {
      return generation === run && !current.signal.aborted
        ? resource<import("./contracts").Detection>(
            [],
            "error",
            "Impossible de consulter le rapport d’analyse.",
          )
        : null;
    }
  }
  const capabilities = computed(() => ({
    write: !!auth.user,
    readOnly: !auth.user,
  }));
  const summary = computed(() => summarize(data));
  function dispose() {
    cancel();
    stopAuthWatch();
  }
  return {
    sourceId,
    revision: readonly(revision),
    data: readonly(data),
    capabilities,
    summary,
    setActive,
    refresh,
    refreshInPlace,
    report,
    dispose,
  };
}
export type DataModeStore = ReturnType<typeof createDataModeStore>;
export const dataModeKey: InjectionKey<DataModeStore> =
  Symbol("SymbioseDataMode");
export function useDataMode() {
  const store = inject(dataModeKey);
  if (!store) throw new Error("Contexte de données Symbiose absent");
  return store;
}
export function useCollection<K extends keyof Collections>(key: K) {
  const store = useDataMode();
  const items = computed(() => store.data[key].data as Collections[K][]);
  const state = computed(() => store.data[key]);
  return { store, items, state };
}
