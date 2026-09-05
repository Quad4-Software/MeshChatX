<!-- SPDX-License-Identifier: 0BSD -->

<script lang="ts">
    import Compressor from "compressorjs";
    import MaterialDesignIcon from "../../../../ui/svelte/MaterialDesignIcon.svelte";
    import ToastUtils from "../../../../js/ToastUtils.js";
    import { t } from "../../../../js/i18n.js";

    let {
        onaddimage,
    }: {
        onaddimage?: (file: File) => void;
    } = $props();

    let isShowingMenu = $state(false);
    let selectedImageQuality: string | null = $state(null);
    let imageInput: HTMLInputElement | undefined = $state();
    let rootEl: HTMLDivElement | undefined = $state();

    function addImage(quality: string) {
        isShowingMenu = false;
        selectedImageQuality = quality;
        imageInput?.click();
    }

    function clearImageInput() {
        if (imageInput) imageInput.value = "";
    }

    function emitCompressed(file: File, result: Blob | File) {
        const compressedFile = new File([result], file.name, { type: result.type });
        onaddimage?.(compressedFile);
    }

    function onImageInputChange(event: Event) {
        const input = event.currentTarget as HTMLInputElement;
        if (!input.files || input.files.length === 0) return;
        const file = input.files[0];
        switch (selectedImageQuality) {
            case "low":
                new Compressor(file, {
                    maxWidth: 320,
                    maxHeight: 320,
                    quality: 0.2,
                    mimeType: "image/webp",
                    success: (result) => emitCompressed(file, result),
                    error: (err) => ToastUtils.error(err.message),
                });
                break;
            case "medium":
                new Compressor(file, {
                    maxWidth: 640,
                    maxHeight: 640,
                    quality: 0.6,
                    mimeType: "image/webp",
                    success: (result) => emitCompressed(file, result),
                    error: (err) => ToastUtils.error(err.message),
                });
                break;
            case "high":
                new Compressor(file, {
                    maxWidth: 1280,
                    maxHeight: 1280,
                    quality: 0.75,
                    mimeType: "image/webp",
                    success: (result) => emitCompressed(file, result),
                    error: (err) => ToastUtils.error(err.message),
                });
                break;
            case "original":
                onaddimage?.(file);
                break;
            default:
                ToastUtils.warning(`Unsupported image quality: ${selectedImageQuality}`);
                break;
        }
        clearImageInput();
    }

    $effect(() => {
        if (!isShowingMenu) return;
        const onDoc = (event: MouseEvent) => {
            if (rootEl && !rootEl.contains(event.target as Node)) {
                isShowingMenu = false;
            }
        };
        document.addEventListener("mousedown", onDoc, true);
        return () => document.removeEventListener("mousedown", onDoc, true);
    });
</script>

<div bind:this={rootEl} class="inline-flex">
    <button
        type="button"
        class="my-auto inline-flex items-center gap-x-1 rounded-lg px-2 py-1.5 text-xs font-medium text-sem-fg-muted hover:bg-sem-surface-muted hover:text-gray-900 dark:hover:text-white transition-colors focus-ring-sem"
        onclick={() => {
            isShowingMenu = true;
        }}
    >
        <MaterialDesignIcon iconName="image-plus" class="w-4 h-4" />
        <span class="hidden sm:inline whitespace-nowrap">{t("messages.add_image")}</span>
    </button>

    <div class="relative block">
        {#if isShowingMenu}
            <div
                class="absolute bottom-0 -ml-11 sm:right-0 sm:ml-0 z-10 mb-10 rounded-xl bg-sem-surface shadow-lg ring-1 ring-gray-200 dark:ring-zinc-800 focus:outline-hidden"
            >
                <div class="py-1">
                    <button
                        type="button"
                        class="w-full block text-left px-4 py-2 text-sm text-sem-fg-muted hover:bg-sem-surface-muted whitespace-nowrap"
                        onclick={() => addImage("low")}
                    >
                        {t("messages.image_quality_low")}
                    </button>
                    <button
                        type="button"
                        class="w-full block text-left px-4 py-2 text-sm text-sem-fg-muted hover:bg-sem-surface-muted whitespace-nowrap"
                        onclick={() => addImage("medium")}
                    >
                        {t("messages.image_quality_medium")}
                    </button>
                    <button
                        type="button"
                        class="w-full block text-left px-4 py-2 text-sm text-sem-fg-muted hover:bg-sem-surface-muted whitespace-nowrap"
                        onclick={() => addImage("high")}
                    >
                        {t("messages.image_quality_high")}
                    </button>
                    <button
                        type="button"
                        class="w-full block text-left px-4 py-2 text-sm text-sem-fg-muted hover:bg-sem-surface-muted whitespace-nowrap"
                        onclick={() => addImage("original")}
                    >
                        {t("messages.image_quality_original")}
                    </button>
                </div>
            </div>
        {/if}
    </div>

    <input bind:this={imageInput} type="file" accept="image/*" class="hidden" onchange={onImageInputChange} />
</div>
