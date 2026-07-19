<!-- SPDX-License-Identifier: 0BSD -->

<template>
    <div
        class="absolute top-2 left-2 right-2 sm:top-4 sm:left-4 sm:right-4 z-10 flex flex-col sm:flex-row gap-2 pointer-events-none"
    >
        <div
            class="pointer-events-auto border border-gray-200/50 dark:border-zinc-800/50 bg-white/90 dark:bg-zinc-900/90 rounded-2xl overflow-hidden w-full sm:w-[280px] sm:max-w-[280px] transition-all duration-300"
        >
            <div
                class="flex items-center px-4 sm:px-5 py-3 sm:py-4 cursor-pointer hover:bg-gray-50/50 dark:hover:bg-zinc-800/50 transition-colors"
                @click="$emit('update:isShowingControls', !isShowingControls)"
            >
                <div class="flex-1 flex flex-col min-w-0 mr-2">
                    <span class="font-bold text-gray-900 dark:text-zinc-100 tracking-tight truncate">{{
                        $t("visualiser.reticulum_mesh")
                    }}</span>
                    <span
                        class="text-[10px] uppercase font-bold text-gray-500 dark:text-zinc-500 tracking-widest truncate"
                        >{{ $t("visualiser.network_visualizer") }}</span
                    >
                </div>
                <div class="flex items-center gap-2">
                    <button
                        type="button"
                        class="inline-flex items-center justify-center w-8 h-8 sm:w-9 sm:h-9 rounded-xl bg-blue-600 hover:bg-blue-700 dark:bg-blue-600 dark:hover:bg-blue-700 text-white transition-all active:scale-95 disabled:opacity-60"
                        :disabled="isUpdating || isLoading"
                        :aria-label="$t('visualiser.refresh')"
                        @click.stop="$emit('manual-update')"
                    >
                        <MaterialDesignIcon
                            :icon-name="isLoading ? 'loading' : 'refresh'"
                            class="w-4 h-4 sm:w-5 sm:h-5"
                            :class="{ 'animate-spin': isLoading }"
                        />
                    </button>
                    <div class="w-5 sm:w-6 flex justify-center">
                        <MaterialDesignIcon
                            icon-name="chevron-down"
                            class="w-4 h-4 sm:w-5 sm:h-5 text-gray-400 transition-transform duration-300"
                            :class="{ 'rotate-180': isShowingControls }"
                        />
                    </div>
                </div>
            </div>

            <div
                v-show="isShowingControls"
                class="px-5 pb-5 space-y-4 animate-in fade-in slide-in-from-top-2 duration-300"
            >
                <div class="h-px bg-linear-to-r from-transparent via-gray-200 dark:via-zinc-800 to-transparent"></div>

                <div class="grid grid-cols-2 gap-2">
                    <div
                        class="relative min-w-0 rounded-xl px-3 py-2 border border-gray-100 dark:border-zinc-700/50 bg-gray-50/60 dark:bg-zinc-800/40"
                        :title="engineSelectTitle"
                    >
                        <div
                            class="text-[10px] font-bold text-gray-500 dark:text-zinc-500 uppercase tracking-wider mb-0.5"
                        >
                            {{ $t("visualiser.engine") }}
                        </div>
                        <button
                            id="visualiser-engine-select"
                            type="button"
                            class="flex w-full min-w-0 items-center gap-1 bg-transparent text-left text-xs font-bold focus:outline-hidden focus-visible:ring-1 focus-visible:ring-blue-500/50 rounded"
                            :class="engineSelectClass"
                            :aria-label="$t('visualiser.engine')"
                            :aria-expanded="engineMenuOpen ? 'true' : 'false'"
                            aria-haspopup="listbox"
                            @click.stop="toggleEngineMenu"
                        >
                            <span class="min-w-0 flex-1 truncate">{{ engineTriggerLabel }}</span>
                            <MaterialDesignIcon
                                icon-name="chevron-down"
                                class="w-3.5 h-3.5 shrink-0 text-gray-400 transition-transform duration-200"
                                :class="{ 'rotate-180': engineMenuOpen }"
                            />
                        </button>
                        <Teleport to="body">
                            <div
                                v-if="engineMenuOpen"
                                ref="engineMenuPanel"
                                v-click-outside="closeEngineMenu"
                                class="fixed z-200 w-56 overflow-hidden rounded-xl border border-gray-200 bg-white shadow-lg dark:border-zinc-700 dark:bg-zinc-900"
                                :style="engineMenuStyle"
                                role="listbox"
                                :aria-label="$t('visualiser.engine')"
                            >
                                <button
                                    v-for="opt in engineOptions"
                                    :key="opt.value"
                                    type="button"
                                    role="option"
                                    class="flex w-full items-center justify-between gap-2 px-3 py-2.5 text-left text-xs font-semibold transition-colors hover:bg-gray-100 dark:hover:bg-zinc-800"
                                    :class="
                                        preferredRenderer === opt.value
                                            ? 'bg-blue-50 text-blue-700 dark:bg-blue-950/40 dark:text-blue-300'
                                            : 'text-gray-800 dark:text-zinc-100'
                                    "
                                    :aria-selected="preferredRenderer === opt.value ? 'true' : 'false'"
                                    @click.stop="selectEngine(opt.value)"
                                >
                                    <span class="min-w-0 flex-1">{{ opt.label }}</span>
                                    <MaterialDesignIcon
                                        v-if="preferredRenderer === opt.value"
                                        icon-name="check"
                                        class="w-4 h-4 shrink-0"
                                    />
                                </button>
                            </div>
                        </Teleport>
                    </div>
                    <div
                        class="min-w-0 rounded-xl px-3 py-2 border border-gray-100 dark:border-zinc-700/50 bg-gray-50/60 dark:bg-zinc-800/40"
                    >
                        <div
                            class="text-[10px] font-bold text-gray-500 dark:text-zinc-500 uppercase tracking-wider mb-0.5"
                        >
                            {{ $t("visualiser.fps") }}
                        </div>
                        <div class="text-xs font-bold text-gray-800 dark:text-zinc-100 tabular-nums">
                            {{ fpsDisplay }}
                        </div>
                    </div>
                </div>

                <div class="flex items-center justify-between">
                    <label
                        for="auto-reload"
                        class="text-sm font-semibold text-gray-700 dark:text-zinc-300 cursor-pointer"
                        >{{ $t("visualiser.auto_update") }}</label
                    >
                    <Toggle
                        id="auto-reload"
                        :model-value="autoReload"
                        @update:model-value="$emit('update:autoReload', $event)"
                    />
                </div>

                <div class="flex items-center justify-between">
                    <label
                        for="enable-physics"
                        class="text-sm font-semibold text-gray-700 dark:text-zinc-300 cursor-pointer"
                        >{{ $t("visualiser.live_layout") }}</label
                    >
                    <Toggle
                        id="enable-physics"
                        :model-value="enablePhysics"
                        @update:model-value="$emit('update:enablePhysics', $event)"
                    />
                </div>

                <div class="space-y-2">
                    <div class="flex items-center justify-between gap-2">
                        <label
                            for="hop-filter-slider"
                            class="text-sm font-semibold text-gray-700 dark:text-zinc-300 cursor-pointer"
                            >{{ $t("visualiser.max_hops_filter") }}</label
                        >
                        <input
                            id="hop-max-hops-input"
                            type="text"
                            inputmode="numeric"
                            autocomplete="off"
                            maxlength="4"
                            :aria-label="$t('visualiser.max_hops_filter')"
                            class="w-13 shrink-0 rounded-lg border border-gray-200 bg-white px-1.5 py-1 text-center text-xs font-bold text-blue-600 tabular-nums shadow-xs focus:border-blue-500 focus:outline-hidden focus:ring-1 focus:ring-blue-500/40 dark:border-zinc-600 dark:bg-zinc-800 dark:text-blue-400 dark:focus:border-blue-500"
                            :value="hopMaxInputShown"
                            :placeholder="$t('visualiser.all')"
                            @focus="onHopMaxInputFocus"
                            @input="onHopMaxInputInput"
                            @blur="onHopMaxInputBlur"
                        />
                    </div>
                    <input
                        id="hop-filter-slider"
                        type="range"
                        min="0"
                        :max="hopSliderPosAll"
                        step="1"
                        :value="hopSliderUiPos"
                        :aria-valuetext="hopSliderAriaText"
                        class="w-full h-2 rounded-lg appearance-none cursor-pointer bg-gray-200 dark:bg-zinc-700 accent-blue-600 dark:accent-blue-500"
                        @input="onHopSliderInput"
                    />
                </div>

                <div class="grid grid-cols-2 gap-3 pt-2">
                    <div
                        class="bg-gray-50/50 dark:bg-zinc-800/50 rounded-xl p-3 border border-gray-100 dark:border-zinc-700/50"
                    >
                        <div
                            class="text-[10px] font-bold text-gray-500 dark:text-zinc-500 uppercase tracking-wider mb-1"
                        >
                            {{ $t("visualiser.nodes") }}
                        </div>
                        <div class="text-lg font-bold text-blue-600 dark:text-blue-400">{{ nodeCount }}</div>
                    </div>
                    <div
                        class="bg-gray-50/50 dark:bg-zinc-800/50 rounded-xl p-3 border border-gray-100 dark:border-zinc-700/50"
                    >
                        <div
                            class="text-[10px] font-bold text-gray-500 dark:text-zinc-500 uppercase tracking-wider mb-1"
                        >
                            {{ $t("visualiser.links") }}
                        </div>
                        <div class="text-lg font-bold text-emerald-600 dark:text-emerald-400">{{ edgeCount }}</div>
                    </div>
                </div>

                <div
                    class="bg-zinc-950/5 dark:bg-white/5 rounded-xl p-3 border border-gray-100 dark:border-zinc-700/50"
                >
                    <div class="text-[10px] font-bold text-gray-500 dark:text-zinc-500 uppercase tracking-wider mb-2">
                        {{ $t("visualiser.interfaces") }}
                    </div>
                    <div class="flex items-center gap-4">
                        <div class="flex items-center gap-1.5">
                            <div class="w-2 h-2 rounded-full bg-emerald-500"></div>
                            <span class="text-xs font-bold text-gray-700 dark:text-zinc-300"
                                >{{ onlineInterfaceCount }} {{ $t("visualiser.online") }}</span
                            >
                        </div>
                        <div class="flex items-center gap-1.5">
                            <div class="w-2 h-2 rounded-full bg-red-500"></div>
                            <span class="text-xs font-bold text-gray-700 dark:text-zinc-300"
                                >{{ offlineInterfaceCount }} {{ $t("visualiser.offline") }}</span
                            >
                        </div>
                    </div>
                </div>
            </div>
        </div>

        <div class="sm:ml-auto w-full sm:w-auto pointer-events-auto">
            <div class="relative group">
                <div
                    class="absolute inset-y-0 left-0 pl-3 flex items-center pointer-events-none text-gray-400 group-focus-within:text-blue-500 transition-colors"
                >
                    <MaterialDesignIcon icon-name="magnify" class="w-4 h-4" />
                </div>
                <input
                    :value="searchQuery"
                    type="text"
                    :placeholder="$t('visualiser.search_nodes_placeholder', { count: nodeCount })"
                    class="block w-full sm:w-64 pl-9 pr-10 py-2.5 sm:py-3 bg-white/90 dark:bg-zinc-900/90 border border-gray-200/50 dark:border-zinc-800/50 rounded-2xl text-xs font-semibold focus:outline-hidden focus:ring-2 focus:ring-blue-500/50 sm:focus:w-80 md:max-lg:focus:w-72 lg:focus:w-80 transition-all dark:text-zinc-100 shadow-xs"
                    @input="$emit('update:searchQuery', $event.target.value)"
                />
                <button
                    v-if="searchQuery"
                    type="button"
                    class="absolute inset-y-0 right-0 pr-3 flex items-center text-gray-400 hover:text-gray-600 dark:hover:text-zinc-200 transition-colors"
                    :aria-label="$t('visualiser.clear_search')"
                    @click="$emit('update:searchQuery', '')"
                >
                    <MaterialDesignIcon icon-name="close" class="w-4 h-4" />
                </button>
            </div>
        </div>
    </div>
