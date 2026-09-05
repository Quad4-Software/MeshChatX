<!-- SPDX-License-Identifier: 0BSD -->

<script lang="ts">
    import MaterialDesignIcon from "../../../ui/svelte/MaterialDesignIcon.svelte";
    import { t } from "../../../js/i18n.js";
</script>

<div
    class="flex flex-col sm:flex-row items-center justify-between gap-3 p-4 border border-zinc-200 dark:border-zinc-800 rounded-2xl bg-zinc-50 dark:bg-zinc-900/30"
>
    <div class="flex items-center gap-3 text-sm text-zinc-500">
        <MaterialDesignIcon iconName="help-circle-outline" class="size-5" />
        <span>{t("tools.rnode_flasher.find_device_issue")}</span>
    </div>
    <div class="flex items-center gap-4">
        <a
            target="_blank"
            href="https://github.com/liamcottle/rnode-flasher"
            class="text-blue-500 hover:underline text-sm font-bold"
        >
            RNode Flasher
        </a>
        <a
            target="_blank"
            href="https://github.com/markqvist/RNode_Firmware"
            class="text-blue-500 hover:underline text-sm font-bold"
        >
            RNode Firmware
        </a>
    </div>
</div>
