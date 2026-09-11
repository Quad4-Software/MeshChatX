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
                class="size-4 accent-blue-600"
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

<script>
export function defaultRrcDraft() {
    return {
        hub: "",
        rooms: "",
        nick: "",
        mention_only: true,
        prefix: "!",
        rate_seconds: "8",
    };
}

export function buildRrcPayload(draft) {
    const rooms = String(draft.rooms || "")
        .split(",")
        .map((r) => r.trim().replace(/^#+/, ""))
        .filter(Boolean);
    return {
        hub: String(draft.hub || "")
            .trim()
            .toLowerCase(),
        rooms,
        nick: String(draft.nick || "").trim() || null,
        mention_only: Boolean(draft.mention_only),
        prefix: String(draft.prefix || "!"),
        rate_seconds: Math.max(0, Math.min(3600, Number(draft.rate_seconds) || 8)),
    };
}

export default {
    name: "BotRrcFields",
    props: {
        modelValue: {
            type: Object,
            default: null,
        },
    },
    emits: ["update:modelValue"],
    computed: {
        draft() {
            return this.modelValue || defaultRrcDraft();
        },
    },
    methods: {
        patch(update) {
            this.$emit("update:modelValue", { ...this.draft, ...update });
        },
    },
};
</script>

<style scoped>
@reference "../../../style.css";
.glass-label {
    @apply block text-sm font-semibold text-gray-700 dark:text-gray-300 mb-1;
}
</style>
