<!-- SPDX-License-Identifier: 0BSD -->

<script lang="ts">
    import Toggle from "../Toggle.svelte";
    import PropagationNodePrefs from "./PropagationNodePrefs.svelte";
    import Utils from "../../../../js/Utils.js";
    import { t } from "../../../../js/i18n.js";

    interface Props {
        visible?: boolean;
        config?: Record<string, any>;
        onupdatefield?: (data: { key: string; value: any }) => void;
        onsavepreferredhash?: (showToast?: boolean) => void;
        onclearpreferredhash?: () => void;
    }

    let { visible = true, config = {}, onupdatefield, onsavepreferredhash, onclearpreferredhash }: Props = $props();

    let lxmfIncomingDeliveryPreset = $state("25mb");
    let lxmfIncomingDeliveryCustomAmount = $state<number | null>(null);
    let lxmfIncomingDeliveryCustomUnit = $state<"mb" | "gb">("mb");

    let lxmfPropagationTransferLimitInputMb = $state<number | null>(null);
    let lxmfPropagationSyncLimitInputMb = $state<number | null>(null);

    const PRESET_BYTES: Record<string, number> = {
        "1mb": 1024 * 1024,
        "10mb": 10 * 1024 * 1024,
        "25mb": 25 * 1024 * 1024,
        "50mb": 50 * 1024 * 1024,
        "1gb": 1024 * 1024 * 1024,
    };

    $effect(() => {
        const raw = config?.lxmf_delivery_transfer_limit_in_bytes;
        const matched = Object.entries(PRESET_BYTES).find(([, bytes]) => bytes === raw);
        if (matched) {
            lxmfIncomingDeliveryPreset = matched[0];
            lxmfIncomingDeliveryCustomAmount = null;
        } else if (raw != null && raw > 0) {
            lxmfIncomingDeliveryPreset = "custom";
            if (raw >= 1024 * 1024 * 1024 && raw % (1024 * 1024 * 1024) === 0) {
                lxmfIncomingDeliveryCustomAmount = raw / (1024 * 1024 * 1024);
                lxmfIncomingDeliveryCustomUnit = "gb";
            } else {
                lxmfIncomingDeliveryCustomAmount = Math.round((raw / (1024 * 1024)) * 1000) / 1000;
                lxmfIncomingDeliveryCustomUnit = "mb";
            }
        }
    });

    $effect(() => {
        const rawTransfer = config?.lxmf_propagation_transfer_limit_in_bytes;
        lxmfPropagationTransferLimitInputMb =
            rawTransfer != null && rawTransfer > 0 ? Math.round((rawTransfer / (1024 * 1024)) * 1000) / 1000 : null;

        const rawSync = config?.lxmf_propagation_sync_limit_in_bytes;
        lxmfPropagationSyncLimitInputMb =
            rawSync != null && rawSync > 0 ? Math.round((rawSync / (1024 * 1024)) * 1000) / 1000 : null;
    });

    function emitToggle(key: string, value: boolean) {
        onupdatefield?.({ key, value });
    }

    function emitValue(key: string, value: any) {
        onupdatefield?.({ key, value });
    }

    function onPresetChange(event: Event) {
        const target = event.target as HTMLSelectElement;
        const val = target.value;
        lxmfIncomingDeliveryPreset = val;
        if (val !== "custom" && PRESET_BYTES[val]) {
            emitValue("lxmf_delivery_transfer_limit_in_bytes", PRESET_BYTES[val]);
        }
    }

    function onCustomChange() {
        const amount = Number(lxmfIncomingDeliveryCustomAmount);
        if (Number.isFinite(amount) && amount > 0) {
            const mult = lxmfIncomingDeliveryCustomUnit === "gb" ? 1024 * 1024 * 1024 : 1024 * 1024;
            emitValue("lxmf_delivery_transfer_limit_in_bytes", Math.round(amount * mult));
        }
    }

    function onTransferLimitChange(event: Event) {
        const target = event.target as HTMLInputElement;
        const mb = Number(target.value);
        if (Number.isFinite(mb) && mb > 0) {
            emitValue("lxmf_propagation_transfer_limit_in_bytes", Math.round(mb * 1024 * 1024));
        }
    }

    function onSyncLimitChange(event: Event) {
        const target = event.target as HTMLInputElement;
        const mb = Number(target.value);
        if (Number.isFinite(mb) && mb > 0) {
            emitValue("lxmf_propagation_sync_limit_in_bytes", Math.round(mb * 1024 * 1024));
        }
    }
</script>

