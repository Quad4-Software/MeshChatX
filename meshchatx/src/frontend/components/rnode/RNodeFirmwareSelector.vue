<!-- SPDX-License-Identifier: 0BSD -->

<template>
    <div class="space-y-4">
        <div class="flex items-center gap-2">
            <div
                class="p-2 bg-purple-100 dark:bg-purple-900/30 rounded-lg text-purple-600 dark:text-purple-400 shrink-0"
            >
                <MaterialDesignIcon icon-name="file-download" class="size-5" />
            </div>
            <h2 class="font-bold text-gray-900 dark:text-zinc-100">
                {{ stepNumber }}. {{ $t("tools.rnode_flasher.select_firmware") }}
            </h2>
        </div>

        <div
            v-if="recommendedFirmwareFilename"
            class="p-4 rounded-xl border border-blue-100 dark:border-blue-900/30 bg-blue-50/50 dark:bg-blue-900/10 space-y-3"
        >
            <div class="flex items-center justify-between gap-2">
                <div class="text-xs font-bold text-blue-700 dark:text-blue-400 uppercase">
                    {{ $t("tools.rnode_flasher.download_recommended") }}
                </div>
                <span
                    v-if="latestRelease?.tag_name"
                    class="text-[10px] font-mono text-blue-600 dark:text-blue-300 bg-blue-100/60 dark:bg-blue-900/30 px-2 py-0.5 rounded-full"
                >
                    {{ latestRelease.tag_name }}
                </span>
            </div>
            <div class="text-sm text-gray-600 dark:text-zinc-400 break-all font-mono">
                {{ recommendedFirmwareFilename }}
            </div>
            <button
                :disabled="isDownloadingFirmware || !recommendedFirmwareFilename"
                class="w-full inline-flex items-center justify-center gap-2 rounded-xl bg-blue-600 hover:bg-blue-700 px-4 py-2.5 text-sm font-bold text-white transition-colors disabled:opacity-50"
                @click="$emit('download-recommended')"
            >
                <v-progress-circular v-if="isDownloadingFirmware" indeterminate size="16" width="2" />
                <MaterialDesignIcon v-else icon-name="cloud-download" class="size-4" />
                <span>
                    {{
                        isDownloadingFirmware
                            ? $t("tools.rnode_flasher.downloading")
                            : $t("tools.rnode_flasher.download_recommended")
                    }}
                </span>
            </button>
        </div>

        <div class="space-y-1">
            <label class="rnf-label">{{ $t("tools.rnode_flasher.select_firmware_file") }}</label>
            <input
                ref="file"
                type="file"
                accept=".zip"
                data-testid="rnode-firmware-file"
                class="block w-full text-sm text-gray-900 dark:text-zinc-100 border border-gray-200 dark:border-zinc-800 rounded-xl cursor-pointer bg-white dark:bg-zinc-900 focus:outline-none file:mr-4 file:py-2.5 file:px-4 file:border-0 file:text-sm file:font-bold file:bg-zinc-200 dark:file:bg-zinc-700 file:text-zinc-700 dark:file:text-zinc-200 hover:file:bg-zinc-300 dark:hover:file:bg-zinc-600"
                @change="onFileChange"
            />
        </div>

        <div
            v-if="firmwareFile"
            class="flex items-center justify-between gap-2 px-3 py-2 rounded-xl border border-emerald-200 dark:border-emerald-900/40 bg-emerald-50 dark:bg-emerald-900/10"
        >
            <div class="flex items-center gap-2 min-w-0">
                <MaterialDesignIcon
                    icon-name="check-circle"
                    class="size-4 text-emerald-600 dark:text-emerald-400 shrink-0"
                />
                <span class="text-xs font-mono truncate text-emerald-800 dark:text-emerald-200">
                    {{ firmwareFile.name }}
                </span>
            </div>
            <button
                type="button"
                class="text-[10px] font-bold uppercase text-emerald-700 dark:text-emerald-300 hover:underline"
                @click="clearFile"
            >
                {{ $t("common.clear") }}
            </button>
        </div>
    </div>
</template>

<script>
import MaterialDesignIcon from "../MaterialDesignIcon.vue";

export default {
    name: "RNodeFirmwareSelector",
    components: { MaterialDesignIcon },
    props: {
        stepNumber: { type: Number, default: 2 },
        recommendedFirmwareFilename: { type: String, default: null },
        latestRelease: { type: Object, default: null },
        isDownloadingFirmware: { type: Boolean, default: false },
        firmwareFile: { type: Object, default: null },
    },
    emits: ["download-recommended", "update:firmwareFile"],
    methods: {
        onFileChange(event) {
            const file = event.target.files?.[0] || null;
            this.$emit("update:firmwareFile", file);
        },
        clearFile() {
            if (this.$refs.file) {
                this.$refs.file.value = "";
            }
            this.$emit("update:firmwareFile", null);
        },
        setFile(file) {
            if (!this.$refs.file) return;
            const dataTransfer = new DataTransfer();
            dataTransfer.items.add(file);
            this.$refs.file.files = dataTransfer.files;
            this.$emit("update:firmwareFile", file);
        },
    },
};
</script>

<style scoped>
.rnf-label {
    @apply text-xs font-semibold text-gray-500 dark:text-zinc-500 uppercase tracking-wider;
}
</style>
