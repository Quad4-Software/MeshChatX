// SPDX-License-Identifier: 0BSD

import { describe, it, expect } from "vitest";
import * as libs from "@/libs/index.js";

describe("libs/index barrel", () => {
    it("exports the public MeshChatX lib surface", () => {
        expect(typeof libs.createEmitter).toBe("function");
        expect(typeof libs.emitter).toBe("function");
        expect(typeof libs.uuidv4).toBe("function");
        expect(typeof libs.randomUuidV4).toBe("function");
        expect(typeof libs.formatDate).toBe("function");
        expect(typeof libs.fromNow).toBe("function");
        expect(typeof libs.relativeLabel).toBe("function");
        expect(typeof libs.meshDate).toBe("function");
        expect(typeof libs.clickOutside.install).toBe("function");
        expect(typeof libs.processDirectiveArguments).toBe("function");
        expect(typeof libs.bindingsEqual).toBe("function");
        expect(Array.isArray(libs.FROM_NOW_GOLDEN)).toBe(true);
        expect(Array.isArray(libs.SUPPORTED_FORMAT_TOKENS)).toBe(true);
        expect(libs.FROM_NOW_GOLDEN.length).toBeGreaterThan(10);
    });
});
