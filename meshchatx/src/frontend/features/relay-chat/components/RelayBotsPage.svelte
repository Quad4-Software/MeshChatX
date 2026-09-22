<!-- SPDX-License-Identifier: 0BSD -->

<script lang="ts">
    import { onMount, onDestroy } from "svelte";
    import MaterialDesignIcon from "../../../ui/svelte/MaterialDesignIcon.svelte";
    import Toggle from "../../../ui/svelte/Toggle.svelte";
    import DialogUtils from "../../../js/DialogUtils.js";
    import ToastUtils from "../../../js/ToastUtils.js";
    import { apiPath } from "../../../js/constants.js";
    import { t } from "../../../js/i18n.js";
    import type { RrcBotRecord, RrcKnownHub } from "../lib/types.js";

    const BTN_PRIMARY =
        "inline-flex items-center justify-center gap-1.5 rounded-lg bg-sem-action-primary px-3 py-2 text-sm font-semibold text-white transition hover:bg-sem-action-primary-hover disabled:opacity-50";
    const BTN_SECONDARY =
        "inline-flex items-center justify-center gap-1.5 rounded-lg border border-sem-border bg-sem-surface-raised px-3 py-2 text-sm font-medium text-sem-fg transition hover:bg-sem-surface-muted disabled:opacity-50";
    const BTN_ICON =
        "inline-flex items-center justify-center rounded-lg p-2 text-sem-fg-muted transition hover:bg-sem-surface-muted hover:text-sem-fg";

    interface BotsForm {
        name: string;
        nick: string;
        hubPick: string;
        hubCustom: string;
        roomsCsv: string;
        mentionOnly: boolean;
        prefix: string;
        rateSeconds: number;
    }

    const DEFAULT_FORM = (): BotsForm => ({
        name: "",
        nick: "",
        hubPick: "",
        hubCustom: "",
        roomsCsv: "#general",
        mentionOnly: true,
        prefix: "!",
        rateSeconds: 8,
    });

    interface Props {
        knownHubs?: RrcKnownHub[];
    }

    let { knownHubs = [] }: Props = $props();

    let botsLoading = $state(false);
    let bots = $state<RrcBotRecord[]>([]);
    let creating = $state(false);
    let showCreate = $state(false);
    let form = $state<BotsForm>(DEFAULT_FORM());
    let pollTimer: ReturnType<typeof setInterval> | null = null;

    const rrcBots = $derived(bots.filter((b) => (b.template_id || b.template) === "rrc"));
    const effectiveHubHash = $derived(form.hubPick || form.hubCustom);

    function formatHash(h: unknown): string {
        const s = String(h || "");
        return s.length > 20 ? `${s.slice(0, 10)}…${s.slice(-8)}` : s;
    }

    function parseRooms(csv: string): string[] {
        return String(csv || "")
            .split(",")
            .map((r) => r.trim().replace(/^#+/, ""))
            .filter(Boolean);
    }

    async function fetchBots({ quiet = false } = {}): Promise<void> {
        if (!quiet) botsLoading = true;
        try {
            const res = await window.api.get(apiPath("/bots/status"));
            bots = (res?.data as { status?: { bots?: RrcBotRecord[] } })?.status?.bots || [];
        } catch {
            if (!quiet) bots = [];
        } finally {
            botsLoading = false;
        }
    }

    function resetCreate(): void {
        form = DEFAULT_FORM();
        showCreate = false;
    }

    function errorMessage(e: unknown, fallback: string): string {
        return (e as { response?: { data?: { message?: string } } })?.response?.data?.message || fallback;
    }

    async function createBot(): Promise<void> {
        creating = true;
        try {
            await window.api.post(apiPath("/bots/start"), {
                template_id: "rrc",
                name: form.name,
                rrc: {
                    hub: effectiveHubHash,
                    rooms: parseRooms(form.roomsCsv),
                    nick: form.nick || form.name,
                    mention_only: form.mentionOnly,
                    prefix: form.prefix || "!",
                    rate_seconds: Math.max(0, Math.min(3600, Number(form.rateSeconds) || 8)),
                },
            });
            ToastUtils.success(t("bots.bot_started"));
            resetCreate();
            await fetchBots({ quiet: true });
        } catch (e) {
            ToastUtils.error(errorMessage(e, t("bots.failed_to_start")));
        } finally {
            creating = false;
        }
    }

    async function startBot(bot: RrcBotRecord): Promise<void> {
        try {
            await window.api.post(apiPath("/bots/start"), {
                template_id: "rrc",
                bot_id: bot.id,
                name: bot.name,
            });
            ToastUtils.success(t("bots.bot_started"));
        } catch (e) {
            ToastUtils.error(errorMessage(e, t("bots.failed_to_start")));
        }
        await fetchBots({ quiet: true });
    }

    async function stopBot(bot: RrcBotRecord): Promise<void> {
        try {
            await window.api.post(apiPath("/bots/stop"), { bot_id: bot.id });
            ToastUtils.success(t("bots.bot_stopped"));
        } catch (e) {
            ToastUtils.error(errorMessage(e, t("bots.failed_to_stop")));
        }
        await fetchBots({ quiet: true });
    }

    async function confirmDelete(bot: RrcBotRecord): Promise<void> {
        const ok = await DialogUtils.confirm(t("relay_chat.bots_delete_confirm", { name: bot.name }));
        if (!ok) return;
        try {
            await window.api.post(apiPath("/bots/delete"), { bot_id: bot.id });
            ToastUtils.success(t("bots.bot_deleted"));
        } catch (e) {
            ToastUtils.error(errorMessage(e, t("bots.failed_to_delete")));
        }
        await fetchBots({ quiet: true });
    }

    onMount(() => {
        void fetchBots();
        pollTimer = setInterval(() => void fetchBots({ quiet: true }), 5000);
    });

    onDestroy(() => {
        if (pollTimer) clearInterval(pollTimer);
    });
</script>

<div class="flex-1 overflow-y-auto custom-scrollbar p-3 sm:p-4">
    <div class="mx-auto w-full max-w-3xl space-y-4">
        <div class="flex flex-wrap items-start justify-between gap-3">
            <div>
                <h2 class="text-lg font-semibold">{t("relay_chat.bots_title")}</h2>
                <p class="text-sm text-sem-fg-muted">{t("relay_chat.bots_subtitle")}</p>
            </div>
            <div class="flex items-center gap-2">
                <a href="#/bots" class={BTN_SECONDARY} title={t("relay_chat.bots_manage_all")}>
                    <MaterialDesignIcon iconName="cog" class="size-4" />
                    {t("relay_chat.bots_manage_all")}
                </a>
                <button
                    type="button"
                    class={BTN_PRIMARY}
                    onclick={() => {
                        showCreate = !showCreate;
                    }}
                >
                    <MaterialDesignIcon iconName="plus" class="size-4" />
                    {t("relay_chat.bots_new")}
                </button>
            </div>
        </div>

        {#if showCreate}
            <div class="rounded-xl border border-sem-border bg-sem-canvas p-4 space-y-3">
                <div class="grid gap-3 sm:grid-cols-2">
                    <label class="flex flex-col gap-1">
                        <span class="text-xs font-medium text-sem-fg-muted">{t("bots.bot_name")}</span>
                        <input bind:value={form.name} type="text" class="input-field" maxlength="48" />
                    </label>
                    <label class="flex flex-col gap-1">
                        <span class="text-xs font-medium text-sem-fg-muted">{t("relay_chat.bots_form_nick")}</span>
                        <input bind:value={form.nick} type="text" class="input-field" maxlength="32" />
                    </label>
                    <label class="flex flex-col gap-1 sm:col-span-2">
                        <span class="text-xs font-medium text-sem-fg-muted">{t("relay_chat.bots_form_hub")}</span>
                        <div class="flex gap-2">
                            <select bind:value={form.hubPick} class="input-field min-w-0 flex-1">
                                <option value="">{t("relay_chat.bots_form_hub_custom")}</option>
                                {#each knownHubs as h (h.hash)}
                                    <option value={h.hash}>
                                        {h.name || t("relay_chat.bots_form_hub_custom")} ({formatHash(h.hash)})
                                    </option>
                                {/each}
                            </select>
                            {#if !form.hubPick}
                                <input
                                    bind:value={form.hubCustom}
                                    type="text"
                                    class="input-field min-w-0 flex-1 font-mono"
                                    maxlength="64"
                                    placeholder="<hub destination hash>"
                                />
                            {/if}
                        </div>
                    </label>
                    <label class="flex flex-col gap-1 sm:col-span-2">
                        <span class="text-xs font-medium text-sem-fg-muted">{t("relay_chat.bots_form_rooms")}</span>
                        <input
                            bind:value={form.roomsCsv}
                            type="text"
                            class="input-field"
                            placeholder="#general, #dev"
                        />
                        <span class="text-xs text-sem-fg-muted">{t("relay_chat.bots_form_rooms_hint")}</span>
                    </label>
                    <label class="flex items-center justify-between gap-2 sm:col-span-2">
                        <span class="text-sm">{t("relay_chat.bots_form_mention_only")}</span>
                        <Toggle bind:checked={form.mentionOnly} />
                    </label>
                    <label class="flex flex-col gap-1">
                        <span class="text-xs font-medium text-sem-fg-muted">{t("relay_chat.bots_form_prefix")}</span>
                        <input bind:value={form.prefix} type="text" class="input-field" maxlength="4" />
                    </label>
                    <label class="flex flex-col gap-1">
                        <span class="text-xs font-medium text-sem-fg-muted">{t("relay_chat.bots_form_cooldown")}</span>
                        <input bind:value={form.rateSeconds} type="number" min="0" max="3600" class="input-field" />
                    </label>
                </div>
                <div class="flex items-center justify-end gap-2">
                    <button type="button" class={BTN_SECONDARY} onclick={resetCreate}>
                        {t("bots.cancel")}
                    </button>
                    <button
                        type="button"
                        class={BTN_PRIMARY}
                        disabled={creating || !form.name || !effectiveHubHash}
                        onclick={createBot}
                    >
                        {#if creating}
                            <MaterialDesignIcon iconName="loading" class="size-4 animate-spin" />
                        {/if}
                        {t("relay_chat.bots_create")}
                    </button>
                </div>
            </div>
        {/if}

        {#if botsLoading}
            <div class="flex justify-center py-8">
                <MaterialDesignIcon iconName="loading" class="size-6 animate-spin text-sem-fg-muted" />
            </div>
        {:else if rrcBots.length === 0}
            <div
                class="flex flex-col items-center gap-2 rounded-xl border border-sem-border bg-sem-canvas p-8 text-center text-sm text-sem-fg-muted"
            >
                <MaterialDesignIcon iconName="robot-off" class="size-10 opacity-40" />
                {t("relay_chat.bots_none")}
            </div>
        {:else}
            {#each rrcBots as bot (bot.id)}
                <div class="rounded-xl border border-sem-border bg-sem-canvas p-4 space-y-3">
                    <div class="flex flex-wrap items-start justify-between gap-3">
                        <div class="min-w-0 flex-1">
                            <div class="flex items-center gap-2">
                                <span
                                    class="size-2 shrink-0 rounded-full {bot.running
                                        ? 'bg-sem-success'
                                        : 'bg-sem-fg-muted'}"
                                ></span>
                                <span class="font-semibold truncate">{bot.name}</span>
                                {#if bot.rrc?.nick}
                                    <span class="text-xs text-sem-fg-muted">@{bot.rrc.nick}</span>
                                {/if}
                            </div>
                            <div class="mt-1 space-y-0.5 text-xs text-sem-fg-muted">
                                {#if bot.rrc?.hub}
                                    <div class="font-mono truncate">
                                        {t("relay_chat.bots_hub")}: {formatHash(bot.rrc.hub)}
                                    </div>
                                {/if}
                                {#if bot.rrc?.rooms?.length}
                                    <div>
                                        {t("relay_chat.bots_rooms")}:
                                        {bot.rrc.rooms.map((r) => "#" + r.replace(/^#/, "")).join(", ")}
                                    </div>
                                {/if}
                                {#if bot.last_error}
                                    <div class="text-sem-danger break-all">{bot.last_error}</div>
                                {/if}
                            </div>
                        </div>
                        <div class="flex shrink-0 items-center gap-1.5">
                            {#if !bot.running}
                                <button
                                    type="button"
                                    class="{BTN_SECONDARY} px-2.5! py-1.5! text-xs!"
                                    onclick={() => startBot(bot)}
                                >
                                    <MaterialDesignIcon iconName="play" class="size-4" />
                                    {t("relay_chat.host_start")}
                                </button>
                            {:else}
                                <button
                                    type="button"
                                    class="{BTN_SECONDARY} px-2.5! py-1.5! text-xs!"
                                    onclick={() => stopBot(bot)}
                                >
                                    <MaterialDesignIcon iconName="stop" class="size-4" />
                                    {t("relay_chat.host_stop")}
                                </button>
                            {/if}
                            <button
                                type="button"
                                class={BTN_ICON}
                                title={t("bots.delete_bot")}
                                onclick={() => confirmDelete(bot)}
                            >
                                <MaterialDesignIcon iconName="delete" class="size-4" />
                            </button>
                        </div>
                    </div>
                </div>
            {/each}
        {/if}
    </div>
</div>
