<!-- SPDX-License-Identifier: 0BSD -->

<script lang="ts">
    import { t } from "../../../js/i18n.js";
    import type { TranslationMode, TranslatorConfig } from "../lib/types.js";

    interface Props {
        config: TranslatorConfig | null;
        hasArgos: boolean;
        libreClientAvailable: boolean;
        libretranslateReachable: boolean;
        translationMode: TranslationMode;
        libretranslateUrl: string;
        libretranslateApiKey: string;
        onArgosEnabledChange: (value: boolean) => void;
        onLibreEnabledChange: (value: boolean) => void;
        onModeChange: (mode: TranslationMode) => void;
        onUrlChange: (url: string) => void;
        onApiKeyChange: (key: string) => void;
    }

    let {
        config,
        hasArgos,
        libreClientAvailable,
        libretranslateReachable,
        translationMode,
        libretranslateUrl,
        libretranslateApiKey,
        onArgosEnabledChange,
        onLibreEnabledChange,
        onModeChange,
        onUrlChange,
        onApiKeyChange,
    }: Props = $props();
</script>

{#if config}
    <div class="space-y-3">
        <div class="text-sm font-semibold text-gray-800 dark:text-gray-200">
            Translation backends
        </div>
        {#if hasArgos}
            <label
                class="flex items-start gap-3 cursor-pointer p-2 rounded-lg hover:bg-slate-100/80 dark:hover:bg-zinc-900/40"
            >
                <span class="relative inline-flex w-auto shrink-0 items-center">
                    <input
                        type="checkbox"
                        checked={Boolean(config.translator_argos_enabled)}
                        onchange={(e) => onArgosEnabledChange(e.currentTarget.checked)}
                        class="sr-only peer"
                    />
                    <span
                        class="relative h-6 w-11 shrink-0 bg-gray-200 peer-focus:outline-hidden peer-focus:ring-4 peer-focus:ring-blue-300 dark:peer-focus:ring-blue-800 rounded-full peer dark:bg-zinc-700 peer-checked:after:translate-x-full peer-checked:after:border-white after:content-[''] after:absolute after:top-[2px] after:left-[2px] after:bg-white after:border-gray-300 after:border after:rounded-full after:h-5 after:w-5 after:transition-all dark:border-gray-600 peer-checked:bg-blue-600 dark:peer-checked:bg-blue-600"
                    ></span>
                </span>
                <span>
                    <span class="block text-sm font-medium text-sem-fg">Argos Translate (local)</span>
                    <span class="text-xs text-sem-fg-muted"
                        >Local packages when Argos is installed. Load languages to refresh this list.</span
                    >
                </span>
            </label>
        {/if}
        {#if libreClientAvailable}
            <label
                class="flex items-start gap-3 cursor-pointer p-2 rounded-lg hover:bg-slate-100/80 dark:hover:bg-zinc-900/40"
            >
                <span class="relative inline-flex w-auto shrink-0 items-center">
                    <input
                        type="checkbox"
                        checked={Boolean(config.translator_libretranslate_enabled)}
                        onchange={(e) => onLibreEnabledChange(e.currentTarget.checked)}
                        class="sr-only peer"
                    />
                    <span
                        class="relative h-6 w-11 shrink-0 bg-gray-200 peer-focus:outline-hidden peer-focus:ring-4 peer-focus:ring-blue-300 dark:peer-focus:ring-blue-800 rounded-full peer dark:bg-zinc-700 peer-checked:after:translate-x-full peer-checked:after:border-white after:content-[''] after:absolute after:top-[2px] after:left-[2px] after:bg-white after:border-gray-300 after:border after:rounded-full after:h-5 after:w-5 after:transition-all dark:border-gray-600 peer-checked:bg-blue-600 dark:peer-checked:bg-blue-600"
                    ></span>
                </span>
                <span>
                    <span class="block text-sm font-medium text-sem-fg">LibreTranslate (HTTP)</span>
                    <span class="text-xs text-sem-fg-muted"
                        >Set the base URL below, then enable. Use Refresh languages after the server is up.</span
                    >
                </span>
            </label>
        {/if}
        {#if libreClientAvailable && !libretranslateReachable}
            <p class="text-xs text-amber-800/90 dark:text-amber-200/80 px-2 -mt-1">
                No response from the LibreTranslate URL yet. Check the address, start the service, and tap Refresh languages.
            </p>
        {/if}
    </div>
{/if}

<div class="border-b border-sem-border">
    {#if hasArgos || libreClientAvailable}
        <div class="flex -mb-px">
            {#if hasArgos}
                <button
                    type="button"
                    class="px-4 py-2 text-sm font-semibold border-b-2 transition-colors {translationMode === 'argos'
                        ? 'border-blue-500 text-blue-600 dark:border-blue-400 dark:text-blue-300'
                        : 'border-transparent text-sem-fg-muted hover:text-gray-700 dark:hover:text-gray-300'}"
                    onclick={() => onModeChange("argos")}
                >
                    {t("translator.argos_translate")}
                </button>
            {/if}
            {#if libreClientAvailable}
                <button
                    type="button"
                    class="px-4 py-2 text-sm font-semibold border-b-2 transition-colors {translationMode === 'libretranslate'
                        ? 'border-blue-500 text-blue-600 dark:border-blue-400 dark:text-blue-300'
                        : 'border-transparent text-sem-fg-muted hover:text-gray-700 dark:hover:text-gray-300'}"
                    onclick={() => onModeChange("libretranslate")}
                >
                    {t("translator.libretranslate")}
                </button>
            {/if}
        </div>
    {/if}
</div>

{#if translationMode === "libretranslate"}
    <div class="p-3 rounded-lg bg-gray-50 dark:bg-zinc-800/50 border border-gray-100 dark:border-zinc-700/50 space-y-3">
        <div>
            <label class="glass-label mb-2" for="translator-libre-url">
                {t("translator.api_server")}
            </label>
            <input
                id="translator-libre-url"
                value={libretranslateUrl}
                oninput={(e) => onUrlChange(e.currentTarget.value)}
                type="text"
                placeholder="http://localhost:5000"
                class="input-field"
            />
            <div class="text-xs text-sem-fg-muted mt-1">
                {t("translator.api_server_description")}
            </div>
        </div>
        <div>
            <label class="glass-label mb-2" for="translator-libre-key">
                {t("translator.api_key_optional")}
            </label>
            <input
                id="translator-libre-key"
                value={libretranslateApiKey}
                oninput={(e) => onApiKeyChange(e.currentTarget.value)}
                type="password"
                autocomplete="off"
                class="input-field"
                placeholder={t("translator.api_key_placeholder")}
            />
            <div class="text-xs text-sem-fg-muted mt-1">
                {t("translator.api_key_description")}
            </div>
        </div>
    </div>
{/if}
