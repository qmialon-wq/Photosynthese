<script setup lang="ts">
import { onMounted, ref } from 'vue'

const status = ref('Vérification en cours…')
const busy = ref(false)

async function checkHealth(): Promise<void> {
  busy.value = true
  try {
    const response = await fetch('/api/health', { signal: AbortSignal.timeout(8000) })
    const health: { status: string } = await response.json()
    status.value = response.ok && health.status === 'ok'
      ? 'API, PostgreSQL et Redis disponibles'
      : 'Un service est indisponible'
  } catch {
    status.value = 'Connexion à l’API impossible'
  } finally {
    busy.value = false
  }
}

onMounted(checkHealth)
</script>

<template>
  <main>
    <p class="region">OBSERVATOIRE LOCAL · NORMANDIE</p>
    <h1>BioSentinelle</h1>
    <p>Suivi de la biodiversité par vidéos de pièges photographiques.</p>
    <section aria-labelledby="infrastructure">
      <h2 id="infrastructure">État de l’infrastructure</h2>
      <p role="status" aria-live="polite">{{ status }}</p>
      <button :disabled="busy" @click="checkHealth">Actualiser</button>
    </section>
    <p class="note">Socle technique initial. L’analyse vidéo et la validation humaine seront intégrées ultérieurement.</p>
  </main>
</template>

<style>
:root { font-family: system-ui, sans-serif; color: #153d30; background: #f3f5ee; }
body { margin: 0; }
main { max-width: 760px; margin: 10vh auto; padding: 24px; }
h1 { font-size: clamp(2.4rem, 8vw, 4rem); margin: 12px 0; }
.region { letter-spacing: .12em; font-size: .8rem; }
section { margin: 40px 0; padding: 24px; border: 1px solid #becab9; border-radius: 12px; background: white; }
h2 { font-size: 1.2rem; }
button { background: #235a43; color: white; padding: 10px 18px; border: 0; border-radius: 6px; cursor: pointer; }
button:disabled { opacity: .6; cursor: wait; }
.note { color: #526354; line-height: 1.6; }
</style>
