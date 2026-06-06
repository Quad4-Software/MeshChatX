<!-- SPDX-License-Identifier: 0BSD -->

<template>
    <div class="flex flex-col min-h-0 flex-1 min-w-0" :class="fullscreen ? 'h-dvh max-h-dvh' : ''">
        <div
            class="shrink-0 flex flex-wrap items-center justify-between gap-1.5 sm:gap-2 border-b border-gray-200 dark:border-zinc-800"
            :class="fullscreen ? 'px-2 py-2 bg-zinc-900 safe-top' : 'px-2 sm:px-3 md:px-4 py-2 sm:py-2.5'"
        >
            <div class="min-w-0 flex-1 flex items-center gap-1.5">
                <button
                    v-if="showSessionsToggle"
                    type="button"
                    class="secondary-chip text-xs px-2 py-1.5 shrink-0 lg:hidden"
                    :aria-label="sessionsOpen ? $t('rnsh.hide_sessions') : $t('rnsh.show_sessions')"
                    @click="$emit('toggle-sessions')"
                >
                    <MaterialDesignIcon icon-name="format-list-bulleted" class="size-4" />
                    <span class="hidden sm:inline">{{
                        sessionsOpen ? $t("rnsh.hide_sessions") : $t("rnsh.show_sessions")
                    }}</span>
                </button>
                <div class="min-w-0">
                    <div class="text-xs sm:text-sm font-semibold text-gray-900 dark:text-zinc-100 truncate">
                        {{ session?.name || $t("rnsh.session_output") }}
                    </div>
                    <div
                        v-if="!compactHeader"
                        class="text-[10px] sm:text-xs text-gray-500 dark:text-zinc-400 font-mono truncate"
                    >
                        {{ session?.last_command || $t("rnsh.no_command_yet") }}
                    </div>
                </div>
            </div>
            <div class="flex flex-wrap items-center gap-1 sm:gap-2 shrink-0">
                <button
                    type="button"
                    class="secondary-chip text-xs p-1.5 sm:px-2 sm:py-1.5"
                    :disabled="!session"
                    :title="$t('rnsh.start')"
                    :aria-label="$t('rnsh.start')"
                    @click="$emit('start')"
                >
                    <MaterialDesignIcon icon-name="play" class="size-4" />
                    <span class="hidden sm:inline ml-1">{{ $t("rnsh.start") }}</span>
                </button>
                <button
                    type="button"
                    class="secondary-chip text-xs p-1.5 sm:px-2 sm:py-1.5 text-red-600 dark:text-red-300 border-red-200 dark:border-red-500/40"
                    :disabled="!session"
                    :title="$t('rnsh.stop')"
                    :aria-label="$t('rnsh.stop')"
                    @click="$emit('stop')"
                >
                    <MaterialDesignIcon icon-name="stop" class="size-4" />
                    <span class="hidden sm:inline ml-1">{{ $t("rnsh.stop") }}</span>
                </button>
                <button
                    type="button"
                    class="secondary-chip text-xs p-1.5 sm:px-2 sm:py-1.5"
                    :disabled="!session"
                    :title="$t('rnsh.clear')"
                    :aria-label="$t('rnsh.clear')"
                    @click="$emit('clear')"
                >
                    <MaterialDesignIcon icon-name="broom" class="size-4" />
                    <span class="hidden sm:inline ml-1">{{ $t("rnsh.clear") }}</span>
                </button>
                <button
                    type="button"
                    class="secondary-chip text-xs p-1.5 sm:px-2 sm:py-1.5 text-red-600 dark:text-red-300 border-red-200 dark:border-red-500/40"
                    :disabled="!session"
                    :title="$t('rnsh.remove')"
                    :aria-label="$t('rnsh.remove')"
                    @click="$emit('remove')"
                >
                    <MaterialDesignIcon icon-name="trash-can-outline" class="size-4" />
                    <span class="hidden sm:inline ml-1">{{ $t("rnsh.remove") }}</span>
                </button>
                <button
                    type="button"
                    class="secondary-chip text-xs p-1.5 sm:px-2 sm:py-1.5"
                    :title="fullscreen ? $t('rnsh.exit_fullscreen') : $t('rnsh.fullscreen')"
                    :aria-label="fullscreen ? $t('rnsh.exit_fullscreen') : $t('rnsh.fullscreen')"
                    @click="$emit('toggle-fullscreen')"
                >
                    <MaterialDesignIcon :icon-name="fullscreen ? 'fullscreen-exit' : 'fullscreen'" class="size-4" />
                </button>
            </div>
        </div>

        <div
            v-if="session && session.mode === 'listen'"
            class="shrink-0 flex items-center gap-2 px-2 sm:px-3 md:px-4 py-1.5 border-b border-gray-200 dark:border-zinc-800 bg-indigo-50 dark:bg-indigo-950/40"
        >
            <span
                class="text-[10px] sm:text-xs font-semibold uppercase tracking-wide text-indigo-700 dark:text-indigo-300 shrink-0"
            >
                {{ $t("rnsh.listening_on") }}
            </span>
            <span class="min-w-0 flex-1 font-mono text-[11px] sm:text-xs text-gray-900 dark:text-zinc-100 truncate">
                {{ listenAddress || $t("rnsh.waiting_for_address") }}
            </span>
            <button
                v-if="listenAddress"
                type="button"
                class="secondary-chip text-xs p-1 sm:px-2 sm:py-1 shrink-0"
                :title="$t('rnsh.copy_address')"
                :aria-label="$t('rnsh.copy_address')"
                @click="$emit('copy-address')"
            >
                <MaterialDesignIcon icon-name="content-copy" class="size-4" />
                <span class="hidden sm:inline ml-1">{{ $t("rnsh.copy_address") }}</span>
            </button>
        </div>

        <div
            ref="outputBox"
            class="flex-1 min-h-0 bg-zinc-950 dark:bg-black text-zinc-100 font-mono whitespace-pre-wrap break-words overflow-auto custom-scrollbar"
            :class="fullscreen ? 'text-[11px] leading-relaxed px-2 py-2' : 'text-xs px-2 sm:px-3 md:px-4 py-2 sm:py-3'"
        >
            {{ output }}
        </div>

        <form
            class="shrink-0 flex gap-1.5 sm:gap-2 border-t border-gray-200 dark:border-zinc-800 bg-slate-50 dark:bg-zinc-950"
            :class="
                fullscreen
                    ? 'px-2 py-2 pb-[max(0.5rem,env(safe-area-inset-bottom))] safe-bottom'
                    : 'px-2 sm:px-3 md:px-4 py-2 sm:py-2.5'
            "
            @submit.prevent="$emit('send')"
        >
            <input
                :value="commandInput"
                type="text"
                class="input-field flex-1 min-w-0 font-mono text-xs"
                :placeholder="$t('rnsh.command_input_placeholder')"
                :disabled="!session"
                autocomplete="off"
                autocapitalize="off"
                spellcheck="false"
                @input="$emit('update:commandInput', $event.target.value)"
            />
            <button
                type="submit"
                class="primary-chip px-2.5 sm:px-3 py-2 text-xs shrink-0"
                :disabled="!session || !commandInput.trim()"
                :aria-label="$t('rnsh.send_line')"
            >
                <MaterialDesignIcon icon-name="send" class="size-4" />
                <span class="hidden sm:inline ml-1">{{ $t("rnsh.send_line") }}</span>
            </button>
        </form>
    </div>
</template>

<script>
import MaterialDesignIcon from "../MaterialDesignIcon.vue";

export default {
    name: "RNSHSessionTerminal",
    components: { MaterialDesignIcon },
    props: {
        session: { type: Object, default: null },
        output: { type: String, required: true },
        commandInput: { type: String, default: "" },
        listenAddress: { type: String, default: "" },
        fullscreen: { type: Boolean, default: false },
        showSessionsToggle: { type: Boolean, default: false },
        sessionsOpen: { type: Boolean, default: false },
        compactHeader: { type: Boolean, default: false },
    },
    emits: [
        "update:commandInput",
        "send",
        "start",
        "stop",
        "clear",
        "remove",
        "copy-address",
        "toggle-fullscreen",
        "toggle-sessions",
    ],
    methods: {
        scrollToBottom() {
            const target = this.$refs.outputBox;
            if (target) {
                target.scrollTop = target.scrollHeight;
            }
        },
    },
};
</script>

<style scoped>
.safe-top {
    padding-top: max(0.5rem, env(safe-area-inset-top));
}
.safe-bottom {
    padding-bottom: max(0.5rem, env(safe-area-inset-bottom));
}
</style>
