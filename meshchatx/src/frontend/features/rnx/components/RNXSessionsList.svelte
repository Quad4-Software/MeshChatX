<!-- SPDX-License-Identifier: 0BSD -->

<script lang="ts">
    import MaterialDesignIcon from "../../../ui/svelte/MaterialDesignIcon.svelte";
    import { t } from "../../../js/i18n.js";
    import { getSessionStatusClass, getSessionSubtitle } from "../../remote-shell/lib/sessionOutput.js";
    import type { RnxSession } from "../lib/types.js";

    interface Props {
        sessions: RnxSession[];
        selectedSessionId: string | null;
        onselect: (id: string) => void;
        onrefresh: () => void;
    }

    let { sessions, selectedSessionId, onselect, onrefresh }: Props = $props();

    function statusLabel(session: RnxSession): string {
        return t(`rnx.status_${session.status}`);
    }

    function subtitle(session: RnxSession): string {
        return getSessionSubtitle(session, t("rnx.listen_mode"));
    }
</script>

<div class="flex items-center justify-between gap-2">
    <div class="text-xs sm:text-sm font-semibold text-sem-fg">
        {t("rnx.sessions")}
    </div>
    <button type="button" class="secondary-chip text-xs px-2 py-1.5" onclick={onrefresh}>
        <MaterialDesignIcon iconName="refresh" class="size-4" />
        <span class="hidden sm:inline">{t("rnx.refresh")}</span>
    </button>
</div>

<div class="flex-1 min-h-0 space-y-1 overflow-y-auto custom-scrollbar pr-0.5">
    {#each sessions as session (session.id)}
        <button
            type="button"
            class="w-full text-left rounded-lg px-2.5 sm:px-3 py-1.5 sm:py-2 transition-colors {session.id ===
            selectedSessionId
                ? 'bg-indigo-100 dark:bg-indigo-900/35 text-indigo-950 dark:text-indigo-100'
                : 'text-sem-fg hover:bg-sem-surface-muted/70'}"
            onclick={() => onselect(session.id)}
        >
            <div class="flex items-center justify-between gap-2">
                <div class="font-medium text-xs sm:text-sm text-sem-fg truncate">
                    {session.name || t("rnx.unnamed_session")}
                </div>
                <span
                    class="text-[10px] sm:text-[11px] font-semibold uppercase tracking-wide shrink-0 {getSessionStatusClass(
                        session
                    )}"
                >
                    {statusLabel(session)}
                </span>
            </div>
            <div class="font-mono text-[10px] sm:text-xs text-sem-fg-muted truncate mt-0.5">
                {subtitle(session)}
            </div>
        </button>
    {/each}
    {#if sessions.length === 0}
        <div class="text-xs text-sem-fg-muted px-1">
            {t("rnx.no_sessions")}
        </div>
    {/if}
</div>
