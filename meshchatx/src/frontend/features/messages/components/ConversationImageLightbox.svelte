<!-- SPDX-License-Identifier: 0BSD -->

<script lang="ts">
    import ConversationImageModal from "./modals/ConversationImageModal.svelte";

    let {
        url = "",
        gallery = null as string[] | null,
        index = 0,
        onclose,
        onnavigate,
        ondownload,
        oncontextmenu,
    }: {
        url?: string;
        gallery?: string[] | null;
        index?: number;
        onclose?: () => void;
        onnavigate?: (delta: number) => void;
        ondownload?: () => void;
        oncontextmenu?: (event: MouseEvent) => void;
    } = $props();
</script>

<ConversationImageModal {url} {gallery} {index} {onclose} {onnavigate} {ondownload} {oncontextmenu} />
