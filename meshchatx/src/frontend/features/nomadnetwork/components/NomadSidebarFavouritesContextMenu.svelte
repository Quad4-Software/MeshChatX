<!-- SPDX-License-Identifier: 0BSD -->

<script lang="ts">
    import MaterialDesignIcon from "../../../ui/svelte/MaterialDesignIcon.svelte";
    import ToastUtils from "../../../js/ToastUtils.js";
    import { t } from "../../../js/i18n.js";
    import { DEFAULT_SECTION_ID } from "../lib/nomadSidebarFavourites.js";
    import type { NomadFavourite, NomadSection } from "../lib/types.js";

    interface Props {
        favContextMenu: {
            show: boolean;
            x: number;
            y: number;
            targetHash: string;
            targetSectionId: string;
        };
        secContextMenu: {
            show: boolean;
            x: number;
            y: number;
            sectionId: string;
        };
        favMenuLeft: number;
        favMenuTop: number;
        secMenuLeft: number;
        secMenuTop: number;
        orderedSections: NomadSection[];
        targetFavourite?: NomadFavourite | null;
        isTargetBlocked?: boolean;
        onclose?: () => void;
        onrename?: (fav: NomadFavourite) => void;
        ontoggleidentify?: (hash: string) => void;
        onmovetosection?: (hash: string, secId: string) => void;
        onremove?: (fav: NomadFavourite) => void;
        onbanish?: (fav: NomadFavourite) => void;
        onunblock?: (hash: string) => void;
        onrenamesection?: (sec: NomadSection) => void;
        onexportsection?: (sec: NomadSection) => void;
        onremovesection?: (secId: string) => void;
    }

    let {
        favContextMenu,
        secContextMenu,
        favMenuLeft,
        favMenuTop,
        secMenuLeft,
        secMenuTop,
        orderedSections,
        targetFavourite = null,
        isTargetBlocked = false,
        onclose,
        onrename,
        ontoggleidentify,
        onmovetosection,
        onremove,
        onbanish,
        onunblock,
        onrenamesection,
        onexportsection,
        onremovesection,
    }: Props = $props();

    const targetSection = $derived(orderedSections.find((s) => s.id === secContextMenu.sectionId) || null);
</script>

