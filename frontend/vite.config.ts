import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";

// Proxy /api to the FastAPI backend so the app uses relative URLs (no CORS in
// dev, and video <src> range requests stream through the same origin).
export default defineConfig({
  plugins: [react()],
  server: {
    port: 5173,
    proxy: {
      "/api": {
        target: process.env.ADAPTIVE_BACKEND_URL || "http://localhost:8000",
        changeOrigin: true,
      },
    },
  },
});
