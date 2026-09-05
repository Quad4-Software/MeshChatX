<!-- SPDX-License-Identifier: 0BSD -->

<script lang="ts">
    import { onMount } from "svelte";
    import MaterialDesignIcon from "../../ui/svelte/MaterialDesignIcon.svelte";
    import ToolsPageHeader from "../../ui/svelte/ToolsPageHeader.svelte";
    import ToastUtils from "../../js/ToastUtils.js";
    import { t } from "../../js/i18n.js";
    import { DEFAULT_LIBRETRANSLATE_URL, LIBRE_PERSIST_DEBOUNCE_MS } from "./lib/constants.js";
    import {
        canTranslate,
        computeSwappedLanguages,
        computeSyncedMode,
        filterLanguagesByMode,
        hasArgosLanguages,
    } from "./lib/translatorEngine.js";
    import type {
        TranslationMode,
        TranslationResult,
        TranslatorConfig,
        TranslatorLanguage,
        TranslatorLanguagesResponse,
    } from "./lib/types.js";
    import TranslatorArgosGuidance from "./components/TranslatorArgosGuidance.svelte";
    import TranslatorBackendsCard from "./components/TranslatorBackendsCard.svelte";
    import TranslatorLanguagesList from "./components/TranslatorLanguagesList.svelte";

    let config = $state<TranslatorConfig | null>(null);
    let languages = $state<TranslatorLanguage[]>([]);
    let sourceLang = $state("");
    let targetLang = $state("");
    let inputText = $state("");
    let translationMode = $state<TranslationMode>("argos");
    let libretranslateUrl = $state(DEFAULT_LIBRETRANSLATE_URL);
    let libretranslateApiKey = $state("");
    let hasArgos = $state(false);
    let libreClientAvailable = $state(false);
    let libretranslateReachable = $state(false);
    let isTranslating = $state(false);
    let isInstallingLanguages = $state(false);
    let translationResult = $state<TranslationResult | null>(null);
    let error = $state<string | null>(null);

    let debouncedLibrePersistTimer: ReturnType<typeof setTimeout> | null = null;

    const filteredLanguages = $derived(filterLanguagesByMode(languages, translationMode));
    const hasArgosLangs = $derived(hasArgosLanguages(languages));
    const canTranslateNow = $derived(
        canTranslate({
            config,
            mode: translationMode,
            inputText,
            sourceLang,
            targetLang,
        })
    );

    function syncTranslationModeFromBackends(): void {
        const nextMode = computeSyncedMode({
            currentMode: translationMode,
            hasArgos,
            libreClientAvailable,
        });

        if (nextMode !== translationMode) {
            translationMode = nextMode;
            if (nextMode === "libretranslate" && !sourceLang) {
                sourceLang = "auto";
            } else if (nextMode === "argos" && sourceLang === "auto") {
                sourceLang = "";
            }
        } else if (nextMode === "libretranslate" && !sourceLang) {
            sourceLang = "auto";
        }
    }

    function onModeChange(mode: TranslationMode): void {
        translationMode = mode;
        if (mode === "libretranslate" && !sourceLang) {
            sourceLang = "auto";
        } else if (mode === "argos" && sourceLang === "auto") {
            sourceLang = "";
        }
        void loadLanguages();
    }

    async function getConfig(): Promise<void> {
        try {
            const response = await window.api.get("/api/v1/config");
            const data = response.data as { config?: TranslatorConfig } | undefined;
            config = data?.config ?? null;
            if (config?.libretranslate_url) {
                libretranslateUrl = String(config.libretranslate_url);
            }
            libretranslateApiKey = (config?.libretranslate_api_key as string) || "";
            await loadLanguages();
        } catch (e) {
            console.error(e);
        }
    }

    async function loadLanguages(): Promise<void> {
        if (!config) {
            return;
        }
        try {
            const params: Record<string, string> = {};
            if (translationMode === "libretranslate" && libretranslateUrl) {
                params.libretranslate_url = libretranslateUrl;
            }
            const response = await window.api.get("/api/v1/translator/languages", { params });
            const data = (response.data as TranslatorLanguagesResponse) ?? {};
            languages = Array.isArray(data.languages) ? data.languages : [];
            hasArgos = Boolean(data.has_argos);
            libreClientAvailable = Boolean(data.libre_client_available);
            libretranslateReachable = Boolean(data.libretranslate_reachable);
            syncTranslationModeFromBackends();
        } catch (e) {
            console.error(e);
            void ToastUtils.error(t("translator.failed_load_languages"));
        }
    }

    async function onArgosEnabledChange(value: boolean): Promise<void> {
        if (config) {
            config.translator_argos_enabled = value;
        }
        try {
            await window.api.patch("/api/v1/config", { translator_argos_enabled: value });
        } catch (e) {
            console.error(e);
        }
    }

    async function onLibreEnabledChange(value: boolean): Promise<void> {
        if (config) {
            config.translator_libretranslate_enabled = value;
        }
        try {
            await window.api.patch("/api/v1/config", { translator_libretranslate_enabled: value });
        } catch (e) {
            console.error(e);
        }
    }

    function scheduleDebouncedLibrePersist(): void {
        if (debouncedLibrePersistTimer) {
            clearTimeout(debouncedLibrePersistTimer);
        }
        debouncedLibrePersistTimer = setTimeout(() => {
            void persistLibreClientSettings();
        }, LIBRE_PERSIST_DEBOUNCE_MS);
    }

    async function persistLibreClientSettings(): Promise<void> {
        if (!config) {
            return;
        }
        const urlTarget = libretranslateUrl || "";
        const keyTarget = (libretranslateApiKey || "").trim();
        const urlEq = urlTarget === (config.libretranslate_url || "");
        const cfgKeyRaw = config.libretranslate_api_key;
        const cfgKey = cfgKeyRaw == null ? "" : String(cfgKeyRaw).trim();
        const keyEq = keyTarget === cfgKey;

        if (urlEq && keyEq) {
            return;
        }
        const patch: Record<string, unknown> = {};
        if (!urlEq) {
            patch.libretranslate_url = libretranslateUrl;
        }
        if (!keyEq) {
            patch.libretranslate_api_key = keyTarget === "" ? null : keyTarget;
        }
        try {
            await window.api.patch("/api/v1/config", patch);
            if (!urlEq) {
                config.libretranslate_url = libretranslateUrl;
            }
            if (!keyEq) {
                config.libretranslate_api_key = keyTarget === "" ? null : keyTarget;
            }
        } catch (e) {
            console.error(e);
        }
    }

    function onUrlChange(url: string): void {
        libretranslateUrl = url;
        scheduleDebouncedLibrePersist();
        if (translationMode === "libretranslate") {
            void loadLanguages();
        }
    }

    function onApiKeyChange(key: string): void {
        libretranslateApiKey = key;
        scheduleDebouncedLibrePersist();
        if (translationMode === "libretranslate") {
            void loadLanguages();
        }
    }

    function copyToClipboard(text: string): void {
        void navigator.clipboard.writeText(text);
        ToastUtils.success(t("common.copied"));
    }

    async function translateText(): Promise<void> {
        if (!canTranslateNow || isTranslating) {
            return;
        }
        if (!sourceLang || !targetLang) {
            error = t("translator.select_languages_warning");
            return;
        }
        if (translationMode === "argos" && sourceLang === "auto") {
            error = t("translator.auto_detect_not_supported");
            return;
        }

        isTranslating = true;
        error = null;
        translationResult = null;

        try {
            const payload: Record<string, unknown> = {
                text: inputText,
                source_lang: sourceLang,
                target_lang: targetLang,
                use_argos: translationMode === "argos",
            };
            if (translationMode === "libretranslate" && libretranslateUrl) {
                payload.libretranslate_url = libretranslateUrl;
            }
            const keyTrimmed = (libretranslateApiKey || "").trim();
            if (translationMode === "libretranslate" && keyTrimmed) {
                payload.libretranslate_api_key = keyTrimmed;
            }
            const response = await window.api.post("/api/v1/translator/translate", payload);
            translationResult = (response.data as TranslationResult) ?? null;
            if (translationResult?.source_lang === "auto") {
                sourceLang = translationResult.source_lang;
            }
        } catch (e: unknown) {
            console.error(e);
            const errObj = e as { response?: { data?: { message?: string } } };
            error = errObj.response?.data?.message || t("translator.failed_translate");
        } finally {
            isTranslating = false;
        }
    }

    function swapLanguages(): void {
        if (!targetLang) {
            return;
        }
        const res = computeSwappedLanguages({
            mode: translationMode,
            currentSource: sourceLang,
            currentTarget: targetLang,
            resultSource: translationResult?.source_lang,
            resultText: translationResult?.translated_text,
        });

        sourceLang = res.newSource;
        targetLang = res.newTarget;
        if (res.newInputText !== undefined) {
            inputText = res.newInputText;
            translationResult = null;
        }
    }

    function clearText(): void {
        inputText = "";
        translationResult = null;
        error = null;
    }

    async function installLanguages(packageName: string): Promise<void> {
        if (isInstallingLanguages) {
            return;
        }
        isInstallingLanguages = true;
        error = null;

        try {
            const response = await window.api.post("/api/v1/translator/install-languages", {
                package: packageName,
            });
            const data = response.data as { message?: string } | undefined;
            ToastUtils.success(data?.message || "Languages installed successfully");
            await loadLanguages();
        } catch (e: unknown) {
            console.error(e);
            const errObj = e as { response?: { data?: { message?: string } } };
            error =
                errObj.response?.data?.message ||
                "Failed to install languages. Make sure argospm is available in PATH.";
            ToastUtils.error(error);
        } finally {
            isInstallingLanguages = false;
        }
    }

    onMount(() => {
        void getConfig();
        return () => {
            if (debouncedLibrePersistTimer) {
                clearTimeout(debouncedLibrePersistTimer);
            }
        };
    });
