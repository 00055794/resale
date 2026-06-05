import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";

export default defineConfig({
  plugins: [react()],
  server: { port: 5173 },
  build: { sourcemap: true, target: "es2022" },
  test: { environment: "jsdom", globals: true, setupFiles: ["./src/test/setup.ts"] }
});
