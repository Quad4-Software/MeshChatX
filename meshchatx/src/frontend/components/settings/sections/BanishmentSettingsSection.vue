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
            @update:model-value="emit('enabled-change', $event)"
        />

        <div v-if="config.banished_effect_enabled" class="space-y-4">
            <div class="space-y-2">
                <div class="text-sm font-medium text-sem-fg">
                    {{ $t("app.banished_text_label") }}
                </div>
                <input :value="config.banished_text" type="text" class="input-field" @input="onTextInput" />
                <div class="text-xs text-sem-fg-muted">
                    {{ $t("app.banished_text_description") }}
                </div>
            </div>

            <div class="space-y-2">
                <div class="text-sm font-medium text-sem-fg">
                    {{ $t("app.banished_color_label") }}
                </div>
                <div class="flex gap-2">
                    <input
                        :value="config.banished_color"
                        type="color"
                        class="color-fill-input w-12 h-10 rounded-xl border border-sem-border cursor-pointer"
                        @input="onColorInput"
                    />
                    <input
                        :value="config.banished_color"
                        type="text"
                        class="input-field monospace-field"
                        @input="onColorInput"
                    />
                </div>
                <div class="text-xs text-sem-fg-muted">
                    {{ $t("app.banished_color_description") }}
                </div>
            </div>
        </div>
    </SettingsSectionBlock>
</template>

<script setup lang="ts">
import SettingsSectionBlock from "../SettingsSectionBlock.vue";
import SettingToggleRow from "../SettingToggleRow.vue";

withDefaults(
    defineProps<{
        visible?: boolean;
        config: Record<string, any>;
    }>(),
    {
        visible: true,
    }
);

const emit = defineEmits<{
    "enabled-change": [value: boolean];
    "text-change": [value: string];
    "color-change": [value: string];
}>();

function onTextInput(event: Event) {
    emit("text-change", (event.target as HTMLInputElement).value);
}

function onColorInput(event: Event) {
    emit("color-change", (event.target as HTMLInputElement).value);
}
</script>
