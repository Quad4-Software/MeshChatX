<!-- SPDX-License-Identifier: 0BSD -->

<template>
    <div v-if="active" class="flex-1 flex flex-col max-w-3xl mx-auto w-full pt-2">
        <div class="mb-4 flex gap-2">
            <div class="relative flex-1">
                <input
                    :value="contactsSearch"
                    type="text"
                    :placeholder="$t('contacts.search_placeholder')"
                    class="block w-full rounded-lg border-0 py-2 pl-10 text-gray-900 dark:text-white shadow-xs ring-1 ring-inset ring-gray-300 dark:ring-zinc-800 placeholder:text-gray-400 focus:ring-2 focus:ring-inset focus:ring-blue-600 sm:text-sm dark:bg-zinc-900"
                    @input="onSearchInput"
                />
                <div class="pointer-events-none absolute inset-y-0 left-0 flex items-center pl-3">
                    <MaterialDesignIcon icon-name="magnify" class="size-5 text-gray-400" />
                </div>
            </div>
            <button
                type="button"
                class="rounded-lg bg-blue-600 px-3 py-2 text-sm font-semibold text-white shadow-xs hover:bg-blue-500 transition-colors flex items-center gap-2"
                @click="$emit('add')"
            >
                <MaterialDesignIcon icon-name="plus" class="size-5" />
                {{ $t("common.add") }}
            </button>
        </div>

        <div v-if="contacts.length === 0" class="my-auto text-center">
            <div class="bg-gray-200 dark:bg-zinc-800 p-6 rounded-full inline-block mb-4">
                <MaterialDesignIcon icon-name="account-multiple" class="size-12 text-gray-400" />
            </div>
            <h3 class="text-lg font-medium text-gray-900 dark:text-white">{{ $t("contacts.no_contacts") }}</h3>
            <p class="text-gray-500 dark:text-zinc-400">{{ $t("call.no_contacts_hint") }}</p>
        </div>

        <div v-else class="space-y-4">
            <div class="border-b border-gray-200 dark:border-zinc-800 overflow-hidden">
                <ul class="divide-y divide-gray-100 dark:divide-zinc-800">
                    <li
                        v-for="contact in contacts"
                        :key="contact.id"
                        class="px-4 py-3 hover:bg-gray-50 dark:hover:bg-zinc-800/50 transition-colors"
                    >
                        <div class="flex items-center space-x-3">
                            <div class="shrink-0">
                                <LxmfUserIcon
                                    :custom-image="contact.custom_image"
                                    :icon-name="contact.remote_icon ? contact.remote_icon.icon_name : ''"
                                    :icon-foreground-colour="
                                        contact.remote_icon ? contact.remote_icon.foreground_colour : ''
                                    "
                                    :icon-background-colour="
                                        contact.remote_icon ? contact.remote_icon.background_colour : ''
                                    "
                                    class="size-10"
                                />
                            </div>
                            <div class="flex-1 min-w-0">
                                <div class="flex items-center justify-between">
                                    <p class="text-sm font-bold text-gray-900 dark:text-white truncate">
                                        {{ contact.name }}
                                    </p>
                                    <div class="flex items-center gap-2">
                                        <span
                                            v-if="contact.preferred_ringtone_id"
                                            class="text-[9px] px-1.5 py-0.5 rounded-sm bg-amber-50 dark:bg-amber-900/30 text-amber-600 dark:text-amber-400 border border-amber-100 dark:border-amber-800/50 flex items-center gap-1"
                                            :title="$t('call.custom_ringtone_set')"
                                        >
                                            <MaterialDesignIcon icon-name="music" class="size-2.5" />
                                            {{
                                                contact.preferred_ringtone_id === -1
                                                    ? $t("call.random")
                                                    : $t("call.custom")
                                            }}
                                        </span>
                                        <div class="flex items-center gap-1">
                                            <button
                                                type="button"
                                                class="p-1.5 text-gray-400 hover:text-blue-500 transition-colors"
                                                :aria-label="$t('common.edit')"
                                                :title="$t('common.edit')"
                                                @click="$emit('edit', contact)"
                                            >
                                                <MaterialDesignIcon icon-name="pencil" class="size-4" />
                                            </button>
                                            <button
                                                type="button"
                                                class="p-1.5 text-gray-400 hover:text-red-500 transition-colors"
                                                :aria-label="$t('common.delete')"
                                                :title="$t('common.delete')"
                                                @click="$emit('delete', contact.id)"
                                            >
                                                <MaterialDesignIcon icon-name="delete" class="size-4" />
                                            </button>
                                        </div>
                                    </div>
                                </div>
                                <div class="flex items-center justify-between mt-1">
                                    <div class="flex flex-col min-w-0">
                                        <span
                                            class="text-[10px] text-gray-500 dark:text-zinc-500 font-mono truncate cursor-pointer hover:text-blue-500 transition-colors"
                                            :title="contact.remote_identity_hash"
                                            @click.stop="$emit('copy-hash', contact.remote_identity_hash)"
                                        >
                                            ID:
                                            {{ formatDestinationHash(contact.remote_identity_hash) }}
                                        </span>
                                        <span
                                            v-if="contact.lxmf_address"
                                            class="text-[9px] text-gray-400 dark:text-zinc-500 font-mono truncate cursor-pointer hover:text-blue-500 transition-colors"
                                            :title="contact.lxmf_address"
                                            @click.stop="$emit('copy-hash', contact.lxmf_address)"
                                        >
                                            LXMF: {{ formatDestinationHash(contact.lxmf_address) }}
                                        </span>
                                        <span
                                            v-if="contact.lxst_address"
                                            class="text-[9px] text-gray-400 dark:text-zinc-500 font-mono truncate cursor-pointer hover:text-blue-500 transition-colors"
                                            :title="contact.lxst_address"
                                            @click.stop="$emit('copy-hash', contact.lxst_address)"
                                        >
                                            LXST: {{ formatDestinationHash(contact.lxst_address) }}
                                        </span>
                                    </div>
                                    <button
                                        type="button"
                                        class="text-[10px] bg-blue-100 text-blue-600 dark:bg-blue-900/30 dark:text-blue-400 px-3 py-1 rounded-full font-bold uppercase tracking-wider hover:bg-blue-200 dark:hover:bg-blue-900/50 transition-colors shrink-0"
                                        @click="
                                            $emit(
                                                'call',
                                                contact.remote_telephony_hash ||
                                                    contact.remote_destination_hash ||
                                                    contact.remote_identity_hash
                                            )
                                        "
                                    >
                                        Call
                                    </button>
                                </div>
                            </div>
                        </div>
                    </li>
                </ul>
            </div>
        </div>
    </div>
</template>

<script>
import MaterialDesignIcon from "../../MaterialDesignIcon.vue";
import LxmfUserIcon from "../../LxmfUserIcon.vue";

export default {
    name: "CallContactsTab",
    components: {
        MaterialDesignIcon,
        LxmfUserIcon,
    },
    props: {
        active: {
            type: Boolean,
            default: false,
        },
        contactsSearch: {
            type: String,
            default: "",
        },
        contacts: {
            type: Array,
            default: () => [],
        },
        formatDestinationHash: {
            type: Function,
            required: true,
        },
    },
    emits: ["update:contactsSearch", "search-input", "add", "edit", "delete", "copy-hash", "call"],
    methods: {
        onSearchInput(event) {
            this.$emit("update:contactsSearch", event.target.value);
            this.$emit("search-input");
        },
    },
};
</script>
