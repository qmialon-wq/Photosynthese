import { readonly, ref } from "vue";

export const LOGIN_TRANSITION_MS = 2800;
export const LOGIN_TRANSITION_REDUCED_MS = 120;
export type TransitionEnd =
  | "completed"
  | "skipped"
  | "cancelled"
  | "timeout"
  | "replaced";

/** Presentation lifecycle only. Authentication and navigation remain with the caller. */
export function createLoginTransition() {
  const active = ref(false);
  const reduced = ref(false);
  const runId = ref(0);
  let timer: ReturnType<typeof setTimeout> | undefined;
  let resolve: ((reason: TransitionEnd) => void) | undefined;

  function finish(reason: TransitionEnd = "completed", id = runId.value) {
    if (id !== runId.value || !active.value) return;
    clearTimeout(timer);
    timer = undefined;
    active.value = false;
    const complete = resolve;
    resolve = undefined;
    complete?.(reason);
  }

  function start(reduceMotion: boolean) {
    finish("replaced");
    const id = ++runId.value;
    reduced.value = reduceMotion;
    const finished = new Promise<TransitionEnd>((done) => {
      resolve = done;
    });
    active.value = true;
    // Independent of CSS events, route/data readiness and component mounting.
    timer = setTimeout(
      () => finish("timeout", id),
      (reduceMotion ? LOGIN_TRANSITION_REDUCED_MS : LOGIN_TRANSITION_MS) + 300,
    );
    return {
      id,
      finished,
      finish: (reason: TransitionEnd = "completed") => finish(reason, id),
    };
  }

  return {
    active: readonly(active),
    reduced: readonly(reduced),
    runId: readonly(runId),
    start,
    finish,
  };
}

const shared = createLoginTransition();
export const useLoginTransition = () => shared;
