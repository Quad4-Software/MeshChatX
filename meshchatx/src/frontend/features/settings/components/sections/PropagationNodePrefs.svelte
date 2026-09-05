<!-- SPDX-License-Identifier: 0BSD -->

<script lang="ts">
    import Toggle from "../Toggle.svelte";
    import ToastUtils from "../../../../js/ToastUtils.js";
    import Utils from "../../../../js/Utils.js";
    import { t } from "../../../../js/i18n.js";

    interface Props {
        config: Record<string, any>;
        onupdatefield?: (data: { key: string; value: any }) => void;
        onsavepreferredhash?: (showToast?: boolean) => void;
        onclearpreferredhash?: () => void;
    }

    let { config, onupdatefield, onsavepreferredhash, onclearpreferredhash }: Props = $props();

    function emitToggle(key: string, value: boolean) {
        onupdatefield?.({ key, value });
    }

    function emitValue(key: string, value: any) {
        onupdatefield?.({ key, value });
    }

    async function pastePreferredHash() {
        try {
            const text = await navigator.clipboard.readText();
            if (text && text.trim()) {
                emitValue("lxmf_preferred_propagation_node_destination_hash", text.trim());
            }
        } catch {
            ToastUtils.error(t("common.copy_failed"));
        }
    }
</script>

<label class="setting-toggle">
    <Toggle
        id="local-propagation-node"
        checked={Boolean(config.lxmf_local_propagation_node_enabled)}
        onchange={(val) => emitToggle("lxmf_local_propagation_node_enabled", val)}
    />
    <span class="setting-toggle__label">
        <span class="setting-toggle__title">{t("app.run_local_node")}</span>
        <span class="setting-toggle__description">{t("app.run_local_node_description")}</span>
        <span class="setting-toggle__hint monospace-field">
            {config.lxmf_local_propagation_node_address_hash || "-"}
        </span>
    </span>
</label>

<label class="setting-toggle">
    <Toggle
        id="auto-select-propagation-node"
        checked={Boolean(config.lxmf_preferred_propagation_node_auto_select)}
        onchange={(val) => emitToggle("lxmf_preferred_propagation_node_auto_select", val)}
    />
    <span class="setting-toggle__label">
        <span class="setting-toggle__title">{t("app.auto_select_node")}</span>
        <span class="setting-toggle__description">{t("app.auto_select_node_description")}</span>
        {#if config.lxmf_preferred_propagation_node_auto_select}
            <span class="setting-toggle__hint block mt-1 text-xs text-sem-fg-muted">
                {#if config.lxmf_preferred_propagation_node_destination_hash}
                    <span class="block">{t("app.auto_select_using_label")}</span>
                    <span class="monospace-field break-all block mt-0.5">
                        {config.lxmf_preferred_propagation_node_destination_hash}
                    </span>
                {:else}
                    {t("app.auto_select_pending")}
                {/if}
            </span>
        {/if}
    </span>
</label>

<div class="space-y-2">
    <label for="preferred-prop-node-hash" class="text-sm font-medium text-sem-fg block">
        {t("app.preferred_propagation_node")}
    </label>
    <div class="flex flex-col sm:flex-row gap-2">
        <input
            id="preferred-prop-node-hash"
            value={config.lxmf_preferred_propagation_node_destination_hash || ""}
            type="text"
            spellcheck="false"
            autocomplete="off"
            placeholder={t("app.preferred_node_placeholder")}
            class="input-field monospace-field flex-1 min-w-0"
            oninput={(e) => {
                config.lxmf_preferred_propagation_node_destination_hash = (e.target as HTMLInputElement).value;
            }}
            onkeydown={(e) => {
                if (e.key === "Enter") {
                    e.preventDefault();
                    onsavepreferredhash?.(true);
                }
            }}
        />
        <button type="button" class="secondary-chip shrink-0 cursor-pointer" onclick={pastePreferredHash}>
            {t("tools.propagation_nodes.paste_hash")}
        </button>
        <button type="button" class="primary-chip shrink-0 cursor-pointer" onclick={() => onsavepreferredhash?.(true)}>
            {t("tools.propagation_nodes.set_preferred")}
        </button>
        {#if config.lxmf_preferred_propagation_node_destination_hash}
            <button type="button" class="secondary-chip shrink-0 cursor-pointer" onclick={onclearpreferredhash}>
                {t("tools.propagation_nodes.clear_preferred")}
            </button>
        {/if}
    </div>
    <div class="text-xs text-sem-fg-muted">
        {t("app.fallback_node_description")}
    </div>
    <div class="text-xs text-sem-fg-muted">
        {t("tools.propagation_nodes.manual_hint")}
    </div>
</div>

<div class="space-y-2">
    <label for="auto-sync-interval-select" class="text-sm font-medium text-sem-fg block">
        {t("app.auto_sync_interval")}
    </label>
    <select
        id="auto-sync-interval-select"
        value={config.lxmf_preferred_propagation_node_auto_sync_interval_seconds ?? 0}
        class="input-field"
        onchange={(e) =>
            emitValue(
                "lxmf_preferred_propagation_node_auto_sync_interval_seconds",
                Number((e.target as HTMLSelectElement).value)
            )}
    >
        <option value={0}>{t("app.disabled")}</option>
        <option value={900}>Every 15 Minutes</option>
        <option value={1800}>Every 30 Minutes</option>
        <option value={3600}>Every 1 Hour</option>
        <option value={10800}>Every 3 Hours</option>
        <option value={21600}>Every 6 Hours</option>
        <option value={43200}>Every 12 Hours</option>
        <option value={86400}>Every 24 Hours</option>
    </select>
    <div class="text-xs text-sem-fg-muted">
        {#if config.lxmf_preferred_propagation_node_last_synced_at}
            <span
                >{t("app.last_synced", {
                    time: Utils.formatSecondsAgoForI18n(config.lxmf_preferred_propagation_node_last_synced_at),
                })}</span
            >
        {:else}
            <span>{t("app.last_synced_never")}</span>
        {/if}
    </div>
</div>
