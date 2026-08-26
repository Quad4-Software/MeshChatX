<!-- SPDX-License-Identifier: 0BSD AND MIT -->

<template>
    <div class="relative inline-flex items-stretch rounded-xl shadow-xs">
        <template v-if="compact">
            <button
                :disabled="!canSendMessage && !canOpenSendMenu"
                type="button"
                class="inline-flex items-center justify-center rounded-xl p-2.5 min-h-[44px] min-w-[44px] text-white transition-colors focus-visible:outline-solid focus-visible:outline-2 focus-visible:outline-offset-2 touch-manipulation select-none"
                :class="[
                    canSendMessage || canOpenSendMenu
                        ? 'bg-blue-600 dark:bg-blue-600 hover:bg-blue-700 dark:hover:bg-blue-700 focus-visible:outline-blue-500'
                        : 'bg-gray-400 dark:bg-zinc-500 focus-visible:outline-gray-500 cursor-not-allowed',
                ]"
                :title="compactTitle"
                @pointerdown="onCompactPointerDown"
                @pointerup="onCompactPointerUp"
                @pointercancel="onCompactPointerCancel"
                @click="onCompactClick"
            >
                <svg
                    v-if="!isSendingMessage"
                    xmlns="http://www.w3.org/2000/svg"
                    fill="none"
                    viewBox="0 0 24 24"
                    stroke-width="1.5"
                    stroke="currentColor"
                    class="w-5 h-5"
                >
                    <path
                        stroke-linecap="round"
                        stroke-linejoin="round"
                        d="M6 12 3.269 3.125A59.769 59.769 0 0 1 21.485 12 59.768 59.768 0 0 1 3.27 20.875L5.999 12Zm0 0h7.5"
                    />
                </svg>
                <span v-else class="text-xs font-semibold opacity-90">...</span>
            </button>
        </template>
        <template v-else>
            <button
                :disabled="!canSendMessage"
                type="button"
                class="inline-flex items-center gap-2 rounded-l-xl px-4 py-2.5 text-sm font-semibold text-white transition-colors focus-visible:outline-solid focus-visible:outline-2 focus-visible:outline-offset-2"
                :class="[
                    canSendMessage
                        ? 'bg-blue-600 dark:bg-blue-600 hover:bg-blue-700 dark:hover:bg-blue-700 focus-visible:outline-blue-500'
                        : 'bg-gray-400 dark:bg-zinc-500 focus-visible:outline-gray-500 cursor-not-allowed',
                ]"
                :title="isSendingMessage ? sendingTooltip : ''"
                @click="send"
            >
                <svg
                    v-if="!isSendingMessage"
                    xmlns="http://www.w3.org/2000/svg"
                    fill="none"
                    viewBox="0 0 24 24"
                    stroke-width="1.5"
                    stroke="currentColor"
                    class="w-4 h-4"
                >
                    <path
                        stroke-linecap="round"
                        stroke-linejoin="round"
                        d="M6 12 3.269 3.125A59.769 59.769 0 0 1 21.485 12 59.768 59.768 0 0 1 3.27 20.875L5.999 12Zm0 0h7.5"
                    />
                </svg>
                <span :class="isSendingMessage ? 'opacity-60' : ''">
                    <span v-if="deliveryMethod === 'direct'">{{ $t("messages.send_direct") }}</span>
                    <span v-else-if="deliveryMethod === 'opportunistic'">{{ $t("messages.send_opportunistic") }}</span>
                    <span v-else-if="deliveryMethod === 'propagated'">{{ $t("messages.send_propagated") }}</span>
                    <span v-else>{{ $t("messages.send") }}</span>
                </span>
            </button>
            <div class="relative self-stretch">
                <button
                    :disabled="!canSendMessage && !canOpenSendMenu"
                    type="button"
                    class="border-l relative inline-flex items-center justify-center rounded-r-xl px-2.5 h-full text-white transition-colors focus-visible:outline-solid focus-visible:outline-2 focus-visible:outline-offset-2"
                    :class="[
                        canSendMessage || canOpenSendMenu
                            ? 'bg-blue-600 dark:bg-blue-600 hover:bg-blue-700 dark:hover:bg-blue-700 focus-visible:outline-blue-500 border-blue-700 dark:border-blue-800'
                            : 'bg-gray-400 dark:bg-zinc-500 focus-visible:outline-gray-500 border-gray-500 dark:border-zinc-600 cursor-not-allowed',
                    ]"
                    @click="showMenu"
                >
                    <svg class="h-4 w-4" viewBox="0 0 20 20" fill="currentColor" aria-hidden="true">
                        <path
                            fill-rule="evenodd"
                            d="M5.22 8.22a.75.75 0 0 1 1.06 0L10 11.94l3.72-3.72a.75.75 0 1 1 1.06 1.06l-4.25 4.25a.75.75 0 0 1-1.06 0L5.22 9.28a.75.75 0 0 1 0-1.06Z"
                            clip-rule="evenodd"
                        />
                    </svg>
                </button>
            </div>
        </template>

        <Transition
            enter-active-class="transition ease-out duration-100"
            enter-from-class="transform opacity-0 scale-95"
            enter-to-class="transform opacity-100 scale-100"
            leave-active-class="transition ease-in duration-75"
            leave-from-class="transform opacity-100 scale-100"
            leave-to-class="transform opacity-0 scale-95"
        >
            <div
                v-if="isShowingMenu"
                v-click-outside="hideMenu"
                class="absolute bottom-full right-0 mb-1 z-10 rounded-xl bg-sem-surface shadow-lg ring-1 ring-gray-200 dark:ring-zinc-800 focus:outline-hidden overflow-hidden min-w-[200px]"
            >
                <div class="py-1">
                    <button
                        type="button"
                        class="w-full block text-left px-4 py-2 text-sm text-gray-700 dark:text-gray-300 hover:bg-sem-surface-muted whitespace-nowrap border-b border-sem-border"
                        @click="setDeliveryMethod(null)"
                    >
                        {{ $t("messages.send_automatically") }}
                    </button>
                    <button
                        type="button"
                        class="w-full block text-left px-4 py-2 text-sm text-gray-700 dark:text-gray-300 hover:bg-sem-surface-muted whitespace-nowrap"
                        @click="setDeliveryMethod('direct')"
                    >
                        {{ $t("messages.send_over_direct_link") }}
                    </button>
                    <button
                        type="button"
                        class="w-full block text-left px-4 py-2 text-sm text-gray-700 dark:text-gray-300 hover:bg-sem-surface-muted whitespace-nowrap"
                        @click="setDeliveryMethod('opportunistic')"
                    >
                        {{ $t("messages.send_opportunistically") }}
                    </button>
                    <button
                        type="button"
                        class="w-full block text-left px-4 py-2 text-sm text-gray-700 dark:text-gray-300 hover:bg-sem-surface-muted whitespace-nowrap"
                        @click="setDeliveryMethod('propagated')"
                    >
                        {{ $t("messages.send_to_propagation_node") }}
                    </button>
                    <div class="border-t border-sem-border text-[11px] font-medium text-sem-fg-muted px-4 pt-2 pb-1">
                        {{ $t("messages.send_menu_more_label") }}
                    </div>
                    <button
                        type="button"
                        class="w-full block text-left px-4 py-2 text-sm text-gray-700 dark:text-gray-300 hover:bg-sem-surface-muted whitespace-nowrap"
                        :disabled="!canOpenSendMenu"
                        @click="emitCommandOrRequest"
                    >
                        {{ $t("messages.send_menu_telemetry_request") }}
                    </button>
                    <button
                        type="button"
                        class="w-full block text-left px-4 py-2 text-sm text-gray-700 dark:text-gray-300 hover:bg-sem-surface-muted whitespace-nowrap"
                        :disabled="!canSendMessage"
                        @click="emitPaperCompose"
                    >
                        {{ $t("messages.send_menu_paper_compose") }}
                    </button>
                </div>
            </div>
        </Transition>
    </div>