{#if visible}
    <section class="settings-section break-inside-avoid">
        <header class="settings-section__header">
            <div>
                <div class="settings-section__eyebrow">LXMF</div>
                <h2>{t("app.propagation_nodes")}</h2>
                <p>{t("app.propagation_nodes_description")}</p>
            </div>
            <a href="#/propagation-nodes" class="primary-chip">
                {t("app.browse_nodes")}
            </a>
        </header>
        <div class="settings-section__body space-y-5">
            <div class="info-callout">
                <ul class="list-disc list-inside space-y-1 text-sm">
                    <li>{t("app.nodes_info_1")}</li>
                    <li>{t("app.nodes_info_2")}</li>
                    <li>{t("app.nodes_info_3")}</li>
                </ul>
            </div>

            <PropagationNodePrefs {config} {onupdatefield} {onsavepreferredhash} {onclearpreferredhash} />

            <div class="space-y-2">
                <label for="incoming-message-size-select" class="text-sm font-medium text-sem-fg block">
                    {t("app.incoming_message_size")}
                </label>
                <div class="text-xs text-sem-fg-muted">
                    {t("app.incoming_message_size_description")}
                </div>
                <select
                    id="incoming-message-size-select"
                    value={lxmfIncomingDeliveryPreset}
                    class="input-field"
                    onchange={onPresetChange}
                >
                    <option value="1mb">{t("app.incoming_message_size_1mb")}</option>
                    <option value="10mb">{t("app.incoming_message_size_10mb")}</option>
                    <option value="25mb">{t("app.incoming_message_size_25mb")}</option>
                    <option value="50mb">{t("app.incoming_message_size_50mb")}</option>
                    <option value="1gb">{t("app.incoming_message_size_1gb")}</option>
                    <option value="custom">{t("app.incoming_message_size_custom")}</option>
                </select>
                {#if lxmfIncomingDeliveryPreset === "custom"}
                    <div class="flex flex-wrap items-center gap-2">
                        <input
                            value={lxmfIncomingDeliveryCustomAmount}
                            type="number"
                            min="0.001"
                            step="any"
                            class="input-field max-w-40"
                            oninput={(e) => {
                                lxmfIncomingDeliveryCustomAmount = Number((e.target as HTMLInputElement).value);
                                onCustomChange();
                            }}
                        />
                        <select
                            value={lxmfIncomingDeliveryCustomUnit}
                            class="input-field max-w-32"
                            onchange={(e) => {
                                lxmfIncomingDeliveryCustomUnit = (e.target as HTMLSelectElement).value as "mb" | "gb";
                                onCustomChange();
                            }}
                        >
                            <option value="mb">{t("app.incoming_message_size_unit_mb")}</option>
                            <option value="gb">{t("app.incoming_message_size_unit_gb")}</option>
                        </select>
                    </div>
                {/if}
                <div class="text-xs text-sem-fg-muted">
                    {Utils.formatBytes(Number(config.lxmf_delivery_transfer_limit_in_bytes) || 0)}
                </div>
            </div>

            <div class="space-y-2">
                <label for="prop-transfer-limit-mb" class="text-sm font-medium text-sem-fg block">
                    Propagation transfer limit (MB)
                </label>
                <input
                    id="prop-transfer-limit-mb"
                    value={lxmfPropagationTransferLimitInputMb}
                    type="number"
                    min="0.001"
                    step="0.01"
                    class="input-field"
                    oninput={onTransferLimitChange}
                />
                <div class="text-xs text-sem-fg-muted">
                    {Utils.formatBytes(Number(config.lxmf_propagation_transfer_limit_in_bytes) || 0)}
                </div>
            </div>

            <div class="space-y-2">
                <label for="prop-sync-limit-mb" class="text-sm font-medium text-sem-fg block">
                    Propagation sync limit (MB)
                </label>
                <input
                    id="prop-sync-limit-mb"
                    value={lxmfPropagationSyncLimitInputMb}
                    type="number"
                    min="0.001"
                    step="0.01"
                    class="input-field"
                    oninput={onSyncLimitChange}
                />
                <div class="text-xs text-sem-fg-muted">
                    {Utils.formatBytes(Number(config.lxmf_propagation_sync_limit_in_bytes) || 0)}
                </div>
            </div>

            {#if config.lxmf_local_propagation_node_enabled}
                <div class="space-y-2">
                    <label for="prop-stamp-cost" class="text-sm font-medium text-sem-fg block">
                        {t("app.propagation_stamp_cost")}
                    </label>
                    <input
                        id="prop-stamp-cost"
                        value={config.lxmf_propagation_node_stamp_cost}
                        type="number"
                        min="13"
                        max="254"
                        placeholder="16"
                        class="input-field"
                        oninput={(e) =>
                            emitValue("lxmf_propagation_node_stamp_cost", Number((e.target as HTMLInputElement).value))}
                    />
                    <div class="text-xs text-sem-fg-muted">
                        {t("app.propagation_stamp_description")}
                    </div>
                </div>

                <label class="setting-toggle">
                    <Toggle
                        id="propagation-sequential-validation"
                        checked={Boolean(config.lxmf_propagation_sequential_validation)}
                        onchange={(val) => emitToggle("lxmf_propagation_sequential_validation", val)}
                    />
                    <span class="setting-toggle__label">
                        <span class="setting-toggle__title">
                            {t("app.propagation_sequential_validation")}
                        </span>
                        <span class="setting-toggle__description">
                            {t("app.propagation_sequential_validation_description")}
                        </span>
                    </span>
                </label>

                <label class="setting-toggle">
                    <Toggle
                        id="propagation-static-peers-bypass-sequential"
                        checked={Boolean(config.lxmf_propagation_static_peers_bypass_sequential)}
                        onchange={(val) => emitToggle("lxmf_propagation_static_peers_bypass_sequential", val)}
                    />
                    <span class="setting-toggle__label">
                        <span class="setting-toggle__title">
                            {t("app.propagation_static_peers_bypass_sequential")}
                        </span>
                        <span class="setting-toggle__description">
                            {t("app.propagation_static_peers_bypass_sequential_description")}
                        </span>
                    </span>
                </label>

                <div class="space-y-2">
                    <label for="prop-max-inbound-syncs" class="text-sm font-medium text-sem-fg block">
                        {t("app.propagation_max_inbound_syncs")}
                    </label>
                    <input
                        id="prop-max-inbound-syncs"
                        value={config.lxmf_propagation_max_inbound_syncs}
                        type="number"
                        min="1"
                        max="64"
                        placeholder="3"
                        class="input-field"
                        oninput={(e) =>
                            emitValue(
                                "lxmf_propagation_max_inbound_syncs",
                                Number((e.target as HTMLInputElement).value)
                            )}
                    />
                    <div class="text-xs text-sem-fg-muted">
                        {t("app.propagation_max_inbound_syncs_description")}
                    </div>
                </div>
            {/if}
        </div>
    </section>
{/if}
