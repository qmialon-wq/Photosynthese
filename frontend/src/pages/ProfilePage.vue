<script setup lang="ts">
import { ref } from "vue";
import { useRouter } from "vue-router";
import { auth, clearSession, type User } from "../auth-state";
import { api, apiUrl, post, message } from "../api";
const router = useRouter();
const name = ref(auth.user?.display_name ?? ""),
  email = ref(auth.user?.email ?? ""),
  current = ref(""),
  next = ref(""),
  confirmPassword = ref("");
const deletionPassword = ref(""),
  confirmation = ref("");
const busy = ref(false),
  error = ref(""),
  notice = ref(""),
  receipt = ref("");
async function run(action: () => Promise<void>) {
  busy.value = true;
  error.value = "";
  notice.value = "";
  try {
    await action();
  } catch (reason) {
    error.value = message(reason);
  } finally {
    busy.value = false;
  }
}
function save() {
  void run(async () => {
    auth.user = await api<User>("/auth/me", {
      method: "PATCH",
      body: JSON.stringify({
        display_name: name.value,
        email: email.value,
        current_password: current.value || null,
      }),
    });
    current.value = "";
    notice.value = "Profil enregistré.";
  });
}
function changePassword() {
  void run(async () => {
    if (next.value !== confirmPassword.value)
      throw new Error("Les mots de passe ne correspondent pas.");
    await post("/auth/password", {
      current_password: current.value,
      new_password: next.value,
    });
    clearSession();
    await router.push("/connexion");
  });
}
function remove() {
  void run(async () => {
    const result = await api<{ erasure_request: string }>("/auth/me", {
      method: "DELETE",
      body: JSON.stringify({
        current_password: deletionPassword.value,
        confirmation: confirmation.value,
      }),
    });
    receipt.value = result.erasure_request;
    deletionPassword.value = "";
    current.value = "";
    next.value = "";
    confirmPassword.value = "";
    // Keep the receipt visible until the user leaves this page; cookie is already revoked.
    auth.csrf = "";
  });
}
async function leave() {
  clearSession();
  await router.push("/connexion");
}
</script>
<template>
  <h1>Mon profil</h1>
  <p v-if="error" role="alert" class="notice error">{{ error }}</p>
  <p v-if="notice" role="status" class="notice">{{ notice }}</p>
  <section v-if="receipt" class="panel" role="status">
    <h2>Compte supprimé</h2>
    <p>
      Votre connexion est révoquée et vos informations d’identité ont été
      retirées du compte. La demande d’effacement des données associées a été
      transmise à l’administration.
    </p>
    <p>
      Référence à conserver : <code>{{ receipt }}</code>
    </p>
    <button class="account-button" @click="leave">Retour à la connexion</button>
  </section>
  <template v-else>
    <section class="panel">
      <h2>Informations du compte</h2>
      <p>{{ auth.user?.role === "admin" ? "Administrateur" : "Client" }}</p>
      <form class="account-form" @submit.prevent="save">
        <label
          >Nom du profil<input
            v-model="name"
            required
            maxlength="100"
            autocomplete="name"
        /></label>
        <label
          >Adresse e-mail<input
            v-model="email"
            required
            type="email"
            autocomplete="username"
        /></label>
        <label
          >Mot de passe actuel (requis pour changer l’adresse e-mail)<input
            v-model="current"
            type="password"
            autocomplete="current-password"
        /></label>
        <button class="account-button" :disabled="busy">
          Enregistrer le profil
        </button>
      </form>
      <a :href="apiUrl('/auth/me/export')" download="mes-donnees.json"
        >Télécharger mes données (JSON)</a
      >
      <p class="muted">
        Cet export contient vos informations et enregistrements de la
        plateforme. Les fichiers vidéo sont téléchargeables depuis votre
        vidéothèque.
      </p>
    </section>
    <section class="panel">
      <h2>Changer de mot de passe</h2>
      <p>Cette opération déconnecte toutes vos sessions.</p>
      <form class="account-form" @submit.prevent="changePassword">
        <label
          >Mot de passe actuel<input
            v-model="current"
            required
            type="password"
            autocomplete="current-password"
        /></label>
        <label
          >Nouveau mot de passe<input
            v-model="next"
            required
            minlength="12"
            maxlength="1024"
            type="password"
            autocomplete="new-password"
        /></label>
        <label
          >Confirmer le nouveau mot de passe<input
            v-model="confirmPassword"
            required
            type="password"
            autocomplete="new-password"
        /></label>
        <button class="account-button" :disabled="busy">
          Modifier et me déconnecter
        </button>
      </form>
    </section>
    <section class="panel">
      <h2>Supprimer mon compte</h2>
      <p>
        La suppression retire votre identité et bloque immédiatement l’accès au
        compte. Vos vidéos, dossiers et historiques font l’objet d’une demande
        d’effacement distincte, suivie par un administrateur. Des obligations
        légales peuvent imposer certaines conservations.
      </p>
      <p>
        Exportez vos données avant de continuer. Le dernier administrateur doit
        d’abord désigner un autre administrateur.
      </p>
      <form class="account-form" @submit.prevent="remove">
        <label
          >Mot de passe actuel<input
            v-model="deletionPassword"
            required
            type="password"
            autocomplete="current-password"
        /></label>
        <label
          >Saisir SUPPRIMER pour confirmer<input
            v-model="confirmation"
            required
            pattern="SUPPRIMER"
            autocomplete="off"
        /></label>
        <button class="account-button" :disabled="busy">
          Supprimer définitivement l’accès à mon compte
        </button>
      </form>
    </section>
  </template>
</template>
