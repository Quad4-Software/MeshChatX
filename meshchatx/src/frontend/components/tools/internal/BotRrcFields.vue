<!-- SPDX-License-Identifier: 0BSD -->

<template>
    <div class="space-y-3">
        <div>
            <label class="glass-label">{{ $t("bots.rrc_hub_hash") }}</label>
            <input
                :value="draft.hub"
                type="text"
                class="input-field font-mono text-xs"
                maxlength="64"
                spellcheck="false"
                :placeholder="$t('bots.rrc_hub_hash_placeholder')"
                @input="patch({ hub: $event.target.value })"
            />
        </div>
        <div>
            <label class="glass-label">{{ $t("bots.rrc_rooms") }}</label>
            <input
                :value="draft.rooms"
                type="text"
                class="input-field"
                :placeholder="$t('bots.rrc_rooms_placeholder')"
                @input="patch({ rooms: $event.target.value })"
            />
        </div>
        <div class="grid grid-cols-2 gap-3">
            <div>
                <label class="glass-label">{{ $t("bots.rrc_nick") }}</label>
                <input
                    :value="draft.nick"
                    type="text"
                    class="input-field"
                    maxlength="32"
                    @input="patch({ nick: $event.target.value })"
                />
            </div>
            <div>
                <label class="glass-label">{{ $t("bots.rrc_prefix") }}</label>
                <input
                    :value="draft.prefix"
                    type="text"
                    class="input-field font-mono"
                    maxlength="4"
                    @input="patch({ prefix: $event.target.value })"
                />
            </div>
        </div>
        <div class="flex items-center justify-between gap-3">
            <label class="text-sm font-medium text-sem-fg">{{ $t("bots.rrc_mention_only") }}</label>
            <input
                type="checkbox"
                class="size-4 accent-sem-accent"
                :checked="draft.mention_only"
                @change="patch({ mention_only: $event.target.checked })"
            />
        </div>
        <div>
            <label class="glass-label">{{ $t("bots.rrc_rate_seconds") }}</label>
            <input
                :value="draft.rate_seconds"
                type="number"
                min="0"
                max="3600"
                class="input-field"
                @input="patch({ rate_seconds: $event.target.value })"
            />
            <p class="text-xs text-sem-fg-muted mt-1">
                {{ $t("bots.rrc_rate_seconds_hint") }}
            </p>
        </div>
    </div>
</template>

<script lang="ts">
export { buildRrcPayload, defaultRrcDraft, draftFromBotRrc } from "./botRrcDraft";
</script>

<script setup lang="ts">
import { computed } from "vue";
import { defaultRrcDraft, type RrcDraft } from "./botRrcDraft";

const props = withDefaults(
    defineProps<{
        modelValue?: RrcDraft | null;
    }>(),
    {
        modelValue: null,
    }
);

const emit = defineEmits<{
    "update:modelValue": [value: RrcDraft];
}>();

const draft = computed<RrcDraft>(() => props.modelValue || defaultRrcDraft());

function patch(update: Partial<RrcDraft>) {
    emit("update:modelValue", { ...draft.value, ...update });
}
</script>

<style scoped>
@reference "../../../style.css";
.glass-label {
    @apply block text-sm font-semibold text-sem-fg mb-1;
}
</style>
