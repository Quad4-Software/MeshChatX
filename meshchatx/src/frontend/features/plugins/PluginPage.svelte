<!-- SPDX-License-Identifier: 0BSD -->

<script lang="ts">
    import { onMount, onDestroy } from "svelte";
    import PluginSlotRenderer from "./components/PluginSlotRenderer.svelte";
    import { pluginHost } from "../../js/plugins/PluginHost.js";
    import GlobalState from "../../js/GlobalState.js";
    import { resolveEffectiveTheme, shellCanvasBackgroundStyle } from "../../theme/themeEngine.js";

    interface Props {
        pluginId?: string;
    }

    let { pluginId = "" }: Props = $props();

    let resolvedPluginId = $derived.by(() => {
        if (pluginId) return pluginId;
        if (typeof window !== "undefined" && window.location.hash) {
            const match = window.location.hash.match(/^#\/plugins\/([^/?#]+)/);
            if (match?.[1]) {
                return decodeURIComponent(match[1]);
            }
        }
        return "";
    });

    let caps = $derived(
        resolvedPluginId ? pluginHost.getPluginUiCaps(resolvedPluginId) : { allowedWidgets: [], allowHtmlFrame: false }
    );
    let allowedWidgets = $derived(caps?.allowedWidgets || []);
    let allowHtmlFrame = $derived(Boolean(caps?.allowHtmlFrame));

    let descriptor = $state<any>(null);
    let uiError = $state("");

    let config = $derived(GlobalState.config || {});
    let effectiveThemeMode = $derived(resolveEffectiveTheme((config as any)?.theme));
    let pageStyle = $derived.by(() => {
        const transparency = Number((config as any)?.ui_transparency) || 0;
        if (transparency <= 0) {
            return "";
        }
        const bg = shellCanvasBackgroundStyle(config, effectiveThemeMode);
        return bg ? `background-color: ${bg}` : "";
    });
    let panelClass = $derived.by(() => {
        const glass = (config as any)?.ui_glass_enabled !== false;
        return glass ? "glass-card bg-sem-surface/90" : "bg-sem-surface";
    });

    let uiListener: ((event: any) => void) | null = null;
    let errorListener: ((event: any) => void) | null = null;

    function onAction(actionId: string): void {
        if (resolvedPluginId) {
            pluginHost.postAction(resolvedPluginId, actionId);
        }
    }

    function onInput(payload: { id: string; value: any }): void {
        if (resolvedPluginId) {
            pluginHost.postInput(resolvedPluginId, payload.id, payload.value);
        }
    }

    $effect(() => {
        const pid = resolvedPluginId;
        if (pid) {
            descriptor = pluginHost.getLastDescriptor(pid);
            uiError = pluginHost.getLastUiError(pid) || "";
            pluginHost.requestUiRefresh(pid);
        }
    });

    onMount(() => {
        uiListener = (event: any) => {
            if (event.detail?.pluginId === resolvedPluginId) {
                descriptor = event.detail.descriptor;
                uiError = event.detail.error || "";
            }
        };
        errorListener = (event: any) => {
            if (event.detail?.pluginId === resolvedPluginId && event.detail?.uiError) {
                uiError = event.detail.message || "";
            }
        };
        window.addEventListener("meshchatx-plugin-ui", uiListener);
        window.addEventListener("meshchatx-plugin-ui-error", errorListener);
    });

    onDestroy(() => {
        if (uiListener) {
            window.removeEventListener("meshchatx-plugin-ui", uiListener);
        }
        if (errorListener) {
            window.removeEventListener("meshchatx-plugin-ui-error", errorListener);
        }
    });
</script>

<div class="h-full overflow-y-auto p-4 sm:p-6" style={pageStyle}>
    <div class="mx-auto max-w-5xl rounded-xl border border-sem-border p-4 sm:p-6 shadow-sm {panelClass}">
        <PluginSlotRenderer
            pluginId={resolvedPluginId}
            {descriptor}
            {allowedWidgets}
            {allowHtmlFrame}
            {uiError}
            onaction={onAction}
            oninput={onInput}
        />
    </div>
</div>
