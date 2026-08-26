<!-- SPDX-License-Identifier: 0BSD -->

<template>
    <SettingsSectionBlock
        v-show="visible"
        :eyebrow="$t('app.privacy_eyebrow')"
        :title="$t('app.banishment')"
        :description="$t('app.banishment_description')"
        body-class="space-y-4"
    >
        <SettingToggleRow
            id="banished-effect-enabled"
            :model-value="config.banished_effect_enabled"
            :title="$t('app.banished_effect_enabled')"
            :description="$t('app.banished_effect_description')"
            @update:model-value="$emit('enabled-change', $event)"
        />

        <div v-if="config.banished_effect_enabled" class="space-y-4">
            <div class="space-y-2">
                <div class="text-sm font-medium text-gray-900 dark:text-gray-100">
                    {{ $t("app.banished_text_label") }}
                </div>
                <input
                    :value="config.banished_text"
                    type="text"
                    class="input-field"
                    @input="$emit('text-change', $event.target.value)"
                />
                <div class="text-xs text-gray-600 dark:text-gray-400">
                    {{ $t("app.banished_text_description") }}
                </div>
            </div>

            <div class="space-y-2">
                <div class="text-sm font-medium text-gray-900 dark:text-gray-100">
                    {{ $t("app.banished_color_label") }}
                </div>
                <div class="flex gap-2">
                    <input
                        :value="config.banished_color"
                        type="color"
                        class="color-fill-input w-12 h-10 rounded-xl border border-sem-border cursor-pointer"
                        @input="$emit('color-change', $event.target.value)"
                    />
                    <input
                        :value="config.banished_color"
                        type="text"
                        class="input-field monospace-field"
                        @input="$emit('color-change', $event.target.value)"
                    />
                </div>
                <div class="text-xs text-gray-600 dark:text-gray-400">
                    {{ $t("app.banished_color_description") }}
                </div>
            </div>
        </div>
    </SettingsSectionBlock>
</template>

<script>
import SettingsSectionBlock from "../SettingsSectionBlock.vue";
import SettingToggleRow from "../SettingToggleRow.vue";

export default {
    name: "BanishmentSettingsSection",
    components: {
        SettingsSectionBlock,
        SettingToggleRow,
    },
    props: {
        visible: {
            type: Boolean,
            default: true,
        },
        config: {
            type: Object,
            required: true,
        },
    },
    emits: ["enabled-change", "text-change", "color-change"],
};
</script>
