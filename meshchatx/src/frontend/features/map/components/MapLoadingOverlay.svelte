<!-- SPDX-License-Identifier: 0BSD -->

<script lang="ts">
    import { t } from "../../../js/i18n.js";

    interface Props {
        message?: string | null;
    }

    let { message = null }: Props = $props();
</script>

<div class="absolute inset-0 z-20 flex items-center justify-center bg-white/50 dark:bg-black/50 backdrop-blur-xs">
    <div class="bg-sem-surface p-6 rounded-xl shadow-xl flex flex-col items-center space-y-4">
        <div class="animate-spin rounded-full h-12 w-12 border-4 border-blue-500 border-t-transparent"></div>
        <p class="text-sem-fg font-medium">{message || t("map.uploading")}</p>
    </div>
</div>
