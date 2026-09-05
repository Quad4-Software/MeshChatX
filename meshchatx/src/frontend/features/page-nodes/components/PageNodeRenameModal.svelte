<!-- SPDX-License-Identifier: 0BSD -->

<script lang="ts">
    import Modal from "../../../ui/svelte/Modal.svelte";
    import { t } from "../../../js/i18n.js";

    interface Props {
        open: boolean;
        placeholderName?: string;
        onClose: () => void;
        onRename: (newName: string) => void;
    }

    let { open = $bindable(false), placeholderName = "", onClose, onRename }: Props = $props();

    let nodeName = $state("");

    function handleRename() {
        if (!nodeName.trim()) return;
        onRename(nodeName.trim());
        nodeName = "";
    }

    function handleKeydown(event: KeyboardEvent) {
        if (event.key === "Enter") {
            handleRename();
        }
    }
</script>

<Modal bind:open title={t("tools.mesh_server.rename_dialog_title")} {onClose} maxWidth={448}>
    <div class="space-y-4">
        <div>
            <label for="rename-node-name-input" class="glass-label">
                {t("tools.mesh_server.new_name_label")}
            </label>
            <input
                id="rename-node-name-input"
                type="text"
                placeholder={placeholderName}
                class="input-field"
                bind:value={nodeName}
                onkeydown={handleKeydown}
            />
        </div>
        <div class="flex justify-end gap-2 pt-2">
            <button type="button" class="secondary-chip focus-ring-sem px-4 py-2 text-sm" onclick={onClose}>
                {t("common.cancel")}
            </button>
            <button
                type="button"
                class="primary-chip focus-ring-sem px-4 py-2 text-sm"
                disabled={!nodeName.trim()}
                title={!nodeName.trim() ? t("tools.mesh_server.new_name_label") : t("tools.mesh_server.rename")}
                onclick={handleRename}
            >
                {t("tools.mesh_server.rename")}
            </button>
        </div>
    </div>
</Modal>
