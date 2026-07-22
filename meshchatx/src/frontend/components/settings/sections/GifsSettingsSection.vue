<!-- SPDX-License-Identifier: 0BSD -->

<template>
    <SettingsSectionBlock
        v-show="visible"
        eyebrow="Messages"
        :title="$t('gifs.settings_title')"
        :description="$t('gifs.settings_description')"
        body-class="space-y-4"
    >
        <div class="text-sm text-gray-600 dark:text-gray-400">
            {{ $t("gifs.count", { count: gifCount }) }}
        </div>
        <label class="flex items-center gap-2 text-sm text-gray-800 dark:text-gray-200 cursor-pointer">
            <input
                :checked="replaceDuplicates"
                type="checkbox"
                class="rounded-sm"
                @change="$emit('update:replaceDuplicates', $event.target.checked)"
            />
            {{ $t("gifs.replace_duplicates") }}
        </label>
        <div class="grid grid-cols-1 sm:grid-cols-2 gap-3">
            <button
                type="button"
                class="flex flex-col items-center justify-center gap-2 p-4 rounded-2xl border border-amber-200 dark:border-zinc-800 bg-white/50 dark:bg-zinc-800/50 hover:border-amber-500 transition group"
                @click="$emit('export')"
            >
                <MaterialDesignIcon icon-name="export" class="size-6 text-amber-500 group-hover:scale-110 transition" />
                <div class="text-sm font-bold">{{ $t("gifs.export") }}</div>
            </button>
            <button
                type="button"
                class="flex flex-col items-center justify-center gap-2 p-4 rounded-2xl border border-teal-200 dark:border-zinc-800 bg-white/50 dark:bg-zinc-800/50 hover:border-teal-500 transition group"
                @click="triggerImport"
            >
                <MaterialDesignIcon icon-name="import" class="size-6 text-teal-500 group-hover:scale-110 transition" />
                <div class="text-sm font-bold">{{ $t("gifs.import") }}</div>
            </button>
            <input
                ref="importFile"
                type="file"
                accept=".json,application/json"
                class="hidden"
                @change="onImportChange"
            />
        </div>
    </SettingsSectionBlock>
</template>

<script>
import MaterialDesignIcon from "../../MaterialDesignIcon.vue";
import SettingsSectionBlock from "../SettingsSectionBlock.vue";

export default {
    name: "GifsSettingsSection",
    components: {
        MaterialDesignIcon,
        SettingsSectionBlock,
    },
    props: {
        visible: {
            type: Boolean,
            default: true,
        },
        gifCount: {
            type: Number,
            default: 0,
        },
        replaceDuplicates: {
            type: Boolean,
            default: false,
        },
    },
    emits: ["export", "import", "update:replaceDuplicates"],
    methods: {
        triggerImport() {
            this.$refs.importFile?.click();
        },
        onImportChange(event) {
            this.$emit("import", event);
        },
    },
};
</script>
