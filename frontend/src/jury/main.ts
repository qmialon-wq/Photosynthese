import { createApp } from "vue";
import { createMemoryHistory, createRouter } from "vue-router";
import JuryApp from "./JuryApp.vue";
import "./jury.css";

// Deliberately independent of App.vue, authentication, API providers and business workers.
const router = createRouter({
  history: createMemoryHistory(),
  routes: [{ path: "/:pathMatch(.*)*", component: { render: () => null } }],
});
createApp(JuryApp).use(router).mount("#app");
