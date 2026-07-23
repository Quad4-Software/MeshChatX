<!-- SPDX-License-Identifier: 0BSD -->

<template>
    <div class="flex flex-wrap justify-center border-b border-gray-200 dark:border-zinc-800 shrink-0">
        <button
            :class="tabClass('phone')"
            class="py-2 px-4 border-b-2 font-medium text-sm transition-all"
            @click="$emit('update:activeTab', 'phone')"
        >
            Phone
        </button>
        <button
            :class="tabClass('phonebook')"
            class="py-2 px-4 border-b-2 font-medium text-sm transition-all"
            @click="$emit('update:activeTab', 'phonebook')"
        >
            Phonebook
        </button>
        <button
            :class="tabClass('voicemail')"
            class="py-2 px-4 border-b-2 font-medium text-sm flex items-center gap-2 transition-all"
            @click="$emit('update:activeTab', 'voicemail')"
        >
            Voicemail
            <span
                v-if="unreadVoicemailsCount > 0"
                class="bg-red-500 text-white text-[10px] px-1.5 py-0.5 rounded-full animate-pulse"
                >{{ unreadVoicemailsCount }}</span
            >
        </button>
        <button
            :class="tabClass('contacts')"
            class="py-2 px-4 border-b-2 font-medium text-sm transition-all"
            @click="$emit('update:activeTab', 'contacts')"
        >
            Contacts
        </button>
        <button
            :class="tabClass('ringtone')"
            class="py-2 px-4 border-b-2 font-medium text-sm transition-all"
            @click="$emit('update:activeTab', 'ringtone')"
        >
            {{ $t("call.ringtone") }}
        </button>
    </div>
</template>

<script>
export default {
    name: "CallTabBar",
    props: {
        activeTab: {
            type: String,
            required: true,
        },
        unreadVoicemailsCount: {
            type: Number,
            default: 0,
        },
    },
    emits: ["update:activeTab"],
    methods: {
        tabClass(tab) {
            return this.activeTab === tab
                ? "border-blue-500 text-blue-600 dark:text-blue-400"
                : "border-transparent text-gray-500 hover:text-gray-700 dark:text-zinc-400 dark:hover:text-zinc-200 hover:border-gray-300";
        },
    },
};
</script>
