import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";

// Fixed dev port so the existing API CORS origin (GEMETRO_ALLOWED_ORIGINS=http://localhost:5500) works.
export default defineConfig({
  plugins: [react()],
  server: {
    port: 5500,
    strictPort: true,
  },
  test: {
    environment: "jsdom",
    setupFiles: ["./tests/setup.js"],
    globals: false,
    exclude: ["**/node_modules/**"],
  },
});