</template>

<script>
import Toggle from "../../forms/Toggle.vue";
import MaterialDesignIcon from "../../MaterialDesignIcon.vue";
import { clampFloatingToViewport } from "../../../js/clampFloatingToViewport.js";
import { HOP_SLIDER_POS_ALL, hopSliderPosToMaxHops, hopMaxHopsToSliderPos } from "./hopMaxFilterSliderMap.js";

const ENGINE_VALUES = ["auto", "webgl", "vis"];

export default {
    name: "NetworkVisualiserToolbar",
    components: { Toggle, MaterialDesignIcon },
    props: {
        isShowingControls: { type: Boolean, default: true },
        isUpdating: { type: Boolean, default: false },
        isLoading: { type: Boolean, default: false },
        autoReload: { type: Boolean, default: false },
        enablePhysics: { type: Boolean, default: true },
        hopMaxFilter: {
            default: 4,
            validator(v) {
                return v === null || (typeof v === "number" && Number.isFinite(v) && v >= 0 && v <= 128);
            },
        },
        nodeCount: { type: Number, default: 0 },
        edgeCount: { type: Number, default: 0 },
        onlineInterfaceCount: { type: Number, default: 0 },
        offlineInterfaceCount: { type: Number, default: 0 },
        searchQuery: { type: String, default: "" },
        preferredRenderer: {
            type: String,
            default: "auto",
            validator(v) {
                return ENGINE_VALUES.includes(v);
            },
        },
        engineMode: {
            type: String,
            default: "checking",
            validator(v) {
                return ["checking", "wasm", "fallback", "webgl"].includes(v);
            },
        },
        fps: { type: Number, default: 0 },
    },
    emits: [
        "update:isShowingControls",
        "update:autoReload",
        "update:enablePhysics",
        "update:hopMaxFilter",
        "update:searchQuery",
        "update:preferredRenderer",
        "manual-update",
    ],
    data() {
        return {
            hopMaxInputDraft: null,
            engineMenuOpen: false,
            engineMenuPosition: null,
        };
    },
    computed: {
        hopSliderPosAll() {
            return HOP_SLIDER_POS_ALL;
        },
        hopSliderUiPos() {
            return hopMaxHopsToSliderPos(this.hopMaxFilter);
        },
        hopMaxInputShown() {
            if (this.hopMaxInputDraft !== null) return this.hopMaxInputDraft;
            if (this.hopMaxFilter === null) return "";
            return String(this.hopMaxFilter);
        },
        hopSliderAriaText() {
            if (this.hopMaxFilter === null) return this.$t("visualiser.all");
            return String(this.hopMaxFilter);
        },
        engineOptions() {
            return [
                { value: "auto", label: this.$t("visualiser.renderer_option_auto") },
                { value: "webgl", label: this.$t("visualiser.renderer_option_webgl") },
                { value: "vis", label: this.$t("visualiser.renderer_option_vis") },
            ];
        },
        engineTriggerLabel() {
            if (this.preferredRenderer === "webgl") return this.$t("visualiser.renderer_option_webgl_short");
            if (this.preferredRenderer === "vis") return this.$t("visualiser.renderer_option_vis_short");
            return this.$t("visualiser.renderer_option_auto_short");
        },
        engineSelectTitle() {
            if (this.engineMode === "webgl") return this.$t("visualiser.engine_webgl_hint");
            if (this.engineMode === "wasm") return this.$t("visualiser.engine_wasm_hint");
            if (this.engineMode === "fallback") return this.$t("visualiser.engine_fallback_hint");
            return this.$t("visualiser.renderer_desc");
        },
        engineSelectClass() {
            if (this.engineMode === "webgl") return "text-sky-600 dark:text-sky-400";
            if (this.engineMode === "wasm") return "text-emerald-600 dark:text-emerald-400";
            if (this.engineMode === "fallback") return "text-amber-600 dark:text-amber-400";
            return "text-gray-800 dark:text-zinc-100";
        },
        fpsDisplay() {
            const n = Number(this.fps);
            if (!Number.isFinite(n) || n <= 0) return "--";
            return String(Math.round(n));
        },
        engineMenuStyle() {
            if (!this.engineMenuPosition) return {};
            const style = {
                left: `${this.engineMenuPosition.left}px`,
                top: `${this.engineMenuPosition.top}px`,
            };
            if (this.engineMenuPosition.maxHeight != null) {
                style.maxHeight = `${this.engineMenuPosition.maxHeight}px`;
                style.overflowY = "auto";
            }
            return style;
        },
    },
    watch: {
        isShowingControls(open) {
            if (!open) this.closeEngineMenu();
        },
    },
    beforeUnmount() {
        this.closeEngineMenu();
    },
    methods: {
        toggleEngineMenu() {
            if (this.engineMenuOpen) {
                this.closeEngineMenu();
                return;
            }
            this.openEngineMenu();
        },
        openEngineMenu() {
            this.engineMenuOpen = true;
            this.$nextTick(() => this.positionEngineMenu());
        },
        closeEngineMenu() {
            this.engineMenuOpen = false;
            this.engineMenuPosition = null;
        },
        positionEngineMenu() {
            const trigger = this.$el?.querySelector?.("#visualiser-engine-select");
            if (!trigger) return;
            const rect = trigger.getBoundingClientRect();
            this.engineMenuPosition = {
                left: Math.max(8, rect.left),
                top: rect.bottom + 6,
                maxHeight: null,
            };
            this.$nextTick(() => {
                const panel = this.$refs.engineMenuPanel;
                if (!panel) return;
                const pr = panel.getBoundingClientRect();
                const { left, top, maxHeight } = clampFloatingToViewport(pr.left, pr.top, pr.width, pr.height);
                this.engineMenuPosition = { left, top, maxHeight };
            });
        },
        selectEngine(value) {
            if (ENGINE_VALUES.includes(value)) {
                this.$emit("update:preferredRenderer", value);
            }
            this.closeEngineMenu();
        },
        onHopSliderInput(e) {
            const v = hopSliderPosToMaxHops(Number(e.target.value));
            this.$emit("update:hopMaxFilter", v);
        },
        onHopMaxInputFocus() {
            this.hopMaxInputDraft = this.hopMaxFilter === null ? "" : String(this.hopMaxFilter);
        },
        onHopMaxInputInput(e) {
            const raw = e.target.value.replace(/\D/g, "");
            this.hopMaxInputDraft = raw;
            if (raw === "") return;
            const n = parseInt(raw, 10);
            if (!Number.isFinite(n)) return;
            const clamped = Math.max(0, Math.min(128, Math.round(n)));
            this.$emit("update:hopMaxFilter", clamped);
            this.hopMaxInputDraft = String(clamped);
        },
        onHopMaxInputBlur() {
            const d = this.hopMaxInputDraft;
            this.hopMaxInputDraft = null;
            if (d === null) return;
            const trimmed = (d || "").trim();
            if (trimmed === "") {
                this.$emit("update:hopMaxFilter", null);
                return;
            }
            const n = parseInt(trimmed, 10);
            if (!Number.isFinite(n)) return;
            this.$emit("update:hopMaxFilter", Math.max(0, Math.min(128, Math.round(n))));
        },
    },
};
</script>
