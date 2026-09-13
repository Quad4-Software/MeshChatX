<!-- SPDX-License-Identifier: 0BSD -->

<script lang="ts">
    /* eslint-disable svelte/no-dom-manipulating -- the frame is parked on document.body */
    import { onMount, onDestroy, tick } from "svelte";
    import { useEventListener } from "runed";
    import { nomadCrashTabRendererUrl } from "../../../js/nomadCrashTabShell.js";
    import { readTextFromClipboard } from "../../../js/clipboardUtils.js";
    import { t } from "../../../js/i18n.js";
    import MaterialDesignIcon from "../../../ui/svelte/MaterialDesignIcon.svelte";
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
        onimages?: (images: unknown[]) => void;
        onimageaction?: (payload: Record<string, unknown>) => void;
        oncontextmenu?: (coords: { clientX: number; clientY: number }) => void;
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
        onimages,
        onimageaction,
        oncontextmenu,
        onviewsource,
        onready,
        onhung,
        onrenderstarted,
        onrenderdone,
        onaborted,
        onshellbackground,
    }: Props = $props();

    /**
     * Transition or animation property names that can move or resize the host
     * slot without producing a resize or scroll event. Filtered so paint-only
     * transitions (color, opacity) never start the rect poll.
     */
    const GEOMETRY_TRANSITION_RE =
        /transform|translate|scale|rotate|inset|^top$|^left$|^right$|^bottom$|width|height|margin|padding|gap|flex|grid/;
    /** How long the rect poll keeps running after the last geometry transition. */
    const RECT_POLL_TAIL_MS = 700;

    let hostEl = $state<HTMLDivElement | null>(null);
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
    // Placeholder rect the teleported frame is parked over.
    let frameRect = $state({ left: 0, top: 0, width: 0, height: 0 });
    let rectPollUntil = 0;
    let rectPollRaf: number | null = null;
    let fieldContextMenu = $state({ show: false, justOpened: false, x: 0, y: 0 });
    let fieldContextMenuEl = $state<HTMLDivElement | null>(null);

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

    const frameVisible = $derived(
        // Hide under the hung/crashed overlay too: the teleported frame is at
        // body level, so an in-tree overlay cannot rely on z-order alone.
        active && status !== "hung" && status !== "crashed" && frameRect.width > 0 && frameRect.height > 0
    );

    const frameStyle = $derived.by(() => {
        const bg = background && background !== "transparent" ? background : "#000000";
        const show = reveal && framePainted && status !== "rendering" && status !== "loading";
        const rect = frameRect;
        return (
            `position: fixed; left: ${rect.left}px; top: ${rect.top}px; ` +
            `width: ${rect.width}px; height: ${rect.height}px; ` +
            `background-color: ${bg}; opacity: ${show ? "1" : "0"}; ` +
            `visibility: ${frameVisible ? "visible" : "hidden"}; ` +
            `pointer-events: ${frameVisible && reveal ? "auto" : "none"};`
        );
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
            onRenderDone: (partials, images) => {
                if (skipRenderUntilPropChange) return;
                deadline.clear();
                status = "ready";
                framePainted = true;
                watchdog.recordPong();
                onrenderdone?.();
                onpartials?.(partials);
                onimages?.(images);
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
            onPageContextMenu: (data) => {
                const { x, y } = frameOffsetCoords(data);
                oncontextmenu?.({ clientX: x, clientY: y });
            },
            onFieldContextMenu: (data) => {
                const { x, y } = frameOffsetCoords(data);
                fieldContextMenu = { show: true, justOpened: true, x, y };
                setTimeout(() => {
                    fieldContextMenu.justOpened = false;
                }, 50);
            },
            onImageAction: (payload) => {
                onimageaction?.(payload);
            },
        });
    }

    export function setImage(index: number, state: string, payload: Record<string, unknown> = {}) {
        sendToFrame({ type: "set-image", index, state, ...payload });
    }

    function frameOffsetCoords(data: { x?: number; y?: number }) {
        const rect = frame && typeof frame.getBoundingClientRect === "function" ? frame.getBoundingClientRect() : null;
        return {
            x: Math.round((rect ? rect.left : 0) + (Number(data?.x) || 0)),
            y: Math.round((rect ? rect.top : 0) + (Number(data?.y) || 0)),
        };
    }

    async function pasteIntoFrameField() {
        fieldContextMenu.show = false;
        const res = await readTextFromClipboard();
        let text: string | null = res.ok ? res.text : null;
        if (text == null) {
            const bridge = (window as any).MeshChatXAndroid;
            if (bridge && typeof bridge.getClipboardText === "function") {
                try {
                    text = bridge.getClipboardText();
                } catch {
                    text = null;
                }
            }
        }
        if (text == null || text === "") {
            return;
        }
        sendToFrame({ type: "paste-text", text });
    }

    function onFieldMenuWindowClick(event: MouseEvent) {
        if (!fieldContextMenu.show || fieldContextMenu.justOpened) {
            return;
        }
        if (fieldContextMenuEl && !fieldContextMenuEl.contains(event.target as Node)) {
            fieldContextMenu.show = false;
        }
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

    function updateFrameRect() {
        const host = hostEl;
        const rect = host && typeof host.getBoundingClientRect === "function" ? host.getBoundingClientRect() : null;
        const next = rect
            ? { left: rect.left, top: rect.top, width: rect.width, height: rect.height }
            : { left: 0, top: 0, width: 0, height: 0 };
        const prev = frameRect;
        // Skip the write when nothing moved. Assigning a fresh object on every
        // patch would re-render and loop forever on identical rects.
        if (
            next.left === prev.left &&
            next.top === prev.top &&
            next.width === prev.width &&
            next.height === prev.height
        ) {
            return;
        }
        frameRect = next;
    }

    function onGeometryTransition(event: Event) {
        const prop = event ? (event as TransitionEvent).propertyName : null;
        if (prop != null && !GEOMETRY_TRANSITION_RE.test(prop)) {
            return;
        }
        rectPollUntil = Date.now() + RECT_POLL_TAIL_MS;
        if (rectPollRaf != null) {
            return;
        }
        const step = () => {
            rectPollRaf = null;
            if (Date.now() >= rectPollUntil) {
                return;
            }
            updateFrameRect();
            rectPollRaf = requestAnimationFrame(step);
        };
        rectPollRaf = requestAnimationFrame(step);
    }

    function portalFrameToBody(node: HTMLElement) {
        // The frame lives outside the component subtree. Detaching the host
        // (route change, tab switch) would otherwise destroy the iframe
        // browsing context and force a renderer reload plus a full content
        // re-push on every return.
        document.body.appendChild(node);
        return {
            destroy() {
                node.remove();
            },
        };
    }

    $effect(() => {
        const host = hostEl;
        if (!host || typeof ResizeObserver !== "function") {
            return;
        }
        const observer = new ResizeObserver(() => updateFrameRect());
        observer.observe(host);
        observer.observe(document.documentElement);
        return () => observer.disconnect();
    });

    $effect(() => {
        // Reactive siblings (banners, state blocks) can shift the slot without
        // firing resize or scroll. A rect read per patch is cheap insurance.
        void status;
        void framePainted;
        void reveal;
        void active;
        void className;
        updateFrameRect();
    });

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
        void tick().then(() => updateFrameRect());
    });

    useEventListener(window, "message", onWindowMessage);
    useEventListener(window, "visibilitychange", onVisibilityChange);
    useEventListener(window, "click", onFieldMenuWindowClick, { capture: true });
    useEventListener(window, "resize", updateFrameRect);
    useEventListener(document, "scroll", updateFrameRect, { capture: true });
    useEventListener(document, ["transitionrun", "animationstart"], onGeometryTransition, { capture: true });

    onMount(() => {
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
        watchdog.stop();
        deadline.clear();
        rectPollUntil = 0;
        if (rectPollRaf != null && typeof cancelAnimationFrame === "function") {
            cancelAnimationFrame(rectPollRaf);
            rectPollRaf = null;
        }
    });
</script>

<div bind:this={hostEl} class="nomad-crash-tab relative h-full min-h-0 w-full min-w-0 bg-black {className}">
    <iframe
        bind:this={frame}
        use:portalFrameToBody
        class="nomad-crash-tab__frame border-0 bg-black"
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

    {#if fieldContextMenu.show}
        <div
            bind:this={fieldContextMenuEl}
            class="context-menu-panel fixed z-200 min-w-32 rounded-xl shadow-xl border border-sem-border bg-sem-surface py-1 text-sem-fg"
            style="left: {fieldContextMenu.x}px; top: {fieldContextMenu.y}px;"
            role="menu"
        >
            <button
                type="button"
                class="context-item flex w-full items-center gap-2 px-3 py-2 text-left text-sm hover:bg-sem-surface-muted"
                onclick={() => void pasteIntoFrameField()}
            >
                <MaterialDesignIcon iconName="content-paste" class="size-5" />
                <span>{t("common.paste")}</span>
            </button>
        </div>
    {/if}
</div>
