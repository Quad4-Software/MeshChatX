<!-- SPDX-License-Identifier: 0BSD -->

<script lang="ts">
    import { t } from "../../../js/i18n.js";

    interface Props {
        open: boolean;
        placeholderName?: string;
        onClose: () => void;
        onRename: (newName: string) => void;
    }

    let { open, placeholderName = "", onClose, onRename }: Props = $props();

    let nodeName = $state("");

    function handleRename() {
        if (!nodeName.trim()) return;
        onRename(nodeName.trim());
        nodeName = "";
    }

    function handleKeydown(event: KeyboardEvent) {
        if (event.key === "Enter") {
            handleRename();
        } else if (event.key === "Escape") {
            onClose();
        }
    }

    function handleBackdropClick(event: MouseEvent) {
        if (event.target === event.currentTarget) {
            onClose();
        }
    }
</script>

{#if open}
    <div
        class="fixed inset-0 bg-black/50 flex items-center justify-center z-50"
        onclick={handleBackdropClick}
        role="presentation"
    >
        <div class="bg-sem-surface rounded-2xl p-6 w-full max-w-md mx-4 shadow-xl space-y-4">
            <div class="text-lg font-semibold text-sem-fg">
                {t("tools.mesh_server.rename_dialog_title")}
            </div>
            <div>
                <label for="rename-node-name-input" class="glass-label">{t("tools.mesh_server.new_name_label")}</label>
                <input
                    id="rename-node-name-input"
                    type="text"
                    placeholder={placeholderName}
                    class="input-field"
                    bind:value={nodeName}
                    onkeydown={handleKeydown}
                />
            </div>
            <div class="flex justify-end gap-2">
                <button type="button" class="secondary-chip py-1.5! px-4! text-sm!" onclick={onClose}>
                    {t("common.cancel")}
                </button>
                <button type="button" class="primary-chip py-1.5! px-4! text-sm!" onclick={handleRename}>
                    {t("tools.mesh_server.rename")}
                </button>
            </div>
        </div>
    </div>
{/if}
