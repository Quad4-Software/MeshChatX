// SPDX-License-Identifier: 0BSD

import { describe, it, expect } from "vitest";
import { readFileSync } from "node:fs";
import { resolve } from "node:path";
import {
    DEFAULT_SHELL_PRECACHE,
    renderServiceWorkerSource,
    stripEsmForServiceWorker,
    writeServiceWorker,
} from "../../scripts/build/generate_service_worker.mjs";

const ROOT = resolve(import.meta.dirname, "../..");

describe("service worker build", () => {
    it("template bootstrap wires runtime prune, claim, and fetch resolve", () => {
        const template = readFileSync(resolve(ROOT, "meshchatx/src/frontend/sw/service-worker.template.js"), "utf8");
        expect(template).toContain("createShellRuntime");
        expect(template).toContain("pruneOldShellCaches");
        expect(template).toContain("skipWaiting");
        expect(template).toContain("clients.claim");
        expect(template).toContain("navigationPreload");
        expect(template).toContain("UPDATE_MESSAGE_TYPE");
        expect(template).toContain("handleFetchEvent");
        expect(template).not.toContain("preloadResponse: event.preloadResponse");
        expect(template).toContain("__MESHCHATX_SW_BUILD_ID__");
        expect(template).toContain("__MESHCHATX_SW_PRECACHE_JSON__");
    });

    it("stripEsmForServiceWorker removes imports and exports", () => {
        const stripped = stripEsmForServiceWorker(
            'import { x } from "./y.js";\nexport function foo() { return 1; }\nexport const BAR = 2;\n'
        );
        expect(stripped).not.toContain("import ");
        expect(stripped).not.toContain("export ");
        expect(stripped).toContain("function foo()");
        expect(stripped).toContain("const BAR = 2");
    });

    it("renderServiceWorkerSource inlines policy+runtime and injects build id", () => {
        const source = renderServiceWorkerSource({
            buildId: "test-build",
            precacheUrls: DEFAULT_SHELL_PRECACHE,
        });
        expect(source).toContain('const BUILD_ID = "test-build"');
        expect(source).toContain('"/boot-theme.js"');
        expect(source).toContain("function classifyShellRequest");
        expect(source).toContain("function createShellRuntime");
        expect(source).toContain("function handleFetchEvent");
        expect(source).toContain("handleFetchEvent(event, runtime, self.location.origin)");
        expect(source).not.toContain("preloadResponse: event.preloadResponse");
        expect(source).toContain("function settlePreloadResponse");
        expect(source).toContain("function shouldAttachNavigationPreload");
        expect(source).toContain("function findForbiddenCachedUrls");
        expect(source).not.toContain("__MESHCHATX_SW_BUILD_ID__");
        expect(source).not.toContain("__MESHCHATX_SW_PRECACHE_JSON__");
        expect(source).not.toMatch(/^import /m);
        expect(source).toContain("pruneOldShellCaches");
    });

    it("public service-worker.js is generated for dev without placeholders", () => {
        const result = writeServiceWorker({ buildId: "dev" });
        const publicSw = readFileSync(result.outfile, "utf8");
        expect(publicSw).toContain('const BUILD_ID = "dev"');
        expect(publicSw).toContain("createShellRuntime");
        expect(publicSw).toContain("handleFetchEvent");
        expect(publicSw).toContain("resolveFetch");
        expect(publicSw).not.toContain("preloadResponse: event.preloadResponse");
        expect(publicSw).not.toContain("__MESHCHATX_SW_");
    });

    it("main.js uses client register helpers and skips Electron", () => {
        const main = readFileSync(resolve(ROOT, "meshchatx/src/frontend/main.js"), "utf8");
        expect(main).toContain("ElectronUtils.isElectron()");
        expect(main).toContain("decideControllerChangeReload");
        expect(main).toContain("serviceWorkerRegisterOptions");
        expect(main).toContain("isIgnorableServiceWorkerRegistrationError");
        expect(main).toContain("controllerchange");
        expect(main).toContain("registration.update()");
        expect(main).toContain("visibilitychange");
    });
});
