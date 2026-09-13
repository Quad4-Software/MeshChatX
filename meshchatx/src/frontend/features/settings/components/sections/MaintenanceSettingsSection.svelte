<!-- SPDX-License-Identifier: 0BSD -->

<script lang="ts">
    import MaintenanceMessagePurgeCard from "./MaintenanceMessagePurgeCard.svelte";
    import MaintenanceClearGrid from "./MaintenanceClearGrid.svelte";
    import MaintenanceDataTransferGrid from "./MaintenanceDataTransferGrid.svelte";
    import { t } from "../../../../js/i18n.js";

    interface Props {
        visible?: boolean;
        config?: Record<string, any>;
        onupdatefield?: (data: { key: string; value: any }) => void;
    }

    let { visible = true, config = {}, onupdatefield }: Props = $props();
</script>

{#if visible}
    <section class="settings-section break-inside-avoid">
        <header class="settings-section__header">
            <div>
                <div class="settings-section__eyebrow">Maintenance</div>
                <h2>{t("maintenance.title")}</h2>
                <p>{t("maintenance.description")}</p>
            </div>
        </header>
        <div class="settings-section__body space-y-4">
            <MaintenanceMessagePurgeCard />

            <MaintenanceClearGrid />

            <div class="space-y-2 pt-2 border-t border-sem-border">
                <label for="backup-max-count-input" class="text-sm font-medium text-sem-fg block">
                    Automatic Backup Limit
                </label>
                <input
                    id="backup-max-count-input"
                    value={config.backup_max_count}
                    type="number"
                    min="1"
                    max="50"
                    class="input-field"
                    oninput={(e) =>
                        onupdatefield?.({
                            key: "backup_max_count",
                            value: Number((e.target as HTMLInputElement).value),
                        })}
                />
                <div class="text-xs text-sem-fg-muted">Number of automatic backups to keep.</div>
            </div>

            <MaintenanceDataTransferGrid />
        </div>
    </section>
{/if}
