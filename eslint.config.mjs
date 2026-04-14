import js from "@eslint/js";
import pluginVue from "eslint-plugin-vue";
import pluginPrettier from "eslint-plugin-prettier/recommended";
import pluginSecurity from "eslint-plugin-security";
import globals from "globals";

export default [
    {
        ignores: [
            "**/node_modules/**",
            "**/dist/**",
            "**/build/**",
            "**/out/**",
            "**/android/**",
            "**/MagicMock/**",
            "**/reticulum_meshchatx.egg-info/**",
            "**/meshchat-config/**",
            "**/screenshots/**",
            "**/electron/assets/**",
            "**/meshchatx/public/**",
            "**/meshchatx/src/frontend/public/**",
            "**/storage/**",
            "**/__pycache__/**",
            "**/.venv/**",
            "**/*.min.js",
            "**/pnpm-lock.yaml",
            "**/poetry.lock",
            "**/linux-unpacked/**",
            "**/win-unpacked/**",
            "**/mac-unpacked/**",
            "**/*.asar",
            "**/*.asar.unpacked/**",
            "**/*.wasm",
            "**/*.proto",
            "**/tests/**",
            "**/.pnpm-store/**",
            "**/packaging/**",
        ],
    },
    {
        files: ["**/*.{js,mjs,cjs,vue}"],
        languageOptions: {
            globals: {
                ...globals.browser,
                ...globals.node,
                __APP_BUILD_TIME__: "readonly",
                axios: "readonly",
                Codec2Lib: "readonly",
                Codec2MicrophoneRecorder: "readonly",
            },
        },
    },
    js.configs.recommended,
    ...pluginVue.configs["flat/recommended"],
    pluginPrettier,
    pluginSecurity.configs.recommended,
    {
        files: ["**/*.{js,mjs,cjs,vue}"],
        rules: {
            "vue/multi-word-component-names": "off",
            "no-unused-vars": "warn",
            "no-console": "off",
            "security/detect-object-injection": "off",
            "security/detect-non-literal-fs-filename": "off",
        },
    },
];
