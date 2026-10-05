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
            <div class="w-full max-w-4xl mx-auto">
                <div class="fused-panel">
                    <div class="fused-section space-y-4">
                        <div class="text-sm font-semibold text-sem-fg">
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
                            <span v-if="isImporting" class="text-xs text-sem-fg-muted">{{
                                $t("translator.importing")
                            }}</span>
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

                        <div class="border-t border-sem-border pt-3">
                            <div class="flex flex-wrap items-center gap-2">
                                <button
                                    type="button"
                                    class="secondary-chip text-xs px-3.5 py-2"
                                    :disabled="isLoadingCatalog"
                                    @click="toggleCatalog"
                                >
                                    {{ showCatalog ? $t("translator.hide_catalog") : $t("translator.show_catalog") }}
                                </button>
                                <button
                                    v-if="showCatalog && catalogPairs.length"
                                    type="button"
                                    class="secondary-chip text-xs px-3.5 py-2"
                                    :disabled="isDownloadingAll"
                                    @click="downloadAll"
                                >
                                    {{
                                        isDownloadingAll ? $t("translator.downloading") : $t("translator.download_all")
                                    }}
                                </button>
                                <input
                                    v-if="showCatalog && catalogPairs.length"
                                    v-model="catalogSearch"
                                    type="text"
                                    class="input-field flex-1 min-w-32 max-w-56 text-xs px-2.5 py-1.5"
                                    :placeholder="$t('translator.search_packs')"
                                />
                            </div>
                            <div v-if="catalogError" class="mt-2 text-xs text-sem-danger">
                                {{ catalogError }}
                            </div>
                            <div
                                v-if="showCatalog && filteredCatalog.length"
                                class="mt-2 grid gap-2 sm:grid-cols-2 lg:grid-cols-3"
                            >
                                <div
                                    v-for="group in filteredCatalog"
                                    :key="group.key"
                                    class="flex items-center justify-between p-2 rounded-lg bg-sem-surface/60 border border-sem-border"
                                >
                                    <div class="min-w-0">
                                        <div class="text-xs font-medium text-sem-fg truncate">
                                            {{ groupLabel(group) }}
                                        </div>
                                        <div class="text-[10px] text-sem-fg-muted">
                                            {{ group.architecture }} ·
                                            {{ $t("translator.size_kb", { size: Math.ceil(group.size / 1024) }) }}
                                        </div>
                                    </div>
                                    <button
                                        v-if="!isGroupInstalled(group)"
                                        type="button"
                                        class="text-xs text-sem-info hover:underline shrink-0 ml-2"
                                        :disabled="isGroupDownloading(group) || isDownloadingAll"
                                        @click="downloadGroup(group)"
                                    >
                                        {{
                                            isGroupDownloading(group)
                                                ? $t("translator.downloading")
                                                : $t("translator.download")
                                        }}
                                    </button>
                                    <span v-else class="text-xs text-sem-success shrink-0 ml-2">{{
                                        $t("translator.installed")
                                    }}</span>
                                </div>
                            </div>
                            <div
                                v-else-if="showCatalog && catalogPairs.length && !filteredCatalog.length"
                                class="mt-2 text-xs text-sem-fg-muted"
                            >
                                {{ $t("translator.no_search_results") }}
                            </div>
                            <div v-if="fetchError" class="mt-2 text-xs text-sem-danger">
                                {{ fetchError }}
                            </div>
                        </div>
                    </div>

                    <div class="fused-section space-y-4">
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
                                @click="
                                    inputText = '';
                                    outputText = '';
                                    error = null;
                                "
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
                            <div
                                class="p-3 rounded-lg bg-sem-surface/60 border border-sem-border whitespace-pre-wrap text-sm text-sem-fg"
                            >
                                {{ outputText }}
                            </div>
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
            showCatalog: false,
            catalogPairs: [],
            catalogError: null,
            isLoadingCatalog: false,
            downloadingPairs: {},
            isDownloadingAll: false,
            catalogSearch: "",
            fetchError: null,
            error: null,
        };
    },
    computed: {
        canTranslate() {
            return this.inputText.trim() && this.sourceLang && this.targetLang && this.sourceLang !== this.targetLang;
        },
        installedPairs() {
            return this.packs.map((p) => ({
                pair: p.pair,
                from: p.from || p.pair.slice(0, 2),
                to: p.to || p.pair.slice(2, 4),
            }));
        },
        installedPairSet() {
            return new Set(this.packs.map((p) => p.pair));
        },
        mergedCatalog() {
            // Catalog entries are directional (enru, ruen). Show both ways of
            // a language pair as a single entry that downloads every
            // direction present in the catalog.
            const groups = new Map();
            for (const entry of this.catalogPairs) {
                const from = entry.from || entry.pair.slice(0, 2);
                const to = entry.to || entry.pair.slice(2, 4);
                const key = [from, to].sort().join("-");
                let group = groups.get(key);
                if (!group) {
                    group = {
                        key,
                        from,
                        to,
                        directions: [],
                        architecture: entry.architecture,
                        size: 0,
                    };
                    groups.set(key, group);
                }
                group.directions.push(entry.pair);
                group.size += entry.size || 0;
            }
            return Array.from(groups.values()).sort((a, b) =>
                this.groupLabel(a).localeCompare(this.groupLabel(b), undefined, {
                    sensitivity: "base",
                })
            );
        },
        filteredCatalog() {
            const query = (this.catalogSearch || "").trim().toLowerCase();
            if (!query) {
                return this.mergedCatalog;
            }
            return this.mergedCatalog.filter((group) => {
                if (group.directions.some((pair) => pair.includes(query))) {
                    return true;
                }
                return this.groupLabel(group).toLowerCase().includes(query);
            });
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
        const q = this.$route?.query;
        if (q?.text) {
            this.inputText = String(q.text);
        }
        if (q?.source && q?.target) {
            this.sourceLang = String(q.source);
            this.targetLang = String(q.target);
        }
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
            return `${displayNames.of(from) || from} -> ${displayNames.of(to) || to}`;
        },
        languageName(code) {
            const userLocale = (navigator.language || "en").slice(0, 2);
            try {
                return new Intl.DisplayNames([userLocale], { type: "language" }).of(code) || code;
            } catch {
                return code;
            }
        },
        groupLabel(group) {
            const fromName = this.languageName(group.from);
            const toName = this.languageName(group.to);
            return group.directions.length > 1 ? `${fromName} <-> ${toName}` : `${fromName} -> ${toName}`;
        },
        isGroupInstalled(group) {
            return group.directions.every((pair) => this.installedPairSet.has(pair));
        },
        isGroupDownloading(group) {
            return Boolean(this.downloadingPairs[group.key]);
        },
        async downloadGroup(group) {
            if (this.isGroupDownloading(group)) {
                return;
            }
            const missing = group.directions.filter((pair) => !this.installedPairSet.has(pair));
            if (!missing.length) {
                return;
            }
            this.downloadingPairs = { ...this.downloadingPairs, [group.key]: true };
            this.fetchError = null;
            const failed = [];
            try {
                for (const pair of missing) {
                    try {
                        await TranslationService.downloadPack(pair);
                    } catch (e) {
                        console.error(`Failed to download pack ${pair}:`, e);
                        failed.push(pair);
                    }
                }
                if (failed.length) {
                    this.fetchError = this.$t("translator.download_failed", {
                        pair: failed.map((p) => p.toUpperCase()).join(", "),
                    });
                }
                await this.loadPacks();
            } finally {
                const next = { ...this.downloadingPairs };
                delete next[group.key];
                this.downloadingPairs = next;
            }
        },
        async toggleCatalog() {
            if (this.showCatalog) {
                this.showCatalog = false;
                return;
            }
            this.showCatalog = true;
            if (this.catalogPairs.length || this.isLoadingCatalog) {
                return;
            }
            this.isLoadingCatalog = true;
            this.catalogError = null;
            try {
                this.catalogPairs = await TranslationService.fetchCatalog();
            } catch (e) {
                console.error("Failed to load pack catalog:", e);
                this.catalogError = this.$t("translator.catalog_failed");
            } finally {
                this.isLoadingCatalog = false;
            }
        },
        async downloadAll() {
            if (this.isDownloadingAll) {
                return;
            }
            this.isDownloadingAll = true;
            this.fetchError = null;
            try {
                const result = await TranslationService.downloadAllPacks();
                if (result?.failed?.length) {
                    this.fetchError = this.$t("translator.download_failed_some", {
                        count: result.failed.length,
                    });
                }
                await this.loadPacks();
            } catch (e) {
                console.error("Failed to download packs:", e);
                this.fetchError = this.$t("translator.download_failed_all");
            } finally {
                this.isDownloadingAll = false;
            }
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
