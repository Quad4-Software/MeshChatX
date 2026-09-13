<!-- SPDX-License-Identifier: 0BSD -->

<script lang="ts">
    import { onMount } from "svelte";
    import MaterialDesignIcon from "../../ui/svelte/MaterialDesignIcon.svelte";
    import ToolsPageHeader from "../../ui/svelte/ToolsPageHeader.svelte";
    import { t } from "../../js/i18n.js";
    import { copyTextToClipboard } from "../../js/clipboardUtils.js";
    import { getCurrentRoute } from "../../shell/hashRouter.js";
    import * as TranslationService from "../../js/TranslationService.js";
    import { PACK_FILE_ACCEPT } from "./lib/constants.js";
    import { canTranslate, guessDefaultLanguages, languageOptions, packLabel } from "./lib/translatorEngine.js";
    import type { TranslationPack } from "./lib/types.js";

    let packs = $state<TranslationPack[]>([]);
    let sourceLang = $state("");
    let targetLang = $state("");
    let inputText = $state("");
    let outputText = $state("");
    let isTranslating = $state(false);
    let isImporting = $state(false);
    let error = $state<string | null>(null);

    let packFileInput: HTMLInputElement | undefined = $state();

    const userLocale = (typeof navigator !== "undefined" && navigator.language) || "en";
    const sourceOptions = $derived(languageOptions(packs, userLocale));
    const targetOptions = $derived(languageOptions(packs, userLocale));
    const canTranslateNow = $derived(canTranslate(inputText, sourceLang, targetLang));

    async function loadPacks(): Promise<void> {
        try {
            packs = await TranslationService.listPacks();
            guessDefaults();
        } catch (e) {
            console.error("Failed to load packs:", e);
            error = t("translator.load_packs_failed");
        }
    }

    function guessDefaults(): void {
        if (sourceLang && targetLang) {
            return;
        }
        const next = guessDefaultLanguages(packs);
        if (!sourceLang) {
            sourceLang = next.source;
        }
        if (!targetLang) {
            targetLang = next.target;
        }
    }

    function selectPackFile(): void {
        packFileInput?.click();
    }

    async function onPackFileSelected(event: Event): Promise<void> {
        const input = event.currentTarget as HTMLInputElement;
        const file = input.files?.[0];
        if (!file) {
            return;
        }
        isImporting = true;
        error = null;
        try {
            await TranslationService.importPack(file);
            await loadPacks();
        } catch (e) {
            console.error("Pack import failed:", e);
            error = String((e as Error).message || e);
        } finally {
            isImporting = false;
            input.value = "";
        }
    }

    async function removePackEntry(pair: string): Promise<void> {
        try {
            await TranslationService.removePack(pair);
            await loadPacks();
        } catch (e) {
            console.error("Pack removal failed:", e);
            error = String((e as Error).message || e);
        }
    }

    function swapLanguages(): void {
        const prevSource = sourceLang;
        sourceLang = targetLang;
        targetLang = prevSource;
    }

    async function runTranslate(): Promise<void> {
        if (!canTranslateNow || isTranslating) {
            return;
        }
        isTranslating = true;
        error = null;
        outputText = "";
        try {
            const result = await TranslationService.translate({
                from: sourceLang,
                to: targetLang,
                text: inputText,
            });
            outputText = result?.target?.text || "";
        } catch (e) {
            console.error("Translation failed:", e);
            error = t("translator.translation_failed");
        } finally {
            isTranslating = false;
        }
    }

    function clearText(): void {
        inputText = "";
        outputText = "";
        error = null;
    }

    async function copyOutput(): Promise<void> {
        try {
            await copyTextToClipboard(outputText);
        } catch (e) {
            console.error("Copy failed:", e);
        }
    }

    onMount(() => {
        const query = getCurrentRoute()?.query || {};
        if (query.text) {
            inputText = String(query.text);
        }
        if (query.source && query.target) {
            sourceLang = String(query.source);
            targetLang = String(query.target);
        }
        void loadPacks();
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
        <div class="w-full max-w-4xl mx-auto">
            <div class="fused-panel">
                <div class="fused-section space-y-4">
                    <div class="text-sm font-semibold text-sem-fg">
                        {t("translator.pack_library")}
                    </div>
                    <p class="text-sm text-sem-fg-muted">
                        {t("translator.pack_library_description")}
                    </p>
                    <div class="flex flex-wrap items-center gap-2">
                        <input
                            bind:this={packFileInput}
                            type="file"
                            accept={PACK_FILE_ACCEPT}
                            class="hidden"
                            onchange={onPackFileSelected}
                        />
                        <button type="button" class="primary-chip text-xs px-3.5 py-2" onclick={selectPackFile}>
                            {t("translator.import_pack")}
                        </button>
                        {#if isImporting}
                            <span class="text-xs text-sem-fg-muted">{t("translator.importing")}</span>
                        {/if}
                    </div>
                    {#if packs.length}
                        <div class="space-y-2">
                            {#each packs as pack (pack.pair)}
                                <div
                                    class="flex items-center justify-between p-2.5 rounded-lg bg-sem-surface/60 border border-sem-border"
                                >
                                    <div>
                                        <div class="text-sm font-medium text-sem-fg">
                                            {packLabel(pack, userLocale)}
                                        </div>
                                        <div class="text-xs text-sem-fg-muted">
                                            {t("translator.pair_code", { pair: pack.pair.toUpperCase() })}
                                            ·
                                            {t("translator.size_kb", { size: Math.ceil(pack.size / 1024) })}
                                        </div>
                                    </div>
                                    <button
                                        type="button"
                                        class="text-xs text-sem-danger hover:underline"
                                        onclick={() => removePackEntry(pack.pair)}
                                    >
                                        {t("translator.remove")}
                                    </button>
                                </div>
                            {/each}
                        </div>
                    {:else}
                        <div class="text-sm text-sem-warning">
                            {t("translator.no_packs")}
                        </div>
                    {/if}
                </div>

                <div class="fused-section space-y-4">
                    <div class="flex flex-col sm:flex-row gap-3 items-stretch sm:items-end">
                        <div class="flex-1">
                            <label class="glass-label mb-2" for="translator-source-lang">
                                {t("translator.source_language")}
                            </label>
                            <select id="translator-source-lang" bind:value={sourceLang} class="input-field w-full">
                                {#each sourceOptions as opt (`src-${opt.value}`)}
                                    <option value={opt.value}>{opt.label}</option>
                                {/each}
                            </select>
                        </div>
                        <button
                            type="button"
                            class="p-2 rounded-lg border border-sem-border bg-sem-surface text-sem-fg hover:bg-sem-surface-muted"
                            title={t("translator.swap_languages")}
                            onclick={swapLanguages}
                        >
                            <MaterialDesignIcon iconName="swap-horizontal" class="size-5" />
                        </button>
                        <div class="flex-1">
                            <label class="glass-label mb-2" for="translator-target-lang">
                                {t("translator.target_language")}
                            </label>
                            <select id="translator-target-lang" bind:value={targetLang} class="input-field w-full">
                                {#each targetOptions as opt (`tgt-${opt.value}`)}
                                    <option value={opt.value}>{opt.label}</option>
                                {/each}
                            </select>
                        </div>
                    </div>

                    <div>
                        <label class="glass-label mb-2" for="translator-input-text">
                            {t("translator.input_text")}
                        </label>
                        <textarea
                            id="translator-input-text"
                            bind:value={inputText}
                            rows={5}
                            class="input-field w-full resize-y"
                            placeholder={t("translator.input_placeholder")}></textarea>
                    </div>

                    <div class="flex flex-wrap items-center gap-2">
                        <button
                            type="button"
                            class="primary-chip px-4 py-2"
                            disabled={!canTranslateNow || isTranslating}
                            onclick={runTranslate}
                        >
                            {#if isTranslating}
                                <span class="flex items-center gap-2">
                                    <MaterialDesignIcon iconName="loading" class="size-4 animate-spin" />
                                    {t("translator.translating")}
                                </span>
                            {:else}
                                {t("translator.translate")}
                            {/if}
                        </button>
                        <button
                            type="button"
                            class="secondary-chip px-3.5 py-2"
                            disabled={!inputText}
                            onclick={clearText}
                        >
                            {t("translator.clear")}
                        </button>
                        {#if outputText}
                            <button type="button" class="secondary-chip px-3.5 py-2" onclick={copyOutput}>
                                {t("translator.copy")}
                            </button>
                        {/if}
                    </div>

                    {#if error}
                        <div class="p-3 rounded-lg bg-sem-danger/10 text-sm text-sem-danger">
                            {error}
                        </div>
                    {/if}

                    {#if outputText}
                        <div class="space-y-2">
                            <div class="glass-label">{t("translator.output_text")}</div>
                            <div
                                class="p-3 rounded-lg bg-sem-surface/60 border border-sem-border whitespace-pre-wrap text-sm text-sem-fg"
                            >
                                {outputText}
                            </div>
                        </div>
                    {/if}
                </div>
            </div>
        </div>
    </div>
</div>
