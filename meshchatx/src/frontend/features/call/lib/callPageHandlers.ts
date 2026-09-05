// SPDX-License-Identifier: 0BSD

import { t } from "../../../js/i18n.js";
import {
    executeAnswer,
    executeCall,
    executeClearCallHistory,
    executeCompressContactImage,
    executeDeleteContact,
    executeDeleteGreeting,
    executeDeleteRecording,
    executeDeleteRingtone,
    executeDeleteVoicemail,
    executeGenerateGreeting,
    executeHangup,
    executeMarkVoicemailRead,
    executePatchConfig,
    executeSaveContact,
    executeSaveRingtoneName,
    executeSendToVoicemail,
    executeSetPrimaryRingtone,
    executeSetPttActive,
    executeStartRecordingGreetingMic,
    executeStopRecordingGreetingMic,
    executeSwitchAudioProfile,
    executeSwitchCallMode,
    executeToggleMicrophone,
    executeToggleSpeaker,
    executeUploadGreeting,
    executeUploadRingtone,
} from "./callPageActions.js";
import { DEFAULT_CALL_HISTORY_LIMIT, DEFAULT_DISCOVERY_LIMIT } from "./constants.js";
import type { CallPageRuntime } from "./callPageRuntime.js";
import type { RingtoneItem } from "./ringtoneEditorLogic.js";
import type { CallHistoryEntry, Recording, Ringtone, TelephoneConfig, TelephoneContact, Voicemail } from "./types.js";

