<!-- SPDX-License-Identifier: 0BSD -->

<template>
    <div class="space-y-3">
        <div>
            <label class="glass-label">{{ $t("bots.custom_welcome") }}</label>
            <textarea
                :value="draft.welcome"
                class="input-field"
                rows="2"
                :placeholder="$t('bots.custom_welcome_placeholder')"
                @input="patch({ welcome: $event.target.value })"
            ></textarea>
            <p class="text-xs text-sem-fg-muted mt-1">
                {{ $t("bots.custom_welcome_hint") }}
            </p>
        </div>

        <div class="space-y-2">
            <label class="glass-label">{{ $t("bots.custom_commands") }}</label>
            <div v-for="(cmd, index) in draft.commands" :key="index" class="flex items-start gap-2">
                <input
                    :value="cmd.name"
                    type="text"
                    class="input-field font-mono text-xs w-28 sm:w-32 shrink-0"
                    maxlength="32"
                    spellcheck="false"
                    :placeholder="$t('bots.custom_command_name')"
                    @input="patchCommand(index, { name: $event.target.value })"
                />
                <input
                    :value="cmd.response"
                    type="text"
                    class="input-field text-xs min-w-0 flex-1"
                    :placeholder="$t('bots.custom_command_response')"
                    @input="patchCommand(index, { response: $event.target.value })"
                />
                <button
                    type="button"
                    class="p-2 rounded-lg text-sem-fg-muted hover:text-red-600 dark:hover:text-sem-danger hover:bg-sem-surface-muted/80 dark:hover:bg-sem-surface/80 shrink-0"
                    :title="$t('bots.custom_command_remove')"
                    @click="removeCommand(index)"
                >
                    <MaterialDesignIcon icon-name="close" class="size-4" />
                </button>
            </div>
            <button
                type="button"
                class="inline-flex items-center gap-1.5 text-xs font-medium text-sem-info hover:underline disabled:opacity-40"
                :disabled="draft.commands.length >= 64"
                @click="addCommand"
            >
                <MaterialDesignIcon icon-name="plus" class="size-4" />
                {{ $t("bots.custom_command_add") }}
            </button>
            <p class="text-xs text-sem-fg-muted">
                {{ $t("bots.custom_commands_hint") }}
            </p>
        </div>
    </div>
</template>

<script lang="ts">
export { buildCustomPayload, defaultCustomDraft, draftFromBotCustom } from "./botCustomDraft";
</script>

<script setup lang="ts">
import { computed } from "vue";
import MaterialDesignIcon from "../../MaterialDesignIcon.vue";
import { defaultCustomDraft, type CustomDraft } from "./botCustomDraft";

const props = withDefaults(
    defineProps<{
        modelValue?: CustomDraft | null;
    }>(),
    {
        modelValue: null,
    }
);

const emit = defineEmits<{
    "update:modelValue": [value: CustomDraft];
}>();

const draft = computed<CustomDraft>(() => props.modelValue || defaultCustomDraft());

function patch(update: Partial<CustomDraft>) {
    emit("update:modelValue", { ...draft.value, ...update });
}

function patchCommand(index: number, update: Partial<{ name: string; response: string; description: string }>) {
    const commands = draft.value.commands.map((c, i) => (i === index ? { ...c, ...update } : c));
    patch({ commands });
}

function addCommand() {
    patch({
        commands: [...draft.value.commands, { name: "", response: "", description: "" }],
    });
}

function removeCommand(index: number) {
    patch({
        commands: draft.value.commands.filter((_, i) => i !== index),
    });
}
</script>

<style scoped>
@reference "../../../style.css";
.glass-label {
    @apply block text-sm font-semibold text-sem-fg mb-1;
}
</style>
