<!-- SPDX-License-Identifier: 0BSD -->

<script lang="ts">
    import { t } from "../../../js/i18n.js";
    import { SORT_OPTIONS } from "../lib/constants.js";

    interface Props {
        includeLinkStats: boolean;
        showAll: boolean;
        sorting: string;
        disabled?: boolean;
        onChange?: () => void;
    }

    let {
        includeLinkStats = $bindable(false),
        showAll = $bindable(false),
        sorting = $bindable(""),
        disabled = false,
        onChange,
    }: Props = $props();

    function handleChange() {
        onChange?.();
    }
</script>

<div class="rounded-xl border border-sem-border bg-sem-surface p-4 space-y-3">
    <div class="flex flex-wrap items-center gap-3">
        <label
            class="inline-flex cursor-pointer items-center gap-2 rounded-lg border border-sem-border bg-sem-canvas px-3 py-2 text-sm text-sem-fg"
        >
            <input
                type="checkbox"
                class="rounded-sm"
                bind:checked={includeLinkStats}
                {disabled}
                onchange={handleChange}
            />
            <span>{t("rnstatus.include_link_stats")}</span>
        </label>
        <label
            class="inline-flex cursor-pointer items-center gap-2 rounded-lg border border-sem-border bg-sem-canvas px-3 py-2 text-sm text-sem-fg"
        >
            <input type="checkbox" class="rounded-sm" bind:checked={showAll} {disabled} onchange={handleChange} />
            <span>{t("rnstatus.show_all_interfaces")}</span>
        </label>
        <div class="flex min-w-0 flex-wrap items-center gap-2">
            <label class="shrink-0 text-sm text-gray-700 dark:text-gray-300" for="rnstatus-sorting">
                {t("rnstatus.sort_by")}
            </label>
            <select
                id="rnstatus-sorting"
                class="input-field min-w-40 text-sm"
                bind:value={sorting}
                {disabled}
                onchange={handleChange}
            >
                {#each SORT_OPTIONS as opt (opt.value)}
                    <option value={opt.value}>{t(opt.labelKey)}</option>
                {/each}
            </select>
        </div>
    </div>
</div>
