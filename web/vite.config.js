import fs from "node:fs";
import path from "node:path";

import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";

const rootDir = path.resolve(import.meta.dirname, "..");
const configPath = process.env.PAPER_ANALYSIS_CONFIG_PATH || path.join(rootDir, "config", "app.json");
const settings = JSON.parse(fs.readFileSync(configPath, "utf-8"));
const frontend = settings.frontend;
const backend = settings.backend;
const apiBaseUrl = `http://${backend.host}:${backend.port}`;

export default defineConfig({
  plugins: [react()],
  server: {
    host: frontend.host,
    port: frontend.port,
    strictPort: true,
  },
  define: {
    __PAPER_ANALYSIS_API_BASE_URL__: JSON.stringify(apiBaseUrl),
  },
});
