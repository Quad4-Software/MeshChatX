<!-- SPDX-License-Identifier: 0BSD -->

<template>
    <SettingsSectionBlock
        v-show="visible"
        eyebrow="Messages"
        :title="$t('gifs.settings_title')"
        :description="$t('gifs.settings_description')"
        body-class="space-y-4"
    >
        <div class="text-sm text-sem-fg-muted">
            {{ $t("gifs.count", { count: gifCount }) }}
        </div>
        <label class="flex items-center gap-2 text-sm text-sem-fg cursor-pointer">
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
                class="flex flex-col items-center justify-center gap-2 p-4 rounded-2xl border border-sem-warning dark:border-sem-border bg-white/50 dark:bg-sem-surface/80 hover:border-sem-warning transition group"
                @click="$emit('export')"
            >
                <MaterialDesignIcon
                    icon-name="export"
                    class="size-6 text-sem-warning group-hover:scale-110 transition"
                />
                <div class="text-sm font-bold">{{ $t("gifs.export") }}</div>
            </button>
            <button
                type="button"
                class="flex flex-col items-center justify-center gap-2 p-4 rounded-2xl border border-sem-success dark:border-sem-border bg-white/50 dark:bg-sem-surface/80 hover:border-sem-success transition group"
                @click="triggerImport"
            >
                <MaterialDesignIcon
                    icon-name="import"
                    class="size-6 text-sem-success group-hover:scale-110 transition"
                />
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
