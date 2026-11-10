import { computed, onBeforeUnmount, ref, watch } from "vue";
import { api, message, post } from "./api";
import { useDataMode } from "./data/data-mode";

interface ImportTask {
  id: string;
  filename: string;
  status: string;
  error?: string;
  result?: { video_id?: string };
}

export function useClientVideoImport(imported: (ids: string[]) => void) {
  const store = useDataMode();
  const busy = ref(false),
    progress = ref(0),
    error = ref("");
  const tasks = ref<ImportTask[]>([]);
  const pending = computed(() =>
    tasks.value.some((task) => ["queued", "running"].includes(task.status)),
  );
  let controller: AbortController | undefined,
    currentUpload = "",
    disposed = false,
    polling = false;
  const seen = new Set<string>();
  const timer = setInterval(() => {
    if (!document.hidden) void poll();
  }, 3000);
  function reset() {
    controller?.abort();
    currentUpload = "";
    tasks.value = [];
    busy.value = false;
    progress.value = 0;
    error.value = "";
    seen.clear();
  }
  watch(() => store.sourceId.value, reset, { flush: "sync" });
  async function poll() {
    if (
      !pending.value ||
      polling ||
      !store.capabilities.value.write ||
      disposed
    )
      return;
    const source = store.sourceId.value;
    polling = true;
    try {
      const rows = await post<ImportTask[]>("/parcels/import-status", {
        task_ids: tasks.value.map((task) => task.id),
      });
      if (disposed || source !== store.sourceId.value) return;
      const ids: string[] = [];
      tasks.value = tasks.value.map((task) => {
        const update = rows.find((row) => row.id === task.id);
        if (
          update?.status === "completed" &&
          update.result?.video_id &&
          !seen.has(task.id)
        ) {
          seen.add(task.id);
          ids.push(update.result.video_id);
        }
        return update ? { ...task, ...update } : task;
      });
      if (ids.length) {
        imported(ids);
        await store.refreshInPlace();
      }
    } catch (reason) {
      if (!disposed && source === store.sourceId.value)
        error.value = message(reason);
    } finally {
      polling = false;
    }
  }
  async function upload(files: File[]) {
    if (!store.capabilities.value.write || busy.value) return;
    if (
      !files.length ||
      files.length > 1000 ||
      files.some((file) => !file.size)
    ) {
      error.value = "Sélectionnez de 1 à 1000 vidéos non vides.";
      return;
    }
    const source = store.sourceId.value;
    controller = new AbortController();
    const signal = controller.signal;
    const total = files.reduce((sum, file) => sum + file.size, 0);
    let sent = 0;
    busy.value = true;
    progress.value = 0;
    error.value = "";
    try {
      for (const file of files) {
        const session = await api<{ id: string; chunk_size: number }>(
          "/console/uploads",
          {
            method: "POST",
            body: JSON.stringify({ filename: file.name, size: file.size }),
            signal,
          },
        );
        if (
          !Number.isSafeInteger(session.chunk_size) ||
          session.chunk_size <= 0
        )
          throw new Error("Taille de fragment invalide.");
        currentUpload = session.id;
        for (
          let start = 0, index = 0;
          start < file.size;
          start += session.chunk_size, index++
        ) {
          await api(
            `/console/uploads/${encodeURIComponent(session.id)}/chunks/${index}`,
            {
              method: "PUT",
              body: file.slice(start, start + session.chunk_size),
              signal,
            },
          );
          if (disposed || source !== store.sourceId.value) return;
          progress.value = Math.round(
            (100 * (sent + Math.min(file.size, start + session.chunk_size))) /
              total,
          );
        }
        const task = await api<{ id: string }>(
          `/console/uploads/${encodeURIComponent(session.id)}/complete`,
          { method: "POST", signal },
        );
        currentUpload = "";
        if (disposed || source !== store.sourceId.value) return;
        tasks.value.push({
          id: task.id,
          filename: file.name,
          status: "queued",
        });
        sent += file.size;
      }
      await poll();
    } catch (reason) {
      if (!disposed && source === store.sourceId.value)
        error.value = signal.aborted ? "Transfert annulé." : message(reason);
    } finally {
      if (!disposed && source === store.sourceId.value) busy.value = false;
    }
  }
  async function cancel() {
    controller?.abort();
    const upload = currentUpload;
    currentUpload = "";
    if (upload && store.capabilities.value.write) {
      try {
        await api(`/console/uploads/${encodeURIComponent(upload)}`, {
          method: "DELETE",
        });
      } catch (reason) {
        error.value = message(reason);
      }
    }
  }
  onBeforeUnmount(() => {
    disposed = true;
    controller?.abort();
    clearInterval(timer);
  });
  return { busy, progress, error, tasks, pending, upload, cancel };
}
