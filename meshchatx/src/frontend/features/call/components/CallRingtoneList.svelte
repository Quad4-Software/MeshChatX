<!-- SPDX-License-Identifier: 0BSD -->

<script lang="ts">
    import MaterialDesignIcon from "../../../ui/svelte/MaterialDesignIcon.svelte";
    import EmptyState from "../../../ui/svelte/EmptyState.svelte";
    import { t } from "../../../js/i18n.js";
    import { getRingtoneAudioSrc } from "../lib/callRingtoneTabUi.js";
    import type { Ringtone } from "../lib/types.js";
    import type { RingtoneItem } from "../lib/ringtoneEditorLogic.js";

    interface Props {
        ringtones?: (Ringtone | RingtoneItem)[];
        isUploadingRingtone?: boolean;
        isPlayingRingtone?: boolean;
        playingRingtoneId?: number | string | null;
        editingRingtoneId?: number | string | null;
        editingRingtoneName?: string;
        onupload?: (event: Event, file: File) => void;
        onplay?: (ringtone: Ringtone | RingtoneItem) => void;
        ondelete?: (ringtone: Ringtone | RingtoneItem) => void;
        onsetdefault?: (ringtone: Ringtone | RingtoneItem) => void;
        onsetprimary?: (ringtone: Ringtone | RingtoneItem) => void;
        onrename?: (ringtoneId: number | string, newName: string) => void;
        onstartrename?: (ringtone: Ringtone | RingtoneItem) => void;
        onrenameinput?: (val: string) => void;
        onopeneditor?: (ringtone: Ringtone | RingtoneItem) => void;
    }

    let {
        ringtones = [],
        isUploadingRingtone = false,
        isPlayingRingtone = false,
        playingRingtoneId = null,
        editingRingtoneId = null,
        editingRingtoneName = "",
        onupload,
        onplay,
        ondelete,
        onsetdefault,
        onsetprimary,
        onrename,
        onstartrename,
        onrenameinput,
        onopeneditor,
    }: Props = $props();

    let ringtoneUploadInput = $state<HTMLInputElement | undefined>();
    let internalEditingId = $state<number | string | null>(null);
    let internalEditingName = $state<string>("");

    const currentEditingId = $derived(editingRingtoneId ?? internalEditingId);
    const currentEditingName = $derived(
        editingRingtoneId !== null && editingRingtoneId !== undefined ? editingRingtoneName : internalEditingName
    );

    function handleFileUpload(event: Event): void {
        const input = event.target as HTMLInputElement;
        const file = input.files?.[0];
        if (!file) return;
        onupload?.(event, file);
        input.value = "";
    }

    function handleStartRename(ringtone: Ringtone | RingtoneItem): void {
        internalEditingId = ringtone.id;
        internalEditingName = ringtone.display_name ?? "";
        onstartrename?.(ringtone);
    }

    function handleRenameInput(event: Event): void {
        const val = (event.target as HTMLInputElement).value;
        internalEditingName = val;
        onrenameinput?.(val);
    }

    function handleSaveRename(ringtone: Ringtone | RingtoneItem): void {
        const nameToSave = (currentEditingName || ringtone.display_name || "").trim();
        internalEditingId = null;
        internalEditingName = "";
        if (nameToSave) {
            onrename?.(ringtone.id, nameToSave);
        }
    }

    function handleSetPrimary(ringtone: Ringtone | RingtoneItem): void {
        onsetdefault?.(ringtone);
        onsetprimary?.(ringtone);
    }
</script>

