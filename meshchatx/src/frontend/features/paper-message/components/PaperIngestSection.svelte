<!-- SPDX-License-Identifier: 0BSD -->

<script lang="ts">
    import MaterialDesignIcon from "../../../ui/svelte/MaterialDesignIcon.svelte";
    import { t } from "../../../js/i18n.js";

    let {
        ingestUri = $bindable(""),
        cameraSupported = false,
        onpaste,
        onscan,
        oningest,
    }: {
        ingestUri: string;
        cameraSupported?: boolean;
        onpaste?: () => void;
        onscan?: () => void;
        oningest?: () => void;
    } = $props();
</script>

<section class="rounded-lg border border-sem-border overflow-hidden bg-sem-surface">
    <div class="px-4 py-3 border-b border-sem-border bg-gray-50/80 dark:bg-zinc-900/50">
        <h2 class="flex items-center gap-2 text-base font-semibold text-sem-fg">
            <MaterialDesignIcon iconName="qrcode-scan" class="size-5 text-gray-400 shrink-0" />
            Ingest Paper Message
        </h2>
    </div>
    <div class="px-4 py-4 space-y-3 text-gray-900 dark:text-gray-100">
        <p class="text-xs text-gray-600 dark:text-gray-400">Paste an LXMF, LXMA, or LXM URI to decode and ingest.</p>
        <div class="flex flex-col sm:flex-row gap-2">
            <input
                bind:value={ingestUri}
                type="text"
                placeholder="lxmf://... or lxma://..."
                class="input-field flex-1 min-w-0 font-mono text-sm"
                onkeydown={(e) => {
                    if (e.key === "Enter") oningest?.();
                }}
            />
            <button
                type="button"
                class="inline-flex items-center justify-center gap-2 px-3 py-2.5 sm:py-2 bg-sem-surface-muted text-sem-fg-muted rounded-lg hover:bg-gray-200 hover:bg-sem-surface-muted transition-colors shrink-0"
                onclick={() => onpaste?.()}
            >
                <MaterialDesignIcon iconName="content-paste" class="size-5" />
                <span class="sm:hidden text-sm font-medium">Paste</span>
            </button>
            {#if cameraSupported}
                <button
                    type="button"
                    class="inline-flex items-center justify-center gap-2 px-3 py-2.5 sm:py-2 bg-sem-surface-muted text-sem-fg-muted rounded-lg hover:bg-gray-200 hover:bg-sem-surface-muted transition-colors shrink-0"
                    onclick={() => onscan?.()}
                >
                    <MaterialDesignIcon iconName="qrcode-scan" class="size-5" />
                    <span class="sm:hidden text-sm font-medium">{t("messages.scan_qr")}</span>
                </button>
            {/if}
        </div>
        <button
            type="button"
            class="w-full py-2.5 px-4 bg-sem-surface-muted text-sem-fg-secondary rounded-xl font-bold hover:bg-gray-200 hover:bg-sem-surface-muted transition-all active:scale-[0.98] text-sm disabled:opacity-50"
            disabled={!ingestUri}
            onclick={() => oningest?.()}
        >
            Read LXM
        </button>
        {#if !cameraSupported}
            <p class="text-xs text-sem-fg-muted">
                {t("messages.camera_not_supported")}
            </p>
        {/if}
    </div>
</section>
