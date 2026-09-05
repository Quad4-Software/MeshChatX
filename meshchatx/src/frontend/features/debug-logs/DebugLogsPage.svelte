<!-- SPDX-License-Identifier: 0BSD -->

<script>
    import { onMount } from "svelte";
    import MaterialDesignIcon from "../../ui/svelte/MaterialDesignIcon.svelte";
    import ToolsPageHeader from "../../ui/svelte/ToolsPageHeader.svelte";
    import ToastUtils from "../../js/ToastUtils.js";
    import { t } from "../../js/i18n.js";
    import { debugLevelClass, formatDebugTime, formatLogLine } from "./lib/debugFormat.js";

    let activeTab = $state("logs");
    /** @type {object[]} */
    let logs = $state([]);
    let total = $state(0);
    let limit = $state(100);
    let offset = $state(0);
    let search = $state("");
    let level = $state("");
    let is_anomaly = $state(false);
    let loading = $state(false);

    /** @type {object[]} */
    let accessAttempts = $state([]);
    let accessTotal = $state(0);
    let accessOffset = $state(0);
    let accessSearch = $state("");
    let accessOutcome = $state("");
    let accessLoading = $state(false);

    /** @type {ReturnType<typeof setInterval> | null} */
    let updateInterval = null;
    /** @type {ReturnType<typeof setTimeout> | null} */
    let searchTimeout = null;
    /** @type {ReturnType<typeof setTimeout> | null} */
    let accessSearchTimeout = null;

    const listOffset = $derived(activeTab === "logs" ? offset : accessOffset);
    const listTotal = $derived(activeTab === "logs" ? total : accessTotal);
    const showingFrom = $derived(listTotal === 0 ? 0 : listOffset + 1);
    const showingTo = $derived(Math.min(listOffset + limit, listTotal));

    async function refreshLogs(silent = false) {
        if (!silent) loading = true;
        try {
            const params = {
                limit,
                offset,
                search: search || undefined,
                level: level || undefined,
                is_anomaly: is_anomaly ? true : undefined,
            };
            const response = await window.api.get("/api/v1/debug/logs", { params });
            logs = response.data.logs;
            total = response.data.total;
        } catch (e) {
            console.log("Failed to fetch logs", e);
            if (!silent) ToastUtils.error(t("debug.failed_fetch_logs"));
        } finally {
            if (!silent) loading = false;
        }
    }

    async function refreshAccessAttempts(silent = false) {
        if (!silent) accessLoading = true;
        try {
            const params = {
                limit,
                offset: accessOffset,
                search: accessSearch || undefined,
                outcome: accessOutcome || undefined,
            };
            const response = await window.api.get("/api/v1/debug/access-attempts", { params });
            accessAttempts = response.data.attempts;
            accessTotal = response.data.total;
        } catch (e) {
            console.log("Failed to fetch access attempts", e);
            if (!silent) ToastUtils.error(t("debug.failed_fetch_access"));
        } finally {
            if (!silent) accessLoading = false;
        }
    }

    function switchTab(tab) {
        activeTab = tab;
        if (tab === "access" && accessAttempts.length === 0 && !accessLoading) {
            refreshAccessAttempts();
        }
    }

    function refreshActive() {
        if (activeTab === "logs") refreshLogs();
        else refreshAccessAttempts();
    }

    function debouncedSearch() {
        if (searchTimeout) clearTimeout(searchTimeout);
        searchTimeout = setTimeout(() => {
            offset = 0;
            refreshLogs();
        }, 500);
    }

    function debouncedAccessSearch() {
        if (accessSearchTimeout) clearTimeout(accessSearchTimeout);
        accessSearchTimeout = setTimeout(() => {
            accessOffset = 0;
            refreshAccessAttempts();
        }, 500);
    }

    function prevPage() {
        if (activeTab === "logs") {
            if (offset >= limit) {
                offset -= limit;
                refreshLogs();
            }
        } else if (accessOffset >= limit) {
            accessOffset -= limit;
            refreshAccessAttempts();
        }
    }

    function nextPage() {
        if (activeTab === "logs") {
            if (offset + limit < total) {
                offset += limit;
                refreshLogs();
            }
        } else if (accessOffset + limit < accessTotal) {
            accessOffset += limit;
            refreshAccessAttempts();
        }
    }

    async function copyActive() {
        if (activeTab === "logs") {
            const logText = logs.map((l) => formatLogLine(l)).join("\n");
            try {
                await navigator.clipboard.writeText(logText);
                ToastUtils.success(t("debug.logs_copied"));
            } catch {
                ToastUtils.error(t("debug.failed_copy_logs"));
            }
        } else {
            const lines = accessAttempts.map((r) =>
                [
                    formatDebugTime(r.created_at),
                    r.outcome,
                    r.method,
                    r.path,
                    r.client_ip,
                    r.user_agent || "",
                    r.detail || "",
                ].join(" | ")
            );
            try {
                await navigator.clipboard.writeText(lines.join("\n"));
                ToastUtils.success(t("debug.access_copied"));
            } catch {
                ToastUtils.error(t("debug.failed_copy_access"));
            }
        }
    }

    async function copyLogLine(log) {
        try {
            await navigator.clipboard.writeText(formatLogLine(log));
            ToastUtils.success(t("debug.logs_copied"));
        } catch {
            ToastUtils.error(t("debug.failed_copy_logs"));
        }
    }

    async function copyAccessLine(row) {
        const line = [
            formatDebugTime(row.created_at),
            row.outcome,
            row.method,
            row.path,
            row.client_ip,
            row.user_agent || "",
            row.detail || "",
        ].join(" | ");
        try {
            await navigator.clipboard.writeText(line);
            ToastUtils.success(t("debug.access_copied"));
        } catch {
            ToastUtils.error(t("debug.failed_copy_access"));
        }
    }

    onMount(() => {
        refreshLogs();
        updateInterval = setInterval(() => {
            if (activeTab !== "logs") return;
            if (offset === 0 && !search && !is_anomaly && !level) {
                refreshLogs(true);
            }
        }, 5000);
        return () => {
            if (updateInterval) clearInterval(updateInterval);
            if (searchTimeout) clearTimeout(searchTimeout);
            if (accessSearchTimeout) clearTimeout(accessSearchTimeout);
        };
    });
