<!-- SPDX-License-Identifier: 0BSD -->

<script lang="ts">
    import { onMount, onDestroy } from "svelte";
    import MaterialDesignIcon from "../../ui/svelte/MaterialDesignIcon.svelte";
    import { t } from "../../js/i18n.js";
    import CallTabBar from "./components/CallTabBar.svelte";
    import CallPhoneTab from "./components/CallPhoneTab.svelte";
    import CallPhonebookTab from "./components/CallPhonebookTab.svelte";
    import CallVoicemailTab from "./components/CallVoicemailTab.svelte";
    import CallContactsTab from "./components/CallContactsTab.svelte";
    import CallRingtoneTab from "./components/CallRingtoneTab.svelte";
    import CallRecordingsTab from "./components/CallRecordingsTab.svelte";
    import { executeBlockIdentity, executeCopyHash } from "./lib/callPageActions.js";
    import {
        formatBitrate,
        formatBytes,
        formatCallDuration,
        formatCallElapsedTime,
        formatDateTime,
        formatDestinationHash,
        formatDuration,
        formatNumber,
        formatTimeAgo,
    } from "./lib/callFormat.js";
    import { createCallPageInitialState, createCallPageRuntime } from "./lib/callPageRuntime.js";
    import { createCallPageHandlers } from "./lib/callPageHandlers.js";

    interface Props {
        routeQuery?: Record<string, string>;
    }

    let { routeQuery = {} }: Props = $props();

    let pageState = $state(createCallPageInitialState());
    const runtime = createCallPageRuntime(() => isPopout, pageState);
    const { controller } = runtime;
    const handlers = createCallPageHandlers(runtime);

    let contactImageInput = $state<HTMLInputElement | null>(null);

    const isPopout = $derived(
        Boolean(
            routeQuery?.popout ||
            routeQuery?.isPopout ||
            (typeof window !== "undefined" && window.location.hash?.includes("/popout/"))
        )
    );
    const webAudioBridgeEnabled = $derived(
        Boolean(pageState.webAudioBridgeRequired || pageState.config?.telephone_web_audio_enabled)
    );
    const isAndroid = $derived(
        typeof window !== "undefined" &&
            Boolean((window as any).MeshChatXAndroid || navigator.userAgent.includes("MeshChatX-Android"))
    );
    const showWebAudioDeviceSelector = $derived(Boolean(webAudioBridgeEnabled && !isAndroid));
    const isHalfDuplexCall = $derived(
        Boolean(pageState.activeCall && pageState.activeCall.status === 6 && pageState.activeCall.is_half_duplex)
    );
    const isMicMuted = $derived(pageState.localMicMuted);
    const isSpeakerMuted = $derived(pageState.localSpeakerMuted);
    const elapsedTimeFormatted = $derived(
        formatCallElapsedTime(pageState.activeCall?.call_start_time, pageState.nowSeconds) || ""
    );
    const callDurationFormatted = $derived(
        formatCallDuration(pageState.lastCall?.call_start_time, pageState.isCallEnded, pageState.nowSeconds) || ""
    );

    onMount(() => {
        runtime.mount(routeQuery);
    });

    onDestroy(() => {
        runtime.destroy();
    });
</script>

