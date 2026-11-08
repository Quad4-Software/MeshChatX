// Copies the canonical Wails desktop bridge into the frontend public dir so
// vite serves it at /desktop-bridge.js (and index.html can load it early).
import { copyFileSync, mkdirSync } from "node:fs";
import { dirname, join } from "node:path";
import { fileURLToPath } from "node:url";

const root = join(dirname(fileURLToPath(import.meta.url)), "..");
const src = join(root, "desktop", "shell", "desktop-bridge.js");
const dest = join(root, "meshchatx", "src", "frontend", "public", "desktop-bridge.js");
mkdirSync(dirname(dest), { recursive: true });
copyFileSync(src, dest);
console.log("synced desktop-bridge.js ->", dest);
