<!-- SPDX-License-Identifier: 0BSD -->

<script lang="ts">
    import { fade } from "svelte/transition";
    import MaterialDesignIcon from "../../../ui/svelte/MaterialDesignIcon.svelte";
    import { t } from "../../../js/i18n.js";
    import RingtoneEditor from "./RingtoneEditor.svelte";
    import CallRingtoneList from "./CallRingtoneList.svelte";
    import type { CallRingtoneTabProps } from "../lib/callRingtoneTabUi.js";

    let {
        active = true,
        config = null,
        ringtones = [],
        ringtoneStatus: _ringtoneStatus = {},
        isRingtoneEditorOpen = false,
        editingRingtoneForAudio = null,
        isUploadingRingtone = false,
        isPlayingRingtone = false,
        playingRingtoneId = null,
        editingRingtoneId = null,
        editingRingtoneName = "",
        formatDestinationHash: _formatDestinationHash,
        onupdateconfig,
        onopeneditor,
        oncloseeditor,
        onringtonesaved,
        onupload,
        onplay,
        ondelete,
        onsetdefault,
        onsetprimary,
        onrename,
        onstartrename,
        onrenameinput,
        oncopy: _oncopy,
    }: CallRingtoneTabProps = $props();

    const transitionDuration = $derived(
        typeof window !== "undefined" && window.matchMedia("(prefers-reduced-motion: reduce)").matches ? 0 : 120
    );
</script>

