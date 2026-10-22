import { createApp } from "vue";
import App from "./App.vue";
import PrimeVue from "primevue/config";
import Aura from "@primeuix/themes/aura";
import { definePreset } from "@primeuix/themes";
import Button from "primevue/button";
import Tag from "primevue/tag";
import Dialog from "primevue/dialog";
import InputText from "primevue/inputtext";
import ProgressBar from "primevue/progressbar";
import LoadState from "./components/LoadState.vue";
import StatusBadge from "./components/StatusBadge.vue";
import TaskPanel from "./components/TaskPanel.vue";
import MetricsPanel from "./components/MetricsPanel.vue";
import { router } from "./router";
import "primeicons/primeicons.css";
import "./style.css";

const app = createApp(App)
  .use(router)
  .use(PrimeVue, {
    theme: {
      preset: definePreset(Aura, {
        semantic: {
          primary: {
            50: "#f2f7ee",
            100: "#e0ebd6",
            200: "#c6dbb7",
            300: "#a2c496",
            400: "#729c6e",
            500: "#28614c",
            600: "#215540",
            700: "#194634",
            800: "#153b2e",
            900: "#103024",
            950: "#092219",
          },
        },
      }),
      options: { darkModeSelector: ".dark-mode" },
    },
  });
for (const [name, component] of Object.entries({
  PButton: Button,
  PTag: Tag,
  PDialog: Dialog,
  PInputText: InputText,
  PProgressBar: ProgressBar,
  LoadState,
  StatusBadge,
  TaskPanel,
  MetricsPanel,
}))
  app.component(name, component);
app.mount("#app");
