// SPDX-License-Identifier: 0BSD

import { readFileSync } from "fs";
import { join } from "path";
import { describe, expect, it, beforeEach } from "vitest";
import { createRegistry } from "../../meshchatx/src/frontend/js/registries/registryCore.js";
import {
    navRegistry,
    registerNavItem,
    unregisterNavItem,
    listNavItems,
} from "../../meshchatx/src/frontend/js/registries/navRegistry.js";
import { toolsRegistry, registerTool, listTools } from "../../meshchatx/src/frontend/js/registries/toolsRegistry.js";
import {
    commandRegistry,
    registerCommand,
    listCommands,
} from "../../meshchatx/src/frontend/js/registries/commandRegistry.js";
import {
    settingsSectionRegistry,
    registerSettingsSection,
    getAllSettingsSectionKeywords,
} from "../../meshchatx/src/frontend/js/registries/settingsSectionRegistry.js";
import {
    registerCoreContributions,
    resetCoreContributionsForTests,
} from "../../meshchatx/src/frontend/js/registries/registerCoreContributions.js";
import { CORE_NAV_ENTRIES } from "../../meshchatx/src/frontend/js/registries/coreNavEntries.js";
import { CORE_TOOLS_ENTRIES } from "../../meshchatx/src/frontend/js/registries/coreToolsEntries.js";
import { CORE_COMMAND_ENTRIES } from "../../meshchatx/src/frontend/js/registries/coreCommandEntries.js";
import {
    postInstallPromptRegistry,
    listPostInstallPrompts,
} from "../../meshchatx/src/frontend/js/registries/postInstallPromptRegistry.js";
import { CORE_POST_INSTALL_PROMPT_ENTRIES } from "../../meshchatx/src/frontend/js/registries/corePostInstallPromptEntries.js";
import { registerAllFeatures } from "../../meshchatx/src/frontend/features/registerAllFeatures.js";
import { buildRouterRoutesFromRegistry } from "../../meshchatx/src/frontend/shell/buildRouterRoutes.js";

describe("registryCore", () => {
    it("registers and lists entries", () => {
        const registry = createRegistry("test");
        registry.register({ id: "a", value: 1 });
        registry.register({ id: "b", value: 2 });
        expect(registry.list()).toHaveLength(2);
        expect(registry.get("a")?.value).toBe(1);
    });

    it("rejects duplicate ids", () => {
        const registry = createRegistry("test");
        registry.register({ id: "dup" });
        expect(() => registry.register({ id: "dup" })).toThrow(/duplicate/);
    });

    it("unregisters entries", () => {
        const registry = createRegistry("test");
        registry.register({ id: "x" });
        registry.unregister("x");
        expect(registry.list()).toHaveLength(0);
    });
});

describe("contribution registries", () => {
    beforeEach(() => {
        resetCoreContributionsForTests();
        navRegistry.clear();
        toolsRegistry.clear();
        commandRegistry.clear();
        settingsSectionRegistry.clear();
        postInstallPromptRegistry.clear();
    });

    it("registers nav items", () => {
        registerNavItem({
            id: "test",
            route: { name: "about" },
            icon: "information",
            labelKey: "app.about",
        });
        expect(listNavItems()).toHaveLength(1);
        unregisterNavItem("test");
        expect(listNavItems()).toHaveLength(0);
    });

    it("registers tools by name", () => {
        registerTool({
            name: "custom-tool",
            route: { name: "ping" },
            icon: "radar",
            iconBg: "tool-card__icon",
            titleKey: "tools.ping.title",
            descriptionKey: "tools.ping.description",
        });
        expect(listTools()).toHaveLength(1);
        expect(listTools()[0].name).toBe("custom-tool");
    });

    it("registers commands", () => {
        registerCommand({
            id: "cmd-test",
            title: "nav_ping",
            description: "nav_ping_desc",
            icon: "radar",
            type: "navigation",
            route: { name: "ping" },
        });
        expect(listCommands()).toHaveLength(1);
    });

    it("registers settings section keywords", () => {
        registerSettingsSection({ id: "plugins", keywords: ["Plugins", "extensions"] });
        expect(getAllSettingsSectionKeywords().plugins).toContain("Plugins");
    });
});

