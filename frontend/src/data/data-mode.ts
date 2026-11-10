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
import { DemoDataProvider, summarize } from "./demo-provider";
import { RealDataProvider } from "./real-provider";
import {
  emptySnapshot,
  resource,
  type Collections,
  type DataMode,
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
  providers: Record<DataMode, DataProvider> = {
    demo: new DemoDataProvider(),
    real: new RealDataProvider(),
  },
) {
  let initial: DataMode = "demo";
  try {
    if (storage?.getItem(DATA_MODE_KEY) === "real") initial = "real";
  } catch {
    /* Navigation privée : le mode reste utilisable sans persistance. */
  }
  const mode = ref<DataMode>(initial),
    active = ref(false),
    revision = ref(0);
  const data = reactive<Snapshot>(emptySnapshot());
  let controller: AbortController | undefined,
    reportController: AbortController | undefined,
    generation = 0;
  const isDemo = computed(() => mode.value === "demo"),
    isReal = computed(() => mode.value === "real");
  const sourceId = computed(
    () =>
      `${providers[mode.value].id}:${isReal.value ? auth.user?.id || "anonymous" : "local"}`,
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
    if (!active.value) return;
    const current = new AbortController();
    controller = current;
    const run = generation;
    await providers[mode.value].load(current.signal, (key, value) => {
      if (generation === run && !current.signal.aborted && active.value)
        Object.assign(data, { [key]: value });
    });
  }
  const refresh = () => load(true);
  const refreshInPlace = () => load(false);
  function setMode(value: DataMode) {
    if (!["demo", "real"].includes(value) || value === mode.value) return;
    mode.value = value;
    try {
      storage?.setItem(DATA_MODE_KEY, value);
    } catch {
      /* Même comportement sans stockage. */
    }
    void refresh();
  }
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
    () => auth.user?.id,
    (id, previous) => {
      if (isReal.value && active.value && id !== previous && previous)
        void refresh();
    },
    { flush: "sync" },
  );
  function replace<K extends keyof Collections>(
    key: K,
    values: Collections[K][],
  ) {
    if (!isDemo.value) return;
    Object.assign(data, { [key]: resource(values) });
  }
  function simulate(action: () => void) {
    if (isDemo.value && active.value) action();
  }
  async function report(id: string) {
    reportController?.abort();
    const current = new AbortController();
    reportController = current;
    const run = generation;
    const loader = providers[mode.value].report;
    if (!loader)
      return resource<import("./contracts").Detection>([], "unconnected");
    try {
      const result = await loader.call(
        providers[mode.value],
        id,
        current.signal,
      );
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
    simulate: isDemo.value,
    write: isReal.value && !!auth.user,
    readOnly: isReal.value,
  }));
  const summary = computed(() => summarize(data, isDemo.value));
  function dispose() {
    cancel();
    stopAuthWatch();
  }
  return {
    mode: readonly(mode),
    isDemo,
    isReal,
    sourceId,
    revision: readonly(revision),
    data: readonly(data),
    capabilities,
    summary,
    setMode,
    setActive,
    refresh,
    refreshInPlace,
    replace,
    simulate,
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
  const items = computed<Collections[K][]>({
    get: () => store.data[key].data as Collections[K][],
    set: (value) => store.replace(key, value),
  });
  const state = computed(() => store.data[key]);
  return { store, items, state };
}
