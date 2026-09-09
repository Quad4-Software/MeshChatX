<!-- SPDX-License-Identifier: 0BSD -->

<template>
    <div class="flex flex-col flex-1 overflow-hidden min-w-0 bg-sem-canvas">
        <ToolsPageHeader
            icon="translate"
            :title="$t('translator.title')"
            :description="$t('translator.description')"
            accent="indigo"
        />
        <div
            class="flex-1 overflow-y-auto w-full px-4 md:px-5 lg:px-8 py-6 pb-[max(1.5rem,env(safe-area-inset-bottom))]"
        >
            <div class="space-y-5 w-full max-w-4xl mx-auto">
                <div class="glass-card space-y-4">
                    <div class="text-sm font-semibold text-gray-800 dark:text-gray-200">
                        {{ $t("translator.pack_library") }}
                    </div>
                    <p class="text-sm text-sem-fg-muted">
                        {{ $t("translator.pack_library_description") }}
                    </p>
                    <div class="flex flex-wrap items-center gap-2">
                        <input
                            ref="pack-file-input"
                            type="file"
                            accept=".zip,.tar,.tar.gz,.tgz"
                            class="hidden"
                            @change="onPackFileSelected"
                        />
                        <button type="button" class="primary-chip text-xs px-3.5 py-2" @click="selectPackFile">
                            {{ $t("translator.import_pack") }}
                        </button>
                        <span v-if="isImporting" class="text-xs text-sem-fg-muted">{{ $t("translator.importing") }}</span>
                    </div>
                    <div v-if="packs.length" class="space-y-2">
                        <div
                            v-for="pack in packs"
                            :key="pack.pair"
                            class="flex items-center justify-between p-2.5 rounded-lg bg-sem-surface/60 border border-sem-border"
                        >
                            <div>
                                <div class="text-sm font-medium text-sem-fg">
                                    {{ packLabel(pack) }}
                                </div>
                                <div class="text-xs text-sem-fg-muted">
                                    {{ $t("translator.pair_code", { pair: pack.pair.toUpperCase() }) }}
                                    ·
                                    {{ $t("translator.size_kb", { size: Math.ceil(pack.size / 1024) }) }}
                                </div>
                            </div>
                            <button
                                type="button"
                                class="text-xs text-sem-danger hover:underline"
                                @click="removePack(pack.pair)"
                            >
                                {{ $t("translator.remove") }}
                            </button>
                        </div>
                    </div>
                    <div v-else class="text-sm text-sem-warning">
                        {{ $t("translator.no_packs") }}
                    </div>
                </div>

                <div class="glass-card space-y-4">
                    <div class="flex flex-col sm:flex-row gap-3 items-stretch sm:items-end">
                        <div class="flex-1">
                            <label class="glass-label mb-2">{{ $t("translator.source_language") }}</label>
                            <select v-model="sourceLang" class="input-field w-full">
                                <option v-for="opt in sourceOptions" :key="opt.value" :value="opt.value">
                                    {{ opt.label }}
                                </option>
                            </select>
                        </div>
                        <button
                            type="button"
                            class="p-2 rounded-lg border border-sem-border bg-sem-surface text-sem-fg hover:bg-sem-surface-muted"
                            :title="$t('translator.swap_languages')"
                            @click="swapLanguages"
                        >
                            <MaterialDesignIcon icon-name="swap-horizontal" class="size-5" />
                        </button>
                        <div class="flex-1">
                            <label class="glass-label mb-2">{{ $t("translator.target_language") }}</label>
                            <select v-model="targetLang" class="input-field w-full">
                                <option v-for="opt in targetOptions" :key="opt.value" :value="opt.value">
                                    {{ opt.label }}
                                </option>
                            </select>
                        </div>
                    </div>

                    <div>
                        <label class="glass-label mb-2">{{ $t("translator.input_text") }}</label>
                        <textarea
                            v-model="inputText"
                            rows="5"
                            class="input-field w-full resize-y"
                            :placeholder="$t('translator.input_placeholder')"
                        />
                    </div>

                    <div class="flex flex-wrap items-center gap-2">
                        <button
                            type="button"
                            class="primary-chip px-4 py-2"
                            :disabled="!canTranslate || isTranslating"
                            @click="runTranslate"
                        >
                            <span v-if="isTranslating" class="flex items-center gap-2">
                                <MaterialDesignIcon icon-name="loading" class="size-4 animate-spin" />
                                {{ $t("translator.translating") }}
                            </span>
                            <span v-else>{{ $t("translator.translate") }}</span>
                        </button>
                        <button
                            type="button"
                            class="secondary-chip px-3.5 py-2"
                            :disabled="!inputText"
                            @click="inputText = ''; outputText = ''; error = null"
                        >
                            {{ $t("translator.clear") }}
                        </button>
                        <button
                            v-if="outputText"
                            type="button"
                            class="secondary-chip px-3.5 py-2"
                            @click="copyOutput"
                        >
                            {{ $t("translator.copy") }}
                        </button>
                    </div>

                    <div v-if="error" class="p-3 rounded-lg bg-sem-danger/10 text-sm text-sem-danger">
                        {{ error }}
                    </div>

                    <div v-if="outputText" class="space-y-2">
                        <label class="glass-label">{{ $t("translator.output_text") }}</label>
                        <div class="p-3 rounded-lg bg-sem-surface/60 border border-sem-border whitespace-pre-wrap text-sm text-sem-fg">
                            {{ outputText }}
                        </div>
                    </div>
                </div>
            </div>
        </div>
    </div>
