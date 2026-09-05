<!-- SPDX-License-Identifier: 0BSD -->

<script lang="ts">
    import { t } from "../../../js/i18n.js";

    interface Props {
        activeTab: string;
        unreadVoicemailsCount?: number;
        ontabchange?: (tab: string) => void;
    }

    let { activeTab, unreadVoicemailsCount = 0, ontabchange }: Props = $props();

    function tabClass(tab: string): string {
        return activeTab === tab
            ? "border-sem-accent text-sem-accent"
            : "border-transparent text-sem-fg-muted hover:text-sem-fg hover:border-sem-border";
    }
</script>

<div class="flex flex-wrap justify-center border-b border-sem-border shrink-0" role="tablist">
    <button
        type="button"
        role="tab"
        aria-selected={activeTab === "phone"}
        class="py-2 px-4 border-b-2 font-medium text-sm transition-all cursor-pointer focus-ring-sem {tabClass(
            'phone'
        )}"
        onclick={() => ontabchange?.("phone")}
    >
        {t("call.phone")}
    </button>
    <button
        type="button"
        role="tab"
        aria-selected={activeTab === "phonebook"}
        class="py-2 px-4 border-b-2 font-medium text-sm transition-all cursor-pointer focus-ring-sem {tabClass(
            'phonebook'
        )}"
        onclick={() => ontabchange?.("phonebook")}
    >
        {t("call.phonebook")}
    </button>
    <button
        type="button"
        role="tab"
        aria-selected={activeTab === "voicemail"}
        class="py-2 px-4 border-b-2 font-medium text-sm flex items-center gap-2 transition-all cursor-pointer focus-ring-sem {tabClass(
            'voicemail'
        )}"
        onclick={() => ontabchange?.("voicemail")}
    >
        {t("call.voicemail")}
        {#if unreadVoicemailsCount > 0}
            <span class="bg-sem-danger text-white text-[10px] px-1.5 py-0.5 rounded-full animate-pulse font-bold">
                {unreadVoicemailsCount}
            </span>
        {/if}
    </button>
    <button
        type="button"
        role="tab"
        aria-selected={activeTab === "contacts"}
        class="py-2 px-4 border-b-2 font-medium text-sm transition-all cursor-pointer focus-ring-sem {tabClass(
            'contacts'
        )}"
        onclick={() => ontabchange?.("contacts")}
    >
        {t("call.contacts")}
    </button>
    <button
        type="button"
        role="tab"
        aria-selected={activeTab === "ringtone"}
        class="py-2 px-4 border-b-2 font-medium text-sm transition-all cursor-pointer focus-ring-sem {tabClass(
            'ringtone'
        )}"
        onclick={() => ontabchange?.("ringtone")}
    >
        {t("call.ringtone")}
    </button>
</div>
