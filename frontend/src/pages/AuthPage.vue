<script setup lang="ts">
import { computed, onMounted, ref, watch } from "vue";
import { useRoute, useRouter } from "vue-router";
import { message, post, api } from "../api";
import { auth, acceptSession, type Session } from "../auth-state";
import symbioseLogo from "../assets/symbiose-logo.png";
const route = useRoute(),
  router = useRouter();
const mode = computed(() => route.path.slice(1));
const title = computed(
  () =>
    ({
      connexion: "Se connecter",
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
  setupRequired = ref(false),
  passwordVisible = ref(false),
  resetHelpVisible = ref(false);
watch(mode, () => {
  error.value = "";
  notice.value = "";
  password.value = "";
  confirmation.value = "";
  token.value = "";
  passwordVisible.value = false;
  resetHelpVisible.value = false;
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
  <section class="auth-card" aria-labelledby="auth-title">
    <header class="auth-header">
      <RouterLink to="/connexion" aria-label="Symbiose — connexion">
        <img
          :src="symbioseLogo"
          alt="Symbiose"
          class="auth-logo"
          width="3634"
          height="1242"
        />
      </RouterLink>
      <p class="auth-tagline">
        L’humain en symbiose avec la nature
      </p>
    </header>
    <h1 id="auth-title">{{ title }}</h1>
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
      <label v-if="mode !== 'reinitialiser'" class="auth-field">
        <span class="auth-sr-only">Adresse e-mail</span>
        <i class="pi pi-envelope" aria-hidden="true" />
        <input
          v-model="email"
          type="email"
          placeholder="Adresse e-mail"
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
      <div class="auth-field auth-password">
        <label for="auth-password" class="auth-sr-only">Mot de passe</label>
        <i class="pi pi-lock" aria-hidden="true" />
        <input
          id="auth-password"
          v-model="password"
          :type="passwordVisible ? 'text' : 'password'"
          placeholder="Mot de passe"
          required
          :minlength="mode === 'connexion' ? undefined : 12"
          maxlength="1024"
          :autocomplete="
            mode === 'connexion' ? 'current-password' : 'new-password'
          "
        />
        <button
          type="button"
          class="auth-password-toggle"
          :aria-label="
            passwordVisible
              ? 'Masquer le mot de passe'
              : 'Afficher le mot de passe'
          "
          :aria-pressed="passwordVisible"
          aria-controls="auth-password"
          @click="passwordVisible = !passwordVisible"
        >
          <i
            :class="['pi', passwordVisible ? 'pi-eye-slash' : 'pi-eye']"
            aria-hidden="true"
          />
        </button>
      </div>
      <div v-if="mode === 'connexion'" class="auth-recovery">
        <button
          type="button"
          class="auth-help-button"
          :aria-expanded="resetHelpVisible"
          aria-controls="auth-reset-help"
          @click="resetHelpVisible = !resetHelpVisible"
        >
          Mot de passe oublié ?
        </button>
        <p v-if="resetHelpVisible" id="auth-reset-help" role="status">
          Demandez un lien de réinitialisation à un administrateur.
        </p>
      </div>
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
        class="auth-submit"
        type="submit"
        :disabled="busy || (mode === 'reinitialiser' && !token)"
      >
        {{ busy ? "Veuillez patienter…" : title }}
        <i v-if="!busy" class="pi pi-arrow-right" aria-hidden="true" />
      </button>
    </form>
    <p v-if="mode === 'connexion' && !setupRequired" class="auth-signup">
      Pas encore de compte ?
      <RouterLink to="/inscription">Créer un compte</RouterLink>
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

<style scoped>
.auth-card {
  width: min(100%, 616px);
  padding: 24px 54px 38px;
  border: 1px solid rgb(255 255 255 / 58%);
  border-radius: 40px;
  background: linear-gradient(
    135deg,
    rgb(214 225 191 / 27%),
    rgb(13 41 31 / 67%) 58%,
    rgb(164 186 154 / 30%)
  );
  box-shadow:
    0 20px 65px rgb(0 15 8 / 30%),
    inset 0 0 0 1px rgb(255 255 255 / 10%);
  backdrop-filter: blur(22px);
  -webkit-backdrop-filter: blur(22px);
  color: #fff;
  font-size: 16px;
  line-height: 1.5;
}
.auth-header {
  text-align: center;
}
.auth-header a {
  display: inline-block;
  max-width: 100%;
  border-radius: 12px;
}
.auth-logo {
  display: block;
  width: 360px;
  max-width: 100%;
  height: auto;
}
.auth-tagline {
  margin: -12px 0 0;
  font-size: 20px;
  line-height: 1.25;
  letter-spacing: -0.5px;
}
.auth-card h1 {
  margin: 28px 0 16px;
  font-size: 26px;
  line-height: 1.25;
  font-weight: 650;
  letter-spacing: -0.7px;
  color: #fff;
}
.auth-card .muted,
.auth-card small {
  color: #ecf2e9;
}
.auth-card a {
  color: #b5ed8b;
}
.auth-card > p {
  font-size: 14px;
}
.auth-card .account-form {
  gap: 12px;
  margin: 0;
  max-width: none;
}
.auth-card .account-form label {
  color: #fff;
  font-size: 15px;
}
.auth-field {
  position: relative;
  display: flex;
  align-items: center;
}
.auth-field > .pi {
  position: absolute;
  left: 20px;
  top: 50%;
  transform: translateY(-50%);
  z-index: 1;
  font-size: 22px;
  pointer-events: none;
}
.auth-card .account-form input {
  min-height: 50px;
  border: 1px solid rgb(255 255 255 / 75%);
  border-radius: 21px;
  background: rgb(219 233 214 / 14%);
  color: #fff;
  box-shadow: inset 0 0 0 2px rgb(255 255 255 / 4%);
  font-size: 16px;
  font-weight: 400;
}
.auth-card .auth-field input {
  padding: 11px 20px 11px 58px;
}
.auth-card .auth-password input {
  padding-right: 58px;
}
.auth-card input::placeholder {
  color: #f0f3ed;
  opacity: 1;
}
.auth-card input:focus-visible {
  outline: 2px solid #b5ed8b;
  outline-offset: 3px;
  background: rgb(219 233 214 / 20%);
}
.auth-card input:-webkit-autofill {
  -webkit-text-fill-color: #fff;
  box-shadow: inset 0 0 0 1000px #304d3d;
  caret-color: #fff;
}
.auth-card .auth-password-toggle {
  position: absolute;
  right: 6px;
  display: grid;
  place-items: center;
  width: 44px;
  height: 44px;
  padding: 0;
  border: 0;
  border-radius: 50%;
  background: transparent;
  color: #fff;
  font-size: 23px;
}
.auth-password-toggle:hover {
  background: rgb(255 255 255 / 12%);
}
.auth-password-toggle .pi {
  font-size: 23px;
}
.auth-recovery {
  text-align: right;
}
.auth-help-button {
  min-height: 32px;
  padding: 0;
  border: 0;
  background: transparent;
  color: #fff;
  font-size: 14px;
}
.auth-help-button:hover {
  text-decoration: underline;
}
.auth-recovery p {
  margin: 6px 0 0;
  font-size: 14px;
}
.auth-card .auth-submit {
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 20px;
  width: 100%;
  min-height: 55px;
  margin-top: 10px;
  padding: 12px 20px;
  border: 1px solid transparent;
  border-radius: 30px;
  background: linear-gradient(100deg, #bfeb8b, #a9e580);
  color: #10230b;
  font-size: 18px;
  font-weight: 700;
  box-shadow: 0 5px 20px rgb(0 20 0 / 10%);
}
.auth-submit .pi {
  font-size: 21px;
}
.auth-submit:hover:not(:disabled) {
  background: #caf4a3;
}
.auth-submit:disabled {
  opacity: 0.65;
}
.auth-card :is(button, a):focus-visible {
  outline: 3px solid #c8f7a2;
  outline-offset: 4px;
}
.auth-card .auth-signup {
  display: flex;
  flex-wrap: wrap;
  justify-content: center;
  gap: 8px 20px;
  margin: 32px 0 0;
  font-size: 14px;
}
.auth-signup a {
  font-weight: 600;
}
.auth-card .notice {
  margin: 14px 0;
  border: 1px solid #b5ed8b;
  border-radius: 12px;
  padding: 12px 16px;
  background: #153c2e;
  color: #fff;
}
.auth-card .notice.error {
  border-color: #ffc1b5;
  background: #572a24;
  color: #fff0ec;
}
.auth-sr-only {
  position: absolute;
  width: 1px;
  height: 1px;
  padding: 0;
  margin: -1px;
  overflow: hidden;
  clip-path: inset(50%);
  white-space: nowrap;
  border: 0;
}
@media (max-width: 600px) {
  .auth-card {
    padding: 22px 24px 30px;
    border-radius: 28px;
    background: rgb(15 44 33 / 76%);
  }
  .auth-logo {
    width: 320px;
  }
  .auth-tagline {
    font-size: 18px;
  }
  .auth-card h1 {
    margin-top: 28px;
    font-size: 24px;
  }
  .auth-card .auth-signup {
    margin-top: 26px;
  }
}
@media (prefers-reduced-transparency: reduce) {
  .auth-card {
    background: #1b3d2e;
    backdrop-filter: none;
  }
}
</style>
