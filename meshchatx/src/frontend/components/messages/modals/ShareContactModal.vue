<!-- SPDX-License-Identifier: 0BSD -->

<template>
    <div
        v-if="show"
        class="fixed inset-0 z-100 flex items-center justify-center p-4 pt-[max(0.75rem,env(safe-area-inset-top))] pb-[max(0.75rem,env(safe-area-inset-bottom))] bg-black/50 backdrop-blur-xs"
        @click.self="$emit('close')"
    >
        <div
            class="w-full max-w-md bg-sem-surface rounded-2xl shadow-2xl overflow-hidden max-h-[min(90dvh,40rem)] flex flex-col"
        >
            <div class="px-6 py-4 border-b border-sem-border flex items-center justify-between">
                <h3 class="text-lg font-bold text-sem-fg">
                    {{ $t("messages.share_contact_modal_title") }}
                </h3>
                <button
                    type="button"
                    class="text-gray-400 hover:text-gray-500 dark:hover:text-zinc-300 transition-colors"
                    @click="$emit('close')"
                >
                    <MaterialDesignIcon icon-name="close" class="size-6" />
                </button>
            </div>
            <div class="p-6">
                <div class="mb-4">
                    <div class="relative">
                        <input
                            :value="search"
                            type="text"
                            :placeholder="$t('messages.share_contact_search_placeholder')"
                            class="block w-full rounded-lg border-0 py-2 pl-10 text-sem-fg shadow-xs ring-1 ring-inset ring-gray-300 dark:ring-zinc-800 placeholder:text-gray-400 focus:ring-2 focus:ring-inset focus:ring-blue-600 sm:text-sm dark:bg-zinc-900"
                            @input="$emit('update:search', $event.target.value)"
                        />
                        <div class="pointer-events-none absolute inset-y-0 left-0 flex items-center pl-3">
                            <MaterialDesignIcon icon-name="magnify" class="size-5 text-gray-400" />
                        </div>
                    </div>
                </div>
                <div class="max-h-64 overflow-y-auto space-y-2">
                    <button
                        v-for="contact in contacts"
                        :key="contact.id"
                        type="button"
                        class="w-full flex items-center gap-3 p-3 rounded-xl hover:bg-sem-surface-muted transition-colors text-left"
                        @click="$emit('share', contact)"
                    >
                        <div class="shrink-0">
                            <LxmfUserIcon
                                :custom-image="contact.custom_image"
                                :icon-name="resolveIcon(contact).iconName"
                                :icon-foreground-colour="resolveIcon(contact).foreground"
                                :icon-background-colour="resolveIcon(contact).background"
                                icon-class="size-10"
                            />
                        </div>
                        <div class="min-w-0">
                            <div class="font-bold text-sem-fg truncate">
                                {{ contact.name }}
                            </div>
                            <div class="text-[10px] text-sem-fg-muted font-mono truncate">
                                {{ destinationHex(contact) || contact.remote_identity_hash }}
                            </div>
                            <div v-if="contact.lxmf_address" class="text-[9px] text-sem-fg-muted font-mono truncate">
                                LXMF: {{ contact.lxmf_address }}
                            </div>
                            <div v-if="contact.lxst_address" class="text-[9px] text-sem-fg-muted font-mono truncate">
                                LXST: {{ contact.lxst_address }}
                            </div>
                        </div>
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
    name: "ShareContactModal",
    components: {
        MaterialDesignIcon,
        LxmfUserIcon,
    },
    props: {
        show: {
            type: Boolean,
            default: false,
        },
        search: {
            type: String,
            default: "",
        },
        contacts: {
            type: Array,
            default: () => [],
        },
        resolveIcon: {
            type: Function,
            required: true,
        },
        destinationHex: {
            type: Function,
            required: true,
        },
    },
    emits: ["close", "share", "update:search"],
};
</script>
