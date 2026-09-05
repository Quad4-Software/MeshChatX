<!-- SPDX-License-Identifier: 0BSD -->

<script lang="ts">
    import { t } from "../../../js/i18n.js";

    interface Props {
        activeTab: string;
        unreadVoicemailsCount?: number;
        ontabchange?: (tab: string) => void;
    }

    let {
        activeTab,
        unreadVoicemailsCount = 0,
        ontabchange,
    }: Props = $props();

    function tabClass(tab: string): string {
        return activeTab === tab
            ? "border-blue-500 text-sem-accent"
            : "border-transparent text-gray-500 hover:text-sem-fg-muted hover:text-sem-fg hover:border-gray-300";
    }
</script>

<div class="flex flex-wrap justify-center border-b border-sem-border shrink-0">
    <button
        type="button"
        class="py-2 px-4 border-b-2 font-medium text-sm transition-all {tabClass('phone')}"
        onclick={() => ontabchange?.("phone")}
    >
        Phone
    </button>
    <button
        type="button"
        class="py-2 px-4 border-b-2 font-medium text-sm transition-all {tabClass('phonebook')}"
        onclick={() => ontabchange?.("phonebook")}
    >
        Phonebook
    </button>
    <button
        type="button"
        class="py-2 px-4 border-b-2 font-medium text-sm flex items-center gap-2 transition-all {tabClass('voicemail')}"
        onclick={() => ontabchange?.("voicemail")}
    >
        Voicemail
        {#if unreadVoicemailsCount > 0}
            <span class="bg-red-500 text-white text-[10px] px-1.5 py-0.5 rounded-full animate-pulse">
                {unreadVoicemailsCount}
            </span>
        {/if}
    </button>
    <button
        type="button"
        class="py-2 px-4 border-b-2 font-medium text-sm transition-all {tabClass('contacts')}"
        onclick={() => ontabchange?.("contacts")}
    >
        Contacts
    </button>
    <button
        type="button"
        class="py-2 px-4 border-b-2 font-medium text-sm transition-all {tabClass('ringtone')}"
        onclick={() => ontabchange?.("ringtone")}
    >
        {t("call.ringtone")}
    </button>
</div>
