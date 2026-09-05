<!-- SPDX-License-Identifier: 0BSD -->

<script lang="ts">
    import MaterialDesignIcon from "../../../ui/svelte/MaterialDesignIcon.svelte";
    import LxmfUserIcon from "../../../ui/svelte/LxmfUserIcon.svelte";
    import EmptyState from "../../../ui/svelte/EmptyState.svelte";
    import Skeleton from "../../../ui/svelte/Skeleton.svelte";
    import AudioWaveformPlayer from "../../messages/components/AudioWaveformPlayer.svelte";
    import CallVoicemailSettings from "./CallVoicemailSettings.svelte";
    import { t } from "../../../js/i18n.js";
    import {
        type CallVoicemailTabProps,
        VOICEMAIL_STYLES,
        resolveCallbackHash,
        getVoicemailAudioSrc,
        getVoicemailDownloadFileName,
        formatVoicemailTimestamp,
        formatVoicemailDuration,
        formatVoicemailHash,
        getVoicemailItemClass,
    } from "../lib/callVoicemailUi.js";

    let props: CallVoicemailTabProps = $props();
    let isVoicemailSettingsExpanded = $state(false);

    function handleSearchInput(event: Event): void {
        const value = (event.target as HTMLInputElement).value;
        props.onsearchinput?.(value);
    }
</script>

