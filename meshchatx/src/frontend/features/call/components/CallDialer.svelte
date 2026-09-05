<!-- SPDX-License-Identifier: 0BSD -->

<script lang="ts">
    import MaterialDesignIcon from "../../../ui/svelte/MaterialDesignIcon.svelte";
    import { t } from "../../../js/i18n.js";
    import { buildCallSuggestions } from "../lib/callHistory.js";
    import type { CallHistoryEntry, TelephoneContact } from "../lib/types.js";
    import CallAudioSettings from "./CallAudioSettings.svelte";

    interface AudioProfile {
        id: number | string;
        name: string;
    }

    interface CallMode {
        id: number | string;
        name: string;
    }

    interface AudioDevice {
        deviceId: string;
        label?: string;
    }

    interface Props {
        destinationHash?: string;
        contacts?: TelephoneContact[];
        callHistory?: CallHistoryEntry[];
        config?: Record<string, unknown> | null;
        webAudioBridgeEnabled?: boolean;
        webAudioBridgeRequired?: boolean;
        showWebAudioDeviceSelector?: boolean;
        selectedAudioInputId?: string;
        selectedAudioOutputId?: string;
        audioInputDevices?: AudioDevice[];
        audioOutputDevices?: AudioDevice[];
        audioProfiles?: AudioProfile[];
        callModes?: CallMode[];
        isAndroid?: boolean;
        formatDestinationHash?: (hash?: string) => string;
        ondestinationchange?: (value: string) => void;
        oncall?: (hash: string) => void;
        oncopyhash?: (hash: string) => void;
        ontogglednd?: (val: boolean) => void;
        ontogglecontactsonly?: (val: boolean) => void;
        ontoggletelephoneannounce?: (val: boolean) => void;
        ontogglewebaudio?: (val: boolean) => void;
        onchangeaudioprofile?: (profileId: number | string) => void;
        onchangecallmode?: (modeId: number | string) => void;
        onselectaudioinput?: (id: string) => void;
        onselectaudiooutput?: (id: string) => void;
        onrefreshaudiodevices?: () => void;
        onrestartwebaudio?: () => void;
    }

    let {
        destinationHash = "",
        contacts = [],
        callHistory = [],
        config = null,
        webAudioBridgeEnabled = false,
        webAudioBridgeRequired = false,
        showWebAudioDeviceSelector = false,
        selectedAudioInputId = "",
        selectedAudioOutputId = "",
        audioInputDevices = [],
        audioOutputDevices = [],
        audioProfiles = [],
        callModes = [],
        isAndroid = false,
        formatDestinationHash = (h?: string) => h || "",
        ondestinationchange,
        oncall,
        oncopyhash: _oncopyhash,
        ontogglednd,
        ontogglecontactsonly,
        ontoggletelephoneannounce,
        ontogglewebaudio,
        onchangeaudioprofile,
        onchangecallmode,
        onselectaudioinput,
        onselectaudiooutput,
        onrefreshaudiodevices,
        onrestartwebaudio,
    }: Props = $props();

    let isCallInputFocused = $state(false);
    let selectedSuggestionIndex = $state(-1);

    const newCallSuggestions = $derived(
        buildCallSuggestions({
            search: destinationHash,
            contacts,
            callHistory,
            isFocused: isCallInputFocused,
        })
    );

    function setDestination(value: string) {
        ondestinationchange?.(value);
    }

    function handleCallInputUp() {
        if (newCallSuggestions.length === 0) return;
        selectedSuggestionIndex =
            selectedSuggestionIndex > 0 ? selectedSuggestionIndex - 1 : newCallSuggestions.length - 1;
    }

    function handleCallInputDown() {
        if (newCallSuggestions.length === 0) return;
        selectedSuggestionIndex =
            selectedSuggestionIndex < newCallSuggestions.length - 1 ? selectedSuggestionIndex + 1 : 0;
    }

    function selectSuggestion(suggestion: { hash: string }) {
        setDestination(suggestion.hash);
        isCallInputFocused = false;
        selectedSuggestionIndex = -1;
        oncall?.(suggestion.hash);
    }

    function handleCallInputEnter() {
        if (selectedSuggestionIndex >= 0 && selectedSuggestionIndex < newCallSuggestions.length) {
            selectSuggestion(newCallSuggestions[selectedSuggestionIndex]);
        } else {
            oncall?.(destinationHash);
        }
    }

    function onCallInputBlur() {
        setTimeout(() => {
            isCallInputFocused = false;
            selectedSuggestionIndex = -1;
        }, 200);
    }
</script>

