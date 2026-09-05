<!-- SPDX-License-Identifier: 0BSD -->

<script lang="ts">
    import { t } from "../../../js/i18n.js";
    import MaterialDesignIcon from "../../../ui/svelte/MaterialDesignIcon.svelte";
    import { DESTINATION_HASH_HEX_LENGTH } from "../lib/constants.js";

    interface Props {
        onRequestPath?: (hash: string) => Promise<void> | void;
        onDropAllVia?: (hash: string) => Promise<void> | void;
        onDropAnnounceQueues?: () => Promise<void> | void;
    }

    let { onRequestPath, onDropAllVia, onDropAnnounceQueues }: Props = $props();

    let requestHash = $state("");
    let dropViaHash = $state("");

    const isRequestHashValid = $derived(requestHash.length === DESTINATION_HASH_HEX_LENGTH);
    const isDropViaHashValid = $derived(dropViaHash.length === DESTINATION_HASH_HEX_LENGTH);

    async function handleRequestPath(): Promise<void> {
        if (!isRequestHashValid) {
            return;
        }
        await onRequestPath?.(requestHash);
        requestHash = "";
    }

    async function handleDropAllVia(): Promise<void> {
        if (!isDropViaHashValid) {
            return;
        }
        await onDropAllVia?.(dropViaHash);
        dropViaHash = "";
    }
</script>

<div class="max-w-2xl mx-auto space-y-6">
    <!-- request path -->
    <section class="rounded-lg border border-sem-border bg-sem-surface p-4 sm:p-6 space-y-4">
        <h2 class="text-lg font-bold text-sem-fg">{t("tools.rnpath.request_path")}</h2>
        <p class="text-sm text-sem-fg-muted">{t("tools.rnpath.request_path_desc")}</p>
        <div class="flex flex-col sm:flex-row gap-2">
            <input
                bind:value={requestHash}
                type="text"
                placeholder={t("tools.rnpath_trace.placeholder")}
                class="input-field flex-1 min-w-0 font-mono"
            />
            <button
                type="button"
                class="primary-chip focus-ring-sem px-4 py-2.5 sm:py-2 justify-center shrink-0"
                disabled={!isRequestHashValid}
                title={!isRequestHashValid ? t("tools.rnpath_trace.invalid_hash_hint") : t("tools.rnpath.request_btn")}
                onclick={() => void handleRequestPath()}
            >
                <MaterialDesignIcon iconName="send" class="size-4" />
                {t("tools.rnpath.request_btn")}
            </button>
        </div>
    </section>

    <!-- drop all via -->
    <section class="rounded-lg border border-sem-border bg-sem-surface p-4 sm:p-6 space-y-4">
        <h2 class="text-lg font-bold text-sem-fg">{t("tools.rnpath.drop_all_via")}</h2>
        <p class="text-sm text-sem-fg-muted">{t("tools.rnpath.drop_all_via_desc")}</p>
        <div class="flex flex-col sm:flex-row gap-2">
            <input
                bind:value={dropViaHash}
                type="text"
                placeholder={t("tools.rnpath_trace.placeholder")}
                class="input-field flex-1 min-w-0 font-mono"
            />
            <button
                type="button"
                class="danger-chip focus-ring-sem px-4 py-2.5 sm:py-2 justify-center shrink-0"
                disabled={!isDropViaHashValid}
                title={!isDropViaHashValid ? t("tools.rnpath_trace.invalid_hash_hint") : t("tools.rnpath.drop_all_btn")}
                onclick={() => void handleDropAllVia()}
            >
                <MaterialDesignIcon iconName="link-variant-remove" class="size-4" />
                {t("tools.rnpath.drop_all_btn")}
            </button>
        </div>
    </section>

    <!-- drop queues -->
    <section class="rounded-lg border border-sem-border bg-sem-surface p-4 sm:p-6 space-y-4">
        <h2 class="text-lg font-bold text-sem-fg">{t("tools.rnpath.drop_queues")}</h2>
        <p class="text-sm text-sem-fg-muted">{t("tools.rnpath.drop_queues_desc")}</p>
        <button
            type="button"
            class="danger-chip focus-ring-sem w-full py-3 justify-center"
            onclick={() => onDropAnnounceQueues?.()}
        >
            <MaterialDesignIcon iconName="delete-sweep" class="size-4" />
            {t("tools.rnpath.purge_all_btn")}
        </button>
    </section>
</div>
