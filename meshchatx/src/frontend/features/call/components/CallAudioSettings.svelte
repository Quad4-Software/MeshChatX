<!-- SPDX-License-Identifier: 0BSD -->

<script lang="ts">
    import { t } from "../../../js/i18n.js";

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

    interface ConfigObject {
        telephone_enabled?: boolean;
        do_not_disturb_enabled?: boolean;
        telephone_allow_calls_from_contacts_only?: boolean;
        telephone_announce_enabled?: boolean;
        telephone_audio_profile_id?: number | string;
        telephone_call_mode_id?: number | string;
        [key: string]: unknown;
    }

    interface Props {
        config?: ConfigObject | null;
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
        ontogglednd?: (enabled: boolean) => void;
        ontogglecontactsonly?: (enabled: boolean) => void;
        ontoggletelephoneannounce?: (enabled: boolean) => void;
        ontogglewebaudio?: (enabled: boolean) => void;
        onchangeaudioprofile?: (profileId: number | string) => void;
        onchangecallmode?: (modeId: number | string) => void;
        onselectaudioinput?: (deviceId: string) => void;
        onselectaudiooutput?: (deviceId: string) => void;
        onrefreshaudiodevices?: () => void;
        onrestartwebaudio?: () => void;
    }

    let {
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
</script>

{#snippet toggleRow(
    id: string,
    checked: boolean,
    label: string,
    disabled: boolean,
    onchange?: (checked: boolean) => void
)}
    <label
        for={id}
        class="relative inline-flex w-auto shrink-0 items-center gap-3 {disabled
            ? 'opacity-50 cursor-not-allowed'
            : 'cursor-pointer'}"
    >
        <input
            {id}
            type="checkbox"
            {checked}
            {disabled}
            class="sr-only peer"
            onchange={(e) => onchange?.((e.target as HTMLInputElement).checked)}
        />
        <div
            class="relative h-6 w-11 shrink-0 bg-sem-surface-muted peer-focus:outline-hidden peer-focus:ring-4 peer-focus:ring-sem-accent/30 rounded-full peer peer-checked:after:translate-x-full peer-checked:after:border-white after:content-[''] after:absolute after:top-[2px] after:left-[2px] after:bg-white after:border-sem-border after:border after:rounded-full after:h-5 after:w-5 after:transition-all peer-checked:bg-sem-accent"
        ></div>
        {#if label}
            <span class="min-w-0 text-sm font-medium leading-snug text-sem-fg">{label}</span>
        {/if}
    </label>
{/snippet}

<div class="pt-2 flex flex-col items-stretch gap-4 lg:flex-row lg:items-start lg:justify-between">
    <div class="flex min-w-0 flex-1 flex-col gap-2">
        {#if config?.telephone_enabled}
            <div class="flex flex-col gap-2">
                {@render toggleRow(
                    "dnd-toggle",
                    Boolean(config?.do_not_disturb_enabled),
                    t("call.do_not_disturb"),
                    false,
                    ontogglednd
                )}

                {@render toggleRow(
                    "contacts-only-toggle",
                    Boolean(config?.telephone_allow_calls_from_contacts_only),
                    t("call.allow_calls_from_contacts_only"),
                    false,
                    ontogglecontactsonly
                )}

                {@render toggleRow(
                    "telephone-announce-toggle",
                    Boolean(config?.telephone_announce_enabled),
                    t("call.announce_telephone_presence"),
                    false,
                    ontoggletelephoneannounce
                )}

                <div class="flex flex-col gap-1">
                    {@render toggleRow(
                        "web-audio-toggle",
                        webAudioBridgeEnabled,
                        isAndroid ? t("call.native_audio_bridge") : t("call.web_audio_bridge"),
                        webAudioBridgeRequired,
                        ontogglewebaudio
                    )}
                    <div class="text-xs text-sem-fg-muted px-1">
                        {#if isAndroid}
                            {t("call.android_audio_bridge_description")}
                        {:else if webAudioBridgeRequired}
                            {t("call.web_audio_bridge_required_description")}
                        {:else}
                            {t("call.web_audio_bridge_description")}
                        {/if}
                    </div>
                </div>
            </div>
        {/if}
    </div>

    <div class="flex w-full shrink-0 flex-col gap-2 lg:w-auto">
        <div class="flex flex-col gap-1">
            <label
                for="telephone-audio-profile-select"
                class="text-[10px] font-bold text-sem-fg-muted uppercase tracking-widest px-1"
            >
                {t("call.default_quality")}
            </label>
            <select
                id="telephone-audio-profile-select"
                value={config?.telephone_audio_profile_id ?? ""}
                class="input-field min-w-0 rounded-lg! border-sem-border! py-1! px-2! text-xs! lg:min-w-[120px]"
                onchange={(e) => onchangeaudioprofile?.((e.target as HTMLSelectElement).value)}
            >
                {#each audioProfiles as audioProfile (audioProfile.id)}
                    <option value={audioProfile.id}>{audioProfile.name}</option>
                {/each}
            </select>
        </div>

        <div class="flex flex-col gap-1">
            <label
                for="telephone-call-mode-select"
                class="text-[10px] font-bold text-sem-fg-muted uppercase tracking-widest px-1"
            >
                {t("call.default_duplex")}
            </label>
            <select
                id="telephone-call-mode-select"
                value={config?.telephone_call_mode_id ?? ""}
                class="input-field min-w-0 rounded-lg! border-sem-border! py-1! px-2! text-xs! lg:min-w-[120px]"
                onchange={(e) => onchangecallmode?.((e.target as HTMLSelectElement).value)}
            >
                {#each callModes as callMode (callMode.id)}
                    <option value={callMode.id}>{callMode.name}</option>
                {/each}
            </select>
        </div>

        {#if showWebAudioDeviceSelector}
            <div class="flex flex-col gap-2 mt-2">
                <div class="flex flex-col gap-1">
                    <label
                        for="telephone-mic-select"
                        class="text-[10px] font-bold text-sem-fg-muted uppercase tracking-widest px-1"
                    >
                        {t("call.microphone")}
                    </label>
                    <select
                        id="telephone-mic-select"
                        value={selectedAudioInputId}
                        class="input-field py-1! px-2! text-[10px]! rounded-lg! border-sem-border! min-w-[120px]"
                        onchange={(e) => {
                            const val = (e.target as HTMLSelectElement).value;
                            onselectaudioinput?.(val);
                            onrestartwebaudio?.();
                        }}
                    >
                        {#each audioInputDevices as d, idx (d.deviceId || `in-${idx}`)}
                            <option value={d.deviceId}>{d.label || t("call.microphone")}</option>
                        {/each}
                    </select>
                </div>

                <div class="flex flex-col gap-1">
                    <label
                        for="telephone-speaker-select"
                        class="text-[10px] font-bold text-sem-fg-muted uppercase tracking-widest px-1"
                    >
                        {t("call.speaker")}
                    </label>
                    <select
                        id="telephone-speaker-select"
                        value={selectedAudioOutputId}
                        class="input-field py-1! px-2! text-[10px]! rounded-lg! border-sem-border! min-w-[120px]"
                        onchange={(e) => {
                            const val = (e.target as HTMLSelectElement).value;
                            onselectaudiooutput?.(val);
                            onrestartwebaudio?.();
                        }}
                    >
                        {#each audioOutputDevices as d, idx (d.deviceId || `out-${idx}`)}
                            <option value={d.deviceId}>{d.label || t("call.speaker")}</option>
                        {/each}
                    </select>
                </div>

                <button
                    type="button"
                    class="text-[10px] bg-sem-surface-muted text-sem-fg-muted py-1.5 px-3 rounded-lg font-bold uppercase tracking-wider hover:bg-sem-surface-subtle hover:text-sem-fg transition-colors focus-ring-sem cursor-pointer"
                    onclick={() => onrefreshaudiodevices?.()}
                >
                    {t("call.refresh_devices")}
                </button>
            </div>
        {/if}
    </div>
</div>
