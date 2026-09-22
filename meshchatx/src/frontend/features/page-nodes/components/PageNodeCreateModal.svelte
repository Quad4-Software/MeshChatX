<!-- SPDX-License-Identifier: 0BSD -->

<script lang="ts">
    import Modal from "../../../ui/svelte/Modal.svelte";
    import { t } from "../../../js/i18n.js";

    interface Props {
        open: boolean;
        onClose: () => void;
        onCreate: (name: string) => void;
    }

    let { open = $bindable(false), onClose, onCreate }: Props = $props();

    let nodeName = $state("");

    function handleCreate() {
        if (!nodeName.trim()) return;
        onCreate(nodeName.trim());
        nodeName = "";
    }

    function handleKeydown(event: KeyboardEvent) {
        if (event.key === "Enter") {
            handleCreate();
        }
    }
</script>

<Modal bind:open title={t("tools.mesh_server.create_dialog_title")} {onClose} maxWidth={448}>
    <div class="space-y-4">
        <div>
            <label for="create-node-name-input" class="glass-label">
                {t("tools.mesh_server.server_name_label")}
            </label>
            <input
                id="create-node-name-input"
                type="text"
                placeholder={t("tools.mesh_server.server_name_placeholder")}
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
                title={!nodeName.trim()
                    ? t("tools.mesh_server.server_name_placeholder")
                    : t("tools.mesh_server.create")}
                onclick={handleCreate}
            >
                {t("tools.mesh_server.create")}
            </button>
        </div>
    </div>
</Modal>
