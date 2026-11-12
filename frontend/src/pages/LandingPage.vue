<script setup lang="ts">
import { auth } from "../auth-state";
import logo from "../assets/symbiose-logo.png";
import forest from "../assets/home-forest.png";
import SymIcon from "../components/symbiose/SymIcon.vue";
import "../styles/landing.css";

const steps = [
  {
    icon: "video",
    title: "Observez votre territoire",
    text: "Importez les vidéos de vos pièges photographiques et regroupez-les par parcelle.",
  },
  {
    icon: "sparkles",
    title: "Analysez vos observations",
    text: "Détectez les animaux, suivez leurs déplacements et consultez les espèces proposées par le modèle.",
  },
  {
    icon: "check-square",
    title: "Gardez le dernier mot",
    text: "Vérifiez les espèces et les recadrages avant de vous appuyer sur les résultats.",
  },
  {
    icon: "leaf",
    title: "Éclairez vos projets",
    text: "Croisez vos observations avec les publications scientifiques et le contexte de votre parcelle.",
  },
];
</script>

<template>
  <div class="landing" :style="{ '--landing-image': `url(${forest})` }">
    <header class="landing-header">
      <RouterLink to="/" aria-label="Symbiose Normandie — accueil"
        ><img :src="logo" alt="Symbiose Normandie" width="3634" height="1242"
      /></RouterLink>
      <nav aria-label="Navigation d’accueil">
        <a href="#parcours">Découvrir la plateforme</a>
        <RouterLink v-if="auth.user" class="landing-button" to="/videos"
          >Mon espace</RouterLink
        >
        <template v-else>
          <RouterLink to="/connexion">Se connecter</RouterLink>
          <RouterLink class="landing-button" to="/inscription"
            >Créer un compte</RouterLink
          >
        </template>
      </nav>
    </header>
    <main id="main-content" tabindex="-1">
      <section class="landing-hero" aria-labelledby="landing-title">
        <p class="landing-eyebrow">OBSERVER · COMPRENDRE · PRÉSERVER</p>
        <h1 id="landing-title">
          La biodiversité de votre territoire,<br />au cœur de vos décisions.
        </h1>
        <p class="landing-intro">
          De vos vidéos de terrain à un dossier biodiversité : Symbiose vous
          accompagne pour observer la faune, confirmer vos découvertes et
          préparer vos projets en Normandie.
        </p>
        <div class="landing-actions">
          <RouterLink
            class="landing-button"
            :to="auth.user ? '/videos' : '/inscription'"
            >{{
              auth.user ? "Accéder à mes vidéos" : "Commencer mes observations"
            }}
            <SymIcon name="arrow" :size="20"
          /></RouterLink>
          <RouterLink v-if="auth.user" class="landing-secondary" to="/parcelles"
            >Retrouver mes dossiers</RouterLink
          >
          <RouterLink v-else class="landing-secondary" to="/connexion"
            >J’ai déjà un compte</RouterLink
          >
        </div>
        <p class="landing-trust">
          Vos données dans votre espace · Validation humaine des espèces
        </p>
      </section>
      <section
        id="parcours"
        class="landing-journey"
        aria-labelledby="journey-title"
      >
        <p class="landing-eyebrow">DU TERRAIN À LA CONNAISSANCE</p>
        <h2 id="journey-title">Un parcours pour comprendre le vivant.</h2>
        <div class="landing-grid">
          <article v-for="(step, index) in steps" :key="step.title">
            <div class="landing-step">
              <SymIcon :name="step.icon" :size="28" /><span
                >0{{ index + 1 }}</span
              >
            </div>
            <h3>{{ step.title }}</h3>
            <p>{{ step.text }}</p>
          </article>
        </div>
      </section>
      <section class="landing-evidence">
        <div>
          <p class="landing-eyebrow">DES RÉSULTATS À EXAMINER</p>
          <h2>
            L’intelligence artificielle vous assiste.<br />Votre expertise reste
            essentielle.
          </h2>
        </div>
        <p>
          Les identifications automatiques sont des propositions à confirmer.
          Les recommandations s’appuient sur les données disponibles et leurs
          sources ; elles conservent leurs limites et leurs conditions
          d’application.
        </p>
      </section>
    </main>
    <footer class="landing-footer">
      <span>Symbiose Normandie</span
      ><span>Observer · Valider · Comprendre</span>
    </footer>
  </div>
</template>
