<!-- SPDX-License-Identifier: 0BSD -->

<template>
    <div v-if="config">
        <div class="bg-sem-surface border-t border-sem-border">
            <div
                class="flex text-sem-fg cursor-pointer"
                :class="isCollapsed ? 'justify-center p-2' : 'p-3'"
                @click="isShowingMyIdentitySection = !isShowingMyIdentitySection"
            >
                <div :class="isCollapsed ? 'shrink-0' : 'my-auto mr-2 shrink-0'">
                    <RouterLink :to="{ name: 'profile.icon' }" @click.stop>
                        <LxmfUserIcon
                            :icon-name="config.lxmf_user_icon_name"
                            :icon-foreground-colour="config.lxmf_user_icon_foreground_colour"
                            :icon-background-colour="config.lxmf_user_icon_background_colour"
                            icon-class="size-7"
                        />
                    </RouterLink>
                </div>
                <div v-if="!isCollapsed" class="my-auto min-w-0 flex-1 text-sem-fg truncate" :title="identityLabel">
                    {{ identityLabel }}
                </div>
            </div>
            <div
                v-if="isShowingMyIdentitySection && !isCollapsed"
                class="divide-y divide-sem-border text-sem-fg border-t border-sem-border"
            >
                <div class="p-2">
                    <input
                        :value="displayName"
                        type="text"
                        data-testid="sidebar-display-name"
                        :placeholder="$t('app.display_name_placeholder')"
                        class="input-field w-full"
                        @input="$emit('update:displayName', $event.target.value)"
                        @keydown.enter.prevent="$emit('save-identity')"
                        @blur="$emit('save-identity')"
                    />
                </div>
                <div class="p-2 dark:border-zinc-900 overflow-hidden text-xs">
                    <div>{{ $t("app.identity_hash") }}</div>
                    <div
                        class="text-[10px] text-sem-fg-muted truncate font-mono cursor-pointer"
                        :title="config.identity_hash"
                        @click="$emit('copy-value', config.identity_hash, $t('app.identity_hash'))"
                    >
                        {{ config.identity_hash }}
                    </div>
                </div>
                <div class="p-2 dark:border-zinc-900 overflow-hidden text-xs">
                    <div>{{ $t("app.lxmf_address") }}</div>
                    <div class="flex min-w-0 items-center gap-1">
                        <div
                            class="min-w-0 flex-1 text-[10px] text-sem-fg-muted truncate font-mono cursor-pointer"
                            :title="config.lxmf_address_hash"
                            @click="$emit('copy-value', config.lxmf_address_hash, $t('app.lxmf_address'))"
                        >
                            {{ config.lxmf_address_hash }}
                        </div>
                        <button
                            type="button"
                            class="shrink-0 rounded-lg p-1 text-gray-500 hover:text-blue-500 dark:hover:text-blue-400 transition-colors"
                            :title="$t('app.show_qr')"
                            @click.stop="$emit('open-lxmf-qr')"
                        >
                            <MaterialDesignIcon icon-name="qrcode" class="size-4" />
                        </button>
                    </div>
                </div>
            </div>
        </div>

        <div class="bg-white border-t border-sem-border dark:bg-zinc-950">
            <div
                class="flex text-gray-700 cursor-pointer dark:text-white"
                :class="isCollapsed ? 'justify-center p-2' : 'p-3'"
                data-testid="sidebar-announce-header"
                @click="isShowingAnnounceSection = !isShowingAnnounceSection"
            >
                <button
                    type="button"
                    class="flex shrink-0 items-center justify-center rounded-md border-0 bg-transparent p-0 text-inherit cursor-pointer"
                    :class="isCollapsed ? '' : 'my-auto mr-2'"
                    :title="$t('app.announce_now')"
                    data-testid="sidebar-announce-radio"
                    @click.stop="$emit('send-announce')"
                >
                    <MaterialDesignIcon icon-name="radio" class="size-6" />
                </button>
                <div v-if="!isCollapsed" class="my-auto truncate">
                    {{ $t("app.announce") }}
                </div>
                <div v-if="!isCollapsed" class="ml-auto shrink-0">
                    <button
                        type="button"
                        class="my-auto inline-flex items-center gap-x-1 rounded-md bg-gray-500 px-2 py-1 text-sm font-semibold text-white shadow-xs hover:bg-gray-400 focus-visible:outline-solid focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-gray-500 dark:bg-zinc-800 dark:text-white hover:bg-sem-surface-muted dark:focus-visible:outline-zinc-500"
                        @click.stop="$emit('send-announce')"
                    >
                        {{ $t("app.announce_now") }}
                    </button>
                </div>
            </div>
            <div
                v-if="isShowingAnnounceSection && !isCollapsed"
                class="divide-y divide-gray-200 text-gray-900 border-t border-gray-200 dark:divide-zinc-800 text-sem-fg dark:border-zinc-800"
            >
                <div class="p-2 dark:border-zinc-800">
                    <select
                        :value="config.auto_announce_interval_seconds"
                        class="bg-gray-50 border border-gray-300 text-gray-900 text-sm rounded-lg focus:ring-blue-500 focus:border-blue-500 block w-full p-2.5 dark:bg-zinc-800 dark:border-zinc-600 text-sem-fg dark:focus:ring-blue-400 dark:focus:border-blue-400"
                        @change="$emit('announce-interval-change', Number($event.target.value))"
                    >
                        <option :value="0">{{ $t("app.disabled") }}</option>
                        <option :value="900">{{ $t("app.announce_interval_15m") }}</option>
                        <option :value="1800">{{ $t("app.announce_interval_30m") }}</option>
                        <option :value="3600">{{ $t("app.announce_interval_1h") }}</option>
                        <option :value="10800">{{ $t("app.announce_interval_3h") }}</option>
                        <option :value="21600">{{ $t("app.announce_interval_6h") }}</option>
                        <option :value="43200">{{ $t("app.announce_interval_12h") }}</option>
                        <option :value="86400">{{ $t("app.announce_interval_24h") }}</option>
                    </select>
                    <div
                        class="text-[10px] leading-snug text-gray-700 text-sem-fg mt-1"
                        data-testid="sidebar-last-announced"
                    >
                        <span v-if="config.last_announced_at">
                            {{ $t("app.last_announced", { time: lastAnnouncedLabel }) }}
                        </span>
                        <span v-else>{{ $t("app.last_announced_never") }}</span>
                    </div>
                </div>
            </div>
        </div>
    </div>
</template>

<script>
import MaterialDesignIcon from "../MaterialDesignIcon.vue";
import LxmfUserIcon from "../LxmfUserIcon.vue";

export default {
    name: "AppSidebarClassicFooter",
    components: {
        MaterialDesignIcon,
        LxmfUserIcon,
    },
    props: {
        config: {
            type: Object,
            required: true,
        },
        displayName: {
            type: String,
            default: "",
        },
        identityLabel: {
            type: String,
            required: true,
        },
        lastAnnouncedLabel: {
            type: String,
            default: "",
        },
        isCollapsed: {
            type: Boolean,
            default: false,
        },
    },
    emits: [
        "update:displayName",
        "save-identity",
        "send-announce",
        "announce-interval-change",
        "copy-value",
        "open-lxmf-qr",
    ],
    data() {
        return {
            isShowingMyIdentitySection: true,
            isShowingAnnounceSection: true,
        };
    },
};
</script>
