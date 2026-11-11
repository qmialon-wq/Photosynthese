<script setup lang="ts">
import { nextTick, onBeforeUnmount, ref, watch } from "vue";
import {
  LOGIN_TRANSITION_MS,
  LOGIN_TRANSITION_REDUCED_MS,
  useLoginTransition,
} from "../../composables/useLoginTransition";
import { useWallpaper } from "../../composables/useWallpaper";
import logo from "../../assets/symbiose-logo.png";
import GallopingDeer from "./GallopingDeer.vue";

const transition = useLoginTransition();
const wallpaper = useWallpaper();
const skipButton = ref<HTMLButtonElement>();
watch(wallpaper.reduced, (reduced) => {
  if (reduced) transition.finish("skipped");
});
watch(
  transition.active,
  async (active) => {
    if (active) {
      await nextTick();
      if (transition.active.value && !transition.reduced.value)
        skipButton.value?.focus({ preventScroll: true });
    } else {
      const restoreFocus = document.activeElement === skipButton.value;
      await nextTick();
      if (restoreFocus)
        document
          .querySelector<HTMLElement>("#main-content")
          ?.focus({ preventScroll: true });
    }
  },
  { flush: "pre" },
);
function animationEnd(event: AnimationEvent) {
  if (event.target === event.currentTarget) transition.finish();
}
onBeforeUnmount(() => transition.finish("cancelled"));
</script>

<template>
  <div
    class="login-announcement"
    :role="transition.active.value ? 'status' : undefined"
    aria-live="polite"
    aria-atomic="true"
  >
    {{
      transition.active.value
        ? "Connexion réussie. Ouverture de votre espace Symbiose."
        : ""
    }}
  </div>
  <div
    v-if="transition.active.value"
    :key="transition.runId.value"
    class="login-transition"
    :class="{ 'is-reduced': transition.reduced.value }"
    :style="{
      '--login-duration': `${transition.reduced.value ? LOGIN_TRANSITION_REDUCED_MS : LOGIN_TRANSITION_MS}ms`,
      '--login-landscape': `url('${wallpaper.selected.value.image}')`,
    }"
    data-testid="login-transition"
    @animationend="animationEnd"
  >
    <div class="login-landscape" aria-hidden="true" />
    <div class="login-mist" aria-hidden="true" />
    <div
      v-if="!transition.reduced.value"
      class="login-particles"
      aria-hidden="true"
    >
      <i v-for="n in 9" :key="n" :style="{ '--i': n }" />
    </div>
    <div
      v-if="!transition.reduced.value"
      class="login-crossing"
      aria-hidden="true"
    >
      <div class="login-deer-wrap"><GallopingDeer /></div>
    </div>
    <div class="login-welcome" aria-hidden="true">
      <img :src="logo" alt="" width="3634" height="1242" />
      <p>Bienvenue dans Symbiose</p>
      <span>L’humain en symbiose avec la nature.</span>
    </div>
    <button
      ref="skipButton"
      type="button"
      class="login-skip"
      @click="transition.finish('skipped')"
    >
      Passer <span aria-hidden="true">→</span>
    </button>
  </div>
</template>

