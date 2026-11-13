import { defineConfig } from "vite";
import vue from "@vitejs/plugin-vue";
import { juryBuild } from "./scripts/jury-build.mjs";

export default defineConfig({
  plugins: [vue(), juryBuild()],
  build: {
    manifest: true,
    rollupOptions: { input: { app: "index.html", jury: "jury/index.html" } },
  },
  server: {
    proxy: {
      "/api": {
        target: "http://127.0.0.1:8000",
        rewrite: (path) => path.replace(/^\/api/, ""),
      },
    },
  },
});
