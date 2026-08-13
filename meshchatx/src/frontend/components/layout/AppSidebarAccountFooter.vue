<!-- SPDX-License-Identifier: 0BSD -->

<template>
    <div v-if="config" class="bg-white border-t border-gray-200 dark:border-zinc-800 dark:bg-zinc-950">
        <div
            class="flex items-center gap-2 p-3 cursor-pointer text-gray-700 dark:text-white"
            data-testid="sidebar-account-chip"
            @click="onAccountChipClick"
        >
            <RouterLink :to="{ name: 'profile.icon' }" class="shrink-0" @click.stop>
                <LxmfUserIcon
                    :icon-name="config.lxmf_user_icon_name"
                    :icon-foreground-colour="config.lxmf_user_icon_foreground_colour"
                    :icon-background-colour="config.lxmf_user_icon_background_colour"
                    icon-class="size-8"
                />
            </RouterLink>
            <div v-if="!isCollapsed" class="min-w-0 flex-1">
                <div class="truncate text-sm font-semibold" :title="identityLabel">
                    {{ identityLabel }}
                </div>
                <div class="truncate text-[11px] text-gray-500 dark:text-zinc-400">
                    <span v-if="config.last_announced_at">
                        {{ $t("app.last_announced", { time: lastAnnouncedLabel }) }}
                    </span>
                    <span v-else>{{ $t("app.last_announced_never") }}</span>
                </div>
            </div>
            <div v-if="!isCollapsed" class="flex shrink-0 items-center gap-1">
                <button
                    type="button"
                    class="inline-flex min-h-[36px] min-w-[36px] items-center justify-center rounded-lg text-gray-500 hover:bg-gray-100 hover:text-blue-600 dark:text-zinc-400 dark:hover:bg-zinc-800 dark:hover:text-blue-400 transition-colors"
                    :title="$t('app.announce_now')"
                    data-testid="sidebar-announce-radio"
                    @click.stop="$emit('send-announce')"
                >
                    <MaterialDesignIcon icon-name="radio" class="size-5" />
                </button>
                <button
                    type="button"
                    class="inline-flex min-h-[36px] min-w-[36px] items-center justify-center rounded-lg text-gray-500 hover:bg-gray-100 hover:text-blue-600 dark:text-zinc-400 dark:hover:bg-zinc-800 dark:hover:text-blue-400 transition-colors"
                    :title="$t('app.show_qr')"
                    @click.stop="$emit('open-lxmf-qr')"
                >
                    <MaterialDesignIcon icon-name="qrcode" class="size-5" />
                </button>
                <MaterialDesignIcon
                    :icon-name="isExpanded ? 'chevron-up' : 'chevron-down'"
                    class="size-5 text-gray-400 shrink-0"
                />
            </div>
        </div>

        <div
            v-if="isExpanded && !isCollapsed"
            class="divide-y divide-gray-200 border-t border-gray-200 text-gray-900 dark:divide-zinc-800 dark:border-zinc-800 dark:text-zinc-200"
        >
            <div class="flex items-center gap-2 p-2">
                <input
                    :value="displayName"
                    type="text"
                    :placeholder="$t('app.display_name_placeholder')"
                    class="bg-gray-50 border border-gray-300 text-gray-900 text-sm rounded-lg focus:ring-blue-500 focus:border-blue-500 block w-full min-w-0 p-2.5 dark:bg-zinc-800 dark:border-zinc-600 dark:text-zinc-200 dark:focus:ring-blue-400 dark:focus:border-blue-400"
                    @input="$emit('update:displayName', $event.target.value)"
                />
                <button type="button" class="primary-chip shrink-0 text-xs" @click="$emit('save-identity')">
                    {{ $t("common.save") }}
                </button>
            </div>

            <div class="p-2 space-y-2 text-xs">
                <div>
                    <div class="text-gray-500 dark:text-zinc-400">{{ $t("app.identity_hash") }}</div>
                    <button
                        type="button"
                        class="mt-0.5 block w-full truncate text-left font-mono text-[11px] text-gray-700 dark:text-zinc-300 hover:text-blue-600 dark:hover:text-blue-400"
                        :title="config.identity_hash"
                        @click="$emit('copy-value', config.identity_hash, $t('app.identity_hash'))"
                    >
                        {{ config.identity_hash }}
                    </button>
                </div>
                <div>
                    <div class="text-gray-500 dark:text-zinc-400">{{ $t("app.lxmf_address") }}</div>
                    <button
                        type="button"
                        class="mt-0.5 block w-full truncate text-left font-mono text-[11px] text-gray-700 dark:text-zinc-300 hover:text-blue-600 dark:hover:text-blue-400"
                        :title="config.lxmf_address_hash"
                        @click="$emit('copy-value', config.lxmf_address_hash, $t('app.lxmf_address'))"
                    >
                        {{ config.lxmf_address_hash }}
                    </button>
                </div>
            </div>

            <div class="p-2">
                <label class="block text-xs text-gray-500 dark:text-zinc-400 mb-1">
                    {{ $t("app.announce_interval") }}
                </label>
                <select
                    :value="config.auto_announce_interval_seconds"
                    class="bg-gray-50 border border-gray-300 text-gray-900 text-sm rounded-lg focus:ring-blue-500 focus:border-blue-500 block w-full p-2.5 dark:bg-zinc-800 dark:border-zinc-600 dark:text-zinc-200 dark:focus:ring-blue-400 dark:focus:border-blue-400"
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
            </div>

            <div class="p-2">
                <RouterLink
                    :to="{ name: 'identities' }"
                    class="text-xs font-semibold text-blue-600 hover:text-blue-700 dark:text-blue-400 dark:hover:text-blue-300"
                >
                    {{ $t("app.manage_identities") }}
                </RouterLink>
            </div>
        </div>
    </div>
</template>

<script>
import MaterialDesignIcon from "../MaterialDesignIcon.vue";
import LxmfUserIcon from "../LxmfUserIcon.vue";

export default {
    name: "AppSidebarAccountFooter",
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
            isExpanded: false,
        };
    },
    methods: {
        onAccountChipClick() {
            if (this.isCollapsed) {
                this.$router.push({ name: "identities" });
                return;
            }
            this.isExpanded = !this.isExpanded;
        },
    },
};
</script>
