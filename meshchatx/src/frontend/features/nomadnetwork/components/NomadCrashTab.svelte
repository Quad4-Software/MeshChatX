<!-- SPDX-License-Identifier: 0BSD -->

<script lang="ts">
    import { onMount, onDestroy } from "svelte";
    import { nomadCrashTabRendererUrl } from "../../../js/nomadCrashTabShell.js";
    import {
        postToFrame,
        isDocumentHidden,
        NomadCrashTabWatchdog,
        NomadRenderDeadline,
        handleCrashTabMessage,
    } from "../lib/nomadCrashTabBridge.js";
    import NomadCrashTabHungAlert from "./NomadCrashTabHungAlert.svelte";
    import type { NomadNavigateEvent } from "../lib/types.js";

    interface Props {
        class?: string;
        path?: string;
        content?: string;
        showSource?: boolean;
        pagePartials?: Record<string, string>;
        renderOptions?: Record<string, unknown>;
        contentClass?: string;
        color?: string;
        background?: string;
        active?: boolean;
        reveal?: boolean;
        onnavigate?: (event: NomadNavigateEvent) => void;
        onpartials?: (partials: unknown[]) => void;
        onviewsource?: () => void;
        onready?: () => void;
        onhung?: () => void;
        onrenderstarted?: () => void;
        onrenderdone?: () => void;
        onaborted?: () => void;
        onshellbackground?: (bg: string | null) => void;
    }

    let {
        class: className = "",
        path = "",
        content = "",
        showSource = false,
        pagePartials = {},
        renderOptions = {},
        contentClass = "",
        color = "",
        background = "#000000",
        active = true,
        reveal = true,
        onnavigate,
        onpartials,
        onviewsource,
        onready,
        onhung,
        onrenderstarted,
        onrenderdone,
        onaborted,
        onshellbackground,
    }: Props = $props();

    let frame = $state<HTMLIFrameElement | null>(null);
    let frameSrc = $state(nomadCrashTabRendererUrl());
    let status = $state<"loading" | "ready" | "rendering" | "hung" | "crashed" | "aborted">("loading");
    let frameReady = $state(false);
    let framePainted = $state(false);
    let renderEpoch = 0;
    let skipRenderUntilPropChange = false;
    let lastPostedRenderKey = "";
    let livenessPaused = false;
    let pushRenderQueued = false;
    let chromePushQueued = false;

    const watchdog = new NomadCrashTabWatchdog({
        onHung: () => {
            if (status === "ready") {
                deadline.clear();
                status = "hung";
                framePainted = false;
                onhung?.();
            }
        },
        onPing: (id) => {
            sendToFrame({ type: "ping", id });
        },
    });

    const deadline = new NomadRenderDeadline(() => {
        status = "hung";
        framePainted = false;
        onhung?.();
    });

    const frameStyle = $derived.by(() => {
        const bg = background && background !== "transparent" ? background : "#000000";
        const show = reveal && framePainted && status !== "rendering" && status !== "loading";
        return `background-color: ${bg}; opacity: ${show ? "1" : "0"};`;
    });

    const renderOptionsKey = $derived.by(() => {
        try {
            return JSON.stringify(renderOptions || {});
        } catch {
            return "";
        }
    });

    const pagePartialsKey = $derived.by(() => {
        try {
            return JSON.stringify(pagePartials || {});
        } catch {
            return "";
        }
    });

    const contentRenderKey = $derived(
        [path || "", showSource ? "1" : "0", content || "", renderOptionsKey, pagePartialsKey].join("\u0001")
    );

    function sendToFrame(msg: Record<string, unknown>): boolean {
        return postToFrame(frame, msg);
    }

    function armDeadline(timeoutMs?: number) {
        deadline.arm(
            livenessPaused,
            renderEpoch,
            () => renderEpoch,
            () => status,
            timeoutMs
        );
    }

    function pushChrome() {
        if (!frameReady || skipRenderUntilPropChange || content == null || content === "") {
            return;
        }
        if (status === "rendering" || status === "loading") {
            return;
        }
        sendToFrame({
            type: "chrome",
            className: contentClass || "",
            color: color || "#dddddd",
            background: background || "#000000",
            showSource: showSource === true,
        });
    }

    function schedulePushChrome() {
        if (chromePushQueued) return;
        chromePushQueued = true;
        queueMicrotask(() => {
            chromePushQueued = false;
            pushChrome();
        });
    }

    function pushRender() {
        if (skipRenderUntilPropChange) {
            return;
        }
        if (!frameReady) {
            if (content && status === "loading") {
                armDeadline();
            }
            return;
        }
        if (content == null || content === "") {
            framePainted = false;
            lastPostedRenderKey = "";
            deadline.clear();
            sendToFrame({ type: "clear" });
            status = "ready";
            return;
        }
        const renderKey = contentRenderKey;
        if (renderKey === lastPostedRenderKey && status === "ready" && framePainted) {
            pushChrome();
            onrenderdone?.();
            return;
        }
        renderEpoch += 1;
        const epoch = renderEpoch;
        framePainted = false;
        status = "rendering";
        watchdog.recordPong();
        lastPostedRenderKey = renderKey;
        onrenderstarted?.();
        armDeadline();

        queueMicrotask(() => {
            if (skipRenderUntilPropChange || epoch !== renderEpoch) {
                return;
            }
            const posted = sendToFrame({
                type: "render",
                path: path || "",
                content: content || "",
                showSource: showSource === true,
                pagePartials: pagePartials || {},
                renderOptions: renderOptions || {},
                className: contentClass || "",
                color: color || "#dddddd",
                background: background || "#000000",
            });
            if (!posted) {
                deadline.clear();
                status = "crashed";
                onhung?.();
            }
        });
    }

    function schedulePushRender() {
        if (pushRenderQueued) return;
        pushRenderQueued = true;
        queueMicrotask(() => {
            pushRenderQueued = false;
            pushRender();
        });
    }

    export function reloadFrame() {
        deadline.clear();
        status = "loading";
        frameReady = false;
        framePainted = false;
        lastPostedRenderKey = "";
        frameSrc = `${nomadCrashTabRendererUrl()}?t=${Date.now()}`;
        watchdog.recordPong();
    }

    export function abortRender() {
        renderEpoch += 1;
        skipRenderUntilPropChange = true;
        framePainted = false;
        lastPostedRenderKey = "";
        deadline.clear();
        sendToFrame({ type: "abort" });
        reloadFrame();
        status = "aborted";
        onrenderdone?.();
        onaborted?.();
    }

    export function setPartialHtml(partialId: string, html: string) {
        if (skipRenderUntilPropChange) {
            return;
        }
        sendToFrame({ type: "set-partial", id: partialId, html: html || "" });
    }

    function onWindowMessage(event: MessageEvent) {
        handleCrashTabMessage(event, frame, {
            onReady: () => {
                frameReady = true;
                lastPostedRenderKey = "";
                deadline.clear();
                status = skipRenderUntilPropChange ? "aborted" : "ready";
                watchdog.recordPong();
                onready?.();
                schedulePushRender();
            },
            onPong: () => {
                watchdog.recordPong();
                if (status === "hung" && framePainted) {
                    status = "ready";
                }
            },
            onRenderStarted: () => {
                if (skipRenderUntilPropChange) return;
                status = "rendering";
                watchdog.recordPong();
            },
            onRenderDone: (partials) => {
                if (skipRenderUntilPropChange) return;
                deadline.clear();
                status = "ready";
                framePainted = true;
                watchdog.recordPong();
                onrenderdone?.();
                onpartials?.(partials);
            },
            onRenderError: () => {
                if (skipRenderUntilPropChange) return;
                deadline.clear();
                status = "crashed";
                framePainted = false;
                onhung?.();
            },
            onShellBackground: (bg) => {
                onshellbackground?.(bg);
            },
            onAborted: () => {
                deadline.clear();
                status = "aborted";
                framePainted = false;
                if (!skipRenderUntilPropChange) {
                    onaborted?.();
                }
            },
            onNavigate: (ev) => {
                onnavigate?.(ev);
            },
        });
    }

    function onVisibilityChange() {
        if (isDocumentHidden()) {
            livenessPaused = true;
            watchdog.stop();
            deadline.park(status);
        } else {
            livenessPaused = false;
            watchdog.recordPong();
            if (active) {
                watchdog.start(active, livenessPaused);
                watchdog.ping(active, frameReady, livenessPaused);
            }
            deadline.unpark(
                livenessPaused,
                renderEpoch,
                () => renderEpoch,
                () => status
            );
        }
    }

    $effect(() => {
        const _ = contentRenderKey;
        skipRenderUntilPropChange = false;
        schedulePushRender();
    });

    $effect(() => {
        const _c = `${contentClass}|${color}|${background}`;
        schedulePushChrome();
    });

    $effect(() => {
        if (active && !livenessPaused && !isDocumentHidden()) {
            watchdog.start(active, livenessPaused);
        } else {
            watchdog.stop();
        }
    });

    onMount(() => {
        window.addEventListener("message", onWindowMessage);
        window.addEventListener("visibilitychange", onVisibilityChange);
        if (isDocumentHidden()) {
            livenessPaused = true;
            watchdog.stop();
            deadline.park(status);
        } else if (active) {
            watchdog.start(active, livenessPaused);
        }
        if (content && status === "loading") {
            armDeadline();
        }
    });

    onDestroy(() => {
        window.removeEventListener("message", onWindowMessage);
        window.removeEventListener("visibilitychange", onVisibilityChange);
        watchdog.stop();
        deadline.clear();
    });
</script>

<div class="nomad-crash-tab relative h-full min-h-0 w-full min-w-0 bg-black {className}">
    <iframe
        bind:this={frame}
        class="nomad-crash-tab__frame absolute inset-0 h-full w-full border-0 bg-black"
        title="Nomad page renderer"
        sandbox="allow-scripts"
        allow="local-network-access"
        src={frameSrc}
        style={frameStyle}
        onload={() => {
            watchdog.recordPong();
        }}
    ></iframe>

    {#if status === "hung" || status === "crashed"}
        <NomadCrashTabHungAlert onreload={reloadFrame} onviewsource={() => onviewsource?.()} oncancel={abortRender} />
    {/if}
</div>
