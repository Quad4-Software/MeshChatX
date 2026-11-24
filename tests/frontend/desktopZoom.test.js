/* SPDX-License-Identifier: 0BSD */

import { describe, it, expect, vi, afterEach } from "vitest";
import fs from "fs";
import path from "path";
import {
    DESKTOP_ZOOM_MESSAGE_TYPE,
    desktopZoomBridge,
    desktopZoomKeyAction,
    desktopZoomWheelAction,
    getDesktopZoom,
    installDesktopZoom,
    isDesktopZoomAvailable,
    requestDesktopZoom,
} from "../../meshchatx/src/frontend/js/desktopZoom.js";

const keyEvent = (opts) => ({
    key: "",
    ctrlKey: false,
    metaKey: false,
    altKey: false,
    defaultPrevented: false,
    ...opts,
});

describe("desktopZoomKeyAction", () => {
    it("maps ctrl/cmd + =, +, -, 0 to zoom actions", () => {
        expect(desktopZoomKeyAction(keyEvent({ key: "=", ctrlKey: true }))).toBe("in");
        expect(desktopZoomKeyAction(keyEvent({ key: "+", ctrlKey: true }))).toBe("in");
        expect(desktopZoomKeyAction(keyEvent({ key: "-", ctrlKey: true }))).toBe("out");
        expect(desktopZoomKeyAction(keyEvent({ key: "0", ctrlKey: true }))).toBe("reset");
        expect(desktopZoomKeyAction(keyEvent({ key: "=", metaKey: true }))).toBe("in");
        expect(desktopZoomKeyAction(keyEvent({ key: "0", metaKey: true }))).toBe("reset");
    });

    it("ignores events without ctrl/meta, with alt, already handled, or other keys", () => {
        expect(desktopZoomKeyAction(keyEvent({ key: "=" }))).toBeNull();
        expect(desktopZoomKeyAction(keyEvent({ key: "=", altKey: true, ctrlKey: true }))).toBeNull();
        expect(desktopZoomKeyAction(keyEvent({ key: "=", ctrlKey: true, defaultPrevented: true }))).toBeNull();
        expect(desktopZoomKeyAction(keyEvent({ key: "a", ctrlKey: true }))).toBeNull();
        expect(desktopZoomKeyAction(keyEvent({ key: "Enter", ctrlKey: true }))).toBeNull();
        expect(desktopZoomKeyAction(null)).toBeNull();
    });
});

describe("desktopZoomWheelAction", () => {
    it("maps ctrl/meta + wheel delta to zoom actions", () => {
        expect(desktopZoomWheelAction({ ctrlKey: true, deltaY: -100, defaultPrevented: false })).toBe("in");
        expect(desktopZoomWheelAction({ ctrlKey: true, deltaY: 100, defaultPrevented: false })).toBe("out");
        expect(desktopZoomWheelAction({ metaKey: true, deltaY: -100, defaultPrevented: false })).toBe("in");
        expect(desktopZoomWheelAction({ ctrlKey: true, deltaY: -100, deltaMode: 1, defaultPrevented: false })).toBe(
            "in"
        );
    });

    it("ignores plain wheel, zero delta, and already-handled events", () => {
        expect(desktopZoomWheelAction({ deltaY: -100, defaultPrevented: false })).toBeNull();
        expect(desktopZoomWheelAction({ ctrlKey: true, deltaY: 0, defaultPrevented: false })).toBeNull();
        expect(desktopZoomWheelAction({ ctrlKey: true, deltaY: 100, defaultPrevented: true })).toBeNull();
        expect(desktopZoomWheelAction(null)).toBeNull();
    });
});

describe("desktopZoomBridge helpers", () => {
    it("detects bridge only when window.desktop.zoom is a function", () => {
        expect(desktopZoomBridge({ desktop: { zoom: () => {} } })).not.toBeNull();
        expect(desktopZoomBridge({ desktop: {} })).toBeNull();
        expect(desktopZoomBridge({})).toBeNull();
        expect(desktopZoomBridge(null)).toBeNull();
        expect(isDesktopZoomAvailable({ desktop: { zoom: () => {} } })).toBe(true);
        expect(isDesktopZoomAvailable({ desktop: {} })).toBe(false);
    });

    it("getDesktopZoom resolves the level or null", async () => {
        await expect(getDesktopZoom({ desktop: { getZoom: () => Promise.resolve(1.4) } })).resolves.toBe(1.4);
        await expect(getDesktopZoom({ desktop: { getZoom: () => Promise.resolve("x") } })).resolves.toBeNull();
        await expect(getDesktopZoom({ desktop: {} })).resolves.toBeNull();
        await expect(getDesktopZoom({})).resolves.toBeNull();
    });

    it("requestDesktopZoom validates action and unwraps {zoom}", async () => {
        const zoom = vi.fn(() => Promise.resolve({ zoom: 1.2 }));
        const win = { desktop: { zoom } };
        await expect(requestDesktopZoom(win, "in")).resolves.toBe(1.2);
        expect(zoom).toHaveBeenCalledWith("in");
        await expect(requestDesktopZoom(win, "bogus")).resolves.toBeNull();
        expect(zoom).toHaveBeenCalledTimes(1);
        await expect(requestDesktopZoom({ desktop: {} }, "in")).resolves.toBeNull();
    });
});

