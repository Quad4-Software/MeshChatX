/** @type {import("knip").KnipConfig} */
export default {
    entry: [
        "meshchatx/src/frontend/index.html",
        "meshchatx/src/frontend/nomad-crash-tab.html",
        "electron/preload.js",
        "meshchatx/src/frontend/public/service-worker.js",
        "scripts/**/*.{js,mjs,cjs}",
        "tests/**/*.{js,cjs,mjs}",
    ],
    project: [
        "meshchatx/src/frontend/**/*.{js,ts,vue,svelte}",
        "electron/**/*.{js,ts}",
        "scripts/**/*.{js,mjs,cjs}",
        "tests/**/*.{js,cjs,mjs}",
    ],
    ignore: ["meshchatx/src/frontend/public/**", "electron/assets/**", "**/*.worklet.js"],
    ignoreDependencies: ["@tailwindcss/forms", "emoji-picker-element-data"],
    ignoreIssues: {
        "meshchatx/src/frontend/js/reticulumPathfinding.js": ["unlisted"],
        "meshchatx/src/frontend/js/reticulumPathfinding.ts": ["unlisted"],
    },
    rules: {
        binaries: "off",
        dependencies: "error",
        devDependencies: "off",
        duplicates: "error",
        exports: "off",
        files: "off",
        types: "off",
        unlisted: "error",
        unresolved: "off",
    },
};
