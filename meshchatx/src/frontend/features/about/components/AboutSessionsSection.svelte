<!-- SPDX-License-Identifier: 0BSD -->

<script lang="ts">
    import { t } from "../../../js/i18n.js";
    import MaterialDesignIcon from "../../../ui/svelte/MaterialDesignIcon.svelte";
    import { formatSessionConnectedAt } from "../lib/aboutFormat.js";
    import type { ActiveSession } from "../lib/types.js";

    interface Props {
        activeSessions?: ActiveSession[];
        activeSessionCount?: number;
    }

    let { activeSessions = [], activeSessionCount = 0 }: Props = $props();
</script>

<div class="w-full border-b border-gray-200/60 dark:border-zinc-800/60 py-6 sm:py-8 last:border-0">
    <div class="flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between mb-4">
        <div class="text-xs font-black text-blue-500 uppercase tracking-[0.2em] flex items-center gap-2">
            <MaterialDesignIcon iconName="monitor-multiple" class="size-3.5" />
            {t("about.active_sessions")}
        </div>
        <span class="text-[11px] font-black uppercase tracking-wider text-sem-fg-muted">
            {t("about.active_sessions_count", { count: activeSessionCount })}
        </span>
    </div>
    <p class="text-[11px] leading-relaxed text-sem-fg-muted mb-4">
        {t("about.active_sessions_description")}
    </p>
    {#if !activeSessions.length}
        <div class="text-sm text-sem-fg-muted">
            {t("about.active_sessions_empty")}
        </div>
    {:else}
        <ul class="space-y-3 list-none p-0 m-0">
            {#each activeSessions as session (session.id)}
                <li class="rounded-xl border border-sem-border bg-gray-50/70 dark:bg-zinc-900/40 p-3 min-w-0">
                    <div class="grid gap-2 text-[11px] sm:grid-cols-2">
                        <div class="min-w-0">
                            <div class="text-[10px] font-black uppercase tracking-wider text-sem-fg-muted mb-1">
                                {t("about.active_session_ip")}
                            </div>
                            <div class="font-mono text-sem-fg break-all">
                                {session.ip || "unknown"}
                            </div>
                        </div>
                        <div class="min-w-0">
                            <div class="text-[10px] font-black uppercase tracking-wider text-sem-fg-muted mb-1">
                                {t("about.active_session_connected")}
                            </div>
                            <div class="text-sem-fg">
                                {formatSessionConnectedAt(session.connected_at)}
                            </div>
                        </div>
                        <div class="min-w-0 sm:col-span-2">
                            <div class="text-[10px] font-black uppercase tracking-wider text-sem-fg-muted mb-1">
                                {t("about.active_session_user_agent")}
                            </div>
                            <div class="font-mono text-sem-fg-secondary break-all">
                                {session.user_agent || "unknown"}
                            </div>
                        </div>
                    </div>
                </li>
            {/each}
        </ul>
    {/if}
</div>