describe("installDesktopZoom", () => {
    let uninstall = null;

    afterEach(() => {
        if (uninstall) {
            uninstall();
            uninstall = null;
        }
        delete window.desktop;
        delete window.__desktopZoomInstalled;
        vi.restoreAllMocks();
    });

    it("returns null without a desktop zoom bridge", () => {
        delete window.desktop;
        expect(installDesktopZoom(window)).toBeNull();
        window.desktop = {};
        expect(installDesktopZoom(window)).toBeNull();
    });

    it("handles ctrl zoom keys and ctrl+wheel with preventDefault", () => {
        const zoom = vi.fn(() => Promise.resolve({ zoom: 1.1 }));
        window.desktop = { zoom };
        uninstall = installDesktopZoom(window);
        expect(uninstall).toBeTypeOf("function");

        const key = new KeyboardEvent("keydown", { key: "=", ctrlKey: true, cancelable: true });
        window.dispatchEvent(key);
        expect(key.defaultPrevented).toBe(true);
        expect(zoom).toHaveBeenCalledWith("in");

        const wheel = new WheelEvent("wheel", { ctrlKey: true, deltaY: 120, cancelable: true });
        window.dispatchEvent(wheel);
        expect(wheel.defaultPrevented).toBe(true);
        expect(zoom).toHaveBeenCalledWith("out");

        const plain = new KeyboardEvent("keydown", { key: "a", cancelable: true });
        window.dispatchEvent(plain);
        expect(plain.defaultPrevented).toBe(false);
        expect(zoom).toHaveBeenCalledTimes(2);
    });

    it("handles nomad iframe zoom messages only from opaque origins", () => {
        const zoom = vi.fn(() => Promise.resolve({ zoom: 1.0 }));
        window.desktop = { zoom };
        uninstall = installDesktopZoom(window);

        window.dispatchEvent(
            new MessageEvent("message", {
                data: { channel: "nomad-crash-tab", type: DESKTOP_ZOOM_MESSAGE_TYPE, action: "reset" },
                origin: "null",
            })
        );
        expect(zoom).toHaveBeenCalledWith("reset");

        window.dispatchEvent(
            new MessageEvent("message", {
                data: { channel: "nomad-crash-tab", type: DESKTOP_ZOOM_MESSAGE_TYPE, action: "reset" },
                origin: "https://evil.example.com",
            })
        );
        window.dispatchEvent(
            new MessageEvent("message", {
                data: { channel: "other-channel", type: DESKTOP_ZOOM_MESSAGE_TYPE, action: "in" },
                origin: "null",
            })
        );
        window.dispatchEvent(
            new MessageEvent("message", {
                data: { channel: "nomad-crash-tab", type: DESKTOP_ZOOM_MESSAGE_TYPE, action: "bogus" },
                origin: "null",
            })
        );
        expect(zoom).toHaveBeenCalledTimes(1);
    });

    it("is idempotent and uninstall removes listeners", () => {
        const zoom = vi.fn(() => Promise.resolve({ zoom: 1.0 }));
        window.desktop = { zoom };
        uninstall = installDesktopZoom(window);
        expect(installDesktopZoom(window)).toBeNull();
        uninstall();
        uninstall = null;
        window.dispatchEvent(new KeyboardEvent("keydown", { key: "=", ctrlKey: true, cancelable: true }));
        expect(zoom).not.toHaveBeenCalled();
    });
});

describe("nomadCrashTabMain zoom forwarding", () => {
    it("forwards zoom chords to the parent over the crash-tab channel", () => {
        const src = fs.readFileSync(
            path.resolve(__dirname, "../../meshchatx/src/frontend/js/nomadCrashTabMain.js"),
            "utf-8"
        );
        expect(src).toContain("desktopZoomKeyAction");
        expect(src).toContain("desktopZoomWheelAction");
        expect(src).toContain("DESKTOP_ZOOM_MESSAGE_TYPE");
        expect(src).toContain('addEventListener("keydown"');
        expect(src).toContain('addEventListener("wheel"');
    });
});
