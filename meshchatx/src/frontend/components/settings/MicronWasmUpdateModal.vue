<!-- SPDX-License-Identifier: 0BSD -->

<template>
    <v-dialog
        :model-value="modelValue"
        max-width="560"
        scrollable
        @update:model-value="$emit('update:modelValue', $event)"
    >
        <v-card class="bg-white dark:bg-zinc-900">
            <v-card-title class="text-h6 font-semibold text-gray-900 dark:text-white border-b dark:border-zinc-800">
                {{ $t("settings.micron_wasm_update_modal_title") }}
            </v-card-title>
            <v-card-text class="pt-4 space-y-4 text-gray-800 dark:text-zinc-200">
                <div
                    v-if="currentInfo"
                    class="rounded-lg border border-gray-200 dark:border-zinc-700 p-3 text-sm space-y-1"
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
                    <div v-if="currentInfo.byteLength" class="text-xs text-gray-600 dark:text-zinc-400">
                        {{ $t("settings.micron_wasm_update_active_size", { bytes: currentInfo.byteLength }) }}
                    </div>
                </div>
                <div v-else class="text-sm text-gray-600 dark:text-zinc-400">
                    {{ $t("settings.micron_wasm_update_bundled_only") }}
                </div>

                <p class="text-sm text-gray-600 dark:text-zinc-400">
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
                        class="text-sm max-w-full"
                        :disabled="busy"
                        @change="onWasmFileSelected"
                    />
                </div>

                <v-alert v-if="formError" type="error" density="compact" variant="tonal" class="text-sm">
                    {{ formError }}
                </v-alert>

                <div class="flex flex-wrap gap-2 pt-2 items-center">
                    <v-btn variant="text" color="secondary" :disabled="busy || !currentInfo" @click="onRevertBundled">
                        {{ $t("settings.micron_wasm_update_revert_bundled") }}
                    </v-btn>
                    <div class="flex-1" />
                    <v-btn variant="text" @click="close">{{ $t("common.close") }}</v-btn>
                </div>
            </v-card-text>
        </v-card>
    </v-dialog>
</template>

<script>
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
