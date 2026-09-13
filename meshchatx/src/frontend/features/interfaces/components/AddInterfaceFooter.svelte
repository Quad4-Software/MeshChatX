<!-- SPDX-License-Identifier: 0BSD -->

<script lang="ts">
    import MaterialDesignIcon from "../../../ui/svelte/MaterialDesignIcon.svelte";

    interface Props {
        isEditing?: boolean;
        isSaving?: boolean;
        oncancel?: () => void;
        onsave?: () => void;
    }

    let { isEditing = false, isSaving = false, oncancel, onsave }: Props = $props();
</script>

<div class="pt-8 flex items-center justify-between gap-4 border-t border-sem-border">
    <button type="button" class="secondary-chip px-4 py-2 text-sm" onclick={oncancel}> Cancel </button>
    <button type="button" class="primary-chip px-4 py-2 text-sm" disabled={isSaving} onclick={onsave}>
        <MaterialDesignIcon
            iconName={isSaving ? "loading" : isEditing ? "content-save" : "plus"}
            class="size-5 {isSaving ? 'animate-spin' : ''}"
        />
        <span>{isEditing ? "Update Connection" : "Create Connection"}</span>
    </button>
</div>