{#if active && config}
    <div class="flex-1 space-y-6 max-w-3xl mx-auto w-full pt-2" transition:fade={{ duration: transitionDuration }}>
        <div class="w-full border-b border-sem-border py-6">
            {#if isRingtoneEditorOpen && editingRingtoneForAudio}
                <RingtoneEditor
                    ringtone={editingRingtoneForAudio}
                    onclose={() => oncloseeditor?.()}
                    onsaved={() => onringtonesaved?.()}
                />
            {:else}
                <h3 class="text-sm font-bold text-sem-fg uppercase tracking-wider mb-6 flex items-center gap-2">
                    <MaterialDesignIcon iconName="music" class="size-5 text-sem-accent" />
                    {t("call.ringtone_settings")}
                </h3>

                <div class="space-y-6">
                    <!-- Enabled Toggle and Volume -->
                    <div class="flex flex-col lg:flex-row lg:items-center justify-between gap-6">
                        <div class="flex-1">
                            <div class="flex items-center justify-between mb-1">
                                <div class="text-sm font-semibold text-sem-fg">
                                    {t("call.enable_custom_ringtone")}
                                </div>
                                <button
                                    type="button"
                                    role="switch"
                                    aria-label={t("call.enable_custom_ringtone")}
                                    aria-checked={Boolean(config.custom_ringtone_enabled)}
                                    class="relative inline-flex h-6 w-11 shrink-0 cursor-pointer rounded-full border-2 border-transparent transition-colors duration-200 ease-in-out focus-ring-sem {config.custom_ringtone_enabled
                                        ? 'bg-sem-accent'
                                        : 'bg-sem-surface-muted'}"
                                    onclick={() =>
                                        onupdateconfig?.({ custom_ringtone_enabled: !config.custom_ringtone_enabled })}
                                >
                                    <span
                                        class="pointer-events-none inline-block h-5 w-5 transform rounded-full bg-white shadow-xs ring-0 transition duration-200 ease-in-out {config.custom_ringtone_enabled
                                            ? 'translate-x-5'
                                            : 'translate-x-0'}"
                                    ></span>
                                </button>
                            </div>
                            <div class="text-xs text-sem-fg-muted">
                                {t("call.enable_custom_ringtone_description")}
                            </div>
                        </div>

                        <div class="flex-1 md:max-w-xs">
                            <div class="flex items-center justify-between mb-2">
                                <label
                                    for="call-ringtone-volume-slider"
                                    class="text-xs font-bold text-sem-fg-muted uppercase tracking-wider"
                                >
                                    {t("call.ringtone_volume")}
                                </label>
                                <span class="text-xs font-mono text-sem-fg-muted">
                                    {config.ringtone_volume ?? 0}%
                                </span>
                            </div>
                            <input
                                id="call-ringtone-volume-slider"
                                value={config.ringtone_volume ?? 0}
                                type="range"
                                min="0"
                                max="100"
                                class="w-full h-1.5 bg-sem-surface-muted rounded-lg appearance-none cursor-pointer accent-sem-accent"
                                onchange={(e) =>
                                    onupdateconfig?.({ ringtone_volume: Number((e.target as HTMLInputElement).value) })}
                            />
                        </div>
                    </div>

                    <!-- Tone Generator Settings -->
                    <div
                        class="flex flex-col lg:flex-row lg:items-center justify-between gap-6 pt-4 border-t border-sem-border/50"
                    >
                        <div class="flex-1">
                            <div class="flex items-center justify-between mb-1">
                                <div class="text-sm font-semibold text-sem-fg">{t("call.tone_generator")}</div>
                                <button
                                    type="button"
                                    role="switch"
                                    aria-label={t("call.tone_generator")}
                                    aria-checked={Boolean(config.telephone_tone_generator_enabled)}
                                    class="relative inline-flex h-6 w-11 shrink-0 cursor-pointer rounded-full border-2 border-transparent transition-colors duration-200 ease-in-out focus-ring-sem {config.telephone_tone_generator_enabled
                                        ? 'bg-sem-accent'
                                        : 'bg-sem-surface-muted'}"
                                    onclick={() =>
                                        onupdateconfig?.({
                                            telephone_tone_generator_enabled: !config.telephone_tone_generator_enabled,
                                        })}
                                >
                                    <span
                                        class="pointer-events-none inline-block h-5 w-5 transform rounded-full bg-white shadow-xs ring-0 transition duration-200 ease-in-out {config.telephone_tone_generator_enabled
                                            ? 'translate-x-5'
                                            : 'translate-x-0'}"
                                    ></span>
                                </button>
                            </div>
                            <div class="text-xs text-sem-fg-muted">
                                {t("call.tone_generator_description")}
                            </div>
                        </div>

                        {#if config.telephone_tone_generator_enabled}
                            <div class="flex-1 md:max-w-xs">
                                <div class="flex items-center justify-between mb-2">
                                    <label
                                        for="call-tone-generator-volume-slider"
                                        class="text-xs font-bold text-sem-fg-muted uppercase tracking-wider"
                                    >
                                        {t("call.tone_volume")}
                                    </label>
                                    <span class="text-xs font-mono text-sem-fg-muted">
                                        {config.telephone_tone_generator_volume ?? 0}%
                                    </span>
                                </div>
                                <input
                                    id="call-tone-generator-volume-slider"
                                    value={config.telephone_tone_generator_volume ?? 0}
                                    type="range"
                                    min="0"
                                    max="100"
                                    class="w-full h-1.5 bg-sem-surface-muted rounded-lg appearance-none cursor-pointer accent-sem-accent"
                                    onchange={(e) =>
                                        onupdateconfig?.({
                                            telephone_tone_generator_volume: Number(
                                                (e.target as HTMLInputElement).value
                                            ),
                                        })}
                                />
                            </div>
                        {/if}
                    </div>

                    <!-- Preferred Ringtone for Non Contacts -->
                    <div class="p-4 rounded-xl bg-sem-surface-muted/40 border border-sem-border">
                        <div class="flex flex-col lg:flex-row lg:items-center justify-between gap-4">
                            <div>
                                <label
                                    for="call-preferred-ringtone-select"
                                    class="text-sm font-semibold text-sem-fg block"
                                >
                                    {t("call.default_ringtone")}
                                </label>
                                <div class="text-xs text-sem-fg-muted">
                                    {t("call.ringtone_for_non_contacts")}
                                </div>
                            </div>
                            <select
                                id="call-preferred-ringtone-select"
                                value={config.ringtone_preferred_id ?? 0}
                                class="input-field py-1.5! px-3! text-sm! rounded-xl! min-w-[200px]"
                                onchange={(e) =>
                                    onupdateconfig?.({
                                        ringtone_preferred_id: Number((e.target as HTMLSelectElement).value),
                                    })}
                            >
                                <option value={0}>{t("call.primary_system_default")}</option>
                                <option value={-1}>{t("call.random")}</option>
                                <optgroup label={t("call.uploaded_ringtones")}>
                                    {#each ringtones as rt (rt.id)}
                                        <option value={rt.id}>
                                            {rt.display_name}
                                        </option>
                                    {/each}
                                </optgroup>
                            </select>
                        </div>
                    </div>

                    <CallRingtoneList
                        {ringtones}
                        {isUploadingRingtone}
                        {isPlayingRingtone}
                        {playingRingtoneId}
                        {editingRingtoneId}
                        {editingRingtoneName}
                        {onupload}
                        {onplay}
                        {ondelete}
                        {onsetdefault}
                        {onsetprimary}
                        {onrename}
                        {onstartrename}
                        {onrenameinput}
                        {onopeneditor}
                    />
                </div>
            {/if}
        </div>
    </div>
{/if}
