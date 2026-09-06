import js from "@eslint/js";
import pluginSvelte from "eslint-plugin-svelte";
import pluginPrettier from "eslint-plugin-prettier/recommended";
import pluginSecurity from "eslint-plugin-security";
import globals from "globals";
import tseslint from "typescript-eslint";
import svelteConfig from "./svelte.config.mjs";

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
            "**/electron/assets/**",
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
            "**/*.asar",
            "**/*.asar.unpacked/**",
            "**/*.wasm",
            "**/*.proto",
            "**/tests/**",
            "**/temp-tests/**",
            "**/.pnpm-store/**",
            "**/packaging/**",
        ],
    },
    {
        files: ["**/*.{js,mjs,cjs}"],
        languageOptions: {
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
    js.configs.recommended,
    ...pluginSvelte.configs["flat/recommended"],
    pluginPrettier,
    pluginSecurity.configs.recommended,
    {
        files: ["**/*.{js,mjs,cjs}"],
        rules: {
            "no-unused-vars": "warn",
            "no-console": "off",
            "security/detect-object-injection": "off",
            "security/detect-non-literal-fs-filename": "off",
        },
    },
    {
        files: ["**/*.ts", "**/*.mts", "**/*.cts"],
        languageOptions: {
            globals: {
                ...globals.browser,
                ...globals.node,
            },
            parser: tseslint.parser,
        },
        plugins: {
            "@typescript-eslint": tseslint.plugin,
        },
        rules: {
            "no-undef": "off",
            "no-unused-vars": "off",
            "@typescript-eslint/no-unused-vars": [
                "warn",
                {
                    argsIgnorePattern: "^_",
                    varsIgnorePattern: "^_",
                    caughtErrorsIgnorePattern: "^_",
                },
            ],
            "no-console": "off",
            "security/detect-object-injection": "off",
        },
    },
    {
        files: ["**/*.svelte", "**/*.svelte.ts", "**/*.svelte.js"],
        languageOptions: {
            globals: {
                ...globals.browser,
            },
            parserOptions: {
                parser: tseslint.parser,
                extraFileExtensions: [".svelte"],
                svelteConfig,
            },
        },
        plugins: {
            "@typescript-eslint": tseslint.plugin,
        },
        rules: {
            "no-undef": "off",
            "no-unused-vars": "off",
            "@typescript-eslint/no-unused-vars": [
                "warn",
                {
                    argsIgnorePattern: "^_",
                    varsIgnorePattern: "^_",
                    caughtErrorsIgnorePattern: "^_",
                },
            ],
            "no-console": "off",
            "security/detect-object-injection": "off",
            "svelte/prefer-svelte-reactivity": "off",
        },
    },
    {
        files: ["meshchatx/src/frontend/js/**/*.{js,mjs,ts}"],
        rules: {
            "no-restricted-imports": [
                "error",
                {
                    patterns: [
                        {
                            group: ["**/components/**", "**/ui/svelte/**", "**/features/**", "**/*.svelte"],
                            message: "Kernel js/ must stay framework-free. Import only other kernel modules.",
                        },
                    ],
                },
            ],
        },
    },
];
