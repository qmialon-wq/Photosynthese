<script setup lang="ts">
import { ref } from "vue";
import { api, date, message, post, useResource } from "../api";
import { auth, type User } from "../auth-state";
const erasureStatus: Record<string, string> = {
  pending: "À traiter",
  processing: "En cours",
  completed: "Clôturée",
};
const q = ref(""),
  includeDeleted = ref(false);
const users = useResource<User[]>(
  () =>
    `/admin/users?q=${encodeURIComponent(q.value)}&include_deleted=${includeDeleted.value}`,
);
interface Erasure {
  id: string;
  user_id: string;
  status: string;
  requested_at: string;
  note: string;
}
const erasures = useResource<Erasure[]>(() => "/admin/erasure-requests");
const email = ref(""),
  name = ref(""),
  password = ref(""),
  role = ref<"client" | "admin">("client");
const busy = ref(false),
  error = ref(""),
  notice = ref(""),
  link = ref("");
const deleting = ref<User | null>(null),
  confirmation = ref("");
const notes = ref<Record<string, string>>({});
async function run(action: () => Promise<void>) {
  busy.value = true;
  error.value = "";
  notice.value = "";
  link.value = "";
  try {
    await action();
    await users.refresh();
    await erasures.refresh();
  } catch (reason) {
    error.value = message(reason);
  } finally {
    busy.value = false;
  }
}
function create() {
  void run(async () => {
    await post("/admin/users", {
      email: email.value,
      display_name: name.value,
      password: password.value,
      role: role.value,
    });
    password.value = "";
    email.value = "";
    name.value = "";
    notice.value = "Compte créé.";
  });
}
function changeRole(row: User) {
  void run(async () => {
    await api(`/admin/users/${row.id}/role`, {
      method: "PATCH",
      body: JSON.stringify({ role: row.role === "admin" ? "client" : "admin" }),
    });
    notice.value = "Rôle modifié. Les sessions de ce compte ont été révoquées.";
  });
}
function remove() {
  if (!deleting.value) return;
  const id = deleting.value.id;
  void run(async () => {
    await api(`/admin/users/${id}`, { method: "DELETE" });
    deleting.value = null;
    confirmation.value = "";
    notice.value = "Compte supprimé ; demande d’effacement enregistrée.";
  });
}
function reset(row: User) {
  void run(async () => {
    const result = await post<{ path: string }>(
      `/admin/users/${row.id}/reset-link`,
    );
    link.value = location.origin + result.path;
    notice.value =
      "Lien valable 30 minutes, utilisable une seule fois. Transmettez-le au titulaire par un canal approprié.";
  });
}
function review(row: Erasure, status: string) {
  void run(async () => {
    await api(`/admin/erasure-requests/${row.id}`, {
      method: "PATCH",
      body: JSON.stringify({ status, note: notes.value[row.id] ?? row.note }),
    });
    notice.value = "Suivi de la demande mis à jour.";
  });
}
</script>
<template>
  <h1>Gestion des utilisateurs</h1>
  <p
    v-if="error || users.error.value || erasures.error.value"
    role="alert"
    class="notice error"
  >
    {{ error || users.error.value || erasures.error.value }}
  </p>
  <p v-if="notice" role="status" class="notice">{{ notice }}</p>
  <label v-if="link" class="account-form"
    >Lien de réinitialisation (confidentiel)<input
      :value="link"
      readonly
      @focus="($event.target as HTMLInputElement).select()"
  /></label>
  <section class="panel">
    <h2>Comptes</h2>
    <div class="account-form">
      <label
        >Rechercher par nom ou e-mail<input v-model="q" type="search"
      /></label>
    </div>
    <label
      ><input v-model="includeDeleted" type="checkbox" /> Inclure les comptes
      supprimés</label
    >
    <p class="muted">
      200 résultats maximum. Affinez la recherche si nécessaire. Votre propre
      rôle se gère depuis un autre compte administrateur.
    </p>
    <div class="table-wrap">
      <table>
        <thead>
          <tr>
            <th scope="col">Profil</th>
            <th scope="col">Rôle</th>
            <th scope="col">Création</th>
            <th scope="col">Actions</th>
          </tr>
        </thead>
        <tbody>
          <tr v-for="row in users.data.value" :key="row.id">
            <td>
              {{ row.display_name }}<br /><small>{{
                row.email ?? "Identité retirée"
              }}</small>
            </td>
            <td>
              {{
                row.deleted_at
                  ? "Supprimé"
                  : row.role === "admin"
                    ? "Administrateur"
                    : "Client"
              }}
            </td>
            <td>{{ date(row.created_at) }}</td>
            <td>
              <div v-if="!row.deleted_at" class="account-actions">
                <button
                  class="account-button"
                  :disabled="busy || row.id === auth.user?.id"
                  @click="changeRole(row)"
                >
                  {{
                    row.role === "admin"
                      ? "Passer client"
                      : "Passer administrateur"
                  }}</button
                ><button
                  class="account-button"
                  :disabled="busy"
                  @click="reset(row)"
                >
                  Réinitialiser le mot de passe</button
                ><button
                  class="account-button"
                  :disabled="busy || row.id === auth.user?.id"
                  @click="
                    deleting = row;
                    confirmation = '';
                  "
                >
                  Supprimer le compte
                </button>
              </div>
            </td>
          </tr>
        </tbody>
      </table>
    </div>
  </section>
  <section v-if="deleting" class="panel">
    <h2>Supprimer {{ deleting.display_name }}</h2>
    <p>
      L’identité sera retirée, les connexions révoquées et une demande
      d’effacement des données associées sera ouverte.
    </p>
    <form class="account-form" @submit.prevent="remove">
      <label
        >Saisir SUPPRIMER<input
          v-model="confirmation"
          required
          pattern="SUPPRIMER"
      /></label>
      <div class="account-actions">
        <button class="account-button" :disabled="busy">
          Confirmer la suppression</button
        ><button class="account-button" type="button" @click="deleting = null">
          Annuler
        </button>
      </div>
    </form>
  </section>
  <section class="panel">
    <h2>Créer un compte</h2>
    <form class="account-form" @submit.prevent="create">
      <label
        >Nom du profil<input
          v-model="name"
          required
          maxlength="100"
          autocomplete="off"
      /></label>
      <label
        >Adresse e-mail<input
          v-model="email"
          required
          type="email"
          autocomplete="off"
      /></label>
      <label
        >Mot de passe initial<input
          v-model="password"
          type="password"
          required
          minlength="12"
          maxlength="1024"
          autocomplete="new-password"
      /></label>
      <label
        >Rôle<select v-model="role">
          <option value="client">Client</option>
          <option value="admin">Administrateur</option>
        </select></label
      >
      <button class="account-button" :disabled="busy">Créer le compte</button>
    </form>
  </section>
  <section class="panel">
    <h2>Demandes d’effacement</h2>
    <p>
      La fermeture du compte ne supprime pas automatiquement les fichiers et
      sauvegardes. Traitez les données du titulaire dans les stockages et les
      historiques, documentez les éventuelles obligations de conservation, puis
      renseignez ici les opérations effectuées. Le bouton « Clôturer »
      enregistre ce suivi ; il n’exécute aucune purge.
    </p>
    <article v-for="row in erasures.data.value" :key="row.id" class="panel">
      <h3>Demande {{ row.id }}</h3>
      <p>
        Compte {{ row.user_id }} · {{ date(row.requested_at) }} ·
        {{ erasureStatus[row.status] }}
      </p>
      <div class="account-form">
        <label
          >Traitement effectué et éventuelles conservations (20 caractères
          minimum)<textarea
            v-model="notes[row.id]"
            :placeholder="
              row.note || 'Décrire les opérations et leur justification'
            "
            minlength="20"
            maxlength="4000"
          />
        </label>
        <p v-if="row.note">Dernière note : {{ row.note }}</p>
        <div class="account-actions">
          <button
            class="account-button"
            :disabled="busy || (notes[row.id] ?? row.note).trim().length < 20"
            @click="review(row, 'processing')"
          >
            Marquer en cours</button
          ><button
            class="account-button"
            :disabled="busy || (notes[row.id] ?? row.note).trim().length < 20"
            @click="review(row, 'completed')"
          >
            Clôturer la demande
          </button>
        </div>
      </div>
    </article>
    <p v-if="!erasures.data.value?.length">Aucune demande enregistrée.</p>
  </section>
</template>
