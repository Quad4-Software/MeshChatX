/** @type {import("knip").KnipConfig} */
export default {
    entry: [
        "meshchatx/src/frontend/index.html",
        "electron/main.js",
        "electron/main-legacy.js",
        "electron/preload.js",
        "meshchatx/src/frontend/public/service-worker.js",
        "scripts/**/*.{js,mjs,cjs}",
        "tests/**/*.{js,cjs,mjs}",
    ],
    project: [
        "meshchatx/src/frontend/**/*.{js,vue}",
        "electron/**/*.js",
        "scripts/**/*.{js,mjs,cjs}",
        "tests/**/*.{js,cjs,mjs}",
    ],
    ignore: ["meshchatx/src/frontend/public/**", "electron/assets/**", "**/*.worklet.js"],
    ignoreDependencies: ["@electron/fuses", "@tailwindcss/forms", "electron-builder-squirrel-windows"],
    ignoreBinaries: ["python3"],
    ignoreIssues: {
        "meshchatx/src/frontend/js/reticulumPathfinding.js": ["unlisted"],
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
