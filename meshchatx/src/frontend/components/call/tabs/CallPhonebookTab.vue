<!-- SPDX-License-Identifier: 0BSD -->

<template>
    <div v-if="active" class="flex-1 flex flex-col max-w-3xl mx-auto w-full pt-2">
        <div class="mb-4">
            <div class="relative">
                <input
                    :value="discoverySearch"
                    type="text"
                    :placeholder="`Search phonebook (${totalDiscoveryCount})...`"
                    class="block w-full rounded-lg border-0 py-2 pl-10 text-gray-900 dark:text-white shadow-xs ring-1 ring-inset ring-gray-300 dark:ring-zinc-800 placeholder:text-gray-400 focus:ring-2 focus:ring-inset focus:ring-blue-600 sm:text-sm dark:bg-zinc-900"
                    @input="onSearchInput"
                />
                <div class="pointer-events-none absolute inset-y-0 left-0 flex items-center pl-3">
                    <MaterialDesignIcon icon-name="magnify" class="size-5 text-gray-400" />
                </div>
            </div>
        </div>

        <div v-if="discoveryAnnounces.length === 0" class="my-auto text-center">
            <div class="bg-gray-200 dark:bg-zinc-800 p-6 rounded-full inline-block mb-4">
                <MaterialDesignIcon icon-name="satellite-uplink" class="size-12 text-gray-400" />
            </div>
            <h3 class="text-lg font-medium text-gray-900 dark:text-white">No Telephony Peers</h3>
            <p class="text-gray-500 dark:text-zinc-400">Waiting for announces on the mesh.</p>
        </div>

        <div v-else class="space-y-4">
            <div class="border-b border-gray-200 dark:border-zinc-800 overflow-hidden">
                <ul class="divide-y divide-gray-100 dark:divide-zinc-800">
                    <li
                        v-for="announce in discoveryAnnounces"
                        :key="announce.destination_hash"
                        class="px-4 py-4 hover:bg-gray-50 dark:hover:bg-zinc-800/50 transition-colors"
                    >
                        <div class="flex items-center space-x-4">
                            <div class="shrink-0">
                                <LxmfUserIcon
                                    :custom-image="announce.contact_image"
                                    :icon-name="announce.lxmf_user_icon?.icon_name"
                                    :icon-foreground-colour="announce.lxmf_user_icon?.foreground_colour"
                                    :icon-background-colour="announce.lxmf_user_icon?.background_colour"
                                    class="size-10"
                                />
                            </div>
                            <div class="flex-1 min-w-0">
                                <div class="flex items-center justify-between">
                                    <div class="flex items-center min-w-0">
                                        <p class="text-sm font-bold text-gray-900 dark:text-white truncate">
                                            {{ announce.display_name || "Anonymous Peer" }}
                                        </p>
                                        <a
                                            v-if="announce.lxmf_destination_hash"
                                            :href="`/#/messages/${announce.lxmf_destination_hash}`"
                                            class="ml-2 p-1 text-gray-400 hover:text-blue-500 transition-colors"
                                            title="Message via LXMF"
                                            @click.stop
                                        >
                                            <MaterialDesignIcon icon-name="message-text-outline" class="size-4" />
                                        </a>
                                    </div>
                                    <span class="text-[10px] text-gray-500 dark:text-zinc-500 font-mono ml-2 shrink-0">
                                        {{ formatTimeAgo(announce.updated_at) }}
                                    </span>
                                </div>
                                <div class="flex items-center justify-between mt-1">
                                    <div class="flex items-center space-x-2 min-w-0">
                                        <span
                                            class="text-[10px] text-gray-500 dark:text-zinc-500 font-mono truncate cursor-pointer hover:text-blue-500 transition-colors"
                                            :title="announce.destination_hash"
                                            @click.stop="$emit('copy-hash', announce.destination_hash)"
                                        >
                                            {{ formatDestinationHash(announce.destination_hash) }}
                                        </span>
                                        <span
                                            v-if="announce.hops != null"
                                            class="text-[10px] text-gray-400 dark:text-zinc-600"
                                        >
                                            • {{ announce.hops }} hops
                                        </span>
                                    </div>
                                    <button
                                        type="button"
                                        class="text-[10px] bg-blue-100 text-blue-600 dark:bg-blue-900/30 dark:text-blue-400 px-3 py-1 rounded-full font-bold uppercase tracking-wider hover:bg-blue-200 dark:hover:bg-blue-900/50 transition-colors shrink-0"
                                        @click="$emit('call', announce.destination_hash)"
                                    >
                                        Call
                                    </button>
                                </div>
                            </div>
                        </div>
                    </li>
                </ul>
                <div v-if="hasMoreDiscovery" class="p-3 border-t border-gray-100 dark:border-zinc-800 text-center">
                    <button
                        type="button"
                        class="text-xs text-blue-500 hover:text-blue-600 font-bold uppercase tracking-widest"
                        @click="$emit('load-more')"
                    >
                        {{ $t("call.load_more") }}
                    </button>
                </div>
            </div>
        </div>
    </div>
</template>

<script>
import MaterialDesignIcon from "../../MaterialDesignIcon.vue";
import LxmfUserIcon from "../../LxmfUserIcon.vue";

export default {
    name: "CallPhonebookTab",
    components: {
        MaterialDesignIcon,
        LxmfUserIcon,
    },
    props: {
        active: {
            type: Boolean,
            default: false,
        },
        discoverySearch: {
            type: String,
            default: "",
        },
        totalDiscoveryCount: {
            type: Number,
            default: 0,
        },
        discoveryAnnounces: {
            type: Array,
            default: () => [],
        },
        hasMoreDiscovery: {
            type: Boolean,
            default: false,
        },
        formatTimeAgo: {
            type: Function,
            required: true,
        },
        formatDestinationHash: {
            type: Function,
            required: true,
        },
    },
    emits: ["update:discoverySearch", "search-input", "copy-hash", "load-more", "call"],
    methods: {
        onSearchInput(event) {
            this.$emit("update:discoverySearch", event.target.value);
            this.$emit("search-input");
        },
    },
};
</script>
