<!-- SPDX-License-Identifier: 0BSD -->

<script lang="ts">
    import { t } from "../../../js/i18n.js";
    import PageNodeToggle from "./PageNodeToggle.svelte";

    interface Props {
        announceEnabled: boolean;
        announceIntervalMinutes: number;
        executablePagesEnabled: boolean;
        lastAnnouncedText: string;
        onSave: () => void;
    }

    let {
        announceEnabled = $bindable(true),
        announceIntervalMinutes = $bindable(15),
        executablePagesEnabled = $bindable(false),
        lastAnnouncedText,
        onSave,
    }: Props = $props();
</script>

<div class="p-3 rounded-lg bg-slate-50 dark:bg-zinc-800/50 border border-sem-border space-y-3">
    <div class="text-xs font-bold uppercase tracking-wider text-sem-fg-muted">
        {t("tools.mesh_server.announce_settings")}
    </div>
    <div class="flex items-center justify-between gap-3">
        <PageNodeToggle
            id="mesh-server-executable-pages-enabled"
            bind:checked={executablePagesEnabled}
            label={t("tools.mesh_server.executable_pages_enabled_label")}
        />
    </div>
    <div class="text-xs text-sem-fg-muted">
        {t("tools.mesh_server.executable_pages_warning")}
    </div>
    <div class="flex items-center justify-between gap-3">
        <PageNodeToggle
            id="mesh-server-announce-enabled"
            bind:checked={announceEnabled}
            label={t("tools.mesh_server.announce_enabled_label")}
        />
    </div>
    {#if announceEnabled}
        <div class="space-y-1">
            <div class="flex items-center gap-3">
                <label for="mesh-server-announce-interval" class="glass-label mb-0 shrink-0">
                    {t("tools.mesh_server.announce_interval_label")}
                </label>
                <input
                    id="mesh-server-announce-interval"
                    type="number"
                    min="0"
                    max="1440"
                    class="input-field w-24"
                    bind:value={announceIntervalMinutes}
                />
            </div>
            <div class="text-xs text-sem-fg-muted">
                {t("tools.mesh_server.announce_interval_manual_hint")}
            </div>
        </div>
    {/if}
    <div class="flex items-center justify-between gap-3">
        <span class="text-xs text-sem-fg-muted">
            {lastAnnouncedText}
        </span>
        <button type="button" class="primary-chip py-1! px-3! text-xs!" onclick={onSave}>
            {t("common.save")}
        </button>
    </div>
</div>
