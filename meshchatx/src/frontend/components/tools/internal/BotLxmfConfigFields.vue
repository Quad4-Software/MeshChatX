<!-- SPDX-License-Identifier: 0BSD -->

<template>
    <div class="space-y-3">
        <div>
            <label class="glass-label">{{ $t("bots.propagation_mode") }}</label>
            <select v-model="localDraft.propagation_mode" class="input-field">
                <option value="inherit">{{ $t("bots.propagation_mode_inherit") }}</option>
                <option value="manual">{{ $t("bots.propagation_mode_manual") }}</option>
                <option value="autopeer">{{ $t("bots.propagation_mode_autopeer") }}</option>
                <option value="none">{{ $t("bots.propagation_mode_none") }}</option>
            </select>
        </div>

        <div v-if="localDraft.propagation_mode === 'manual'">
            <label class="glass-label">{{ $t("bots.propagation_node_hash") }}</label>
            <input
                v-model="localDraft.propagation_node"
                type="text"
                class="input-field font-mono text-xs"
                maxlength="64"
                spellcheck="false"
            />
        </div>

        <div>
            <label class="glass-label">{{ $t("bots.propagation_fallback") }}</label>
            <select v-model="localDraft.propagation_fallback_enabled" class="input-field">
                <option value="inherit">{{ $t("bots.inherit_host_default") }}</option>
                <option value="true">{{ $t("bots.enabled") }}</option>
                <option value="false">{{ $t("bots.disabled") }}</option>
            </select>
        </div>

        <div>
            <label class="glass-label">{{ $t("bots.direct_delivery_retries") }}</label>
            <input v-model="localDraft.direct_delivery_retries" type="number" min="0" max="32" class="input-field" />
            <p class="text-xs text-sem-fg-muted mt-1">
                {{ $t("bots.direct_delivery_retries_hint") }}
            </p>
        </div>

        <div>
            <label class="glass-label">{{ $t("bots.opportunistic_sending") }}</label>
            <select v-model="localDraft.opportunistic_sending" class="input-field">
                <option value="inherit">{{ $t("bots.inherit_host_default") }}</option>
                <option value="true">{{ $t("bots.enabled") }}</option>
                <option value="false">{{ $t("bots.disabled") }}</option>
            </select>
        </div>

        <div>
            <label class="glass-label">{{ $t("bots.announce_interval_seconds") }}</label>
            <input
                v-model="localDraft.announce_interval_seconds"
                type="number"
                min="30"
                max="86400"
                class="input-field"
            />
            <p class="text-xs text-sem-fg-muted mt-1">
                {{ $t("bots.announce_interval_hint") }}
            </p>
        </div>

        <div>
            <label class="glass-label">{{ $t("bots.stamp_cost") }}</label>
            <input v-model="localDraft.stamp_cost" type="number" min="0" class="input-field" />
            <p class="text-xs text-sem-fg-muted mt-1">
                {{ $t("bots.stamp_cost_hint") }}
            </p>
        </div>
    </div>
</template>

<script>
import { defaultLxmfConfigDraft } from "./botLxmfConfigForm.js";

export default {
    name: "BotLxmfConfigFields",
    props: {
        modelValue: {
            type: Object,
            default: null,
        },
    },
    emits: ["update:modelValue"],
    computed: {
        localDraft: {
            get() {
                return this.modelValue || defaultLxmfConfigDraft();
            },
            set(value) {
                this.$emit("update:modelValue", value);
            },
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
