import formsPlugin from "@tailwindcss/forms";

const frontendRoot = "./meshchatx/src/frontend";

/** @type {import('tailwindcss').Config} */
module.exports = {
    darkMode: "selector",
    content: [
        `${frontendRoot}/index.html`,
        `${frontendRoot}/**/*.{vue,js,ts,jsx,tsx,html}`,
        "./meshchatx/src/backend/markdown_renderer.py",
    ],
    theme: {
        extend: {},
    },
    plugins: [formsPlugin],
};
