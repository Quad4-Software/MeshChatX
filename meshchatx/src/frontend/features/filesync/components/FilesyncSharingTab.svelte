<!-- SPDX-License-Identifier: 0BSD -->

<script lang="ts">
    import { t } from "../../../js/i18n.js";
    import { formatAclRows } from "../lib/filesyncFormat.js";
    import type { AclRules } from "../lib/types.js";

    interface Props {
        aclEnforce: boolean;
        aclHash: string;
        aclRead: boolean;
        aclWrite: boolean;
        aclDelete: boolean;
        aclRules: AclRules;
        busy: boolean;
        onGrant: () => void;
        onSaveEnforce: () => void;
    }

    let {
        aclEnforce = $bindable(false),
        aclHash = $bindable(""),
        aclRead = $bindable(true),
        aclWrite = $bindable(false),
        aclDelete = $bindable(false),
        aclRules = {},
        busy,
        onGrant,
        onSaveEnforce,
    }: Props = $props();

    const aclRows = $derived(formatAclRows(aclRules));
</script>

<div class="space-y-4">
    <p class="text-sm text-sem-fg-muted">{t("rns_filesync.sharing_help")}</p>
    <label class="flex items-center gap-2 text-sm text-sem-fg cursor-pointer">
        <input bind:checked={aclEnforce} type="checkbox" class="rounded" onchange={onSaveEnforce} />
        {t("rns_filesync.acl_enforce")}
    </label>
    <div class="flex flex-col gap-3">
        <input
            bind:value={aclHash}
            type="text"
            class="input-field w-full font-mono text-sm"
            placeholder={t("rns_filesync.peer_hash_placeholder")}
        />
        <div class="flex flex-wrap items-center gap-4 text-sm text-sem-fg">
            <label class="flex items-center gap-1.5 cursor-pointer">
                <input bind:checked={aclRead} type="checkbox" class="rounded" />
                {t("rns_filesync.perm_read")}
            </label>
            <label class="flex items-center gap-1.5 cursor-pointer">
                <input bind:checked={aclWrite} type="checkbox" class="rounded" />
                {t("rns_filesync.perm_write")}
            </label>
            <label class="flex items-center gap-1.5 cursor-pointer">
                <input bind:checked={aclDelete} type="checkbox" class="rounded" />
                {t("rns_filesync.perm_delete")}
            </label>
        </div>
        <button
            type="button"
            class="primary-chip px-4 py-2 text-sm self-start cursor-pointer"
            disabled={busy}
            onclick={onGrant}
        >
            {t("rns_filesync.acl_grant")}
        </button>
    </div>
    {#if aclRows.length === 0}
        <div class="text-sm text-sem-fg-muted">
            {t("rns_filesync.no_acl_rules")}
        </div>
    {:else}
        <ul class="space-y-2">
            {#each aclRows as row (row.hash)}
                <li class="p-3 rounded-lg border border-sem-border text-sm">
                    <div class="font-mono text-xs break-all text-sem-fg">{row.hash}</div>
                    <div class="text-xs text-sem-fg-muted mt-1">{row.permsLabel}</div>
                </li>
            {/each}
        </ul>
    {/if}
</div>
