<!-- SPDX-License-Identifier: 0BSD -->

<template>
    <AppModal
        :model-value="modelValue"
        :max-width="560"
        :scrollable="true"
        :show-close="true"
        @update:model-value="$emit('update:modelValue', $event)"
    >
        <template #header>
            <h2 class="min-w-0 flex-1 text-lg font-semibold text-sem-fg">
                {{ $t("settings.micron_wasm_update_modal_title") }}
            </h2>
        </template>

        <div class="space-y-4 px-4 py-4 text-sem-fg sm:px-5">
            <div
                v-if="currentInfo"
                class="rounded-lg border border-gray-200 p-3 text-sm space-y-1 dark:border-zinc-700"
            >
                <div class="font-medium">{{ $t("settings.micron_wasm_update_active_label") }}</div>
                <div>
                    {{
                        $t("settings.micron_wasm_update_active_source", {
                            source: $t("settings.micron_wasm_update_source_upload"),
                        })
                    }}
                </div>
                <div class="monospace-field break-all text-xs opacity-90">{{ currentInfo.releaseTag }}</div>
                <div v-if="currentInfo.byteLength" class="text-xs text-sem-fg-muted">
                    {{ $t("settings.micron_wasm_update_active_size", { bytes: currentInfo.byteLength }) }}
                </div>
            </div>
            <div v-else class="text-sm text-sem-fg-muted space-y-1">
                <div>{{ $t("settings.micron_wasm_update_bundled_only") }}</div>
                <div v-if="bundledReleaseLabel" class="text-xs font-mono opacity-90">
                    {{ $t("settings.micron_wasm_installed_version", { version: bundledReleaseLabel }) }}
                </div>
            </div>

            <p class="text-sm text-sem-fg-muted">
                {{ $t("settings.micron_wasm_update_isolation_note") }}
            </p>

            <div class="space-y-2">
                <div class="text-sm font-medium">{{ $t("settings.micron_wasm_update_upload_heading") }}</div>
                <p class="text-xs text-amber-800 dark:text-amber-200/90">
                    {{ $t("settings.micron_wasm_update_upload_warning") }}
                </p>

                <div
                    class="micron-wasm-dropzone rounded-xl border-2 border-dashed p-4 sm:p-6 text-center transition-colors touch-manipulation"
                    :class="dropzoneClass"
                    role="button"
                    tabindex="0"
                    :aria-disabled="busy"
                    @dragenter.prevent="onDragEnter"
                    @dragover.prevent="onDragOver"
                    @dragleave.prevent="onDragLeave"
                    @drop.prevent="onDrop"
                    @click="openFilePicker"
                    @keydown.enter.prevent="openFilePicker"
                    @keydown.space.prevent="openFilePicker"
                >
                    <MaterialDesignIcon
                        icon-name="upload"
                        class="mx-auto mb-2 size-8 text-sem-fg-muted"
                        aria-hidden="true"
                    />
                    <p class="text-sm font-medium text-gray-800 dark:text-gray-200">
                        {{ $t("settings.micron_wasm_update_drop_hint") }}
                    </p>
                    <p class="mt-1 text-xs text-sem-fg-muted">
                        {{ $t("settings.micron_wasm_update_paste_hint") }}
                    </p>
                    <label class="mt-4 inline-flex" @click.stop>
                        <input
                            ref="fileInput"
                            type="file"
                            accept=".wasm,application/wasm"
                            class="sr-only"
                            :disabled="busy"
                            @change="onWasmFileSelected"
                        />
                        <span
                            class="primary-chip min-h-[44px] px-4 py-2.5 text-sm"
                            :class="busy ? 'opacity-60 pointer-events-none' : 'cursor-pointer'"
                        >
                            {{
                                busy
                                    ? $t("settings.micron_wasm_update_installing")
                                    : $t("settings.micron_wasm_update_choose_file")
                            }}
                        </span>
                    </label>
                </div>
            </div>

            <div
                v-if="formError"
                class="rounded-lg border border-red-200 bg-red-50 px-3 py-2 text-sm text-red-700 dark:border-red-900/50 dark:bg-red-950/40 dark:text-red-300"
            >
                {{ formError }}
            </div>

            <div class="flex flex-wrap items-center gap-2 pt-2">
                <button
                    type="button"
                    class="secondary-chip min-h-[44px]"
                    :disabled="busy || !currentInfo"
                    @click="onRevertBundled"
                >
                    {{ $t("settings.micron_wasm_update_revert_bundled") }}
                </button>
                <div class="flex-1" />
                <button type="button" class="secondary-chip min-h-[44px]" @click="close">
                    {{ $t("common.close") }}
                </button>
            </div>
        </div>
    </AppModal>
