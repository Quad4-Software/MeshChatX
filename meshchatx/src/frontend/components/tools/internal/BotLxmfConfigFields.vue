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
            <label class="glass-label">{{ $t("bots.announce_enabled") }}</label>
            <select v-model="localDraft.announce_enabled" class="input-field">
                <option value="inherit">{{ $t("bots.inherit_lxmfy_default") }}</option>
                <option value="true">{{ $t("bots.enabled") }}</option>
                <option value="false">{{ $t("bots.disabled") }}</option>
            </select>
        </div>

        <div>
            <label class="glass-label">{{ $t("bots.stamp_cost") }}</label>
            <input v-model="localDraft.stamp_cost" type="number" min="0" class="input-field" />
            <p class="text-xs text-sem-fg-muted mt-1">
                {{ $t("bots.stamp_cost_hint") }}
            </p>
        </div>

        <h4 class="pt-2 text-xs font-semibold uppercase tracking-wide text-sem-fg-muted">
            {{ $t("bots.section_behaviour") }}
        </h4>

        <div>
            <label class="glass-label">{{ $t("bots.command_prefix") }}</label>
            <input
                v-model="localDraft.command_prefix"
                type="text"
                class="input-field font-mono"
                maxlength="8"
                spellcheck="false"
                placeholder="/"
            />
            <p class="text-xs text-sem-fg-muted mt-1">
                {{ $t("bots.command_prefix_hint") }}
            </p>
        </div>

        <div>
            <label class="glass-label">{{ $t("bots.first_message_enabled") }}</label>
            <select v-model="localDraft.first_message_enabled" class="input-field">
                <option value="inherit">{{ $t("bots.inherit_lxmfy_default") }}</option>
                <option value="true">{{ $t("bots.enabled") }}</option>
                <option value="false">{{ $t("bots.disabled") }}</option>
            </select>
        </div>

        <div>
            <label class="glass-label">{{ $t("bots.lxmf_commands_enabled") }}</label>
            <select v-model="localDraft.lxmf_commands_enabled" class="input-field">
                <option value="inherit">{{ $t("bots.inherit_lxmfy_default") }}</option>
                <option value="true">{{ $t("bots.enabled") }}</option>
                <option value="false">{{ $t("bots.disabled") }}</option>
            </select>
            <p class="text-xs text-sem-fg-muted mt-1">
                {{ $t("bots.lxmf_commands_enabled_hint") }}
            </p>
        </div>

        <div>
            <label class="glass-label">{{ $t("bots.message_queue_size") }}</label>
            <input v-model="localDraft.message_queue_size" type="number" min="1" max="10000" class="input-field" />
            <p class="text-xs text-sem-fg-muted mt-1">
                {{ $t("bots.message_queue_size_hint") }}
            </p>
        </div>

        <h4 class="pt-2 text-xs font-semibold uppercase tracking-wide text-sem-fg-muted">
            {{ $t("bots.section_antispam") }}
        </h4>

        <div class="grid grid-cols-2 gap-3">
            <div>
                <label class="glass-label">{{ $t("bots.rate_limit") }}</label>
                <input v-model="localDraft.rate_limit" type="number" min="0" max="1000" class="input-field" />
            </div>
            <div>
                <label class="glass-label">{{ $t("bots.cooldown") }}</label>
                <input v-model="localDraft.cooldown" type="number" min="0" max="86400" class="input-field" />
            </div>
            <div>
                <label class="glass-label">{{ $t("bots.max_warnings") }}</label>
                <input v-model="localDraft.max_warnings" type="number" min="0" max="100" class="input-field" />
            </div>
            <div>
                <label class="glass-label">{{ $t("bots.warning_timeout") }}</label>
                <input v-model="localDraft.warning_timeout" type="number" min="0" max="86400" class="input-field" />
            </div>
        </div>
        <p class="text-xs text-sem-fg-muted -mt-1">
            {{ $t("bots.antispam_hint") }}
        </p>

        <h4 class="pt-2 text-xs font-semibold uppercase tracking-wide text-sem-fg-muted">
            {{ $t("bots.section_security") }}
        </h4>

        <div>
            <label class="glass-label">{{ $t("bots.signature_verification_enabled") }}</label>
            <select v-model="localDraft.signature_verification_enabled" class="input-field">
                <option value="inherit">{{ $t("bots.inherit_lxmfy_default") }}</option>
                <option value="true">{{ $t("bots.enabled") }}</option>
                <option value="false">{{ $t("bots.disabled") }}</option>
            </select>
        </div>

        <div>
            <label class="glass-label">{{ $t("bots.require_message_signatures") }}</label>
            <select v-model="localDraft.require_message_signatures" class="input-field">
                <option value="inherit">{{ $t("bots.inherit_lxmfy_default") }}</option>
                <option value="true">{{ $t("bots.enabled") }}</option>
                <option value="false">{{ $t("bots.disabled") }}</option>
            </select>
        </div>

        <div>
            <label class="glass-label">{{ $t("bots.require_stamps") }}</label>
            <select v-model="localDraft.require_stamps" class="input-field">
                <option value="inherit">{{ $t("bots.inherit_lxmfy_default") }}</option>
                <option value="true">{{ $t("bots.enabled") }}</option>
                <option value="false">{{ $t("bots.disabled") }}</option>
            </select>
        </div>

        <div>
            <label class="glass-label">{{ $t("bots.request_unknown_identities") }}</label>
            <select v-model="localDraft.request_unknown_identities" class="input-field">
                <option value="inherit">{{ $t("bots.inherit_lxmfy_default") }}</option>
                <option value="true">{{ $t("bots.enabled") }}</option>
                <option value="false">{{ $t("bots.disabled") }}</option>
            </select>
        </div>

        <div>
            <label class="glass-label">{{ $t("bots.identity_pinning_enabled") }}</label>
            <select v-model="localDraft.identity_pinning_enabled" class="input-field">
                <option value="inherit">{{ $t("bots.inherit_lxmfy_default") }}</option>
                <option value="true">{{ $t("bots.enabled") }}</option>
                <option value="false">{{ $t("bots.disabled") }}</option>
            </select>
        </div>

        <div>
            <label class="glass-label">{{ $t("bots.permissions_enabled") }}</label>
            <select v-model="localDraft.permissions_enabled" class="input-field">
                <option value="inherit">{{ $t("bots.inherit_lxmfy_default") }}</option>
                <option value="true">{{ $t("bots.enabled") }}</option>
                <option value="false">{{ $t("bots.disabled") }}</option>
            </select>
        </div>

        <div>
            <label class="glass-label">{{ $t("bots.message_persistence_enabled") }}</label>
            <select v-model="localDraft.message_persistence_enabled" class="input-field">
                <option value="inherit">{{ $t("bots.inherit_lxmfy_default") }}</option>
                <option value="true">{{ $t("bots.enabled") }}</option>
                <option value="false">{{ $t("bots.disabled") }}</option>
            </select>
        </div>

        <div>
            <label class="glass-label">{{ $t("bots.admins") }}</label>
            <textarea
                v-model="localDraft.admins"
                class="input-field font-mono text-xs"
                rows="2"
                spellcheck="false"
                :placeholder="$t('bots.admins_placeholder')"
            ></textarea>
            <p class="text-xs text-sem-fg-muted mt-1">
                {{ $t("bots.admins_hint") }}
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