<div class="space-y-4">
    <div class="flex items-center justify-between">
        <span class="text-sm font-semibold text-sem-fg-muted">{t("call.my_ringtones")}</span>
        <button
            type="button"
            disabled={isUploadingRingtone}
            class="text-xs font-bold text-sem-accent hover:underline flex items-center gap-1 disabled:opacity-50 cursor-pointer focus-ring-sem rounded-md"
            onclick={() => ringtoneUploadInput?.click()}
        >
            <MaterialDesignIcon iconName="plus" class="size-4" />
            {isUploadingRingtone ? t("call.uploading") : t("call.upload_new")}
        </button>
        <input
            bind:this={ringtoneUploadInput}
            type="file"
            class="hidden"
            accept="audio/*"
            onchange={handleFileUpload}
        />
    </div>

    {#if ringtones.length > 0}
        <div class="grid gap-3">
            {#each ringtones as ringtone (ringtone.id)}
                <div
                    class="group p-4 rounded-xl border border-sem-border bg-sem-surface-muted/30 flex items-center gap-4 transition-all hover:shadow-md overflow-hidden {ringtone.is_primary
                        ? 'ring-2 ring-sem-accent/30 bg-sem-accent-subtle/20'
                        : ''}"
                >
                    <div class="flex-1 min-w-0 overflow-hidden">
                        {#if currentEditingId === ringtone.id}
                            <div class="flex items-center gap-2">
                                <input
                                    value={currentEditingName}
                                    class="text-sm input-field py-1 px-2 flex-1 min-w-0"
                                    oninput={handleRenameInput}
                                    onkeydown={(e) => {
                                        if (e.key === "Enter") handleSaveRename(ringtone);
                                    }}
                                    onblur={() => handleSaveRename(ringtone)}
                                />
                            </div>
                        {:else}
                            <div class="flex items-center gap-2 min-w-0">
                                <span class="text-sm font-medium text-sem-fg truncate" title={ringtone.display_name}>
                                    {ringtone.display_name}
                                </span>
                                {#if ringtone.is_primary}
                                    <span
                                        class="shrink-0 text-[10px] uppercase font-bold text-sem-accent bg-sem-accent-subtle px-1.5 py-0.5 rounded-sm"
                                    >
                                        {t("call.primary")}
                                    </span>
                                {/if}
                                <button
                                    type="button"
                                    class="shrink-0 opacity-0 group-hover:opacity-100 p-1 text-sem-fg-muted hover:text-sem-accent transition-opacity focus-ring-sem rounded-md cursor-pointer"
                                    title={t("common.edit")}
                                    onclick={() => handleStartRename(ringtone)}
                                >
                                    <MaterialDesignIcon iconName="pencil" class="size-3" />
                                </button>
                            </div>
                            <div class="text-[10px] text-sem-fg-muted truncate" title={ringtone.filename}>
                                {ringtone.filename}
                            </div>
                        {/if}
                    </div>

                    <div class="flex items-center gap-1">
                        <a
                            href={getRingtoneAudioSrc(ringtone.id, true)}
                            class="p-2 rounded-lg hover:bg-sem-surface-muted text-sem-fg-muted hover:text-sem-accent transition-colors focus-ring-sem"
                            title={t("call.download")}
                        >
                            <MaterialDesignIcon iconName="download" class="size-5" />
                        </a>
                        <button
                            type="button"
                            class="p-2 rounded-lg hover:bg-sem-surface-muted text-sem-fg-muted hover:text-sem-accent transition-colors focus-ring-sem cursor-pointer"
                            title={isPlayingRingtone && playingRingtoneId === ringtone.id
                                ? t("call.stop")
                                : t("call.preview")}
                            onclick={() => onplay?.(ringtone)}
                        >
                            <MaterialDesignIcon
                                iconName={isPlayingRingtone && playingRingtoneId === ringtone.id ? "stop" : "play"}
                                class="size-5"
                            />
                        </button>
                        <button
                            type="button"
                            class="p-2 rounded-lg hover:bg-sem-surface-muted text-sem-fg-muted hover:text-sem-accent transition-colors focus-ring-sem cursor-pointer"
                            title={t("call.edit_audio")}
                            onclick={() => onopeneditor?.(ringtone)}
                        >
                            <MaterialDesignIcon iconName="content-cut" class="size-5" />
                        </button>
                        {#if !ringtone.is_primary}
                            <button
                                type="button"
                                class="p-2 rounded-lg hover:bg-sem-surface-muted text-sem-fg-muted hover:text-sem-accent transition-colors focus-ring-sem cursor-pointer"
                                title={t("call.set_as_primary")}
                                onclick={() => handleSetPrimary(ringtone)}
                            >
                                <MaterialDesignIcon iconName="star-outline" class="size-5" />
                            </button>
                        {/if}
                        <button
                            type="button"
                            class="p-2 rounded-lg hover:bg-sem-surface-muted text-sem-fg-muted hover:text-sem-danger transition-colors focus-ring-sem cursor-pointer"
                            title={t("call.delete")}
                            onclick={() => ondelete?.(ringtone)}
                        >
                            <MaterialDesignIcon iconName="delete-outline" class="size-5" />
                        </button>
                    </div>
                </div>
            {/each}
        </div>
    {:else}
        <EmptyState icon="music-off" title={t("call.no_custom_ringtone_uploaded")} plain class="py-6" />
    {/if}
</div>