</template>

<script>
import AppModal from "../AppModal.vue";
import MaterialDesignIcon from "../MaterialDesignIcon.vue";
import ToastUtils from "../../js/ToastUtils";
import {
    getMicronWasmRuntimeOverride,
    setMicronWasmRuntimeOverride,
    clearMicronWasmRuntimeOverride,
    computeWasmSriSha384,
    MAX_WASM_OVERRIDE_BYTES,
} from "../../js/MicronWasmRuntimeOverride.js";
import {
    invalidateNomadMicronWasmPreload,
    refreshMicronWasmRuntimeOverrideCache,
    preloadNomadMicronWasm,
} from "../../js/MicronWasmLoader.js";
import GlobalEmitter from "../../js/GlobalEmitter";
import {
    MICRON_WASM_OVERRIDE_CHANGED_EVENT,
    normalizeMicronWasmReleaseTag,
    bundledMicronWasmReleaseTag,
} from "../../js/micronWasmVersion.js";
import {
    isWasmUploadFile,
    pickWasmFileFromClipboardEvent,
    pickWasmFileFromDataTransfer,
    pickWasmFileFromFileList,
} from "../../js/micronWasmUpload.js";

export default {
    name: "MicronWasmUpdateModal",
    components: {
        AppModal,
        MaterialDesignIcon,
    },
    props: {
        modelValue: { type: Boolean, default: false },
    },
    emits: ["update:modelValue", "saved"],
    data() {
        return {
            busy: false,
            formError: "",
            currentInfo: null,
            bundledReleaseLabel: bundledMicronWasmReleaseTag(),
            dragDepth: 0,
        };
    },
    computed: {
        dragActive() {
            return this.dragDepth > 0;
        },
        dropzoneClass() {
            if (this.busy) {
                return "border-gray-300 bg-sem-surface-muted/30 opacity-80 dark:border-zinc-700";
            }
            if (this.dragActive) {
                return "border-blue-500 bg-blue-50/60 dark:border-blue-400 dark:bg-blue-950/20";
            }
            return "border-gray-300 bg-sem-surface-muted/40 hover:border-blue-400/70 dark:border-zinc-700 cursor-pointer";
        },
    },
    watch: {
        modelValue(v) {
            if (v) {
                this.formError = "";
                this.dragDepth = 0;
                this.loadCurrentInfo();
                document.addEventListener("paste", this.onWasmPaste);
            } else {
                document.removeEventListener("paste", this.onWasmPaste);
            }
        },
    },
    beforeUnmount() {
        document.removeEventListener("paste", this.onWasmPaste);
    },
    methods: {
        close() {
            this.$emit("update:modelValue", false);
        },
        openFilePicker() {
            if (this.busy) {
                return;
            }
            this.$refs.fileInput?.click();
        },
        onDragEnter() {
            if (this.busy) {
                return;
            }
            this.dragDepth += 1;
        },
        onDragOver() {
            if (this.busy) {
                return;
            }
            this.dragDepth = Math.max(this.dragDepth, 1);
        },
        onDragLeave() {
            this.dragDepth = Math.max(0, this.dragDepth - 1);
        },
        onDrop(event) {
            this.dragDepth = 0;
            if (this.busy) {
                return;
            }
            const file = pickWasmFileFromDataTransfer(event.dataTransfer);
            if (!file) {
                this.formError = this.$t("settings.micron_wasm_update_err_not_wasm");
                return;
            }
            this.installWasmFromFile(file);
        },
        onWasmPaste(event) {
            if (!this.modelValue || this.busy) {
                return;
            }
            const file = pickWasmFileFromClipboardEvent(event);
            if (!file) {
                return;
            }
            event.preventDefault();
            this.installWasmFromFile(file);
        },
        async loadCurrentInfo() {
            try {
                const r = await getMicronWasmRuntimeOverride();
                if (r && r.wasmBytes) {
                    const normalized = normalizeMicronWasmReleaseTag(r.releaseTag);
                    this.currentInfo = {
                        releaseTag: normalized || r.releaseTag,
                        byteLength: r.wasmBytes.byteLength,
                    };
                } else {
                    this.currentInfo = null;
                }
            } catch (e) {
                console.warn(e);
                this.currentInfo = null;
            }
        },
        onWasmFileSelected(ev) {
            const file = pickWasmFileFromFileList(ev.target.files);
            if (!file) {
                if (ev.target.files && ev.target.files.length) {
                    this.formError = this.$t("settings.micron_wasm_update_err_not_wasm");
                }
                ev.target.value = "";
                return;
            }
            this.installWasmFromFile(file).finally(() => {
                ev.target.value = "";
            });
        },
        async installWasmFromFile(file) {
            this.formError = "";
            if (!isWasmUploadFile(file)) {
                this.formError = this.$t("settings.micron_wasm_update_err_not_wasm");
                return;
            }
            this.busy = true;
            try {
                const buf = await file.arrayBuffer();
                if (buf.byteLength > MAX_WASM_OVERRIDE_BYTES) {
                    this.formError = this.$t("settings.micron_wasm_update_err_too_large");
                    return;
                }
                if (buf.byteLength < 4096) {
                    this.formError = this.$t("settings.micron_wasm_update_err_too_small");
                    return;
                }
                const wasmSri = await computeWasmSriSha384(buf);
                const releaseTag =
                    normalizeMicronWasmReleaseTag(file.name) || String(file.name || "").trim() || "upload";
                await setMicronWasmRuntimeOverride({
                    source: "upload",
                    releaseTag,
                    wasmSri,
                    wasmBytes: buf,
                    expectedSha256Hex: null,
                });
                refreshMicronWasmRuntimeOverrideCache();
                invalidateNomadMicronWasmPreload();
                const ok = await preloadNomadMicronWasm();
                if (!ok) {
                    await clearMicronWasmRuntimeOverride();
                    refreshMicronWasmRuntimeOverrideCache();
                    invalidateNomadMicronWasmPreload();
                    this.formError = this.$t("settings.micron_wasm_update_err_activate_failed");
                    return;
                }
                ToastUtils.success(this.$t("settings.micron_wasm_update_toast_uploaded"));
                await this.loadCurrentInfo();
                GlobalEmitter.emit(MICRON_WASM_OVERRIDE_CHANGED_EVENT);
                this.$emit("saved");
            } catch (e) {
                this.formError = (e && e.message) || String(e);
            } finally {
                this.busy = false;
            }
        },
        async onRevertBundled() {
            this.formError = "";
            this.busy = true;
            try {
                await clearMicronWasmRuntimeOverride();
                refreshMicronWasmRuntimeOverrideCache();
                invalidateNomadMicronWasmPreload();
                await preloadNomadMicronWasm();
                ToastUtils.success(this.$t("settings.micron_wasm_update_toast_reverted"));
                await this.loadCurrentInfo();
                GlobalEmitter.emit(MICRON_WASM_OVERRIDE_CHANGED_EVENT);
                this.$emit("saved");
            } catch (e) {
                this.formError = (e && e.message) || String(e);
            } finally {
                this.busy = false;
            }
        },
    },
};
</script>

<style scoped>
@reference "../../style.css";

.micron-wasm-dropzone:focus-visible {
    outline: 2px solid rgba(59, 130, 246, 0.45);
    outline-offset: 2px;
}
</style>
