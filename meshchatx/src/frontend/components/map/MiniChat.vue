<!-- SPDX-License-Identifier: 0BSD -->

<template>
    <div
        class="flex flex-col h-64 bg-gray-50 dark:bg-zinc-950 rounded-lg overflow-hidden border border-gray-200 dark:border-zinc-800"
    >
        <!-- message list -->
        <div ref="messageList" class="flex-1 overflow-y-auto p-2 space-y-2 scrollbar-thin">
            <div v-if="loading" class="flex justify-center py-4">
                <v-icon icon="mdi-loading" class="animate-spin text-gray-400" size="20"></v-icon>
            </div>
            <div v-else-if="messages.length === 0" class="text-center py-4 text-xs text-gray-400">No messages yet</div>
            <div
                v-for="msg in messages"
                :key="msg.hash"
                class="flex flex-col max-w-[90%]"
                :class="msg.is_outbound ? 'ml-auto items-end' : 'mr-auto items-start'"
            >
                <div
                    class="px-2 py-1 rounded-lg text-xs break-words shadow-sm"
                    :class="
                        msg.is_outbound
                            ? 'bg-blue-600 text-white'
                            : 'bg-white dark:bg-zinc-900 text-gray-800 dark:text-zinc-200'
                    "
                >
                    <!-- Telemetry Header if no content -->
                    <div
                        v-if="!msg.content && msg.fields?.telemetry"
                        class="flex items-center gap-1 mb-1 pb-1 border-b border-white/10 opacity-80"
                    >
                        <v-icon icon="mdi-satellite-variant" size="10"></v-icon>
                        <span class="text-[8px] font-bold uppercase tracking-wider"
                            >{{ msg.is_outbound ? "Sent" : "Received" }} Telemetry</span
                        >
                    </div>

                    <div
                        v-if="!msg.content && msg.fields?.commands?.some((c) => c['0x01'] || c['1'] || c['0x1'])"
                        class="flex items-center gap-1 mb-1 pb-1 border-b border-white/10 opacity-80"
                    >
                        <v-icon icon="mdi-crosshairs-question" size="10"></v-icon>
                        <span class="text-[8px] font-bold uppercase tracking-wider">Location Request</span>
                    </div>

                    <div v-if="msg.content" class="leading-normal">{{ msg.content }}</div>

                    <!-- Mini Telemetry Data -->
                    <div v-if="msg.fields?.telemetry" class="mt-1 space-y-1">
                        <div
                            v-if="msg.fields.telemetry.location"
                            class="flex items-center gap-1 text-[9px] font-mono opacity-90"
                        >
                            <v-icon icon="mdi-map-marker" size="10"></v-icon>
                            <span
                                >{{ msg.fields.telemetry.location.latitude.toFixed(4) }},
                                {{ msg.fields.telemetry.location.longitude.toFixed(4) }}</span
                            >
                        </div>
                        <div class="flex gap-2 opacity-70 text-[8px]">
                            <span v-if="msg.fields.telemetry.battery" class="flex items-center gap-0.5">
                                <v-icon icon="mdi-battery" size="8"></v-icon
                                >{{ msg.fields.telemetry.battery.charge_percent }}%
                            </span>
                            <span v-if="msg.fields.telemetry.physical_link" class="flex items-center gap-0.5">
                                <v-icon icon="mdi-antenna" size="8"></v-icon>SNR:
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
        <div class="p-2 bg-white dark:bg-zinc-900 border-t border-gray-200 dark:border-zinc-800">
            <div class="flex gap-1">
                <input
                    v-model="newMessage"
                    type="text"
                    class="flex-1 bg-gray-50 dark:bg-zinc-800 border border-gray-200 dark:border-zinc-700 rounded-md px-2 py-1 text-xs focus:outline-none focus:ring-1 focus:ring-blue-500 text-gray-900 dark:text-zinc-100"
                    placeholder="Type a message..."
                    @keydown.enter="sendMessage"
                />
                <button
                    :disabled="!newMessage.trim() || sending"
                    class="p-1.5 bg-blue-500 hover:bg-blue-600 disabled:bg-gray-300 dark:disabled:bg-zinc-700 text-white rounded-md transition-colors"
                    @click="sendMessage"
                >
                    <v-icon
                        :icon="sending ? 'mdi-loading' : 'mdi-send'"
                        :class="{ 'animate-spin': sending }"
                        size="14"
                    ></v-icon>
                </button>
            </div>
        </div>
    </div>
</template>

<script>
export default {
    name: "MiniChat",
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
