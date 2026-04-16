<!-- SPDX-License-Identifier: 0BSD -->

<template>
    <div
        class="relative z-20 flex flex-wrap items-center gap-y-2 px-3 sm:px-4 py-3 border-b border-gray-200 dark:border-zinc-800 bg-white dark:bg-zinc-950"
    >
        <div class="flex-shrink-0 mr-3">
            <LxmfUserIcon
                :custom-image="selectedPeer.contact_image"
                :icon-name="selectedPeer.lxmf_user_icon ? selectedPeer.lxmf_user_icon.icon_name : ''"
                :icon-foreground-colour="
                    selectedPeer.lxmf_user_icon ? selectedPeer.lxmf_user_icon.foreground_colour : ''
                "
                :icon-background-colour="
                    selectedPeer.lxmf_user_icon ? selectedPeer.lxmf_user_icon.background_colour : ''
                "
                icon-class="shrink-0"
                :icon-style="messageIconStyle"
            />
        </div>

        <div class="min-w-0 flex-1">
            <div class="flex items-center cursor-pointer min-w-0 group" @click="$emit('edit-display-name')">
                <div
                    v-if="selectedPeer.custom_display_name != null"
                    class="mr-1.5 text-gray-500 dark:text-zinc-400 group-hover:text-gray-700 dark:group-hover:text-zinc-200 transition-colors"
                    :title="$t('messages.custom_display_name')"
                >
                    <MaterialDesignIcon icon-name="tag-outline" class="size-4" />
                </div>
                <div
                    class="font-semibold text-gray-900 dark:text-zinc-100 truncate max-w-[120px] sm:max-w-sm text-base"
                    :title="selectedPeer.custom_display_name ?? selectedPeer.display_name"
                >
                    {{ selectedPeer.custom_display_name ?? selectedPeer.display_name }}
                </div>
            </div>
            <div class="text-xs text-gray-500 dark:text-zinc-400 mt-0.5 flex items-center gap-2 min-w-0">
                <div
                    class="cursor-pointer hover:text-blue-500 transition-colors truncate max-w-[120px] sm:max-w-none shrink-0"
                    :title="selectedPeer.destination_hash"
                    @click="$emit('copy-hash', selectedPeer.destination_hash)"
                >
                    {{ destinationDisplay }}
                </div>

                <div
                    v-if="
                        selectedPeerPath ||
                        selectedPeerSignalMetrics?.snr != null ||
                        selectedPeerLxmfStampInfo?.stamp_cost
                    "
                    class="flex items-center gap-2 min-w-0"
                >
                    <span class="text-gray-300 dark:text-zinc-700 shrink-0">•</span>

                    <div class="flex items-center gap-2 truncate">
                        <span
                            v-if="selectedPeerPath"
                            class="flex items-center cursor-pointer hover:text-gray-700 dark:hover:text-zinc-200 shrink-0"
                            title="Path information"
                            @click="$emit('destination-path-click', selectedPeerPath)"
                        >
                            <span v-if="selectedPeerPath.hops === 0 || selectedPeerPath.hops === 1">{{
                                $t("messages.direct")
                            }}</span>
                            <span v-else>{{ $t("messages.hops_away", { count: selectedPeerPath.hops }) }}</span>
                        </span>

                        <span v-if="selectedPeerSignalMetrics?.snr != null" class="flex items-center gap-2 shrink-0">
                            <span class="text-gray-300 dark:text-zinc-700 opacity-50">•</span>
                            <span
                                class="cursor-pointer hover:text-gray-700 dark:hover:text-zinc-200"
                                title="Signal quality"
                                @click="$emit('signal-metrics-click', selectedPeerSignalMetrics)"
                                >{{ $t("messages.snr", { snr: selectedPeerSignalMetrics.snr }) }}</span
                            >
                        </span>

                        <span v-if="selectedPeerLxmfStampInfo?.stamp_cost" class="flex items-center gap-2 shrink-0">
                            <span class="text-gray-300 dark:text-zinc-700 opacity-50">•</span>
                            <span
                                class="cursor-pointer hover:text-gray-700 dark:hover:text-zinc-200"
                                title="LXMF stamp requirement"
                                @click="$emit('stamp-info-click', selectedPeerLxmfStampInfo)"
                                >{{ $t("messages.stamp_cost", { cost: selectedPeerLxmfStampInfo.stamp_cost }) }}</span
                            >
                        </span>
                    </div>
                </div>
            </div>
        </div>

        <div class="ml-auto flex items-center gap-0.5 sm:gap-1.5 min-w-0 shrink-0">
            <ConversationDropDownMenu
                v-if="selectedPeer"
                :peer="selectedPeer"
                :compact="compactPeerActions"
                :has-failed-messages="hasFailedOrCancelledMessages"
                @conversation-deleted="$emit('conversation-deleted')"
                @set-custom-display-name="$emit('edit-display-name')"
                @popout="$emit('popout')"
                @retry-failed="$emit('retry-failed')"
                @open-telemetry-history="$emit('open-telemetry-history')"
                @start-call="$emit('start-call')"
                @share-contact="$emit('share-contact')"
            />

            <IconButton title="Close" class="shrink-0" @click="$emit('close')">
                <MaterialDesignIcon icon-name="close" class="size-6 sm:size-7" />
            </IconButton>
        </div>
    </div>
</template>

<script>
import Utils from "../../js/Utils";
import MaterialDesignIcon from "../MaterialDesignIcon.vue";
import IconButton from "../IconButton.vue";
import LxmfUserIcon from "../LxmfUserIcon.vue";
import ConversationDropDownMenu from "./ConversationDropDownMenu.vue";

export default {
    name: "ConversationPeerHeader",
    components: {
        MaterialDesignIcon,
        IconButton,
        LxmfUserIcon,
        ConversationDropDownMenu,
    },
    props: {
        selectedPeer: {
            type: Object,
            required: true,
        },
        compactPeerActions: {
            type: Boolean,
            default: false,
        },
        hasFailedOrCancelledMessages: {
            type: Boolean,
            default: false,
        },
        messageIconStyle: {
            type: Object,
            default: () => ({}),
        },
        selectedPeerPath: {
            type: Object,
            default: null,
        },
        selectedPeerSignalMetrics: {
            type: Object,
            default: null,
        },
        selectedPeerLxmfStampInfo: {
            type: Object,
            default: null,
        },
    },
    emits: [
        "edit-display-name",
        "copy-hash",
        "destination-path-click",
        "signal-metrics-click",
        "stamp-info-click",
        "conversation-deleted",
        "popout",
        "retry-failed",
        "open-telemetry-history",
        "start-call",
        "share-contact",
        "close",
    ],
    computed: {
        destinationDisplay() {
            return Utils.formatDestinationHash(this.selectedPeer?.destination_hash);
        },
    },
};
</script>