<style scoped>
.login-announcement {
  position: absolute;
  width: 1px;
  height: 1px;
  padding: 0;
  margin: -1px;
  overflow: hidden;
  clip-path: inset(50%);
  white-space: nowrap;
}
.login-transition {
  position: fixed;
  inset: 0;
  z-index: 10000;
  overflow: hidden;
  isolation: isolate;
  pointer-events: none;
  color: #f6f8ee;
  background: color-mix(in srgb, var(--sym-primary) 92%, transparent);
  animation: login-reveal var(--login-duration) linear both;
}
.login-landscape {
  position: absolute;
  inset: -2%;
  z-index: -2;
  background:
    linear-gradient(
      180deg,
      color-mix(in srgb, var(--sym-primary) 82%, transparent),
      color-mix(in srgb, var(--sym-primary) 65%, transparent)
    ),
    var(--login-landscape) center / cover;
  opacity: 0.7;
  transform: scale(1.03);
}
.login-mist {
  position: absolute;
  inset: 0;
  z-index: -1;
  background:
    radial-gradient(
      ellipse at 60% 48%,
      color-mix(in srgb, var(--sym-accent) 24%, transparent),
      transparent 55%
    ),
    linear-gradient(
      170deg,
      transparent 30%,
      color-mix(in srgb, var(--sym-secondary) 55%, transparent) 65%,
      transparent 85%
    );
  animation: login-mist var(--login-duration) ease-out both;
}
.login-crossing {
  position: absolute;
  top: 40%;
  left: 0;
  width: 100%;
}
.login-deer-wrap {
  width: clamp(250px, 29vw, 440px);
  color: color-mix(in srgb, var(--sym-accent) 38%, #f8f0d5);
  filter: drop-shadow(
    0 2px 12px color-mix(in srgb, var(--sym-accent) 18%, transparent)
  );
  animation: login-crossing 2200ms cubic-bezier(0.32, 0.12, 0.68, 0.88) 150ms
    both;
  will-change: transform;
}
.login-welcome {
  position: absolute;
  top: 18%;
  left: 20px;
  right: 20px;
  text-align: center;
  animation: login-welcome 1150ms ease-out both;
}
.login-welcome img {
  display: block;
  width: clamp(220px, 22vw, 340px);
  height: auto;
  margin: 0 auto -5px;
}
.login-welcome p {
  margin: 0;
  color: #fff;
  font-size: clamp(20px, 2vw, 28px);
  font-weight: 500;
  letter-spacing: -0.5px;
}
.login-welcome span {
  display: block;
  margin-top: 10px;
  color: color-mix(in srgb, var(--sym-accent) 35%, white);
  font-size: clamp(12px, 1.1vw, 15px);
}
.login-skip {
  position: absolute;
  right: max(24px, env(safe-area-inset-right));
  bottom: max(24px, env(safe-area-inset-bottom));
  pointer-events: auto;
  display: flex;
  align-items: center;
  gap: 20px;
  min-height: 44px;
  padding: 8px 20px;
  border: 1px solid rgb(255 255 255 / 45%);
  border-radius: 999px;
  background: var(--sym-primary);
  color: #fff;
  font: inherit;
  font-size: 14px;
}
.login-skip:hover {
  background: var(--sym-secondary);
}
.login-skip:focus-visible {
  outline: 2px solid var(--sym-accent);
  outline-offset: 4px;
}
.login-particles {
  position: absolute;
  inset: 0;
}
.login-particles i {
  position: absolute;
  left: calc(7% + var(--i) * 9%);
  top: calc(35% + mod(var(--i), 3) * 16%);
  width: 3px;
  height: 3px;
  border-radius: 50%;
  background: var(--sym-accent);
  box-shadow: 0 0 10px var(--sym-accent);
  animation: login-particle 2600ms ease-out both;
}
.is-reduced {
  animation-name: login-static;
}
.is-reduced .login-welcome {
  animation: none;
}
.is-reduced .login-mist {
  animation: none;
}
.is-reduced .login-skip {
  display: none;
}
@keyframes login-reveal {
  0% {
    opacity: 0;
  }
  9%,
  84% {
    opacity: 1;
  }
  100% {
    opacity: 0;
  }
}
@keyframes login-crossing {
  from {
    transform: translate3d(-110%, 0, 0);
  }
  to {
    transform: translate3d(calc(100vw + 20%), 0, 0);
  }
}
@keyframes login-welcome {
  0%,
  25% {
    opacity: 0;
    transform: translateY(8px);
  }
  70%,
  100% {
    opacity: 1;
    transform: translateY(0);
  }
}
@keyframes login-mist {
  from {
    transform: translateX(-3%);
    opacity: 0.4;
  }
  to {
    transform: translateX(3%);
    opacity: 0.9;
  }
}
@keyframes login-particle {
  from {
    transform: translate(0, 10px);
    opacity: 0;
  }
  40% {
    opacity: 0.55;
  }
  to {
    transform: translate(-35px, -18px);
    opacity: 0;
  }
}
@keyframes login-static {
  from {
    opacity: 0.65;
  }
  to {
    opacity: 0;
  }
}
@media (max-width: 600px) {
  .login-crossing {
    top: 42%;
  }
  .login-deer-wrap {
    width: 250px;
  }
  .login-welcome {
    top: 24%;
  }
  .login-welcome img {
    width: 250px;
  }
}
@media (prefers-reduced-motion: reduce) {
  .login-transition {
    animation: login-static 120ms linear both;
  }
  .login-crossing,
  .login-particles {
    display: none;
  }
  .login-welcome,
  .login-mist {
    animation: none;
  }
}
</style>
