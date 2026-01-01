import formsPlugin from "@tailwindcss/forms";

const frontendRoot = "./meshchatx/src/frontend";

/** @type {import('tailwindcss').Config} */
module.exports = {
    darkMode: "selector",
    content: [`${frontendRoot}/index.html`, `${frontendRoot}/**/*.{vue,js,ts,jsx,tsx,html}`],
    theme: {
        extend: {},
    },
    plugins: [formsPlugin],
};
