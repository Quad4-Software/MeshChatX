<!-- SPDX-License-Identifier: 0BSD -->

<template>
    <div class="space-y-4">
        <div class="flex items-center gap-2">
            <div class="p-2 bg-sem-accent/10 rounded-lg text-sem-accent shrink-0">
                <MaterialDesignIcon icon-name="file-download" class="size-5" />
            </div>
            <h2 class="font-bold text-sem-fg">{{ stepNumber }}. {{ $t("tools.rnode_flasher.select_firmware") }}</h2>
        </div>

        <div class="space-y-1">
            <label class="rnf-label">{{ $t("tools.rnode_flasher.select_firmware_file") }}</label>
            <input
                ref="file"
                type="file"
                accept=".zip"
                data-testid="rnode-firmware-file"
                class="block w-full text-sm text-sem-fg border border-sem-border rounded-xl cursor-pointer bg-sem-surface focus:outline-hidden file:mr-4 file:py-2.5 file:px-4 file:border-0 file:text-sm file:font-bold file:bg-sem-surface-muted file:text-sem-fg hover:file:bg-sem-surface-raised"
                @change="onFileChange"
            />
        </div>

        <div
            v-if="firmwareFile"
            class="flex items-center justify-between gap-2 px-3 py-2 rounded-xl border border-sem-success/40 bg-sem-success/10"
        >
            <div class="flex items-center gap-2 min-w-0">
                <MaterialDesignIcon icon-name="check-circle" class="size-4 text-sem-success shrink-0" />
                <span class="text-xs font-mono truncate text-sem-success">
                    {{ firmwareFile.name }}
                </span>
            </div>
            <button
                type="button"
                class="text-[10px] font-bold uppercase text-sem-success hover:underline"
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
        firmwareFile: { type: Object, default: null },
    },
    emits: ["update:firmwareFile"],
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
@reference "../../style.css";
.rnf-label {
    @apply text-xs font-semibold text-sem-fg-muted uppercase tracking-wider;
}
</style>
