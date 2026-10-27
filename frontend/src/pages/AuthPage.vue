<script setup lang="ts">
import { computed, onMounted, ref, watch } from "vue";
import { useRoute, useRouter } from "vue-router";
import { message, post, api } from "../api";
import { auth, acceptSession, type Session } from "../auth-state";
const route = useRoute(),
  router = useRouter();
const mode = computed(() => route.path.slice(1));
const title = computed(
  () =>
    ({
      connexion: "Connexion",
      inscription: "Créer un compte client",
      initialisation: "Premier administrateur",
      reinitialiser: "Nouveau mot de passe",
    })[mode.value],
);
const email = ref(""),
  name = ref(""),
  password = ref(""),
  confirmation = ref(""),
  token = ref("");
const error = ref(auth.error),
  notice = ref(""),
  busy = ref(false),
  setupRequired = ref(false);
watch(mode, () => {
  error.value = "";
  notice.value = "";
  password.value = "";
  confirmation.value = "";
  token.value = "";
});
onMounted(async () => {
  if (mode.value === "reinitialiser") {
    token.value =
      new URLSearchParams(location.hash.slice(1)).get("token") ?? "";
    history.replaceState(
      history.state,
      "",
      location.pathname + location.search,
    );
  }
  try {
    setupRequired.value = (
      await api<{ setup_required: boolean }>("/auth/status")
    ).setup_required;
  } catch (reason) {
    error.value = message(reason);
  }
});
async function submit() {
  error.value = "";
  notice.value = "";
  if (mode.value !== "connexion" && password.value !== confirmation.value) {
    error.value = "Les mots de passe ne correspondent pas.";
    return;
  }
  busy.value = true;
  try {
    if (mode.value === "reinitialiser") {
      await post("/auth/reset-password", {
        token: token.value,
        password: password.value,
      });
      token.value = "";
      password.value = "";
      confirmation.value = "";
      notice.value = "Mot de passe modifié. Vous pouvez vous connecter.";
    } else {
      const body: Record<string, string> = {
        email: email.value,
        password: password.value,
      };
      if (mode.value !== "connexion") body.display_name = name.value;
      if (mode.value === "initialisation") body.setup_token = token.value;
      const endpoint =
        mode.value === "connexion"
          ? "login"
          : mode.value === "initialisation"
            ? "setup"
            : "register";
      acceptSession(await post<Session>(`/auth/${endpoint}`, body));
      password.value = "";
      token.value = "";
      await router.push("/");
    }
  } catch (reason) {
    error.value = message(reason);
  } finally {
    busy.value = false;
  }
}
</script>
<template>
  <section class="panel auth-card">
    <RouterLink to="/connexion" class="brand">BioSentinelle</RouterLink>
    <h1>{{ title }}</h1>
    <p v-if="mode === 'inscription'" class="muted">
      Votre compte permet d’importer des vidéos, de valider vos observations et
      de générer vos dossiers.
    </p>
    <p v-if="mode === 'inscription'" class="muted">
      Votre nom et votre adresse e-mail servent à gérer votre accès. Depuis
      votre profil, vous pourrez modifier ces informations, exporter vos données
      et supprimer votre compte. L’effacement des fichiers associés fait l’objet
      d’un suivi par l’administration.
    </p>
    <p v-if="mode === 'initialisation'">
      Lisez le jeton local dans <code>data/results/auth/bootstrap-token</code>.
      Il permet de créer le premier administrateur et devient inutilisable après
      cette étape.
    </p>
    <p v-if="mode === 'reinitialiser'" class="muted">
      Le lien fourni par un administrateur est valable 30 minutes et utilisable
      une seule fois.
    </p>
    <p v-if="error" role="alert" class="notice error">{{ error }}</p>
    <p v-if="notice" role="status" class="notice">{{ notice }}</p>
    <form v-if="!notice" class="account-form" @submit.prevent="submit">
      <label v-if="['inscription', 'initialisation'].includes(mode)"
        >Nom du profil<input
          v-model="name"
          required
          maxlength="100"
          autocomplete="name"
      /></label>
      <label v-if="mode !== 'reinitialiser'"
        >Adresse e-mail<input
          v-model="email"
          type="email"
          required
          maxlength="254"
          autocomplete="username"
      /></label>
      <label v-if="mode === 'initialisation'"
        >Jeton d’initialisation<input
          v-model="token"
          type="password"
          required
          autocomplete="off"
      /></label>
      <label
        >Mot de passe<input
          v-model="password"
          type="password"
          required
          :minlength="mode === 'connexion' ? undefined : 12"
          maxlength="1024"
          :autocomplete="
            mode === 'connexion' ? 'current-password' : 'new-password'
          "
      /></label>
      <small v-if="mode !== 'connexion'"
        >Au moins 12 caractères. Une phrase de passe est possible.</small
      >
      <label v-if="mode !== 'connexion'"
        >Confirmer le mot de passe<input
          v-model="confirmation"
          type="password"
          required
          autocomplete="new-password"
      /></label>
      <button
        class="account-button"
        type="submit"
        :disabled="busy || (mode === 'reinitialiser' && !token)"
      >
        {{ busy ? "Veuillez patienter…" : title }}
      </button>
    </form>
    <p v-if="mode === 'connexion' && !setupRequired">
      Pas encore de compte ?
      <RouterLink to="/inscription">S’inscrire</RouterLink>
    </p>
    <p v-if="mode === 'connexion'">
      Mot de passe oublié ? Demandez un lien de réinitialisation à un
      administrateur.
    </p>
    <p v-if="setupRequired && mode !== 'initialisation'">
      <RouterLink to="/initialisation"
        >Initialiser le premier administrateur</RouterLink
      >
    </p>
    <p v-if="mode !== 'connexion'">
      <RouterLink to="/connexion">Se connecter</RouterLink>
    </p>
  </section>
</template>
