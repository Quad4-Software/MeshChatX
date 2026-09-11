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
                    class="text-sem-fg-muted hover:text-sem-fg-muted dark:hover:text-zinc-300 transition-colors"
                    @click="$emit('close')"
                >
                    <MaterialDesignIcon icon-name="close" class="size-6" />
                </button>
            </div>
            <div class="p-6">
                <div class="mb-4">
                    <SearchInput
                        :model-value="search"
                        :placeholder="$t('messages.share_contact_search_placeholder')"
                        @update:model-value="$emit('update:search', $event)"
                    />
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
import SearchInput from "../../SearchInput.vue";
import LxmfUserIcon from "../../LxmfUserIcon.vue";

export default {
    name: "ShareContactModal",
    components: {
        MaterialDesignIcon,
        SearchInput,
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