{#if props.active}
    <div class="flex-1 flex flex-col max-w-3xl mx-auto w-full pt-2">
        <div class="mb-4">
            <div class="relative">
                <input
                    value={props.voicemailSearch ?? ""}
                    type="text"
                    placeholder={t("call.search_voicemails")}
                    class="input-field w-full pl-10"
                    oninput={handleSearchInput}
                />
                <div class="pointer-events-none absolute inset-y-0 left-0 flex items-center pl-3">
                    <MaterialDesignIcon iconName="magnify" class="size-5 text-sem-fg-muted" />
                </div>
            </div>
        </div>

        {#if props.config}
            <div class="mb-4 border-b border-sem-border overflow-hidden">
                <button
                    type="button"
                    class="w-full px-4 py-3 flex items-center justify-between hover:bg-sem-surface-muted/50 transition-colors focus-ring-sem cursor-pointer"
                    onclick={() => (isVoicemailSettingsExpanded = !isVoicemailSettingsExpanded)}
                >
                    <div class="flex items-center gap-2">
                        <MaterialDesignIcon iconName="cog" class="size-5 text-sem-accent" />
                        <h3 class="text-sm font-bold text-sem-fg uppercase tracking-wider">
                            {t("call.voicemail_settings")}
                        </h3>
                    </div>
                    <MaterialDesignIcon
                        iconName={isVoicemailSettingsExpanded ? "chevron-up" : "chevron-down"}
                        class="size-5 text-sem-fg-muted"
                    />
                </button>

                {#if isVoicemailSettingsExpanded}
                    <CallVoicemailSettings
                        config={props.config}
                        voicemailStatus={props.voicemailStatus}
                        isGeneratingGreeting={props.isGeneratingGreeting}
                        isUploadingGreeting={props.isUploadingGreeting}
                        isPlayingGreeting={props.isPlayingGreeting}
                        onupdateconfig={props.onupdateconfig}
                        onpatchconfig={props.onpatchconfig}
                        onsaveandgenerate={props.onsaveandgenerate}
                        onuploadgreeting={props.onuploadgreeting}
                        onstartrecordinggreeting={props.onstartrecordinggreeting}
                        onstoprecordinggreeting={props.onstoprecordinggreeting}
                        ondeletegreeting={props.ondeletegreeting}
                        onplaygreeting={props.onplaygreeting}
                    />
                {/if}
            </div>
        {/if}

        {#if props.isLoading}
            <div class="space-y-3 p-4">
                <Skeleton class="h-16 w-full rounded-xl" />
                <Skeleton class="h-16 w-full rounded-xl" />
                <Skeleton class="h-16 w-full rounded-xl" />
            </div>
        {:else if !props.voicemails || props.voicemails.length === 0}
            <EmptyState
                icon="voicemail"
                title={t("call.no_voicemails")}
                description={t("call.voicemails_will_appear_here")}
                class="my-auto py-12"
            />
        {:else}
            <div class="space-y-4">
                <div class="border-b border-sem-border overflow-hidden">
                    <div class="px-4 py-3 border-b border-sem-border flex justify-between items-center">
                        <h3 class="text-sm font-bold text-sem-fg uppercase tracking-wider">
                            {t("call.voicemail_inbox")}
                        </h3>
                        <span
                            class="text-[10px] bg-sem-accent-subtle text-sem-accent px-2 py-0.5 rounded-full font-bold uppercase"
                        >
                            {props.voicemails.length}
                            {t("call.messages")}
                        </span>
                    </div>
                    <ul class="divide-y divide-sem-border-subtle">
                        {#each props.voicemails as voicemail (voicemail.id)}
                            <li
                                class="px-4 py-4 hover:bg-sem-surface-muted/50 transition-colors {getVoicemailItemClass(
                                    Boolean(voicemail.is_read)
                                )}"
                            >
                                <div class="flex items-start space-x-4">
                                    <div class="relative shrink-0">
                                        <LxmfUserIcon
                                            customImage={props.getContactByHash?.(voicemail.remote_identity_hash || "")
                                                ?.custom_image || undefined}
                                            iconName={voicemail.remote_icon?.icon_name || ""}
                                            iconForegroundColour={voicemail.remote_icon?.foreground_colour || ""}
                                            iconBackgroundColour={voicemail.remote_icon?.background_colour || ""}
                                            iconClass="size-10"
                                        />
                                    </div>

                                    <div class="flex-1 min-w-0">
                                        <div class="flex items-center justify-between mb-1">
                                            <div class="flex items-center min-w-0 mr-2">
                                                <p class="text-sm font-bold text-sem-fg truncate">
                                                    {voicemail.remote_identity_name || t("call.unknown")}
                                                </p>
                                                {#if !voicemail.is_read}
                                                    <span
                                                        class="ml-2 shrink-0 size-2 inline-block rounded-full bg-sem-accent"
                                                    ></span>
                                                {/if}
                                            </div>
                                            <span class="text-[10px] text-sem-fg-muted font-mono shrink-0">
                                                {formatVoicemailTimestamp(
                                                    (voicemail as any).timestamp ?? (voicemail as any).created_at,
                                                    props.formatDateTime
                                                )}
                                            </span>
                                        </div>

                                        <div class="flex items-center text-xs text-sem-fg-muted space-x-3 mb-3">
                                            <span class="flex items-center gap-1">
                                                <MaterialDesignIcon iconName="clock-outline" class="size-3" />
                                                {formatVoicemailDuration(voicemail as any, props.formatDuration)}
                                            </span>
                                            <button
                                                type="button"
                                                class="opacity-60 font-mono text-[10px] text-left truncate cursor-pointer hover:text-sem-accent transition-colors focus-ring-sem"
                                                title={voicemail.remote_identity_hash}
                                                onclick={(e) => {
                                                    e.stopPropagation();
                                                    props.oncopyhash?.(voicemail.remote_identity_hash || "");
                                                }}
                                            >
                                                {formatVoicemailHash(
                                                    voicemail.remote_identity_hash,
                                                    props.formatDestinationHash
                                                )}
                                            </button>
                                        </div>

                                        <div class="mb-4">
                                            <AudioWaveformPlayer
                                                src={getVoicemailAudioSrc(voicemail.id)}
                                                onplay={() => props.onmarkread?.(voicemail)}
                                            />
                                        </div>

                                        <div class="flex items-center gap-4">
                                            <button
                                                type="button"
                                                class={VOICEMAIL_STYLES.actionBtn}
                                                onclick={() =>
                                                    props.oncallback?.(resolveCallbackHash(voicemail as any))}
                                            >
                                                <MaterialDesignIcon iconName="phone" class="size-3" />
                                                {t("call.call_back")}
                                            </button>
                                            <a
                                                href={getVoicemailAudioSrc(voicemail.id)}
                                                download={getVoicemailDownloadFileName(voicemail.id)}
                                                class={VOICEMAIL_STYLES.actionBtn}
                                            >
                                                <MaterialDesignIcon iconName="download" class="size-3" />
                                                {t("call.download")}
                                            </a>
                                            <button
                                                type="button"
                                                class={VOICEMAIL_STYLES.deleteBtn}
                                                onclick={() => props.ondelete?.(voicemail.id)}
                                            >
                                                <MaterialDesignIcon iconName="delete" class="size-3" />
                                                {t("call.delete")}
                                            </button>
                                        </div>
                                    </div>
                                </div>
                            </li>
                        {/each}
                    </ul>
                </div>
            </div>
        {/if}
    </div>
{/if}
