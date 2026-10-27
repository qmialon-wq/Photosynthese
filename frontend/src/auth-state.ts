import { reactive } from "vue";

export interface User {
  id: string;
  email: string | null;
  display_name: string;
  role: "client" | "admin";
  created_at: string;
  deleted_at: string | null;
}
export interface Session {
  user: User;
  csrf_token: string;
}
export const auth = reactive({
  user: null as User | null,
  csrf: "",
  loaded: false,
  error: "",
});
export function acceptSession(session: Session) {
  auth.user = session.user;
  auth.csrf = session.csrf_token;
  auth.loaded = true;
  auth.error = "";
}
export function clearSession() {
  auth.user = null;
  auth.csrf = "";
  auth.loaded = true;
}
