import { readonly, ref } from "vue";
import { auth } from "./auth-state";
import { message, post } from "./api";

const open = ref(false),
  step = ref(0),
  error = ref("");
const dismissed = new Set<string>();
export const clientGuide = {
  open: readonly(open),
  step: readonly(step),
  error: readonly(error),
};
export function openClientGuide() {
  step.value = 0;
  open.value = true;
}
export function guideStep(index: number) {
  step.value = index;
}
export function shouldShowClientGuide() {
  return (
    !!auth.user &&
    auth.user.client_guide_seen_at === null &&
    !dismissed.has(auth.user.id)
  );
}
export function resetClientGuide() {
  open.value = false;
  step.value = 0;
  error.value = "";
}
export async function dismissClientGuide() {
  open.value = false;
  const account = auth.user;
  if (!account || account.client_guide_seen_at !== null) return;
  dismissed.add(account.id);
  try {
    const result = await post<{ seen_at: string }>("/auth/client-guide/seen");
    if (auth.user?.id === account.id) {
      auth.user.client_guide_seen_at = result.seen_at;
      error.value = "";
    }
  } catch (reason) {
    if (auth.user?.id === account.id)
      error.value = `La consultation du guide n’a pas pu être mémorisée : ${message(reason)}. Le guide reste disponible avec Aide.`;
  }
}
