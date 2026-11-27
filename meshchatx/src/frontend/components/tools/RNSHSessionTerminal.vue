<!-- SPDX-License-Identifier: 0BSD -->

<template>
    <div class="flex flex-col min-h-0 flex-1 min-w-0" :class="fullscreen ? 'h-dvh max-h-dvh' : ''">
        <div
            class="shrink-0 flex flex-wrap items-center justify-between gap-1.5 sm:gap-2 border-b border-sem-border"
            :class="fullscreen ? 'px-2 py-2 bg-sem-surface safe-top' : 'px-2 sm:px-3 md:px-4 py-2 sm:py-2.5'"
        >
            <div class="min-w-0 flex-1 flex items-center gap-1.5">
                <button
                    v-if="showSessionsToggle"
                    type="button"
                    class="secondary-chip text-xs px-2 py-1.5 shrink-0 lg:hidden"
                    :aria-label="sessionsOpen ? tKey('hide_sessions') : tKey('show_sessions')"
                    @click="emit('toggle-sessions')"
                >
                    <MaterialDesignIcon icon-name="format-list-bulleted" class="size-4" />
                    <span class="hidden sm:inline">{{
                        sessionsOpen ? tKey("hide_sessions") : tKey("show_sessions")
                    }}</span>
                </button>
                <div class="min-w-0">
                    <div class="text-xs sm:text-sm font-semibold text-sem-fg truncate">
                        {{ session?.name || tKey("session_output") }}
                    </div>
                    <div v-if="!compactHeader" class="text-[10px] sm:text-xs text-sem-fg-muted font-mono truncate">
                        {{ session?.last_command || tKey("no_command_yet") }}
                    </div>
                </div>
            </div>
            <div class="flex flex-wrap items-center gap-1 sm:gap-2 shrink-0">
                <button
                    type="button"
                    class="secondary-chip text-xs p-1.5 sm:px-2 sm:py-1.5"
                    :disabled="!session"
                    :title="tKey('start')"
                    :aria-label="tKey('start')"
                    @click="emit('start')"
                >
                    <MaterialDesignIcon icon-name="play" class="size-4" />
                    <span class="hidden sm:inline ml-1">{{ tKey("start") }}</span>
                </button>
                <button
                    type="button"
                    class="secondary-chip text-xs p-1.5 sm:px-2 sm:py-1.5 text-sem-danger border-sem-danger dark:border-sem-danger/50"
                    :disabled="!session"
                    :title="tKey('stop')"
                    :aria-label="tKey('stop')"
                    @click="emit('stop')"
                >
                    <MaterialDesignIcon icon-name="stop" class="size-4" />
                    <span class="hidden sm:inline ml-1">{{ tKey("stop") }}</span>
                </button>
                <button
                    type="button"
                    class="secondary-chip text-xs p-1.5 sm:px-2 sm:py-1.5"
                    :disabled="!session"
                    :title="tKey('clear')"
                    :aria-label="tKey('clear')"
                    @click="emit('clear')"
                >
                    <MaterialDesignIcon icon-name="broom" class="size-4" />
                    <span class="hidden sm:inline ml-1">{{ tKey("clear") }}</span>
                </button>
                <button
                    type="button"
                    class="secondary-chip text-xs p-1.5 sm:px-2 sm:py-1.5 text-sem-danger border-sem-danger dark:border-sem-danger/50"
                    :disabled="!session"
                    :title="tKey('remove')"
                    :aria-label="tKey('remove')"
                    @click="emit('remove')"
                >
                    <MaterialDesignIcon icon-name="trash-can-outline" class="size-4" />
                    <span class="hidden sm:inline ml-1">{{ tKey("remove") }}</span>
                </button>
                <button
                    type="button"
                    class="secondary-chip text-xs p-1.5 sm:px-2 sm:py-1.5"
                    :title="fullscreen ? tKey('exit_fullscreen') : tKey('fullscreen')"
                    :aria-label="fullscreen ? tKey('exit_fullscreen') : tKey('fullscreen')"
                    @click="emit('toggle-fullscreen')"
                >
                    <MaterialDesignIcon :icon-name="fullscreen ? 'fullscreen-exit' : 'fullscreen'" class="size-4" />
                </button>
            </div>
        </div>

        <div
            v-if="session && session.mode === 'listen'"
            class="shrink-0 flex items-center gap-2 px-2 sm:px-3 md:px-4 py-1.5 border-b border-sem-border bg-sem-info/15 dark:bg-sem-info/15"
        >
            <span
                class="text-[10px] sm:text-xs font-semibold uppercase tracking-wide text-sem-info dark:text-sem-info shrink-0"
            >
                {{ tKey("listening_on") }}
            </span>
            <span class="min-w-0 flex-1 font-mono text-[11px] sm:text-xs text-sem-fg truncate">
                {{ listenAddress || tKey("waiting_for_address") }}
            </span>
            <button
                v-if="listenAddress"
                type="button"
                class="secondary-chip text-xs p-1 sm:px-2 sm:py-1 shrink-0"
                :title="tKey('copy_address')"
                :aria-label="tKey('copy_address')"
                @click="emit('copy-address')"
            >
                <MaterialDesignIcon icon-name="content-copy" class="size-4" />
                <span class="hidden sm:inline ml-1">{{ tKey("copy_address") }}</span>
            </button>
        </div>

        <div
            ref="outputBox"
            class="flex-1 min-h-0 bg-sem-surface dark:bg-black text-sem-fg font-mono whitespace-pre-wrap wrap-break-word overflow-auto custom-scrollbar"
            :class="fullscreen ? 'text-[11px] leading-relaxed px-2 py-2' : 'text-xs px-2 sm:px-3 md:px-4 py-2 sm:py-3'"
        >
            {{ output }}
        </div>

        <form
            class="shrink-0 flex gap-1.5 sm:gap-2 border-t border-sem-border bg-sem-canvas"
            :class="
                fullscreen
                    ? 'px-2 py-2 pb-[max(0.5rem,env(safe-area-inset-bottom))] safe-bottom'
                    : 'px-2 sm:px-3 md:px-4 py-2 sm:py-2.5'
            "
            @submit.prevent="emit('send')"
        >
            <input
                :value="commandInput"
                type="text"
                class="input-field flex-1 min-w-0 font-mono text-xs"
                :placeholder="tKey('command_input_placeholder')"
                :disabled="!session"
                autocomplete="off"
                autocapitalize="off"
                spellcheck="false"
                @input="emit('update:commandInput', $event.target.value)"
            />
            <button
                type="submit"
                class="primary-chip px-2.5 sm:px-3 py-2 text-xs shrink-0"
                :disabled="!session || !commandInput.trim()"
                :aria-label="tKey('send_line')"
            >
                <MaterialDesignIcon icon-name="send" class="size-4" />
                <span class="hidden sm:inline ml-1">{{ tKey("send_line") }}</span>
            </button>
        </form>
    </div>
