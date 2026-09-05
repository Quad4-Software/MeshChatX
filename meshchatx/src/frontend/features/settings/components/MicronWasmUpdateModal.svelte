<!-- SPDX-License-Identifier: 0BSD -->

<script lang="ts">
    import Modal from "../../../ui/svelte/Modal.svelte";
    import MaterialDesignIcon from "../../../ui/svelte/MaterialDesignIcon.svelte";
    import ToastUtils from "../../../js/ToastUtils.js";
    import {
        getMicronWasmRuntimeOverride,
        setMicronWasmRuntimeOverride,
        clearMicronWasmRuntimeOverride,
        computeWasmSriSha384,
        MAX_WASM_OVERRIDE_BYTES,
    } from "../../../js/MicronWasmRuntimeOverride.js";
    import {
        invalidateNomadMicronWasmPreload,
        refreshMicronWasmRuntimeOverrideCache,
        preloadNomadMicronWasm,
    } from "../../../js/MicronWasmLoader.js";
    import GlobalEmitter from "../../../js/GlobalEmitter.js";
    import {
        MICRON_WASM_OVERRIDE_CHANGED_EVENT,
        normalizeMicronWasmReleaseTag,
        bundledMicronWasmReleaseTag,
    } from "../../../js/micronWasmVersion.js";
    import {
        isWasmUploadFile,
        pickWasmFileFromClipboardEvent,
        pickWasmFileFromDataTransfer,
        pickWasmFileFromFileList,
    } from "../../../js/micronWasmUpload.js";
    import { t } from "../../../js/i18n.js";

    interface Props {
        open?: boolean;
        onsaved?: () => void;
    }

    let { open = $bindable(false), onsaved }: Props = $props();

    let busy = $state(false);
    let formError = $state("");
    let currentInfo = $state<{ releaseTag: string; byteLength?: number } | null>(null);
    const bundledReleaseLabel = bundledMicronWasmReleaseTag();
    let dragDepth = $state(0);
    let fileInputEl: HTMLInputElement | undefined = $state();

    const dragActive = $derived(dragDepth > 0);
    const dropzoneClass = $derived.by(() => {
        if (busy) {
            return "border-gray-300 bg-sem-surface-muted/30 opacity-80 dark:border-zinc-700";
        }
        if (dragActive) {
            return "border-blue-500 bg-blue-50/60 dark:border-blue-400 dark:bg-blue-950/20";
        }
        return "border-gray-300 bg-sem-surface-muted/40 hover:border-blue-400/70 dark:border-zinc-700 cursor-pointer";
    });

    $effect(() => {
        if (open) {
            formError = "";
            dragDepth = 0;
            void loadCurrentInfo();
            if (typeof document !== "undefined") {
                document.addEventListener("paste", onWasmPaste);
            }
        } else {
            if (typeof document !== "undefined") {
                document.removeEventListener("paste", onWasmPaste);
            }
        }
        return () => {
            if (typeof document !== "undefined") {
                document.removeEventListener("paste", onWasmPaste);
            }
        };
    });

    function close() {
        open = false;
    }

    function openFilePicker() {
        if (busy) return;
        fileInputEl?.click();
    }

    function onDragEnter() {
        if (busy) return;
        dragDepth += 1;
    }

    function onDragOver() {
        if (busy) return;
        dragDepth = Math.max(dragDepth, 1);
    }

    function onDragLeave() {
        dragDepth = Math.max(0, dragDepth - 1);
    }

    function onDrop(event: DragEvent) {
        dragDepth = 0;
        if (busy) return;
        const file = pickWasmFileFromDataTransfer(event.dataTransfer);
        if (!file) {
            formError = t("settings.micron_wasm_update_err_not_wasm");
            return;
        }
        void installWasmFromFile(file);
    }

    function onWasmPaste(event: ClipboardEvent) {
        if (!open || busy) return;
        const file = pickWasmFileFromClipboardEvent(event);
        if (!file) return;
        event.preventDefault();
        void installWasmFromFile(file);
    }

    async function loadCurrentInfo() {
        try {
            const r = await getMicronWasmRuntimeOverride();
            if (r && r.wasmBytes) {
                const normalized = normalizeMicronWasmReleaseTag(r.releaseTag);
                currentInfo = {
                    releaseTag: normalized || r.releaseTag,
                    byteLength: r.wasmBytes.byteLength,
                };
            } else {
                currentInfo = null;
            }
        } catch (e) {
            console.warn(e);
            currentInfo = null;
        }
    }

    function onWasmFileSelected(ev: Event) {
        const target = ev.target as HTMLInputElement;
        const file = pickWasmFileFromFileList(target.files);
        if (!file) {
            if (target.files && target.files.length) {
                formError = t("settings.micron_wasm_update_err_not_wasm");
            }
            target.value = "";
            return;
        }
        void installWasmFromFile(file).finally(() => {
            target.value = "";
        });
    }

    async function installWasmFromFile(file: File) {
        formError = "";
        if (!isWasmUploadFile(file)) {
            formError = t("settings.micron_wasm_update_err_not_wasm");
            return;
        }
        busy = true;
        try {
            const buf = await file.arrayBuffer();
            if (buf.byteLength > MAX_WASM_OVERRIDE_BYTES) {
                formError = t("settings.micron_wasm_update_err_too_large");
                return;
            }
            if (buf.byteLength < 4096) {
                formError = t("settings.micron_wasm_update_err_too_small");
                return;
            }
            const wasmSri = await computeWasmSriSha384(buf);
            const releaseTag = normalizeMicronWasmReleaseTag(file.name) || String(file.name || "").trim() || "upload";
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
                formError = t("settings.micron_wasm_update_err_activate_failed");
                return;
            }
            ToastUtils.success(t("settings.micron_wasm_update_toast_uploaded"));
            await loadCurrentInfo();
            GlobalEmitter.emit(MICRON_WASM_OVERRIDE_CHANGED_EVENT);
            onsaved?.();
        } catch (e: any) {
            formError = (e && e.message) || String(e);
        } finally {
            busy = false;
        }
    }

    async function onRevertBundled() {
        formError = "";
        busy = true;
        try {
            await clearMicronWasmRuntimeOverride();
            refreshMicronWasmRuntimeOverrideCache();
            invalidateNomadMicronWasmPreload();
            await preloadNomadMicronWasm();
            ToastUtils.success(t("settings.micron_wasm_update_toast_reverted"));
            await loadCurrentInfo();
            GlobalEmitter.emit(MICRON_WASM_OVERRIDE_CHANGED_EVENT);
            onsaved?.();
        } catch (e: any) {
            formError = (e && e.message) || String(e);
        } finally {
            busy = false;
        }
    }
