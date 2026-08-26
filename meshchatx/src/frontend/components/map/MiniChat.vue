<!-- SPDX-License-Identifier: 0BSD -->

<template>
    <div class="flex flex-col h-64 bg-gray-50 dark:bg-zinc-950 rounded-lg overflow-hidden border border-sem-border">
        <!-- message list -->
        <div ref="messageList" class="flex-1 overflow-y-auto p-2 space-y-2 scrollbar-thin">
            <div v-if="loading" class="flex justify-center py-4">
                <MaterialDesignIcon icon-name="loading" class="size-5 animate-spin text-gray-400" />
            </div>
            <div v-else-if="messages.length === 0" class="text-center py-4 text-xs text-gray-400">
                {{ $t("messages.no_messages_yet") }}
            </div>
            <div
                v-for="msg in messages"
                :key="msg.hash"
                class="flex flex-col max-w-[90%]"
                :class="msg.is_outbound ? 'ml-auto items-end' : 'mr-auto items-start'"
            >
                <div
                    class="px-2 py-1 rounded-lg text-xs wrap-break-word shadow-xs"
                    :class="msg.is_outbound ? 'bg-blue-600 text-white' : 'bg-sem-surface text-sem-fg'"
                >
                    <!-- Telemetry Header if no content -->
                    <div
                        v-if="!msg.content && msg.fields?.telemetry"
                        class="flex items-center gap-1 mb-1 pb-1 border-b border-white/10 opacity-80"
                    >
                        <MaterialDesignIcon icon-name="satellite-variant" class="size-2.5" />
                        <span class="text-[8px] font-bold uppercase tracking-wider">{{
                            msg.is_outbound
                                ? $t("messages.telemetry_label_sent")
                                : $t("messages.telemetry_label_received")
                        }}</span>
                    </div>

                    <div
                        v-if="!msg.content && msg.fields?.commands?.some((c) => c['0x01'] || c['1'] || c['0x1'])"
                        class="flex items-center gap-1 mb-1 pb-1 border-b border-white/10 opacity-80"
                    >
                        <MaterialDesignIcon icon-name="crosshairs-question" class="size-2.5" />
                        <span class="text-[8px] font-bold uppercase tracking-wider">{{
                            $t("messages.telemetry_location_request")
                        }}</span>
                    </div>

                    <div v-if="msg.content" class="leading-normal">{{ msg.content }}</div>

                    <!-- Mini Telemetry Data -->
                    <div v-if="msg.fields?.telemetry" class="mt-1 space-y-1">
                        <div
                            v-if="msg.fields.telemetry.location"
                            class="flex items-center gap-1 text-[9px] font-mono opacity-90"
                        >
                            <MaterialDesignIcon icon-name="map-marker" class="size-2.5" />
                            <span
                                >{{ msg.fields.telemetry.location.latitude.toFixed(4) }},
                                {{ msg.fields.telemetry.location.longitude.toFixed(4) }}</span
                            >
                        </div>
                        <div class="flex gap-2 opacity-70 text-[8px]">
                            <span v-if="msg.fields.telemetry.battery" class="flex items-center gap-0.5">
                                <MaterialDesignIcon icon-name="battery" class="size-2" />{{
                                    msg.fields.telemetry.battery.charge_percent
                                }}%
                            </span>
                            <span v-if="msg.fields.telemetry.physical_link" class="flex items-center gap-0.5">
                                <MaterialDesignIcon icon-name="antenna" class="size-2" />SNR:
                                {{ msg.fields.telemetry.physical_link.snr }}dB
                            </span>
                        </div>
                    </div>
                </div>
                <div class="text-[8px] text-gray-400 mt-0.5">
                    {{ formatTime(msg.timestamp) }}
                </div>
            </div>
        </div>

        <!-- input -->
        <div class="p-2 bg-sem-surface border-t border-sem-border">
            <div class="flex gap-1">
                <input
                    v-model="newMessage"
                    type="text"
                    class="flex-1 bg-gray-50 dark:bg-zinc-800 border border-sem-border rounded-md px-2 py-1 text-xs focus:outline-hidden focus:ring-1 focus:ring-blue-500 text-sem-fg"
                    :placeholder="$t('messages.send_placeholder')"
                    @keydown.enter="sendMessage"
                />
                <button
                    type="button"
                    :disabled="!newMessage.trim() || sending"
                    :aria-label="$t('messages.send')"
                    :title="$t('messages.send')"
                    class="p-1.5 bg-blue-500 hover:bg-blue-600 disabled:bg-gray-300 dark:disabled:bg-zinc-700 text-white rounded-md transition-colors"
                    @click="sendMessage"
                >
                    <MaterialDesignIcon
                        :icon-name="sending ? 'loading' : 'send'"
                        :class="['size-3.5', { 'animate-spin': sending }]"
                    />
                </button>
            </div>
        </div>
    </div>
</template>

<script>
import MaterialDesignIcon from "../MaterialDesignIcon.vue";

export default {
    name: "MiniChat",
    components: {
        MaterialDesignIcon,
    },
    props: {
        destinationHash: {
            type: String,
            required: true,
        },
    },
    data() {
        return {
            messages: [],
            newMessage: "",
            loading: false,
            sending: false,
        };
    },
    watch: {
        destinationHash: {
            immediate: true,
            handler() {
                this.fetchMessages();
            },
        },
    },
    mounted() {
        // Listen for new messages via websocket if possible
        // For now we'll just poll or rely on parent updates if needed
    },
    methods: {
        async fetchMessages() {
            if (!this.destinationHash) return;
            this.loading = true;
            try {
                const response = await window.api.get(
                    `/api/v1/lxmf-messages/conversation/${this.destinationHash}?count=20&order=desc`
                );
                this.messages = (response.data.lxmf_messages || []).reverse();
                this.scrollToBottom();
            } catch (e) {
                console.error("Failed to fetch messages", e);
            } finally {
                this.loading = false;
            }
        },
        async sendMessage() {
            if (!this.newMessage.trim() || this.sending) return;
            this.sending = true;
            try {
                const response = await window.api.post("/api/v1/lxmf-messages/send", {
                    lxmf_message: {
                        destination_hash: this.destinationHash,
                        content: this.newMessage,
                    },
                });

                // Add message to list locally for immediate feedback
                const msg = response.data.lxmf_message;
                this.messages.push({
                    hash: msg.hash,
                    content: msg.content,
                    is_outbound: true,
                    timestamp: msg.created_at,
                });
                this.newMessage = "";
                this.scrollToBottom();
            } catch (e) {
                console.error("Failed to send message", e);
            } finally {
                this.sending = false;
            }
        },
        scrollToBottom() {
            this.$nextTick(() => {
                if (this.$refs.messageList) {
                    this.$refs.messageList.scrollTop = this.$refs.messageList.scrollHeight;
                }
            });
        },
        formatTime(ts) {
            if (!ts) return "";
            const date = new Date(ts * 1000);
            if (isNaN(date.getTime())) return "";
            return date.toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" });
        },
    },
};
</script>
