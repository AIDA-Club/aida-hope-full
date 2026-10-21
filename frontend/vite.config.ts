/// <reference types="vitest" />
import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";

// The Python API (api/main.py) runs on port 8000; the dev server proxies /api to it,
// so the session cookie stays same-origin.
const API = process.env.AIDA_API_URL ?? "http://127.0.0.1:8000";

export default defineConfig({
  plugins: [react()],
  server: { port: 5173, strictPort: true, proxy: { "/api": { target: API, changeOrigin: false } } },
  preview: { port: 5173, strictPort: true, proxy: { "/api": { target: API, changeOrigin: false } } },
  test: { environment: "jsdom", include: ["src/**/*.test.{ts,tsx}"] },
});