</script>

<div class="flex flex-col flex-1 overflow-hidden min-w-0 bg-sem-canvas" data-testid="translator-page">
    <ToolsPageHeader
        icon="translate"
        title={t("tools.translator.title")}
        description={t("tools.translator.description")}
        accent="indigo"
    />
    <div class="flex-1 overflow-y-auto w-full px-4 md:px-5 lg:px-8 py-6 pb-[max(1.5rem,env(safe-area-inset-bottom))]">
        <div class="space-y-4 w-full max-w-4xl mx-auto">
            <div class="glass-card space-y-5">
                <TranslatorBackendsCard
                    {config}
                    {hasArgos}
                    {libreClientAvailable}
                    {libretranslateReachable}
                    {translationMode}
                    {libretranslateUrl}
                    {libretranslateApiKey}
                    {onArgosEnabledChange}
                    {onLibreEnabledChange}
                    {onModeChange}
                    {onUrlChange}
                    {onApiKeyChange}
                />

                <div class="grid lg:grid-cols-2 gap-4">
                    <div>
                        <label class="glass-label" for="translator-source-lang">
                            {t("translator.source_language")}
                        </label>
                        <select id="translator-source-lang" bind:value={sourceLang} class="input-field">
                            {#if translationMode === "libretranslate"}
                                <option value="auto">{t("translator.auto_detect")}</option>
                            {/if}
                            {#each filteredLanguages as lang (`src-${lang.code}`)}
                                <option value={lang.code}>
                                    {lang.name} ({lang.code})
                                </option>
                            {/each}
                        </select>
                    </div>
                    <div>
                        <label class="glass-label" for="translator-target-lang">
                            {t("translator.target_language")}
                        </label>
                        <select id="translator-target-lang" bind:value={targetLang} class="input-field">
                            <option value="">{t("translator.select_target_language")}</option>
                            {#each filteredLanguages as lang (`tgt-${lang.code}`)}
                                <option value={lang.code}>
                                    {lang.name} ({lang.code})
                                </option>
                            {/each}
                        </select>
                    </div>
                </div>

                {#if translationMode === "argos"}
                    <TranslatorArgosGuidance
                        {hasArgos}
                        hasArgosLanguages={hasArgosLangs}
                        {isInstallingLanguages}
                        onCopy={copyToClipboard}
                        onInstallLanguages={installLanguages}
                    />
                {/if}

                <div>
                    <label class="glass-label" for="translator-input-text">
                        {t("translator.text_to_translate")}
                    </label>
                    <textarea
                        id="translator-input-text"
                        bind:value={inputText}
                        rows={6}
                        placeholder={t("translator.enter_text_placeholder")}
                        class="input-field"
                        disabled={isTranslating}></textarea>
                </div>

                <div class="flex gap-2">
                    <button
                        type="button"
                        class="primary-chip focus-ring-sem px-4 py-2 text-sm inline-flex items-center"
                        disabled={!canTranslateNow || isTranslating}
                        title={!canTranslateNow ? t("translator.enter_text_placeholder") : t("translator.translate")}
                        onclick={translateText}
                    >
                        {#if isTranslating}
                            <span
                                class="inline-block w-4 h-4 border-2 border-white border-t-transparent rounded-full animate-spin mr-2"
                            ></span>
                            Translating...
                        {:else}
                            <MaterialDesignIcon iconName="translate" class="w-4 h-4 mr-2" />
                            {t("translator.translate")}
                        {/if}
                    </button>
                    <button
                        type="button"
                        class="secondary-chip focus-ring-sem px-4 py-2 text-sm inline-flex items-center gap-1.5"
                        disabled={!targetLang || isTranslating}
                        onclick={swapLanguages}
                    >
                        <MaterialDesignIcon iconName="swap-horizontal" class="w-4 h-4" />
                        {t("translator.swap")}
                    </button>
                    <button
                        type="button"
                        class="secondary-chip focus-ring-sem px-4 py-2 text-sm inline-flex items-center gap-1.5"
                        onclick={clearText}
                    >
                        <MaterialDesignIcon iconName="broom" class="w-4 h-4" />
                        {t("translator.clear")}
                    </button>
                </div>

                {#if translationResult}
                    <div class="space-y-2">
                        <div class="flex items-center justify-between">
                            <div class="text-sm font-semibold text-sem-fg">
                                {t("translator.translation")}
                            </div>
                            <div class="text-xs text-sem-fg-muted">
                                {t("translator.source")}: {translationResult.source}
                            </div>
                        </div>
                        <div class="p-4 rounded-lg bg-gray-50 dark:bg-zinc-800 border border-sem-border">
                            <div class="text-sem-fg whitespace-pre-wrap">
                                {translationResult.translated_text}
                            </div>
                        </div>
                        <div class="text-xs text-sem-fg-muted">
                            {t("translator.detected")}: {translationResult.source_lang} &rarr; {translationResult.target_lang}
                        </div>
                    </div>
                {/if}

                {#if error}
                    <div class="p-3 rounded-lg bg-red-50 dark:bg-red-900/20 text-red-700 dark:text-red-300">
                        {error}
                    </div>
                {/if}
            </div>

            <TranslatorLanguagesList
                languages={filteredLanguages}
                {translationMode}
                {hasArgos}
                {isInstallingLanguages}
                onLoadLanguages={loadLanguages}
                onInstallLanguages={installLanguages}
            />
        </div>
    </div>
</div>
