<!-- SPDX-License-Identifier: 0BSD -->

<template>
    <AppModal :model-value="modelValue" :max-width="560" @update:model-value="$emit('update:modelValue', $event)">
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
            <div v-else class="text-sm text-sem-fg-muted">
                {{ $t("settings.micron_wasm_update_bundled_only") }}
            </div>

            <p class="text-sm text-sem-fg-muted">
                {{ $t("settings.micron_wasm_update_isolation_note") }}
            </p>

            <div class="space-y-2">
                <div class="text-sm font-medium">{{ $t("settings.micron_wasm_update_upload_heading") }}</div>
                <p class="text-xs text-amber-800 dark:text-amber-200/90">
                    {{ $t("settings.micron_wasm_update_upload_warning") }}
                </p>
                <input
                    ref="fileInput"
                    type="file"
                    accept=".wasm,application/wasm"
                    class="max-w-full text-sm"
                    :disabled="busy"
                    @change="onWasmFileSelected"
                />
            </div>

            <div
                v-if="formError"
                class="rounded-lg border border-red-200 bg-red-50 px-3 py-2 text-sm text-red-700 dark:border-red-900/50 dark:bg-red-950/40 dark:text-red-300"
            >
                {{ formError }}
            </div>

            <div class="flex flex-wrap items-center gap-2 pt-2">
                <button type="button" class="secondary-chip" :disabled="busy || !currentInfo" @click="onRevertBundled">
                    {{ $t("settings.micron_wasm_update_revert_bundled") }}
                </button>
                <div class="flex-1" />
                <button type="button" class="secondary-chip" @click="close">{{ $t("common.close") }}</button>
            </div>
        </div>
    </AppModal>
</template>

<script>
import AppModal from "../AppModal.vue";
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

export default {
    name: "MicronWasmUpdateModal",
    components: {
        AppModal,
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
        };
    },
    watch: {
        modelValue(v) {
            if (v) {
                this.formError = "";
                this.loadCurrentInfo();
            }
        },
    },
    methods: {
        close() {
            this.$emit("update:modelValue", false);
        },
        async loadCurrentInfo() {
            try {
                const r = await getMicronWasmRuntimeOverride();
                if (r && r.wasmBytes) {
                    this.currentInfo = {
                        releaseTag: r.releaseTag,
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
        async onWasmFileSelected(ev) {
            this.formError = "";
            const file = ev.target.files && ev.target.files[0];
            if (!file) {
                return;
            }
            if (!String(file.name).toLowerCase().endsWith(".wasm")) {
                this.formError = this.$t("settings.micron_wasm_update_err_not_wasm");
                ev.target.value = "";
                return;
            }
            this.busy = true;
            try {
                const buf = await file.arrayBuffer();
                if (buf.byteLength > MAX_WASM_OVERRIDE_BYTES) {
                    this.formError = this.$t("settings.micron_wasm_update_err_too_large");
                    ev.target.value = "";
                    return;
                }
                if (buf.byteLength < 4096) {
                    this.formError = this.$t("settings.micron_wasm_update_err_too_small");
                    ev.target.value = "";
                    return;
                }
                const wasmSri = await computeWasmSriSha384(buf);
                await setMicronWasmRuntimeOverride({
                    source: "upload",
                    releaseTag: file.name,
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
                    ev.target.value = "";
                    return;
                }
                ToastUtils.success(this.$t("settings.micron_wasm_update_toast_uploaded"));
                await this.loadCurrentInfo();
                this.$emit("saved");
            } catch (e) {
                this.formError = (e && e.message) || String(e);
            } finally {
                this.busy = false;
                ev.target.value = "";
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