</script>

<div class="flex-1 flex flex-col h-full overflow-hidden" data-testid="debug-logs-page">
    <ToolsPageHeader icon="bug" title={t("debug.title")} description={t("debug.description")} accent="red">
        <button type="button" class="secondary-chip" onclick={copyActive}>
            <MaterialDesignIcon iconName="content-copy" class="w-4 h-4" />
            {activeTab === "logs" ? t("debug.copy_logs") : t("debug.copy_access")}
        </button>
        <button type="button" class="primary-chip" onclick={refreshActive}>
            <MaterialDesignIcon iconName="refresh" class="w-4 h-4" />
            {t("common.refresh")}
        </button>
    </ToolsPageHeader>

    <div class="px-4 md:px-6 pt-2 flex gap-2 border-b border-sem-border bg-sem-surface">
        <button
            type="button"
            class="px-3 py-2 text-sm font-medium border-b-2 -mb-px {activeTab === 'logs'
                ? 'border-red-500 text-sem-fg'
                : 'border-transparent text-sem-fg-muted hover:text-sem-fg'}"
            onclick={() => switchTab("logs")}
        >
            {t("debug.tab_logs")}
        </button>
        <button
            type="button"
            class="px-3 py-2 text-sm font-medium border-b-2 -mb-px {activeTab === 'access'
                ? 'border-red-500 text-sem-fg'
                : 'border-transparent text-sem-fg-muted hover:text-sem-fg'}"
            onclick={() => switchTab("access")}
        >
            {t("debug.tab_access_attempts")}
        </button>
    </div>

    <div class="p-4 md:p-6 space-y-4 overflow-y-auto flex-1">
        {#if activeTab === "logs"}
            <div class="glass-card p-4 flex flex-col md:flex-row gap-4 items-end">
                <div class="flex-1 w-full">
                    <label class="glass-label" for="debug-search">{t("common.search")}</label>
                    <div class="relative">
                        <div class="absolute inset-y-0 left-0 pl-3 flex items-center pointer-events-none">
                            <MaterialDesignIcon iconName="magnify" class="text-sem-fg-muted" />
                        </div>
                        <input
                            id="debug-search"
                            type="text"
                            class="input-field pl-10!"
                            placeholder={t("debug.search_logs_placeholder")}
                            bind:value={search}
                            oninput={debouncedSearch}
                        />
                    </div>
                </div>
                <div class="w-full md:w-48">
                    <label class="glass-label" for="debug-level">{t("debug.level")}</label>
                    <select
                        id="debug-level"
                        class="input-field"
                        bind:value={level}
                        onchange={() => {
                            offset = 0;
                            refreshLogs();
                        }}
                    >
                        <option value="">{t("debug.level_all")}</option>
                        <option value="DEBUG">DEBUG</option>
                        <option value="INFO">INFO</option>
                        <option value="WARNING">WARNING</option>
                        <option value="ERROR">ERROR</option>
                        <option value="CRITICAL">CRITICAL</option>
                    </select>
                </div>
                <div class="flex items-center h-[42px] pb-1">
                    <label class="flex items-center gap-2 cursor-pointer select-none">
                        <input
                            type="checkbox"
                            class="form-checkbox rounded-sm text-red-600 focus:ring-red-500"
                            bind:checked={is_anomaly}
                            onchange={() => {
                                offset = 0;
                                refreshLogs();
                            }}
                        />
                        <span class="text-sm font-medium text-sem-fg">{t("debug.anomalies_only")}</span>
                    </label>
                </div>
            </div>
        {:else}
            <div class="glass-card p-4 flex flex-col md:flex-row gap-4 items-end">
                <div class="flex-1 w-full">
                    <label class="glass-label" for="access-search">{t("common.search")}</label>
                    <div class="relative">
                        <div class="absolute inset-y-0 left-0 pl-3 flex items-center pointer-events-none">
                            <MaterialDesignIcon iconName="magnify" class="text-sem-fg-muted" />
                        </div>
                        <input
                            id="access-search"
                            type="text"
                            class="input-field pl-10!"
                            placeholder={t("debug.search_access_placeholder")}
                            bind:value={accessSearch}
                            oninput={debouncedAccessSearch}
                        />
                    </div>
                </div>
                <div class="w-full md:w-56">
                    <label class="glass-label" for="access-outcome">{t("debug.outcome")}</label>
                    <select
                        id="access-outcome"
                        class="input-field"
                        bind:value={accessOutcome}
                        onchange={() => {
                            accessOffset = 0;
                            refreshAccessAttempts();
                        }}
                    >
                        <option value="">{t("debug.outcome_all")}</option>
                        <option value="success">success</option>
                        <option value="failed_password">failed_password</option>
                        <option value="failed_csrf">failed_csrf</option>
                        <option value="failed_auth">failed_auth</option>
                        <option value="rate_limited">rate_limited</option>
                    </select>
                </div>
            </div>
        {/if}

        <div class="glass-card overflow-hidden flex flex-col min-h-[400px]">
            {#if (activeTab === "logs" && loading) || (activeTab === "access" && accessLoading)}
                <div class="flex-1 flex items-center justify-center p-8 text-sem-fg-muted">
                    <MaterialDesignIcon iconName="loading" class="w-8 h-8 animate-spin" />
                </div>
            {:else if activeTab === "logs" && logs.length === 0}
                <div class="flex-1 flex flex-col items-center justify-center p-8 text-sem-fg-muted">
                    <MaterialDesignIcon iconName="text-box-search-outline" class="w-12 h-12 mb-2 opacity-50" />
                    <p>{t("debug.no_logs")}</p>
                </div>
            {:else if activeTab === "access" && accessAttempts.length === 0}
                <div class="flex-1 flex flex-col items-center justify-center p-8 text-sem-fg-muted">
                    <MaterialDesignIcon iconName="shield-lock-outline" class="w-12 h-12 mb-2 opacity-50" />
                    <p>{t("debug.no_access")}</p>
                </div>
            {:else if activeTab === "logs"}
                <div class="flex-1 overflow-y-auto font-mono text-[10px] sm:text-xs debug-log-scroll">
                    {#each logs as log, index (`${log.timestamp}-${index}-${log.message}`)}
                        <div
                            role="button"
                            tabindex="0"
                            class="border-b border-sem-border/50 hover:bg-sem-surface-muted/50 px-2 sm:px-4 py-1.5 sm:py-2 flex gap-2 sm:gap-4 transition-colors cursor-pointer active:bg-sem-surface-muted {log.is_anomaly
                                ? 'bg-red-50/50 dark:bg-red-900/10'
                                : ''}"
                            onclick={() => copyLogLine(log)}
                            onkeydown={(e) => {
                                if (e.key === "Enter" || e.key === " ") {
                                    e.preventDefault();
                                    copyLogLine(log);
                                }
                            }}
                        >
                            <div
                                class="text-sem-fg-muted whitespace-nowrap w-24 sm:w-40 shrink-0 truncate max-sm:text-[8px]"
                            >
                                {formatDebugTime(log.timestamp)}
                            </div>
                            <div class="font-bold w-12 sm:w-20 shrink-0 max-sm:text-[8px] {debugLevelClass(log.level)}">
                                {log.level}
                            </div>
                            <div
                                class="text-purple-600 dark:text-purple-400 w-20 sm:w-32 shrink-0 truncate max-sm:text-[8px]"
                                title={log.module}
                            >
                                {log.module}
                            </div>
                            <div class="flex-1 break-all text-sem-fg max-sm:text-[8px] sm:text-[10px]">
                                {#if log.is_anomaly}
                                    <span
                                        class="bg-red-100 text-red-800 dark:bg-red-900 dark:text-red-100 px-1 rounded-sm mr-2 text-[9px] sm:text-[10px] font-bold uppercase"
                                    >
                                        {log.anomaly_type || "ANOMALY"}
                                    </span>
                                {/if}
                                {log.message}
                            </div>
                        </div>
                    {/each}
                </div>
            {:else}
                <div class="flex-1 overflow-y-auto font-mono text-[10px] sm:text-xs debug-log-scroll">
                    {#each accessAttempts as row (`${row.id}-${row.created_at}`)}
                        <div
                            role="button"
                            tabindex="0"
                            class="border-b border-sem-border/50 hover:bg-sem-surface-muted/50 px-2 sm:px-4 py-1.5 sm:py-2 flex flex-col gap-0.5 transition-colors cursor-pointer active:bg-sem-surface-muted"
                            onclick={() => copyAccessLine(row)}
                            onkeydown={(e) => {
                                if (e.key === "Enter" || e.key === " ") {
                                    e.preventDefault();
                                    copyAccessLine(row);
                                }
                            }}
                        >
                            <div class="flex flex-wrap gap-2 sm:gap-4 items-baseline">
                                <span class="text-sem-fg-muted whitespace-nowrap max-sm:text-[8px]">
                                    {formatDebugTime(row.created_at)}
                                </span>
                                <span
                                    class="font-bold max-sm:text-[8px] {row.outcome === 'success'
                                        ? 'text-emerald-600'
                                        : 'text-red-500'}"
                                >
                                    {row.outcome}
                                </span>
                                <span class="text-sem-fg max-sm:text-[8px]">{row.method} {row.path}</span>
                                <span class="text-sem-fg-muted max-sm:text-[8px]">{row.client_ip}</span>
                            </div>
                            <div class="text-sem-fg-muted break-all max-sm:text-[8px]">
                                <span class="text-sem-fg-muted">UA</span>
                                {row.user_agent || "-"}
                            </div>
                            {#if row.detail}
                                <div class="text-sem-fg-muted max-sm:text-[8px] sm:text-[10px]">{row.detail}</div>
                            {/if}
                        </div>
                    {/each}
                </div>
            {/if}

            <div class="px-4 py-3 flex items-center justify-between border-t border-sem-border bg-sem-surface-muted/50">
                <div class="flex-1 flex justify-between sm:hidden">
                    <button
                        type="button"
                        class="relative inline-flex items-center px-4 py-2 border border-sem-border text-sm font-medium rounded-md text-sem-fg bg-sem-surface hover:bg-sem-surface-muted disabled:opacity-50"
                        disabled={listOffset === 0}
                        onclick={prevPage}
                    >
                        Previous
                    </button>
                    <button
                        type="button"
                        class="ml-3 relative inline-flex items-center px-4 py-2 border border-sem-border text-sm font-medium rounded-md text-sem-fg bg-sem-surface hover:bg-sem-surface-muted disabled:opacity-50"
                        disabled={listOffset + limit >= listTotal}
                        onclick={nextPage}
                    >
                        Next
                    </button>
                </div>
                <div class="hidden sm:flex-1 sm:flex sm:items-center sm:justify-between">
                    <div>
                        <p class="text-sm text-sem-fg-muted font-mono">
                            Showing
                            <span class="font-bold">{showingFrom}</span>
                            to
                            <span class="font-bold">{showingTo}</span>
                            of
                            <span class="font-bold">{listTotal}</span>
                            results
                        </p>
                    </div>
                    <div class="flex gap-2">
                        <button
                            type="button"
                            class="secondary-chip px-3 py-1 text-xs disabled:opacity-50"
                            disabled={listOffset === 0}
                            onclick={prevPage}
                        >
                            <MaterialDesignIcon iconName="chevron-left" class="w-4 h-4" />
                            Previous
                        </button>
                        <button
                            type="button"
                            class="secondary-chip px-3 py-1 text-xs disabled:opacity-50"
                            disabled={listOffset + limit >= listTotal}
                            onclick={nextPage}
                        >
                            Next
                            <MaterialDesignIcon iconName="chevron-right" class="w-4 h-4" />
                        </button>
                    </div>
                </div>
            </div>
        </div>
    </div>
</div>

<style>
    .glass-card {
        border-radius: 2px !important;
    }
    .debug-log-scroll {
        -webkit-text-size-adjust: 100%;
        text-size-adjust: 100%;
    }
</style>
