<!-- SPDX-License-Identifier: 0BSD AND MIT -->

<template>
    <div class="inline-flex">
        <button
            type="button"
            class="my-auto inline-flex items-center gap-x-1 rounded-lg px-2 py-1.5 text-xs font-medium text-sem-fg-muted hover:bg-sem-surface-muted hover:text-sem-fg dark:hover:text-white transition-colors"
            @click="showMenu"
        >
            <MaterialDesignIcon icon-name="image-plus" class="w-4 h-4" />
            <span class="hidden sm:inline whitespace-nowrap">{{ $t("messages.add_image") }}</span>
        </button>

        <div class="relative block">
            <Transition
                enter-active-class="transition ease-out duration-100"
                enter-from-class="transform opacity-0 scale-95"
                enter-to-class="transform opacity-100 scale-100"
                leave-active-class="transition ease-in duration-75"
                leave-from-class="transform opacity-100 scale-100"
                leave-to-class="transform opacity-0 scale-95"
            >
                <div
                    v-if="isShowingMenu"
                    v-click-outside="hideMenu"
                    class="absolute bottom-0 -ml-11 sm:right-0 sm:ml-0 z-10 mb-10 rounded-xl bg-sem-surface shadow-lg ring-1 ring-sem-border focus:outline-hidden"
                >
                    <div class="py-1">
                        <button
                            type="button"
                            class="w-full block text-left px-4 py-2 text-sm text-sem-fg-muted hover:bg-sem-surface-muted whitespace-nowrap"
                            @click="addImage('low')"
                        >
                            {{ $t("messages.image_quality_low") }}
                        </button>
                        <button
                            type="button"
                            class="w-full block text-left px-4 py-2 text-sm text-sem-fg-muted hover:bg-sem-surface-muted whitespace-nowrap"
                            @click="addImage('medium')"
                        >
                            {{ $t("messages.image_quality_medium") }}
                        </button>
                        <button
                            type="button"
                            class="w-full block text-left px-4 py-2 text-sm text-sem-fg-muted hover:bg-sem-surface-muted whitespace-nowrap"
                            @click="addImage('high')"
                        >
                            {{ $t("messages.image_quality_high") }}
                        </button>
                        <button
                            type="button"
                            class="w-full block text-left px-4 py-2 text-sm text-sem-fg-muted hover:bg-sem-surface-muted whitespace-nowrap"
                            @click="addImage('original')"
                        >
                            {{ $t("messages.image_quality_original") }}
                        </button>
                    </div>
                </div>
            </Transition>
        </div>

        <!-- hidden file input for selecting files -->
        <input ref="imageInput" type="file" accept="image/*" style="display: none" @change="onImageInputChange" />
    </div>
</template>

<script setup lang="ts">
import Compressor from "compressorjs";
import { ref } from "vue";
import DialogUtils from "../../../js/DialogUtils";
import MaterialDesignIcon from "../../MaterialDesignIcon.vue";

const emit = defineEmits<{
    "add-image": [file: File];
}>();

const isShowingMenu = ref(false);
const selectedImageQuality = ref<string | null>(null);

const imageInput = ref<HTMLInputElement | null>(null);

function showMenu() {
    isShowingMenu.value = true;
}

function hideMenu() {
    isShowingMenu.value = false;
}

function addImage(quality: string) {
    isShowingMenu.value = false;
    selectedImageQuality.value = quality;
    imageInput.value?.click();
}

function clearImageInput() {
    if (imageInput.value) {
        imageInput.value.value = "";
    }
}

const COMPRESSION_PRESETS: Record<string, { maxWidth: number; maxHeight: number; quality: number }> = {
    low: { maxWidth: 320, maxHeight: 320, quality: 0.2 },
    medium: { maxWidth: 640, maxHeight: 640, quality: 0.6 },
    high: { maxWidth: 1280, maxHeight: 1280, quality: 0.75 },
};

async function onImageInputChange(event: Event) {
    const target = event.target as HTMLInputElement;
    const files = target.files;
    if (!files || files.length === 0) {
        return;
    }

    // get selected file
    const file = files[0];
    const quality = selectedImageQuality.value || "";
    const preset = COMPRESSION_PRESETS[quality];

    if (quality === "original") {
        emit("add-image", file);
    } else if (preset) {
        new Compressor(file, {
            ...preset,
            mimeType: "image/webp",
            success: (result: Blob) => {
                // ensure result is a File with the same name as original
                const compressedFile = new File([result], file.name, { type: result.type });
                emit("add-image", compressedFile);
            },
            error: (err: Error) => {
                DialogUtils.alert(err.message);
            },
        });
    } else {
        DialogUtils.alert(`Unsupported image quality: ${quality}`);
    }

    // clear image input to allow selecting the same file after user removed it
    clearImageInput();
}

defineExpose({ clearImageInput });
</script>