</script>

<Modal bind:open maxWidth={560} title={t("settings.micron_wasm_update_modal_title")} onClose={close}>
    <div class="space-y-4 px-4 py-4 text-sem-fg sm:px-5">
        {#if currentInfo}
            <div class="rounded-lg border border-gray-200 p-3 text-sm space-y-1 dark:border-zinc-700">
                <div class="font-medium">{t("settings.micron_wasm_update_active_label")}</div>
                <div>
                    {t("settings.micron_wasm_update_active_source", {
                        source: t("settings.micron_wasm_update_source_upload"),
                    })}
                </div>
                <div class="monospace-field break-all text-xs opacity-90">{currentInfo.releaseTag}</div>
                {#if currentInfo.byteLength}
                    <div class="text-xs text-sem-fg-muted">
                        {t("settings.micron_wasm_update_active_size", { bytes: currentInfo.byteLength })}
                    </div>
                {/if}
            </div>
        {:else}
            <div class="text-sm text-sem-fg-muted space-y-1">
                <div>{t("settings.micron_wasm_update_bundled_only")}</div>
                {#if bundledReleaseLabel}
                    <div class="text-xs font-mono opacity-90">
                        {t("settings.micron_wasm_installed_version", { version: bundledReleaseLabel })}
                    </div>
                {/if}
            </div>
        {/if}

        <p class="text-sm text-sem-fg-muted">
            {t("settings.micron_wasm_update_isolation_note")}
        </p>

        <div class="space-y-2">
            <div class="text-sm font-medium">{t("settings.micron_wasm_update_upload_heading")}</div>
            <p class="text-xs text-amber-800 dark:text-amber-200/90">
                {t("settings.micron_wasm_update_upload_warning")}
            </p>

            <div
                class="micron-wasm-dropzone rounded-xl border-2 border-dashed p-4 sm:p-6 text-center transition-colors touch-manipulation {dropzoneClass}"
                role="button"
                tabindex="0"
                aria-disabled={busy}
                ondragenter={(e) => {
                    e.preventDefault();
                    onDragEnter();
                }}
                ondragover={(e) => {
                    e.preventDefault();
                    onDragOver();
                }}
                ondragleave={(e) => {
                    e.preventDefault();
                    onDragLeave();
                }}
                ondrop={(e) => {
                    e.preventDefault();
                    onDrop(e);
                }}
                onclick={openFilePicker}
                onkeydown={(e) => {
                    if (e.key === "Enter" || e.key === " ") {
                        e.preventDefault();
                        openFilePicker();
                    }
                }}
            >
                <MaterialDesignIcon iconName="upload" class="mx-auto mb-2 size-8 text-sem-fg-muted" />
                <p class="text-sm font-medium text-gray-800 dark:text-gray-200">
                    {t("settings.micron_wasm_update_drop_hint")}
                </p>
                <p class="mt-1 text-xs text-sem-fg-muted">
                    {t("settings.micron_wasm_update_paste_hint")}
                </p>
                <div class="mt-4 inline-flex" onclick={(e) => e.stopPropagation()} role="presentation">
                    <input
                        bind:this={fileInputEl}
                        type="file"
                        accept=".wasm,application/wasm"
                        class="sr-only"
                        disabled={busy}
                        onchange={onWasmFileSelected}
                    />
                    <span
                        class="primary-chip min-h-[44px] px-4 py-2.5 text-sm {busy
                            ? 'opacity-60 pointer-events-none'
                            : 'cursor-pointer'}"
                    >
                        {busy
                            ? t("settings.micron_wasm_update_installing")
                            : t("settings.micron_wasm_update_choose_file")}
                    </span>
                </div>
            </div>
        </div>

        {#if formError}
            <div
                class="rounded-lg border border-red-200 bg-red-50 px-3 py-2 text-sm text-red-700 dark:border-red-900/50 dark:bg-red-950/40 dark:text-red-300"
            >
                {formError}
            </div>
        {/if}

        <div class="flex flex-wrap items-center gap-2 pt-2">
            <button
                type="button"
                class="secondary-chip min-h-[44px]"
                disabled={busy || !currentInfo}
                onclick={onRevertBundled}
            >
                {t("settings.micron_wasm_update_revert_bundled")}
            </button>
            <div class="flex-1"></div>
            <button type="button" class="secondary-chip min-h-[44px]" onclick={close}>
                {t("common.close")}
            </button>
        </div>
    </div>
</Modal>

<style>
    .micron-wasm-dropzone:focus-visible {
        outline: 2px solid rgba(59, 130, 246, 0.45);
        outline-offset: 2px;
    }
</style>
