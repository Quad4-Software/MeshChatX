import js from "@eslint/js";
import pluginVue from "eslint-plugin-vue";
import pluginPrettier from "eslint-plugin-prettier/recommended";
import pluginSecurity from "eslint-plugin-security";
import globals from "globals";
import tsParser from "@typescript-eslint/parser";
import tsPlugin from "@typescript-eslint/eslint-plugin";

export default [
    {
        ignores: [
            "**/vendor/**",
            "**/node_modules/**",
            "**/dist/**",
            "**/build/**",
            "**/out/**",
            "**/android/**",
            "**/MagicMock/**",
            "**/reticulum_meshchatx.egg-info/**",
            "**/meshchat-config/**",
            "**/screenshots/**",
            "**/meshchatx/public/**",
            "**/meshchatx/src/frontend/public/**",
            "**/storage/**",
            "**/__pycache__/**",
            "**/.venv/**",
            "**/*.min.js",
            "**/pnpm-lock.yaml",
            "**/uv.lock",
            "**/linux-unpacked/**",
            "**/win-unpacked/**",
            "**/mac-unpacked/**",
            "desktop/bin/**",
            "**/.local/**",
            "**/*.asar",
            "**/*.asar.unpacked/**",
            "**/*.wasm",
            "**/*.proto",
            "**/tests/**",
            "**/temp-tests/**",
            "**/.pnpm-store/**",
            "**/packaging/**",
            "**/.tools/**",
        ],
    },
    {
        files: ["**/*.{js,mjs,cjs,ts,vue}"],
        languageOptions: {
            parserOptions: {
                parser: tsParser,
            },
            globals: {
                ...globals.browser,
                ...globals.node,
                __APP_BUILD_TIME__: "readonly",
                __MICRON_WASM_SRI_WASM__: "readonly",
                __MICRON_WASM_SRI_EXEC__: "readonly",
                __VISUALISER_WASM_SRI_WASM__: "readonly",
                __VISUALISER_WASM_SRI_EXEC__: "readonly",
                __GEO_WASM_SRI_WASM__: "readonly",
                __GEO_WASM_SRI_EXEC__: "readonly",
                axios: "readonly",
                Codec2Lib: "readonly",
                Codec2MicrophoneRecorder: "readonly",
            },
        },
    },
    {
        files: ["**/*.worklet.js"],
        languageOptions: {
            globals: {
                AudioWorkletProcessor: "readonly",
                registerProcessor: "readonly",
            },
        },
    },
    {
        files: ["**/*.ts"],
        languageOptions: {
            parser: tsParser,
        },
    },
    js.configs.recommended,
    ...pluginVue.configs["flat/recommended"],
    pluginPrettier,
    pluginSecurity.configs.recommended,
    {
        files: ["**/*.{js,mjs,cjs,ts,vue}"],
        rules: {
            "vue/multi-word-component-names": "off",
            "vue/no-v-html": "error",
            "no-unused-vars": "warn",
            "no-console": "off",
            "security/detect-object-injection": "off",
            "security/detect-non-literal-fs-filename": "off",
        },
    },
    {
        // After the catch-all rules block so the TS-aware rule wins for TS
        // sources: the base rule flags parameter names in TS type positions.
        files: ["**/*.ts", "**/*.vue"],
        plugins: {
            "@typescript-eslint": tsPlugin,
        },
        rules: {
            "no-unused-vars": "off",
            "@typescript-eslint/no-unused-vars": "warn",
        },
    },
];
