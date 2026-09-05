<!-- SPDX-License-Identifier: 0BSD -->

<script lang="ts">
    import { t } from "../../../js/i18n.js";
    import { defaultLxmfConfigDraft, type LxmfConfigDraft } from "../lib/botLxmfConfigForm.js";

    let {
        draft = $bindable(defaultLxmfConfigDraft()),
    }: {
        draft?: LxmfConfigDraft;
    } = $props();
</script>

<div class="space-y-3">
    <div>
        <label class="glass-label" for="bot-prop-mode">{t("bots.propagation_mode")}</label>
        <select id="bot-prop-mode" bind:value={draft.propagation_mode} class="input-field">
            <option value="inherit">{t("bots.propagation_mode_inherit")}</option>
            <option value="manual">{t("bots.propagation_mode_manual")}</option>
            <option value="autopeer">{t("bots.propagation_mode_autopeer")}</option>
            <option value="none">{t("bots.propagation_mode_none")}</option>
        </select>
    </div>

    {#if draft.propagation_mode === "manual"}
        <div>
            <label class="glass-label" for="bot-prop-node">{t("bots.propagation_node_hash")}</label>
            <input
                id="bot-prop-node"
                bind:value={draft.propagation_node}
                type="text"
                class="input-field font-mono text-xs"
                maxlength={64}
                spellcheck="false"
            />
        </div>
    {/if}

    <div>
        <label class="glass-label" for="bot-prop-fallback">{t("bots.propagation_fallback")}</label>
        <select id="bot-prop-fallback" bind:value={draft.propagation_fallback_enabled} class="input-field">
            <option value="inherit">{t("bots.inherit_host_default")}</option>
            <option value="true">{t("bots.enabled")}</option>
            <option value="false">{t("bots.disabled")}</option>
        </select>
    </div>

    <div>
        <label class="glass-label" for="bot-direct-retries">{t("bots.direct_delivery_retries")}</label>
        <input
            id="bot-direct-retries"
            bind:value={draft.direct_delivery_retries}
            type="number"
            min={0}
            max={32}
            class="input-field"
        />
        <p class="text-xs text-sem-fg-muted mt-1">
            {t("bots.direct_delivery_retries_hint")}
        </p>
    </div>

    <div>
        <label class="glass-label" for="bot-opportunistic">{t("bots.opportunistic_sending")}</label>
        <select id="bot-opportunistic" bind:value={draft.opportunistic_sending} class="input-field">
            <option value="inherit">{t("bots.inherit_host_default")}</option>
            <option value="true">{t("bots.enabled")}</option>
            <option value="false">{t("bots.disabled")}</option>
        </select>
    </div>

    <div>
        <label class="glass-label" for="bot-announce-int">{t("bots.announce_interval_seconds")}</label>
        <input
            id="bot-announce-int"
            bind:value={draft.announce_interval_seconds}
            type="number"
            min={30}
            max={86400}
            class="input-field"
        />
        <p class="text-xs text-sem-fg-muted mt-1">
            {t("bots.announce_interval_hint")}
        </p>
    </div>

    <div>
        <label class="glass-label" for="bot-stamp-cost">{t("bots.stamp_cost")}</label>
        <input id="bot-stamp-cost" bind:value={draft.stamp_cost} type="number" min={0} class="input-field" />
        <p class="text-xs text-sem-fg-muted mt-1">
            {t("bots.stamp_cost_hint")}
        </p>
    </div>
</div>

<style>
    .glass-label {
        display: block;
        font-size: 0.875rem;
        font-weight: 600;
        margin-bottom: 0.25rem;
    }
</style>
