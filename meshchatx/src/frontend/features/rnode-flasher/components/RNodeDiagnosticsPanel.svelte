<!-- SPDX-License-Identifier: 0BSD -->

<script lang="ts">
    import MaterialDesignIcon from "../../../ui/svelte/MaterialDesignIcon.svelte";
    import { t } from "../../../js/i18n.js";

    interface Props {
        diagnostics?: any;
    }

    let { diagnostics = null }: Props = $props();

    let hasIssues = $derived(Array.isArray(diagnostics?.issues) && diagnostics.issues.length > 0);

    let summaryRows = $derived.by(() => {
        const s = diagnostics?.summary || {};
        return [
            {
                key: "firmware_version",
                labelKey: "tools.rnode_flasher.diagnostics.firmware_version",
                value: s.firmware_version,
            },
            {
                key: "platform",
                labelKey: "tools.rnode_flasher.diagnostics.platform",
                value: s.platform != null ? `0x${s.platform.toString(16).padStart(2, "0")}` : null,
            },
            {
                key: "board",
                labelKey: "tools.rnode_flasher.diagnostics.board",
                value: s.board != null ? `0x${s.board.toString(16).padStart(2, "0")}` : null,
            },
            {
                key: "is_provisioned",
                labelKey: "tools.rnode_flasher.diagnostics.provisioned",
                value: s.is_provisioned ? "yes" : "no",
            },
            {
                key: "product",
                labelKey: "tools.rnode_flasher.diagnostics.product",
                value: s.product != null ? `0x${s.product.toString(16).padStart(2, "0")}` : null,
            },
            {
                key: "model",
                labelKey: "tools.rnode_flasher.diagnostics.model",
                value: s.model != null ? `0x${s.model.toString(16).padStart(2, "0")}` : null,
            },
            {
                key: "fw_hash",
                labelKey: "tools.rnode_flasher.diagnostics.firmware_hash",
                value: s.firmware_hash ? s.firmware_hash.slice(0, 16) : null,
            },
            {
                key: "target_hash",
                labelKey: "tools.rnode_flasher.diagnostics.target_hash",
                value: s.target_firmware_hash ? s.target_firmware_hash.slice(0, 16) : null,
            },
        ];
    });
</script>

{#if diagnostics}
    <div class="border border-sem-border bg-sem-surface rounded-lg overflow-hidden">
        <div class="px-4 sm:px-6 py-4 border-b border-sem-border flex items-center gap-2">
            <MaterialDesignIcon iconName="stethoscope" class="size-5 text-emerald-500" />
            <h3 class="font-bold text-sem-fg">
                {t("tools.rnode_flasher.diagnostics.title")}
            </h3>
            {#if hasIssues}
                <span
                    class="ml-auto px-2 py-0.5 text-[10px] font-bold uppercase tracking-wider rounded-full bg-amber-100 dark:bg-amber-900/30 text-amber-700 dark:text-amber-300"
                >
                    {t("tools.rnode_flasher.diagnostics.needs_attention")}
                </span>
            {:else}
                <span
                    class="ml-auto px-2 py-0.5 text-[10px] font-bold uppercase tracking-wider rounded-full bg-emerald-100 dark:bg-emerald-900/30 text-emerald-700 dark:text-emerald-300"
                >
                    {t("tools.rnode_flasher.diagnostics.healthy")}
                </span>
            {/if}
        </div>

        <dl class="grid grid-cols-2 sm:grid-cols-4 gap-x-4 gap-y-3 p-4 sm:p-6 text-xs">
            {#each summaryRows as row (row.key)}
                <div class="space-y-0.5 min-w-0">
                    <dt class="text-[10px] font-bold uppercase tracking-wider text-sem-fg-muted">
                        {t(row.labelKey)}
                    </dt>
                    <dd class="font-mono text-sem-fg break-all">
                        {row.value || "-"}
                    </dd>
                </div>
            {/each}
        </dl>

        {#if hasIssues}
            <div class="border-t border-sem-border bg-amber-50/40 dark:bg-amber-900/10 px-4 sm:px-6 py-4 space-y-2">
                <div class="text-[10px] font-bold uppercase tracking-wider text-amber-700 dark:text-amber-300">
                    {t("tools.rnode_flasher.diagnostics.issues_detected")}
                </div>
                <ul class="list-disc pl-4 text-xs text-amber-800 dark:text-amber-200 space-y-1">
                    {#each diagnostics.suggestionKeys as key (key)}
                        <li>{t(key)}</li>
                    {/each}
                </ul>
            </div>
        {/if}
    </div>
{/if}
