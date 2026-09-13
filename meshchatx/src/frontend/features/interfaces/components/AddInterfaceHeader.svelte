<!-- SPDX-License-Identifier: 0BSD -->

<script lang="ts">
    import { t } from "../../../js/i18n.js";
    import MaterialDesignIcon from "../../../ui/svelte/MaterialDesignIcon.svelte";

    interface Props {
        isEditing?: boolean;
        onback?: () => void;
    }

    let { isEditing = false, onback }: Props = $props();
</script>

<div class="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
    <div class="min-w-0">
        <h1 class="text-2xl font-bold text-sem-fg flex items-center gap-2">
            <MaterialDesignIcon iconName={isEditing ? "pencil" : "plus-circle-outline"} class="w-7 h-7 text-blue-500" />
            <span>{isEditing ? t("interfaces.edit_interface") : t("interfaces.add_interface")}</span>
        </h1>
        <p class="text-sm text-sem-fg-muted mt-1">
            {isEditing ? "Update existing connection settings." : "Create a new connection to the Reticulum network."}
        </p>
    </div>
    <div class="flex gap-2 shrink-0">
        <button type="button" class="secondary-chip" onclick={onback}>
            <MaterialDesignIcon iconName="arrow-left" class="w-4 h-4" />
            <span>Back to List</span>
        </button>
    </div>
</div>