{#if favContextMenu.show && targetFavourite}
    <div
        class="fixed z-50 min-w-44 bg-sem-surface border border-sem-border rounded-xl shadow-xl py-1 text-sem-fg"
        style="left: {favMenuLeft}px; top: {favMenuTop}px;"
    >
        <button
            type="button"
            class="w-full text-left px-3 py-1.5 text-xs hover:bg-sem-surface-muted flex items-center gap-2"
            onclick={() => {
                if (targetFavourite) onrename?.(targetFavourite);
                onclose?.();
            }}
        >
            <MaterialDesignIcon iconName="pencil" class="size-4 text-gray-500" />
            {t("common.rename")}
        </button>
        <button
            type="button"
            class="w-full text-left px-3 py-1.5 text-xs hover:bg-sem-surface-muted flex items-center gap-2"
            onclick={() => {
                if (targetFavourite) ontoggleidentify?.(targetFavourite.destination_hash);
                onclose?.();
            }}
        >
            <MaterialDesignIcon
                iconName={targetFavourite.identify_on_connect ? "account-off" : "account-check"}
                class="size-4 text-blue-500"
            />
            {targetFavourite.identify_on_connect
                ? t("nomadnet.disable_identify_on_connect")
                : t("nomadnet.enable_identify_on_connect")}
        </button>
        <button
            type="button"
            class="w-full text-left px-3 py-1.5 text-xs hover:bg-sem-surface-muted flex items-center gap-2"
            onclick={() => {
                navigator.clipboard.writeText(targetFavourite.destination_hash);
                ToastUtils.success("Address copied to clipboard");
                onclose?.();
            }}
        >
            <MaterialDesignIcon iconName="content-copy" class="size-4" />
            {t("nomadnet.copy_address")}
        </button>
        <button
            type="button"
            class="w-full text-left px-3 py-1.5 text-xs hover:bg-sem-surface-muted flex items-center gap-2"
            onclick={() => {
                navigator.clipboard.writeText(`nomadnet://${targetFavourite.destination_hash}`);
                ToastUtils.success("Link copied to clipboard");
                onclose?.();
            }}
        >
            <MaterialDesignIcon iconName="link" class="size-4" />
            {t("nomadnet.copy_nomad_link")}
        </button>

        {#if orderedSections.length > 1}
            <div class="px-3 py-1 text-[10px] uppercase font-semibold text-sem-fg-muted">
                {t("nomadnet.move_to_section")}
            </div>
            {#each orderedSections as s (s.id)}
                {#if s.id !== favContextMenu.targetSectionId}
                    <button
                        type="button"
                        class="w-full text-left px-4 py-1 text-xs hover:bg-sem-surface-muted truncate"
                        onclick={() => {
                            if (targetFavourite) onmovetosection?.(targetFavourite.destination_hash, s.id);
                            onclose?.();
                        }}
                    >
                        {s.name}
                    </button>
                {/if}
            {/each}
        {/if}

        <hr class="my-1 border-sem-border" />
        {#if isTargetBlocked}
            <button
                type="button"
                class="w-full text-left px-3 py-1.5 text-xs text-green-600 dark:text-green-400 hover:bg-sem-surface-muted flex items-center gap-2"
                onclick={() => {
                    if (targetFavourite) onunblock?.(targetFavourite.destination_hash);
                    onclose?.();
                }}
            >
                <MaterialDesignIcon iconName="lock-open-outline" class="size-4" />
                {t("nomadnet.lift_banishment")}
            </button>
        {:else}
            <button
                type="button"
                class="w-full text-left px-3 py-1.5 text-xs text-red-600 dark:text-red-400 hover:bg-sem-surface-muted flex items-center gap-2"
                onclick={() => {
                    if (targetFavourite) onbanish?.(targetFavourite);
                    onclose?.();
                }}
            >
                <MaterialDesignIcon iconName="cancel" class="size-4" />
                {t("nomadnet.block_node")}
            </button>
        {/if}
        <button
            type="button"
            class="w-full text-left px-3 py-1.5 text-xs text-red-600 dark:text-red-400 hover:bg-sem-surface-muted flex items-center gap-2"
            onclick={() => {
                if (targetFavourite) onremove?.(targetFavourite);
                onclose?.();
            }}
        >
            <MaterialDesignIcon iconName="delete" class="size-4" />
            {t("nomadnet.remove_favourite")}
        </button>
    </div>
{/if}

{#if secContextMenu.show && targetSection}
    <div
        class="fixed z-50 min-w-44 bg-sem-surface border border-sem-border rounded-xl shadow-xl py-1 text-sem-fg"
        style="left: {secMenuLeft}px; top: {secMenuTop}px;"
    >
        <button
            type="button"
            class="w-full text-left px-3 py-1.5 text-xs hover:bg-sem-surface-muted flex items-center gap-2"
            onclick={() => {
                if (targetSection) onrenamesection?.(targetSection);
                onclose?.();
            }}
        >
            <MaterialDesignIcon iconName="pencil" class="size-4 text-gray-500" />
            {t("common.rename")}
        </button>
        <button
            type="button"
            class="w-full text-left px-3 py-1.5 text-xs hover:bg-sem-surface-muted flex items-center gap-2"
            onclick={() => {
                if (targetSection) onexportsection?.(targetSection);
                onclose?.();
            }}
        >
            <MaterialDesignIcon iconName="export" class="size-4" />
            {t("nomadnet.export_section")}
        </button>
        {#if targetSection.id !== DEFAULT_SECTION_ID}
            <hr class="my-1 border-sem-border" />
            <button
                type="button"
                class="w-full text-left px-3 py-1.5 text-xs text-red-600 dark:text-red-400 hover:bg-sem-surface-muted flex items-center gap-2"
                onclick={() => {
                    if (targetSection) onremovesection?.(targetSection.id);
                    onclose?.();
                }}
            >
                <MaterialDesignIcon iconName="delete" class="size-4" />
                {t("nomadnet.delete_section")}
            </button>
        {/if}
    </div>
{/if}
