<!-- SPDX-License-Identifier: 0BSD AND MIT -->

<template>
    <div class="inline-flex">
        <button
            type="button"
            class="my-auto inline-flex items-center gap-x-1 rounded-lg px-2 py-1.5 text-xs font-medium text-sem-fg-muted hover:bg-sem-surface-muted hover:text-gray-900 dark:hover:text-white transition-colors"
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
                    class="absolute bottom-0 -ml-11 sm:right-0 sm:ml-0 z-10 mb-10 rounded-xl bg-sem-surface shadow-lg ring-1 ring-gray-200 dark:ring-zinc-800 focus:outline-hidden"
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
        <input ref="image-input" type="file" accept="image/*" style="display: none" @change="onImageInputChange" />
    </div>
</template>

<script>
import Compressor from "compressorjs";
import DialogUtils from "../../../js/DialogUtils";
import MaterialDesignIcon from "../../MaterialDesignIcon.vue";
export default {
    name: "AddImageButton",
    components: {
        MaterialDesignIcon,
    },
    emits: ["add-image"],
    data() {
        return {
            isShowingMenu: false,
            selectedImageQuality: null,
        };
    },
    methods: {
        showMenu() {
            this.isShowingMenu = true;
        },
        hideMenu() {
            this.isShowingMenu = false;
        },
        addImage(quality) {
            this.isShowingMenu = false;
            this.selectedImageQuality = quality;
            this.$refs["image-input"].click();
        },
        clearImageInput: function () {
            this.$refs["image-input"].value = null;
        },
        onImageInputChange: async function (event) {
            if (event.target.files.length > 0) {
                // get selected file
                const file = event.target.files[0];

                // process file based on selected image quality
                switch (this.selectedImageQuality) {
                    case "low": {
                        new Compressor(file, {
                            maxWidth: 320,
                            maxHeight: 320,
                            quality: 0.2,
                            mimeType: "image/webp",
                            success: (result) => {
                                // ensure result is a File with the same name as original
                                const compressedFile = new File([result], file.name, { type: result.type });
                                this.$emit("add-image", compressedFile);
                            },
                            error: (err) => {
                                DialogUtils.alert(err.message);
                            },
                        });
                        break;
                    }
                    case "medium": {
                        new Compressor(file, {
                            maxWidth: 640,
                            maxHeight: 640,
                            quality: 0.6,
                            mimeType: "image/webp",
                            success: (result) => {
                                // ensure result is a File with the same name as original
                                const compressedFile = new File([result], file.name, { type: result.type });
                                this.$emit("add-image", compressedFile);
                            },
                            error: (err) => {
                                DialogUtils.alert(err.message);
                            },
                        });
                        break;
                    }
                    case "high": {
                        new Compressor(file, {
                            maxWidth: 1280,
                            maxHeight: 1280,
                            quality: 0.75,
                            mimeType: "image/webp",
                            success: (result) => {
                                // ensure result is a File with the same name as original
                                const compressedFile = new File([result], file.name, { type: result.type });
                                this.$emit("add-image", compressedFile);
                            },
                            error: (err) => {
                                DialogUtils.alert(err.message);
                            },
                        });
                        break;
                    }
                    case "original": {
                        this.$emit("add-image", file);
                        break;
                    }
                    default: {
                        DialogUtils.alert(`Unsupported image quality: ${this.selectedImageQuality}`);
                        break;
                    }
                }

                // clear image input to allow selecting the same file after user removed it
                this.clearImageInput();
            }
        },
    },
};
</script>
