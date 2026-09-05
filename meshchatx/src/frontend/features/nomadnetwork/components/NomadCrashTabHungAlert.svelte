<!-- SPDX-License-Identifier: 0BSD -->

<script lang="ts">
    import { t } from "../../../js/i18n.js";

    interface Props {
        onreload?: () => void;
        onviewsource?: () => void;
        oncancel?: () => void;
    }

    let { onreload, onviewsource, oncancel }: Props = $props();
</script>

<div
    class="absolute inset-0 z-10 flex flex-col items-center justify-center gap-3 bg-black/80 px-4 text-center text-gray-100"
    role="alert"
>
    <div class="text-lg font-semibold">{t("nomadnet.crash_tab_title")}</div>
    <div class="max-w-md text-sm text-gray-300">{t("nomadnet.crash_tab_body")}</div>
    <div class="flex flex-wrap items-center justify-center gap-2">
        <button
            type="button"
            class="rounded-lg bg-blue-600 px-3 py-1.5 text-sm font-semibold text-white hover:bg-blue-500"
            onclick={() => onreload?.()}
        >
            {t("nomadnet.crash_tab_reload")}
        </button>
        <button
            type="button"
            class="rounded-lg bg-zinc-700 px-3 py-1.5 text-sm font-semibold text-white hover:bg-zinc-600"
            onclick={() => onviewsource?.()}
        >
            {t("nomadnet.view_source")}
        </button>
        <button
            type="button"
            class="rounded-lg bg-red-700 px-3 py-1.5 text-sm font-semibold text-white hover:bg-red-600"
            onclick={() => oncancel?.()}
        >
            {t("common.cancel")}
        </button>
    </div>
</div>
