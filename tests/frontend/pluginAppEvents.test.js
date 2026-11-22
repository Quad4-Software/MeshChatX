// SPDX-License-Identifier: 0BSD

import { describe, expect, it } from "vitest";

import { WS_EVENTS } from "../../meshchatx/src/frontend/js/constants";
import {
    PLUGIN_HOOK_PAYLOAD_MAX_CHARS,
    pluginHookPayloadAllowed,
    wsEventsForPluginHook,
} from "../../meshchatx/src/frontend/js/plugins/pluginAppEvents.js";
import { declaredPermissionIds } from "../../meshchatx/src/frontend/js/plugins/pluginPermissions.js";

describe("pluginAppEvents", () => {
    it("maps lxmf hooks to websocket events", () => {
        expect(wsEventsForPluginHook("lxmf.message.created")).toEqual([
            WS_EVENTS.LXMF_MESSAGE_CREATED,
        ]);
        expect(wsEventsForPluginHook("lxmf.message.state")).toEqual([
            WS_EVENTS.LXMF_MESSAGE_STATE_UPDATED,
        ]);
    });

    it("fans shell hooks out to rnsh and rnx events", () => {
        expect(wsEventsForPluginHook("shell.session")).toEqual([
            WS_EVENTS.RNSH_SESSION_CHANGE,
            WS_EVENTS.RNX_SESSION_CHANGE,
        ]);
        expect(wsEventsForPluginHook("shell.output")).toEqual([
            WS_EVENTS.RNSH_OUTPUT,
            WS_EVENTS.RNX_OUTPUT,
        ]);
    });

    it("returns no events for backend-delivered or unknown hooks", () => {
        expect(wsEventsForPluginHook("announce.received")).toEqual([]);
        expect(wsEventsForPluginHook("rns.link.event")).toEqual([]);
        expect(wsEventsForPluginHook("does.not.exist")).toEqual([]);
    });

    it("caps hook payload size", () => {
        expect(pluginHookPayloadAllowed({ a: 1 })).toBe(true);
        expect(
            pluginHookPayloadAllowed({ data: "x".repeat(PLUGIN_HOOK_PAYLOAD_MAX_CHARS) })
        ).toBe(false);
        expect(pluginHookPayloadAllowed(undefined)).toBe(true);
    });
});

describe("declaredPermissionIds clipboard modes", () => {
    it("expands read, write, and read-write", () => {
        expect(declaredPermissionIds({ permissions: { clipboard: "read" } })).toEqual([
            "clipboard:read",
        ]);
        expect(declaredPermissionIds({ permissions: { clipboard: "write" } })).toEqual([
            "clipboard:write",
        ]);
        expect(declaredPermissionIds({ permissions: { clipboard: "read-write" } })).toEqual([
            "clipboard:read",
            "clipboard:write",
        ]);
        expect(declaredPermissionIds({ permissions: { clipboard: "none" } })).toEqual([]);
    });
});
