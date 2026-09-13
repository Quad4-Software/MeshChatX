<!-- SPDX-License-Identifier: 0BSD -->

<script lang="ts">
    import { tick } from "svelte";
    import MaterialDesignIcon from "../../../ui/svelte/MaterialDesignIcon.svelte";
    import { t } from "../../../js/i18n.js";

    interface Props {
        destinationHash: string;
    }

    let { destinationHash }: Props = $props();

    let messages = $state<any[]>([]);
    let newMessage = $state("");
    let loading = $state(false);
    let sending = $state(false);
    let messageListEl = $state<HTMLDivElement | null>(null);

    $effect(() => {
        if (destinationHash) {
            fetchMessages();
        }
    });

    async function fetchMessages() {
        if (!destinationHash) return;
        loading = true;
        try {
            const response = await window.api.get(
                `/api/v1/lxmf-messages/conversation/${destinationHash}?count=20&order=desc`
            );
            messages = (response?.data?.lxmf_messages || []).reverse();
            scrollToBottom();
        } catch (e) {
            console.error("Failed to fetch messages", e);
        } finally {
            loading = false;
        }
    }

    async function sendMessage() {
        if (!newMessage.trim() || sending) return;
        sending = true;
        try {
            const response = await window.api.post("/api/v1/lxmf-messages/send", {
                lxmf_message: {
                    destination_hash: destinationHash,
                    content: newMessage,
                },
            });
            const msg = response?.data?.lxmf_message;
            if (msg) {
                messages = [
                    ...messages,
                    {
                        hash: msg.hash,
                        content: msg.content,
                        is_outbound: true,
                        timestamp: msg.created_at,
                        fields: msg.fields,
                    },
                ];
            }
            newMessage = "";
            scrollToBottom();
        } catch (e) {
            console.error("Failed to send message", e);
        } finally {
            sending = false;
        }
    }

    function scrollToBottom() {
        tick().then(() => {
            if (messageListEl) {
                messageListEl.scrollTop = messageListEl.scrollHeight;
            }
        });
    }

    function formatTime(ts: number | string | null | undefined): string {
        if (!ts) return "";
        const date = new Date(Number(ts) * 1000);
        if (isNaN(date.getTime())) return "";
        return date.toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" });
    }
</script>

<div class="flex flex-col h-64 bg-gray-50 dark:bg-zinc-950 rounded-lg overflow-hidden border border-sem-border">
    <!-- message list -->
    <div bind:this={messageListEl} class="flex-1 overflow-y-auto p-2 space-y-2 scrollbar-thin">
        {#if loading}
            <div class="flex justify-center py-4">
                <MaterialDesignIcon iconName="loading" class="size-5 animate-spin text-gray-400" />
            </div>
        {:else if messages.length === 0}
            <div class="text-center py-4 text-xs text-gray-400">
                {t("messages.no_messages_yet")}
            </div>
        {:else}
            {#each messages as msg (msg.hash || msg.timestamp)}
                <div class="flex flex-col max-w-[90%] {msg.is_outbound ? 'ml-auto items-end' : 'mr-auto items-start'}">
                    <div
                        class="px-2 py-1 rounded-lg text-xs wrap-break-word shadow-xs {msg.is_outbound
                            ? 'bg-blue-600 text-white'
                            : 'bg-sem-surface text-sem-fg'}"
                    >
                        <!-- Telemetry Header if no content -->
                        {#if !msg.content && msg.fields?.telemetry}
                            <div class="flex items-center gap-1 mb-1 pb-1 border-b border-white/10 opacity-80">
                                <MaterialDesignIcon iconName="satellite-variant" class="size-2.5" />
                                <span class="text-[8px] font-bold uppercase tracking-wider">
                                    {msg.is_outbound
                                        ? t("messages.telemetry_label_sent")
                                        : t("messages.telemetry_label_received")}
                                </span>
                            </div>
                        {/if}

                        {#if !msg.content && msg.fields?.commands?.some((c: any) => c["0x01"] || c["1"] || c["0x1"])}
                            <div class="flex items-center gap-1 mb-1 pb-1 border-b border-white/10 opacity-80">
                                <MaterialDesignIcon iconName="crosshairs-question" class="size-2.5" />
                                <span class="text-[8px] font-bold uppercase tracking-wider">
                                    {t("messages.telemetry_location_request")}
                                </span>
                            </div>
                        {/if}

                        {#if msg.content}
                            <div class="leading-normal">{msg.content}</div>
                        {/if}

                        <!-- Mini Telemetry Data -->
                        {#if msg.fields?.telemetry}
                            <div class="mt-1 space-y-1">
                                {#if msg.fields.telemetry.location}
                                    <div class="flex items-center gap-1 text-[9px] font-mono opacity-90">
                                        <MaterialDesignIcon iconName="map-marker" class="size-2.5" />
                                        <span>
                                            {Number(msg.fields.telemetry.location.latitude).toFixed(4)},
                                            {Number(msg.fields.telemetry.location.longitude).toFixed(4)}
                                        </span>
                                    </div>
                                {/if}
                                <div class="flex gap-2 opacity-70 text-[8px]">
                                    {#if msg.fields.telemetry.battery}
                                        <span class="flex items-center gap-0.5">
                                            <MaterialDesignIcon iconName="battery" class="size-2" />{msg.fields
                                                .telemetry.battery.charge_percent}%
                                        </span>
                                    {/if}
                                    {#if msg.fields.telemetry.physical_link}
                                        <span class="flex items-center gap-0.5">
                                            <MaterialDesignIcon iconName="antenna" class="size-2" />SNR:
                                            {msg.fields.telemetry.physical_link.snr}dB
                                        </span>
                                    {/if}
                                </div>
                            </div>
                        {/if}
                    </div>
                    <div class="text-[8px] text-gray-400 mt-0.5">
                        {formatTime(msg.timestamp)}
                    </div>
                </div>
            {/each}
        {/if}
    </div>

    <!-- input -->
    <div class="p-2 bg-sem-surface border-t border-sem-border">
        <div class="flex gap-1">
            <input
                bind:value={newMessage}
                type="text"
                class="flex-1 bg-gray-50 dark:bg-zinc-800 border border-sem-border rounded-md px-2 py-1 text-xs focus:outline-hidden focus:ring-1 focus:ring-blue-500 text-sem-fg"
                placeholder={t("messages.send_placeholder")}
                onkeydown={(e) => {
                    if (e.key === "Enter") sendMessage();
                }}
            />
            <button
                type="button"
                disabled={!newMessage.trim() || sending}
                aria-label={t("messages.send")}
                title={t("messages.send")}
                class="p-1.5 bg-blue-500 hover:bg-blue-600 disabled:bg-gray-300 dark:disabled:bg-zinc-700 text-white rounded-md transition-colors cursor-pointer"
                onclick={sendMessage}
            >
                <MaterialDesignIcon
                    iconName={sending ? "loading" : "send"}
                    class="size-3.5 {sending ? 'animate-spin' : ''}"
                />
            </button>
        </div>
    </div>
</div>
