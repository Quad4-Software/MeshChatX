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
                    class="p-2 rounded-lg text-gray-400 hover:text-red-600 dark:hover:text-red-400 hover:bg-gray-100/80 dark:hover:bg-zinc-800/80 shrink-0"
                    :title="$t('bots.custom_command_remove')"
                    @click="removeCommand(index)"
                >
                    <MaterialDesignIcon icon-name="close" class="size-4" />
                </button>
            </div>
            <button
                type="button"
                class="inline-flex items-center gap-1.5 text-xs font-medium text-blue-600 dark:text-blue-400 hover:underline disabled:opacity-40"
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

<script>
import MaterialDesignIcon from "../../MaterialDesignIcon.vue";

export function defaultCustomDraft() {
    return { welcome: "", commands: [] };
}

export function draftFromBotCustom(custom) {
    const draft = defaultCustomDraft();
    if (!custom || typeof custom !== "object") {
        return draft;
    }
    if (typeof custom.welcome === "string") {
        draft.welcome = custom.welcome;
    }
    if (Array.isArray(custom.commands)) {
        draft.commands = custom.commands
            .filter((c) => c && typeof c === "object" && c.name)
            .map((c) => ({
                name: String(c.name),
                response: String(c.response || ""),
                description: c.description ? String(c.description) : "",
            }));
    }
    return draft;
}

export function buildCustomPayload(draft) {
    const commands = (draft.commands || [])
        .map((c) => ({
            name: String(c.name || "").trim(),
            response: String(c.response || "").trim(),
            description: String(c.description || "").trim(),
        }))
        .filter((c) => c.name && c.response)
        .map((c) => {
            const out = { name: c.name, response: c.response };
            if (c.description) {
                out.description = c.description;
            }
            return out;
        });
    const payload = { commands };
    const welcome = String(draft.welcome || "").trim();
    if (welcome) {
        payload.welcome = welcome;
    }
    return payload;
}

export default {
    name: "BotCustomCommandsEditor",
    components: {
        MaterialDesignIcon,
    },
    props: {
        modelValue: {
            type: Object,
            default: null,
        },
    },
    emits: ["update:modelValue"],
    computed: {
        draft() {
            return this.modelValue || defaultCustomDraft();
        },
    },
    methods: {
        patch(update) {
            this.$emit("update:modelValue", { ...this.draft, ...update });
        },
        patchCommand(index, update) {
            const commands = this.draft.commands.map((c, i) => (i === index ? { ...c, ...update } : c));
            this.patch({ commands });
        },
        addCommand() {
            this.patch({
                commands: [...this.draft.commands, { name: "", response: "", description: "" }],
            });
        },
        removeCommand(index) {
            this.patch({
                commands: this.draft.commands.filter((_, i) => i !== index),
            });
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