describe("registerCoreContributions", () => {
    beforeEach(() => {
        resetCoreContributionsForTests();
        navRegistry.clear();
        toolsRegistry.clear();
        commandRegistry.clear();
        settingsSectionRegistry.clear();
        postInstallPromptRegistry.clear();
    });

    it("loads all core entries once", () => {
        registerCoreContributions();
        registerCoreContributions();
        expect(listNavItems()).toHaveLength(CORE_NAV_ENTRIES.length);
        expect(listTools()).toHaveLength(CORE_TOOLS_ENTRIES.length);
        expect(listPostInstallPrompts()).toHaveLength(CORE_POST_INSTALL_PROMPT_ENTRIES.length);
    });

    it("calls nav entry has a missed-calls pill badge", () => {
        const call = CORE_NAV_ENTRIES.find((entry) => entry.id === "call");
        expect(call?.badge).toEqual({ source: "missedCallsCount", pill: true, cap: 99 });
    });

    it("demotes secondary nav entries to the more tier", () => {
        const moreIds = CORE_NAV_ENTRIES.filter((entry) => entry.navTier === "more").map((entry) => entry.id);
        expect(moreIds).toEqual(expect.arrayContaining(["archives", "blocked", "identities", "about"]));
        expect(moreIds).not.toContain("interfaces");
        expect(moreIds).not.toContain("network-visualiser");
        const primaryIds = CORE_NAV_ENTRIES.filter((entry) => entry.navTier === "primary").map((entry) => entry.id);
        expect(primaryIds).toEqual(
            expect.arrayContaining([
                "messages",
                "call",
                "contacts",
                "nomadnetwork",
                "map",
                "network-visualiser",
                "interfaces",
                "tools",
                "settings",
            ])
        );
        const interfaces = CORE_NAV_ENTRIES.find((entry) => entry.id === "interfaces");
        expect(interfaces).toMatchObject({ navTier: "primary", group: "app" });
        const visualiser = CORE_NAV_ENTRIES.find((entry) => entry.id === "network-visualiser");
        expect(visualiser).toMatchObject({ navTier: "primary", group: "explore" });
    });

    it("nav, tools, and command route names exist in the hash router", () => {
        registerAllFeatures();
        const mainSrc = readFileSync(join(process.cwd(), "meshchatx/src/frontend/main.ts"), "utf8");
        const routeNames = new Set();
        const pairRe = /name:\s*"([^"]+)",\s*\n\s*path:\s*"/g;
        let match;
        while ((match = pairRe.exec(mainSrc)) !== null) {
            routeNames.add(match[1]);
        }
        for (const r of buildRouterRoutesFromRegistry()) {
            if (r.name) {
                routeNames.add(r.name);
            }
        }
        expect(routeNames.size).toBeGreaterThan(10);

        const missing = [];
        for (const entry of CORE_NAV_ENTRIES) {
            if (entry.route?.name && !routeNames.has(entry.route.name)) {
                missing.push(`nav:${entry.id}->${entry.route.name}`);
            }
        }
        for (const entry of CORE_TOOLS_ENTRIES) {
            if (entry.comingSoon || !entry.route?.name) {
                continue;
            }
            if (!routeNames.has(entry.route.name)) {
                missing.push(`tool:${entry.name}->${entry.route.name}`);
            }
        }
        for (const entry of CORE_COMMAND_ENTRIES) {
            if (entry.type !== "navigation" || !entry.route?.name) {
                continue;
            }
            if (!routeNames.has(entry.route.name)) {
                missing.push(`cmd:${entry.id}->${entry.route.name}`);
            }
        }
        expect(missing).toEqual([]);
    });
});