<div class="w-full border-b border-sem-border py-2">
    <div class="flex items-center gap-3 mb-6">
        <div class="bg-sem-accent-subtle p-2.5 rounded-2xl">
            <MaterialDesignIcon iconName="phone-plus" class="size-6 text-sem-accent" />
        </div>
        <div>
            <h2 class="text-lg font-bold text-sem-fg leading-tight">{t("call.new_call")}</h2>
            <p class="text-xs text-sem-fg-muted">{t("call.enter_identity_hash_to_call")}</p>
        </div>
    </div>

    <div class="space-y-4">
        <div class="relative">
            <div class="flex gap-2">
                <div class="relative flex-1">
                    <input
                        value={destinationHash}
                        type="text"
                        role="combobox"
                        aria-autocomplete="list"
                        aria-expanded={isCallInputFocused && newCallSuggestions.length > 0}
                        aria-controls="call-dialer-suggestions"
                        aria-activedescendant={selectedSuggestionIndex >= 0
                            ? `call-dialer-opt-${selectedSuggestionIndex}`
                            : undefined}
                        placeholder={t("call.identity_or_name")}
                        class="input-field"
                        oninput={(e) => setDestination((e.currentTarget as HTMLInputElement).value)}
                        onkeydown={(e) => {
                            if (e.key === "Enter") {
                                e.preventDefault();
                                handleCallInputEnter();
                            } else if (e.key === "ArrowUp") {
                                e.preventDefault();
                                handleCallInputUp();
                            } else if (e.key === "ArrowDown") {
                                e.preventDefault();
                                handleCallInputDown();
                            } else if (e.key === "Escape") {
                                isCallInputFocused = false;
                                selectedSuggestionIndex = -1;
                            }
                        }}
                        onfocus={() => (isCallInputFocused = true)}
                        onblur={onCallInputBlur}
                    />
                    {#if isCallInputFocused && newCallSuggestions.length > 0}
                        <div
                            id="call-dialer-suggestions"
                            role="listbox"
                            aria-label={t("call.suggestions")}
                            class="absolute z-50 left-0 right-0 mt-1 bg-sem-surface border border-sem-border rounded-xl shadow-xl overflow-hidden"
                        >
                            {#each newCallSuggestions as suggestion, index (suggestion.hash)}
                                <button
                                    type="button"
                                    role="option"
                                    id={`call-dialer-opt-${index}`}
                                    aria-selected={index === selectedSuggestionIndex}
                                    class="w-full text-left px-4 py-2.5 flex items-center gap-3 cursor-pointer transition-colors focus-ring-sem {index ===
                                    selectedSuggestionIndex
                                        ? 'bg-sem-accent-subtle text-sem-accent'
                                        : 'hover:bg-sem-surface-muted/50 text-sem-fg-muted'}"
                                    onmousedown={(e) => {
                                        e.preventDefault();
                                        selectSuggestion(suggestion);
                                    }}
                                >
                                    <div
                                        class="shrink-0 size-8 rounded-full flex items-center justify-center text-xs {suggestion.type ===
                                        'contact'
                                            ? 'bg-sem-accent-subtle text-sem-accent'
                                            : 'bg-sem-surface-muted text-sem-fg-muted'}"
                                    >
                                        <MaterialDesignIcon iconName={suggestion.icon} class="size-4" />
                                    </div>
                                    <div class="flex-1 min-w-0">
                                        <div class="text-sm font-bold truncate">{suggestion.name}</div>
                                        <span
                                            class="text-[10px] font-mono opacity-50 truncate block text-left"
                                            title={suggestion.hash}
                                        >
                                            {formatDestinationHash(suggestion.hash)}
                                        </span>
                                    </div>
                                    {#if suggestion.type === "contact"}
                                        <div class="text-[10px] uppercase font-bold tracking-widest opacity-30">
                                            {t("call.contact")}
                                        </div>
                                    {/if}
                                </button>
                            {/each}
                        </div>
                    {/if}
                </div>
                <button
                    type="button"
                    class="primary-chip px-6! rounded-2xl! focus-ring-sem cursor-pointer flex items-center gap-2"
                    onclick={() => oncall?.(destinationHash)}
                >
                    <MaterialDesignIcon iconName="phone" class="size-5" />
                    {t("call.call_action")}
                </button>
            </div>
        </div>

        <CallAudioSettings
            {config}
            {webAudioBridgeEnabled}
            {webAudioBridgeRequired}
            {showWebAudioDeviceSelector}
            {selectedAudioInputId}
            {selectedAudioOutputId}
            {audioInputDevices}
            {audioOutputDevices}
            {audioProfiles}
            {callModes}
            {isAndroid}
            {ontogglednd}
            {ontogglecontactsonly}
            {ontoggletelephoneannounce}
            {ontogglewebaudio}
            {onchangeaudioprofile}
            {onchangecallmode}
            {onselectaudioinput}
            {onselectaudiooutput}
            {onrefreshaudiodevices}
            {onrestartwebaudio}
        />
    </div>
</div>