export function createCallPageHandlers(runtime: CallPageRuntime) {
    const { pageState, controller } = runtime;

    const isHalfDuplexCall = () =>
        Boolean(pageState.activeCall && pageState.activeCall.status === 6 && pageState.activeCall.is_half_duplex);

    const isWebAudioBridgeEnabled = () =>
        Boolean(pageState.webAudioBridgeRequired || pageState.config?.telephone_web_audio_enabled);

    function getContactByHash(hash: string): TelephoneContact | null {
        if (!hash || !Array.isArray(pageState.contacts)) return null;
        return pageState.contacts.find((c) => c.remote_identity_hash === hash) || null;
    }

    async function onUpdateConfig(patch: Partial<TelephoneConfig>): Promise<void> {
        if (!pageState.config) return;
        Object.assign(pageState.config, patch);
        const updated = await executePatchConfig(patch);
        if (updated) pageState.config = updated;
    }

    function onPatchConfig(patch: Partial<TelephoneConfig>): void {
        if (pageState.config) Object.assign(pageState.config, patch);
    }

    async function onCall(destination: string): Promise<void> {
        pageState.initiationStatus = t("call.initiating");
        pageState.initiationTargetHash = destination;
        const res = await executeCall({
            destinationInput: destination,
            contacts: pageState.contacts,
            webAudioBridgeEnabled: isWebAudioBridgeEnabled(),
            onRequestMic: () => controller.webAudio.requestAudioPermission(),
        });
        if (!res.success) {
            pageState.initiationStatus = null;
        } else {
            pageState.destinationHash = res.cleanedHash;
            pageState.initiationTargetName = res.targetName;
            pageState.activeTab = "phone";
        }
    }

    async function onAnswer(): Promise<void> {
        await executeAnswer({
            webAudioBridgeEnabled: isWebAudioBridgeEnabled(),
            onRequestMic: () => controller.webAudio.requestAudioPermission(),
        });
    }

    async function onHangup(): Promise<void> {
        const res = await executeHangup(pageState.activeCall);
        if (res.wasDeclined) pageState.wasDeclined = true;
    }

    async function onSendToVoicemail(): Promise<void> {
        await executeSendToVoicemail();
    }

    async function onToggleMic(): Promise<void> {
        pageState.isMicMuting = true;
        pageState.localMicMuted = await executeToggleMicrophone(pageState.localMicMuted);
        if (pageState.activeCall) pageState.activeCall.is_mic_muted = pageState.localMicMuted;
        setTimeout(() => {
            pageState.isMicMuting = false;
        }, 500);
    }

    async function onToggleSpeaker(): Promise<void> {
        pageState.isSpeakerMuting = true;
        pageState.localSpeakerMuted = await executeToggleSpeaker(pageState.localSpeakerMuted);
        if (pageState.activeCall) pageState.activeCall.is_speaker_muted = pageState.localSpeakerMuted;
        setTimeout(() => {
            pageState.isSpeakerMuting = false;
        }, 500);
    }

    async function onSetPtt(active: boolean): Promise<void> {
        pageState.localPttActive = await executeSetPttActive(active, isHalfDuplexCall());
        if (pageState.activeCall) pageState.activeCall.is_ptt_active = pageState.localPttActive;
    }

    runtime.onPttTrigger = onSetPtt;

    async function onSwitchCallMode(modeId: number | string): Promise<void> {
        const res = await executeSwitchCallMode(modeId);
        if (res.modeId != null) {
            pageState.selectedCallModeId = res.modeId;
            pageState.localPttActive = Boolean(res.isPttActive);
            if (pageState.activeCall) {
                pageState.activeCall.call_mode_id = Number(res.modeId);
                pageState.activeCall.is_half_duplex = Boolean(res.isHalfDuplex);
                pageState.activeCall.is_ptt_active = pageState.localPttActive;
            }
            if (pageState.config) pageState.config.telephone_call_mode_id = Number(res.modeId);
        }
    }

    async function onSwitchAudioProfile(profileId: number | string): Promise<void> {
        const res = await executeSwitchAudioProfile(profileId);
        if (res != null) pageState.selectedAudioProfileId = res;
    }

    async function onToggleWebAudio(newVal: boolean): Promise<void> {
        if (!pageState.config || (pageState.webAudioBridgeRequired && !newVal)) return;
        const prev = pageState.config.telephone_web_audio_enabled;
        pageState.config.telephone_web_audio_enabled = newVal;
        try {
            if (newVal) {
                const ok = await controller.webAudio.requestAudioPermission();
                if (!ok) {
                    pageState.config.telephone_web_audio_enabled = false;
                    await onUpdateConfig({ telephone_web_audio_enabled: false });
                    return;
                }
            }
            await onUpdateConfig({ telephone_web_audio_enabled: newVal });
            if (newVal && pageState.activeCall) await controller.webAudio.start();
            else if (!newVal) controller.webAudio.stop();
        } catch {
            pageState.config.telephone_web_audio_enabled = prev;
        }
    }

    async function onRestartWebAudio(): Promise<void> {
        controller.webAudio.webAudioStartBlocked = false;
        controller.webAudio.stop();
        await controller.webAudio.start();
    }

    function onPhonebookCall(dest: string): void {
        pageState.destinationHash = dest;
        pageState.activeTab = "phone";
        onCall(dest);
    }

    function openAddContactModal(): void {
        pageState.editingContact = null;
        pageState.contactForm = {
            name: "",
            remote_identity_hash: "",
            lxmf_address: "",
            lxst_address: "",
            preferred_ringtone_id: null,
            custom_image: null,
        };
        pageState.isContactModalOpen = true;
    }

    function openEditContactModal(contact: TelephoneContact): void {
        pageState.editingContact = contact;
        pageState.contactForm = {
            id: contact.id,
            name: contact.name,
            remote_identity_hash: contact.remote_identity_hash,
            lxmf_address: contact.lxmf_address || "",
            lxst_address: contact.lxst_address || "",
            preferred_ringtone_id: contact.preferred_ringtone_id,
            custom_image: contact.custom_image,
        };
        pageState.isContactModalOpen = true;
    }

    function openAddContactFromHistory(entry: CallHistoryEntry): void {
        pageState.editingContact = null;
        pageState.contactForm = {
            name: entry.remote_identity_name || "",
            remote_identity_hash: entry.remote_identity_hash || "",
            lxmf_address: entry.remote_destination_hash || "",
            lxst_address: entry.remote_telephony_hash || "",
            preferred_ringtone_id: null,
            custom_image: null,
        };
        pageState.isContactModalOpen = true;
    }

    async function onSaveContact(): Promise<void> {
        if (await executeSaveContact(pageState.contactForm, pageState.editingContact)) {
            pageState.isContactModalOpen = false;
            runtime.getContacts();
        }
    }

    async function onDeleteContact(id: number | string): Promise<void> {
        if (await executeDeleteContact(id)) runtime.getContacts();
    }

    function onContactImageSelected(e: Event): void {
        const file = (e.target as HTMLInputElement).files?.[0];
        if (!file) return;
        executeCompressContactImage(file, (dataUrl) => {
            pageState.contactForm.custom_image = dataUrl;
        });
        (e.target as HTMLInputElement).value = "";
    }

    function onHistorySearch(q: string): void {
        pageState.callHistorySearch = q;
        runtime.debounceSearch(() => runtime.getHistory());
    }

    function loadMoreHistory(): void {
        pageState.callHistoryOffset += DEFAULT_CALL_HISTORY_LIMIT;
        runtime.getHistory(true);
    }

    async function onClearHistory(): Promise<void> {
        await executeClearCallHistory();
        runtime.getHistory();
    }

    function onVoicemailSearch(q: string): void {
        pageState.voicemailSearch = q;
        runtime.debounceSearch(() => runtime.getVoicemails());
    }

    async function onVoicemailSaveAndGenerate(): Promise<void> {
        if (!pageState.config) return;
        await onUpdateConfig({ voicemail_greeting: pageState.config.voicemail_greeting });
        pageState.isGeneratingGreeting = true;
        await executeGenerateGreeting();
        pageState.isGeneratingGreeting = false;
        runtime.getVoicemailStatus();
    }

    async function onUploadGreeting(e: Event): Promise<void> {
        const file = (e.target as HTMLInputElement).files?.[0];
        if (!file) return;
        pageState.isUploadingGreeting = true;
        await executeUploadGreeting(file);
        pageState.isUploadingGreeting = false;
        (e.target as HTMLInputElement).value = "";
        runtime.getVoicemailStatus();
    }

    async function onDeleteGreeting(): Promise<void> {
        if (await executeDeleteGreeting()) runtime.getVoicemailStatus();
    }

    async function onStartRecordingGreeting(): Promise<void> {
        await executeStartRecordingGreetingMic();
        runtime.getVoicemailStatus();
    }

    async function onStopRecordingGreeting(): Promise<void> {
        await executeStopRecordingGreetingMic();
        runtime.getVoicemailStatus();
    }

    async function onMarkVoicemailRead(vm: Voicemail): Promise<void> {
        if (await executeMarkVoicemailRead(vm)) {
            pageState.unreadVoicemailsCount = Math.max(0, pageState.unreadVoicemailsCount - 1);
        }
    }

    async function onDeleteVoicemail(id: number | string): Promise<void> {
        if (await executeDeleteVoicemail(id)) runtime.getVoicemails();
    }

    function onContactsSearch(q: string): void {
        pageState.contactsSearch = q;
        runtime.debounceSearch(() => runtime.getContacts());
    }

    function onDiscoverySearch(q: string): void {
        pageState.discoverySearch = q;
        runtime.debounceSearch(() => runtime.getDiscovery());
    }

    function loadMoreDiscovery(): void {
        pageState.discoveryOffset += DEFAULT_DISCOVERY_LIMIT;
        runtime.getDiscovery(true);
    }

    function onRecordingSearch(q: string): void {
        pageState.recordingSearch = q;
        runtime.debounceSearch(() => runtime.getRecordings());
    }

    async function onPlayRecording(r: Recording, side: "rx" | "tx"): Promise<void> {
        await controller.audioPlayer.playRecording(r, side);
    }

    async function onDeleteRecording(id: number | string): Promise<void> {
        if (await executeDeleteRecording(id)) runtime.getRecordings();
    }

    async function onUploadRingtone(e: Event, file?: File): Promise<void> {
        const f = file || (e.target as HTMLInputElement).files?.[0];
        if (!f) return;
        pageState.isUploadingRingtone = true;
        await executeUploadRingtone(f);
        pageState.isUploadingRingtone = false;
        if (e.target) (e.target as HTMLInputElement).value = "";
        runtime.getRingtones();
        runtime.getRingtoneStatus();
    }

    function startEditingRingtone(rt: Ringtone | RingtoneItem): void {
        pageState.editingRingtoneId = rt.id;
        pageState.editingRingtoneName = rt.display_name || rt.filename;
    }

    async function saveRingtoneName(id?: number | string, name?: string): Promise<void> {
        const targetId = id ?? pageState.editingRingtoneId;
        const targetName = name ?? pageState.editingRingtoneName;
        if (targetId == null) return;
        await executeSaveRingtoneName(targetId, targetName);
        pageState.editingRingtoneId = null;
        runtime.getRingtones();
    }

    async function onSetPrimaryRingtone(rt: Ringtone | RingtoneItem): Promise<void> {
        await executeSetPrimaryRingtone(rt.id);
        runtime.getRingtones();
        runtime.getRingtoneStatus();
    }

    async function onDeleteRingtone(rt: Ringtone | RingtoneItem): Promise<void> {
        if (await executeDeleteRingtone(rt.id)) {
            runtime.getRingtones();
            runtime.getRingtoneStatus();
        }
    }

    function openRingtoneEditor(rt: Ringtone | RingtoneItem): void {
        pageState.editingRingtoneForAudio = rt;
        pageState.isRingtoneEditorOpen = true;
    }

    function onRingtoneSaved(): void {
        runtime.getRingtones();
        runtime.getRingtoneStatus();
    }

    function openMessageFromHistory(entry: CallHistoryEntry): void {
        const target = entry.remote_destination_hash || entry.remote_identity_hash;
        if (target && typeof window !== "undefined") window.location.hash = `#/messages/${target}`;
    }

    function onPlayLatestVoicemail(): void {
        if (pageState.voicemails.length > 0) onMarkVoicemailRead(pageState.voicemails[0]);
    }

    return {
        getContactByHash,
        isHalfDuplexCall,
        isWebAudioBridgeEnabled,
        loadMoreDiscovery,
        loadMoreHistory,
        onAnswer,
        onCall,
        onClearHistory,
        onContactImageSelected,
        onContactsSearch,
        onDeleteContact,
        onDeleteGreeting,
        onDeleteRecording,
        onDeleteRingtone,
        onDeleteVoicemail,
        onDiscoverySearch,
        onHangup,
        onHistorySearch,
        onMarkVoicemailRead,
        onPatchConfig,
        onPhonebookCall,
        onPlayLatestVoicemail,
        onPlayRecording,
        onRecordingSearch,
        onRestartWebAudio,
        onRingtoneSaved,
        onSaveContact,
        onSendToVoicemail,
        onSetPrimaryRingtone,
        onSetPtt,
        onStartRecordingGreeting,
        onStopRecordingGreeting,
        onSwitchAudioProfile,
        onSwitchCallMode,
        onToggleMic,
        onToggleSpeaker,
        onToggleWebAudio,
        onUpdateConfig,
        onUploadGreeting,
        onUploadRingtone,
        onVoicemailSaveAndGenerate,
        onVoicemailSearch,
        openAddContactFromHistory,
        openAddContactModal,
        openEditContactModal,
        openMessageFromHistory,
        openRingtoneEditor,
        saveRingtoneName,
        startEditingRingtone,
    };
}
