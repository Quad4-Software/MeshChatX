import { defineConfig } from "vitest/config";
import vue from "@vitejs/plugin-vue";
import path from "path";

export default defineConfig({
    plugins: [vue()],
    test: {
        globals: true,
        environment: "jsdom",
        include: ["tests/frontend/**/*.{test,spec}.{js,ts,jsx,tsx}"],
    },
    resolve: {
        alias: {
            "@": path.resolve(__dirname, "meshchatx", "src", "frontend"),
        },
    },
});

