<!-- SPDX-License-Identifier: 0BSD -->

<script lang="ts">
    import { t } from "../../../js/i18n.js";

    interface Props {
        awareMode: "publish" | "subscribe";
        awarePeers: number | string | null;
        needsPermission?: boolean;
        permissionRequesting?: boolean;
        onawaremodechange?: (val: "publish" | "subscribe") => void;
        onawarepeerschange?: (val: string) => void;
        onrequestpermission?: () => void;
    }

    let {
        awareMode = "subscribe",
        awarePeers = 4,
        needsPermission = false,
        permissionRequesting = false,
        onawaremodechange,
        onawarepeerschange,
        onrequestpermission,
    }: Props = $props();
</script>

<!-- WiFi Aware (NAN) - Android only, bundled AwareInterface module -->
<div class="space-y-4">
    <p class="text-xs text-sem-fg-muted leading-relaxed">
        {t("tools.nearby.aware_description")}
    </p>

    {#if needsPermission}
        <div
            class="rounded-xl border border-amber-200/80 dark:border-amber-900/40 bg-amber-50/40 dark:bg-amber-950/20 p-3 space-y-2"
        >
            <p class="text-xs text-amber-900 dark:text-amber-200/90 leading-relaxed">
                {t("interfaces.aware_permission_banner")}
            </p>
            <button
                type="button"
                class="secondary-chip py-1.5! px-3! text-[10px]!"
                disabled={permissionRequesting}
                onclick={() => onrequestpermission?.()}
            >
                {t("interfaces.aware_permission_grant")}
            </button>
        </div>
    {/if}

    <div>
        <span class="glass-label block font-medium mb-1">{t("interfaces.aware_role_label")}</span>
        <div class="flex items-center gap-2">
            <button
                type="button"
                class="flex-1 py-2 rounded-2xl border text-xs font-bold uppercase tracking-tight transition {awareMode ===
                'subscribe'
                    ? 'bg-lime-500/10 border-lime-500 text-lime-700 dark:text-lime-300'
                    : 'bg-gray-50/50 dark:bg-zinc-800/30 border-sem-border text-sem-fg-muted'}"
                onclick={() => onawaremodechange?.("subscribe")}
            >
                {t("tools.nearby.aware_subscribe")}
            </button>
            <button
                type="button"
                class="flex-1 py-2 rounded-2xl border text-xs font-bold uppercase tracking-tight transition {awareMode ===
                'publish'
                    ? 'bg-lime-500/10 border-lime-500 text-lime-700 dark:text-lime-300'
                    : 'bg-gray-50/50 dark:bg-zinc-800/30 border-sem-border text-sem-fg-muted'}"
                onclick={() => onawaremodechange?.("publish")}
            >
                {t("tools.nearby.aware_publish")}
            </button>
        </div>
        <p class="text-xs text-sem-fg-muted mt-1.5 leading-relaxed">
            {t("tools.nearby.aware_hint")}
        </p>
    </div>

    <div>
        <label for="iface-aware-peers" class="glass-label block font-medium mb-1">
            {t("interfaces.aware_max_peers")}
        </label>
        <input
            id="iface-aware-peers"
            value={awarePeers ?? ""}
            type="number"
            min="1"
            max="8"
            placeholder="4"
            class="input-field"
            oninput={(e) => onawarepeerschange?.((e.target as HTMLInputElement).value)}
        />
        <p class="text-xs text-sem-fg-muted mt-1.5 leading-relaxed">
            {t("interfaces.aware_max_peers_hint")}
        </p>
    </div>
</div>