</template>

<script>
import MaterialDesignIcon from "../MaterialDesignIcon.vue";
import ToolsPageHeader from "../tools/ToolsPageHeader.vue";
import * as TranslationService from "../../js/TranslationService.js";
import { copyTextToClipboard } from "../../js/clipboardUtils.js";

export default {
    name: "TranslatorPage",
    components: { MaterialDesignIcon, ToolsPageHeader },
    data() {
        return {
            packs: [],
            sourceLang: "",
            targetLang: "",
            inputText: "",
            outputText: "",
            isTranslating: false,
            isImporting: false,
            error: null,
        };
    },
    computed: {
        canTranslate() {
            return (
                this.inputText.trim() &&
                this.sourceLang &&
                this.targetLang &&
                this.sourceLang !== this.targetLang
            );
        },
        installedPairs() {
            return this.packs.map((p) => ({
                pair: p.pair,
                from: p.from || p.pair.slice(0, 2),
                to: p.to || p.pair.slice(2, 4),
            }));
        },
        languageOptions() {
            const userLocale = (navigator.language || "en").slice(0, 2);
            let displayNames;
            try {
                displayNames = new Intl.DisplayNames([userLocale], { type: "language" });
            } catch {
                displayNames = { of: (code) => code };
            }
            const codes = new Set();
            for (const p of this.installedPairs) {
                codes.add(p.from);
                codes.add(p.to);
            }
            const opts = Array.from(codes).map((code) => ({
                value: code,
                label: displayNames.of(code) || code,
            }));
            return opts.sort((a, b) => a.label.localeCompare(b.label, undefined, { sensitivity: "base" }));
        },
        sourceOptions() {
            return this.languageOptions;
        },
        targetOptions() {
            return this.languageOptions;
        },
    },
    mounted() {
        this.loadPacks();
    },
    methods: {
        async loadPacks() {
            try {
                this.packs = await TranslationService.listPacks();
                this.guessDefaultLanguages();
            } catch (e) {
                console.error("Failed to load packs:", e);
                this.error = this.$t("translator.load_packs_failed");
            }
        },
        guessDefaultLanguages() {
            if (!this.packs.length) {
                return;
            }
            const first = this.packs[0];
            this.sourceLang = first.from || first.pair.slice(0, 2);
            this.targetLang = first.to || first.pair.slice(2, 4);
            if (this.sourceLang === this.targetLang) {
                const diff = this.packs.find((p) => (p.from || p.pair.slice(0, 2)) !== (p.to || p.pair.slice(2, 4)));
                if (diff) {
                    this.sourceLang = diff.from || diff.pair.slice(0, 2);
                    this.targetLang = diff.to || diff.pair.slice(2, 4);
                }
            }
        },
        packLabel(pack) {
            const userLocale = (navigator.language || "en").slice(0, 2);
            let displayNames;
            try {
                displayNames = new Intl.DisplayNames([userLocale], { type: "language" });
            } catch {
                displayNames = { of: (code) => code };
            }
            const from = pack.from || pack.pair.slice(0, 2);
            const to = pack.to || pack.pair.slice(2, 4);
            return `${displayNames.of(from) || from} → ${displayNames.of(to) || to}`;
        },
        selectPackFile() {
            this.$refs["pack-file-input"].click();
        },
        async onPackFileSelected(event) {
            const file = event.target.files?.[0];
            if (!file) {
                return;
            }
            this.isImporting = true;
            this.error = null;
            try {
                await TranslationService.importPack(file);
                await this.loadPacks();
            } catch (e) {
                console.error("Pack import failed:", e);
                this.error = String(e.message || e);
            } finally {
                this.isImporting = false;
                event.target.value = "";
            }
        },
        async removePack(pair) {
            try {
                await TranslationService.removePack(pair);
                await this.loadPacks();
            } catch (e) {
                console.error("Pack removal failed:", e);
                this.error = String(e.message || e);
            }
        },
        swapLanguages() {
            [this.sourceLang, this.targetLang] = [this.targetLang, this.sourceLang];
        },
        async runTranslate() {
            if (!this.canTranslate) {
                return;
            }
            this.isTranslating = true;
            this.error = null;
            this.outputText = "";
            try {
                const result = await TranslationService.translate({
                    from: this.sourceLang,
                    to: this.targetLang,
                    text: this.inputText,
                });
                this.outputText = result?.target?.text || "";
            } catch (e) {
                console.error("Translation failed:", e);
                this.error = this.$t("translator.translation_failed");
            } finally {
                this.isTranslating = false;
            }
        },
        async copyOutput() {
            try {
                await copyTextToClipboard(this.outputText);
            } catch (e) {
                console.error("Copy failed:", e);
            }
        },
    },
};
</script>