</template>

<script setup lang="ts">
import { ref } from "vue";
import MaterialDesignIcon from "../MaterialDesignIcon.vue";
import { useTranslateUi } from "../../js/localeLoader.js";

const props = withDefaults(
    defineProps<{
        session?: Record<string, any> | null;
        output: string;
        commandInput?: string;
        listenAddress?: string;
        fullscreen?: boolean;
        showSessionsToggle?: boolean;
        sessionsOpen?: boolean;
        compactHeader?: boolean;
        i18nPrefix?: string;
    }>(),
    {
        session: null,
        commandInput: "",
        listenAddress: "",
        fullscreen: false,
        showSessionsToggle: false,
        sessionsOpen: false,
        compactHeader: false,
        i18nPrefix: "rnsh",
    }
);

const emit = defineEmits<{
    "update:commandInput": [value: string];
    send: [];
    start: [];
    stop: [];
    clear: [];
    remove: [];
    "copy-address": [];
    "toggle-fullscreen": [];
    "toggle-sessions": [];
}>();

const t = useTranslateUi();

const outputBox = ref<HTMLElement | null>(null);

function tKey(suffix: string) {
    return t(`${props.i18nPrefix}.${suffix}`);
}

function scrollToBottom() {
    const target = outputBox.value;
    if (target) {
        target.scrollTop = target.scrollHeight;
    }
}

defineExpose({ scrollToBottom });
</script>

<style scoped>
.safe-top {
    padding-top: max(0.5rem, env(safe-area-inset-top));
}
.safe-bottom {
    padding-bottom: max(0.5rem, env(safe-area-inset-bottom));
}
</style>