<div class="flex min-w-0 h-full flex-1 flex-col">
    <div class="flex h-full w-full flex-col page-canvas">
        <div class="w-full h-full overflow-y-auto">
            <div class="mx-auto w-full max-w-4xl p-4 md:p-6 flex-1 flex flex-col min-h-full">
                <CallTabBar
                    activeTab={pageState.activeTab}
                    unreadVoicemailsCount={pageState.unreadVoicemailsCount}
                    ontabchange={runtime.onTabChange}
                />

                {#if pageState.activeTab === "phone"}
                    <div class="flex-1 flex flex-col">
                        <CallPhoneTab
                            config={pageState.config}
                            activeCall={pageState.activeCall}
                            lastCall={pageState.lastCall}
                            isCallEnded={pageState.isCallEnded}
                            wasDeclined={pageState.wasDeclined}
                            wasVoicemail={pageState.wasVoicemail}
                            callDuration={callDurationFormatted}
                            elapsedTime={elapsedTimeFormatted}
                            initiationStatus={pageState.initiationStatus}
                            initiationTargetName={pageState.initiationTargetName}
                            initiationTargetHash={pageState.initiationTargetHash}
                            callMinimized={pageState.callMinimized}
                            bind:destinationHash={pageState.destinationHash}
                            audioProfiles={pageState.audioProfiles}
                            callModes={pageState.callModes}
                            selectedAudioProfileId={pageState.selectedAudioProfileId}
                            selectedCallModeId={pageState.selectedCallModeId}
                            {isMicMuted}
                            {isSpeakerMuted}
                            localPttActive={pageState.localPttActive}
                            {isHalfDuplexCall}
                            playingVoicemailId={controller.audioPlayer.state.playingVoicemailId}
                            contacts={pageState.contacts}
                            callHistory={pageState.callHistory}
                            hasMoreCallHistory={pageState.hasMoreCallHistory}
                            callHistorySearch={pageState.callHistorySearch}
                            isLoadingHistory={pageState.isLoadingHistory}
                            {webAudioBridgeEnabled}
                            webAudioBridgeRequired={pageState.webAudioBridgeRequired}
                            {showWebAudioDeviceSelector}
                            selectedAudioInputId={controller.webAudio.selectedAudioInputId}
                            selectedAudioOutputId={controller.webAudio.selectedAudioOutputId}
                            audioInputDevices={controller.webAudio.audioInputDevices}
                            audioOutputDevices={controller.webAudio.audioOutputDevices}
                            {isAndroid}
                            getContactByHash={handlers.getContactByHash}
                            {formatDestinationHash}
                            {formatDateTime}
                            {formatDuration}
                            {formatNumber}
                            {formatBytes}
                            {formatBitrate}
                            onupdateconfig={handlers.onUpdateConfig}
                            oncall={handlers.onCall}
                            onhangup={handlers.onHangup}
                            onanswer={handlers.onAnswer}
                            onsendtovoicemail={handlers.onSendToVoicemail}
                            onexpandcall={() => (pageState.callMinimized = false)}
                            onminimizecall={() => (pageState.callMinimized = true)}
                            ontogglemic={handlers.onToggleMic}
                            ontogglespeaker={handlers.onToggleSpeaker}
                            onsetptt={handlers.onSetPtt}
                            onselectaudioprofile={(id) => handlers.onSwitchAudioProfile(id)}
                            onselectcallmode={(id) => handlers.onSwitchCallMode(id)}
                            onplaylatestvoicemail={handlers.onPlayLatestVoicemail}
                            ontogglednd={(val) => handlers.onUpdateConfig({ do_not_disturb_enabled: val })}
                            ontogglecontactsonly={(val) =>
                                handlers.onUpdateConfig({ telephone_allow_calls_from_contacts_only: val })}
                            ontoggletelephoneannounce={(val) =>
                                handlers.onUpdateConfig({ telephone_announce_enabled: val })}
                            ontogglewebaudio={handlers.onToggleWebAudio}
                            onchangeaudioprofile={(id) => handlers.onUpdateConfig({ telephone_audio_profile_id: id })}
                            onchangecallmode={(id) => handlers.onUpdateConfig({ telephone_call_mode_id: id })}
                            onrefreshaudiodevices={() => controller.webAudio.refreshAudioDevices()}
                            onrestartwebaudio={handlers.onRestartWebAudio}
                            onselectaudioinput={(id) => (controller.webAudio.selectedAudioInputId = id)}
                            onselectaudiooutput={(id) => (controller.webAudio.selectedAudioOutputId = id)}
                            onclearhistory={handlers.onClearHistory}
                            onhistorysearch={handlers.onHistorySearch}
                            onaddcontact={handlers.openAddContactFromHistory}
                            onblockidentity={(h) => executeBlockIdentity(h)}
                            onopenmessage={handlers.openMessageFromHistory}
                            oncallback={handlers.onPhonebookCall}
                            onloadmorehistory={handlers.loadMoreHistory}
                            oncopyhash={(h) => executeCopyHash(h)}
                        />
                    </div>
                {:else if pageState.activeTab === "phonebook"}
                    <div class="flex-1 flex flex-col">
                        <CallPhonebookTab
                            active={pageState.activeTab === "phonebook"}
                            discoverySearch={pageState.discoverySearch}
                            totalDiscoveryCount={pageState.totalDiscoveryCount}
                            discoveryAnnounces={pageState.discoveryAnnounces}
                            hasMoreDiscovery={pageState.hasMoreDiscovery}
                            isLoading={pageState.isLoadingDiscovery}
                            {formatTimeAgo}
                            {formatDestinationHash}
                            onsearchinput={handlers.onDiscoverySearch}
                            oncopyhash={(h) => executeCopyHash(h)}
                            onloadmore={handlers.loadMoreDiscovery}
                            oncall={handlers.onPhonebookCall}
                        />
                    </div>
                {:else if pageState.activeTab === "voicemail"}
                    <div class="flex-1 flex flex-col">
                        <CallVoicemailTab
                            active={pageState.activeTab === "voicemail"}
                            voicemailSearch={pageState.voicemailSearch}
                            config={pageState.config}
                            voicemailStatus={pageState.voicemailStatus}
                            voicemails={pageState.voicemails}
                            isLoading={pageState.isLoadingVoicemails}
                            isGeneratingGreeting={pageState.isGeneratingGreeting}
                            isUploadingGreeting={pageState.isUploadingGreeting}
                            isPlayingGreeting={controller.audioPlayer.state.isPlayingGreeting}
                            getContactByHash={handlers.getContactByHash}
                            {formatDateTime}
                            {formatDuration}
                            {formatDestinationHash}
                            onsearchinput={handlers.onVoicemailSearch}
                            onupdateconfig={handlers.onUpdateConfig}
                            onpatchconfig={handlers.onPatchConfig}
                            onsaveandgenerate={handlers.onVoicemailSaveAndGenerate}
                            onuploadgreeting={handlers.onUploadGreeting}
                            onstartrecordinggreeting={handlers.onStartRecordingGreeting}
                            onstoprecordinggreeting={handlers.onStopRecordingGreeting}
                            ondeletegreeting={handlers.onDeleteGreeting}
                            onplaygreeting={() => controller.audioPlayer.playGreeting()}
                            oncopyhash={(h) => executeCopyHash(h)}
                            onmarkread={handlers.onMarkVoicemailRead}
                            oncallback={(dest) => {
                                if (dest) handlers.onPhonebookCall(dest);
                            }}
                            ondelete={handlers.onDeleteVoicemail}
                        />
                    </div>
                {:else if pageState.activeTab === "contacts"}
                    <div class="flex-1 flex flex-col">
                        <CallContactsTab
                            active={pageState.activeTab === "contacts"}
                            contactsSearch={pageState.contactsSearch}
                            contacts={pageState.contacts}
                            {formatDestinationHash}
                            onsearchinput={handlers.onContactsSearch}
                            onadd={handlers.openAddContactModal}
                            onedit={handlers.openEditContactModal}
                            ondelete={handlers.onDeleteContact}
                            oncopyhash={(h) => executeCopyHash(h)}
                            oncall={handlers.onPhonebookCall}
                        />
                    </div>
                {:else if pageState.activeTab === "ringtone" && pageState.config}
                    <div class="flex-1 flex flex-col">
                        <CallRingtoneTab
                            active={pageState.activeTab === "ringtone"}
                            config={pageState.config}
                            ringtones={pageState.ringtones}
                            ringtoneStatus={pageState.ringtoneStatus}
                            isRingtoneEditorOpen={pageState.isRingtoneEditorOpen}
                            editingRingtoneForAudio={pageState.editingRingtoneForAudio}
                            isUploadingRingtone={pageState.isUploadingRingtone}
                            isPlayingRingtone={controller.audioPlayer.state.isPlayingRingtone}
                            playingRingtoneId={controller.audioPlayer.state.playingRingtoneId}
                            editingRingtoneId={pageState.editingRingtoneId}
                            editingRingtoneName={pageState.editingRingtoneName}
                            {formatDestinationHash}
                            onupdateconfig={handlers.onUpdateConfig}
                            onopeneditor={handlers.openRingtoneEditor}
                            oncloseeditor={() => (pageState.isRingtoneEditorOpen = false)}
                            onringtonesaved={handlers.onRingtoneSaved}
                            onupload={handlers.onUploadRingtone}
                            onplay={(rt) =>
                                controller.audioPlayer.playRingtone(rt, pageState.config?.ringtone_volume ?? 100)}
                            ondelete={handlers.onDeleteRingtone}
                            onsetprimary={handlers.onSetPrimaryRingtone}
                            onsetdefault={handlers.onSetPrimaryRingtone}
                            onrename={handlers.saveRingtoneName}
                            onstartrename={handlers.startEditingRingtone}
                            onrenameinput={(val) => (pageState.editingRingtoneName = val)}
                            oncopy={(h) => executeCopyHash(h)}
                        />
                    </div>
                {:else if pageState.activeTab === "recordings"}
                    <div class="flex-1 flex flex-col">
                        <CallRecordingsTab
                            recordings={pageState.recordings}
                            recordingSearch={pageState.recordingSearch}
                            isLoading={pageState.isLoadingRecordings}
                            playingRecordingId={controller.audioPlayer.state.playingRecordingId}
                            playingSide={controller.audioPlayer.state.playingSide}
                            {formatDestinationHash}
                            {formatDateTime}
                            {formatDuration}
                            onsearchinput={handlers.onRecordingSearch}
                            onplay={handlers.onPlayRecording}
                            ondelete={handlers.onDeleteRecording}
                            oncopyhash={(h) => executeCopyHash(h)}
                        />
                    </div>
                {/if}
            </div>
        </div>
    </div>

    <!-- Contact Add/Edit Modal -->
    {#if pageState.isContactModalOpen}
        <div class="fixed inset-0 z-150 flex items-center justify-center p-4">
            <button
                type="button"
                tabindex="-1"
                aria-label={t("common.close")}
                class="fixed inset-0 bg-black/60 backdrop-blur-xs transition-opacity cursor-default"
                onclick={() => (pageState.isContactModalOpen = false)}
            ></button>
            <div
                class="relative z-10 w-full max-w-lg bg-sem-surface rounded-3xl shadow-2xl overflow-hidden transform transition-all scale-100 border border-sem-border"
                role="dialog"
                aria-modal="true"
                tabindex="-1"
            >
                <div
                    class="px-6 py-5 border-b border-sem-border flex items-center justify-between bg-sem-surface-muted/50"
                >
                    <div class="flex items-center gap-3">
                        <div class="p-2 bg-sem-accent-subtle text-sem-accent rounded-xl">
                            <MaterialDesignIcon iconName="account-plus" class="size-6" />
                        </div>
                        <h3 class="text-xl font-bold text-sem-fg tracking-tight">
                            {pageState.editingContact ? t("call.edit_contact") : t("call.add_contact")}
                        </h3>
                    </div>
                    <button
                        type="button"
                        class="p-2 text-sem-fg-muted hover:text-sem-fg hover:bg-sem-surface-muted rounded-full transition-all focus-ring-sem cursor-pointer"
                        onclick={() => (pageState.isContactModalOpen = false)}
                    >
                        <MaterialDesignIcon iconName="close" class="size-6" />
                    </button>
                </div>
                <div class="p-6 space-y-6">
                    <div class="space-y-4">
                        <div class="flex flex-col items-center justify-center pb-4">
                            <div class="relative group">
                                <div
                                    class="size-24 rounded-full overflow-hidden bg-sem-surface-muted border-2 border-dashed border-sem-border flex items-center justify-center"
                                >
                                    {#if pageState.contactForm.custom_image}
                                        <img
                                            src={pageState.contactForm.custom_image}
                                            alt="Contact avatar preview"
                                            class="w-full h-full object-cover"
                                        />
                                    {:else}
                                        <MaterialDesignIcon iconName="camera-plus" class="size-8 text-sem-fg-muted" />
                                    {/if}
                                </div>
                                <button
                                    type="button"
                                    class="absolute inset-0 flex items-center justify-center bg-black/40 text-white opacity-0 group-hover:opacity-100 transition-opacity rounded-full cursor-pointer focus-ring-sem"
                                    onclick={() => contactImageInput?.click()}
                                >
                                    <span class="text-xs font-bold"
                                        >{pageState.contactForm.custom_image
                                            ? t("common.change")
                                            : t("call.upload")}</span
                                    >
                                </button>
                                {#if pageState.contactForm.custom_image}
                                    <button
                                        type="button"
                                        class="absolute -top-1 -right-1 p-1 bg-sem-danger text-white rounded-full shadow-lg hover:bg-sem-danger/90 transition-colors cursor-pointer focus-ring-sem"
                                        onclick={() => (pageState.contactForm.custom_image = null)}
                                    >
                                        <MaterialDesignIcon iconName="close" class="size-3" />
                                    </button>
                                {/if}
                            </div>
                            <input
                                bind:this={contactImageInput}
                                type="file"
                                class="hidden"
                                accept="image/*"
                                onchange={handlers.onContactImageSelected}
                            />
                            <p class="text-[10px] text-sem-fg-muted mt-2 uppercase font-bold tracking-widest">
                                {t("call.profile_image")}
                            </p>
                        </div>
                        <div>
                            <label
                                for="contact-form-name"
                                class="block text-xs font-bold text-sem-fg-muted uppercase tracking-wider mb-1.5 ml-1"
                                >{t("call.contact_name")}</label
                            >
                            <input
                                id="contact-form-name"
                                bind:value={pageState.contactForm.name}
                                type="text"
                                class="input-field"
                                placeholder="e.g. John Doe"
                            />
                        </div>
                        <div>
                            <label
                                for="contact-form-hash"
                                class="block text-xs font-bold text-sem-fg-muted uppercase tracking-wider mb-1.5 ml-1"
                                >{t("call.identity_hash")}</label
                            >
                            <input
                                id="contact-form-hash"
                                bind:value={pageState.contactForm.remote_identity_hash}
                                type="text"
                                class="input-field font-mono text-sm"
                                placeholder="e.g. a39610c89d18bb48c73e429582423c24"
                            />
                        </div>
                        <div class="grid grid-cols-1 sm:grid-cols-2 gap-4">
                            <div>
                                <label
                                    for="contact-form-lxmf"
                                    class="block text-xs font-bold text-sem-fg-muted uppercase tracking-wider mb-1.5 ml-1"
                                    >{t("app.lxmf_address")}</label
                                >
                                <input
                                    id="contact-form-lxmf"
                                    bind:value={pageState.contactForm.lxmf_address}
                                    type="text"
                                    class="input-field font-mono text-xs"
                                    placeholder={t("common.optional")}
                                />
                            </div>
                            <div>
                                <label
                                    for="contact-form-lxst"
                                    class="block text-xs font-bold text-sem-fg-muted uppercase tracking-wider mb-1.5 ml-1"
                                    >{t("identities.lxst_address")}</label
                                >
                                <input
                                    id="contact-form-lxst"
                                    bind:value={pageState.contactForm.lxst_address}
                                    type="text"
                                    class="input-field font-mono text-xs"
                                    placeholder={t("common.optional")}
                                />
                            </div>
                        </div>
                        <div>
                            <label
                                for="contact-form-ringtone"
                                class="block text-xs font-bold text-sem-fg-muted uppercase tracking-wider mb-1.5 ml-1"
                                >{t("call.preferred_ringtone")}</label
                            >
                            <select
                                id="contact-form-ringtone"
                                bind:value={pageState.contactForm.preferred_ringtone_id}
                                class="input-field"
                            >
                                <option value={null}>{t("call.default_global_setting")}</option>
                                <option value={-1}>{t("call.random")}</option>
                                <optgroup label={t("call.uploaded_ringtones")}>
                                    {#each pageState.ringtones as rt (rt.id)}<option value={rt.id}
                                            >{rt.display_name || rt.filename}</option
                                        >{/each}
                                </optgroup>
                            </select>
                        </div>
                    </div>
                    <div class="flex gap-3 mt-8">
                        <button
                            type="button"
                            class="flex-1 px-6 py-3 rounded-2xl bg-sem-surface-muted text-sem-fg-muted font-bold hover:bg-sem-surface-subtle hover:text-sem-fg transition-all active:scale-95 focus-ring-sem cursor-pointer"
                            onclick={() => (pageState.isContactModalOpen = false)}
                        >
                            {t("common.cancel")}
                        </button>
                        <button
                            type="button"
                            class="flex-2 primary-chip rounded-2xl! py-3! font-bold! focus-ring-sem cursor-pointer"
                            onclick={handlers.onSaveContact}
                        >
                            {t("call.save_contact")}
                        </button>
                    </div>
                </div>
            </div>
        </div>
    {/if}
</div>
