<!-- SPDX-License-Identifier: 0BSD -->

<script lang="ts">
    import { onMount, onDestroy } from "svelte";

    const CHANNEL = "meshchatx-plugin-html-frame";

    interface Props {
        pluginId: string;
        frameId?: string;
        src?: string;
        srcdoc?: string;
        title?: string;
        minHeight?: string;
        csp?: string;
        onframeAction?: (actionId: string) => void;
    }

    let {
        pluginId,
        frameId = "",
        src = "",
        srcdoc = "",
        title = "",
        minHeight = "12rem",
        csp = "default-src 'none'; style-src 'unsafe-inline'; script-src 'unsafe-inline'; img-src data:;",
        onframeAction,
    }: Props = $props();

    let frameEl = $state<HTMLIFrameElement | null>(null);

    let frameSrc = $derived(src || undefined);

    let frameSrcdoc = $derived.by(() => {
        if (src) {
            return undefined;
        }
        if (!srcdoc) {
            return undefined;
        }
        const meta = `<meta http-equiv="Content-Security-Policy" content="${csp.replace(/"/g, "")}">`;
        if (srcdoc.includes("<head>")) {
            return srcdoc.replace("<head>", `<head>${meta}`);
        }
        return `<!DOCTYPE html><html><head>${meta}</head><body>${srcdoc}</body></html>`;
    });

    function onLoad(): void {
        try {
            frameEl?.contentWindow?.postMessage(
                {
                    channel: CHANNEL,
                    type: "ready",
                    pluginId,
                    frameId,
                },
                "*"
            );
        } catch {
            /* opaque sandbox */
        }
    }

    function onMessage(event: MessageEvent): void {
        if (event.source !== frameEl?.contentWindow) {
            return;
        }
        const data = event.data;
        if (!data || data.channel !== CHANNEL || data.pluginId !== pluginId) {
            return;
        }
        if (typeof data.actionId === "string") {
            onframeAction?.(data.actionId);
        }
    }

    onMount(() => {
        window.addEventListener("message", onMessage);
    });

    onDestroy(() => {
        window.removeEventListener("message", onMessage);
    });
</script>

<iframe
    bind:this={frameEl}
    class="w-full rounded-lg border border-sem-border bg-sem-surface"
    style="min-height: {minHeight}"
    title={title || "Plugin frame"}
    src={frameSrc}
    srcdoc={frameSrcdoc}
    sandbox="allow-scripts"
    referrerpolicy="no-referrer"
    onload={onLoad}
></iframe>