</template>

<script>
export default {
    name: "SendMessageButton",
    props: {
        deliveryMethod: {
            required: true,
            validator: (value) => value === null || typeof value === "string",
        },
        canSendMessage: Boolean,
        isSendingMessage: Boolean,
        compact: Boolean,
        sendingTooltip: {
            type: String,
            default:
                "Resolving route to peer (finding path). This can take a while on first contact or after links change. Paths are remembered until they expire.",
        },
        canOpenSendMenu: {
            type: Boolean,
            default: false,
        },
    },
    emits: ["delivery-method-changed", "send", "send-command-or-request", "send-paper-compose"],
    data() {
        return {
            isShowingMenu: false,
            compactLongPressTimer: null,
            compactTapArmed: false,
        };
    },
    computed: {
        compactTitle() {
            if (this.isSendingMessage) {
                return this.sendingTooltip;
            }
            return this.$t("messages.send_hold_for_options");
        },
    },
    beforeUnmount() {
        this.clearCompactLongPressTimer();
    },
    methods: {
        clearCompactLongPressTimer() {
            if (this.compactLongPressTimer != null) {
                clearTimeout(this.compactLongPressTimer);
                this.compactLongPressTimer = null;
            }
        },
        onCompactPointerDown() {
            if (!this.compact || (!this.canSendMessage && !this.canOpenSendMenu)) {
                return;
            }
            this.compactTapArmed = true;
            this.clearCompactLongPressTimer();
            this.compactLongPressTimer = window.setTimeout(() => {
                this.compactLongPressTimer = null;
                this.compactTapArmed = false;
                this.showMenu();
            }, 500);
        },
        onCompactPointerUp() {
            if (!this.compact) {
                return;
            }
            this.clearCompactLongPressTimer();
        },
        onCompactPointerCancel() {
            if (!this.compact) {
                return;
            }
            this.clearCompactLongPressTimer();
            this.compactTapArmed = false;
        },
        onCompactClick() {
            if (!this.compact) {
                return;
            }
            if (!this.compactTapArmed) {
                return;
            }
            this.compactTapArmed = false;
            this.send();
        },
        showMenu() {
            this.isShowingMenu = true;
        },
        hideMenu() {
            this.isShowingMenu = false;
        },
        setDeliveryMethod(deliveryMethod) {
            this.$emit("delivery-method-changed", deliveryMethod);
            this.hideMenu();
        },
        emitCommandOrRequest() {
            this.$emit("send-command-or-request");
            this.hideMenu();
        },
        emitPaperCompose() {
            this.$emit("send-paper-compose");
            this.hideMenu();
        },
        send() {
            this.$emit("send");
        },
    },
};
</script>
