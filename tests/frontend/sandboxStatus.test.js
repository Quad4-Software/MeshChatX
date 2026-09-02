import { describe, it, expect } from "vitest";
import {
    listSandboxFeatures,
    resolveSandboxFeature,
    sandboxSummaryActive,
    sandboxSummaryType,
} from "../../meshchatx/src/frontend/js/sandboxStatus.js";

describe("sandboxStatus", () => {
    it("marks active landlock as enabled with auto note", () => {
        const row = resolveSandboxFeature(
            {
                landlock_active: true,
                landlock_auto_enabled: true,
                landlock_kernel_supported: true,
            },
            "landlock"
        );
        expect(row.active).toBe(true);
        expect(row.badgeKey).toBe("app.enabled");
        expect(row.noteKey).toBe("app.landlock_auto_enabled");
    });

    it("marks unsupported appcontainer as unavailable", () => {
        const row = resolveSandboxFeature(
            {
                appcontainer_active: false,
                appcontainer_supported: false,
            },
            "appcontainer"
        );
        expect(row.active).toBe(false);
        expect(row.unavailable).toBe(true);
        expect(row.badgeKey).toBe("about.sandbox_status_unavailable");
        expect(row.noteKey).toBe("app.appcontainer_unsupported");
    });

    it("lists only features present in app info", () => {
        const rows = listSandboxFeatures({
            landlock_requested: true,
            seccomp_requested: true,
            landlock_active: true,
            seccomp_active: false,
            seccomp_kernel_supported: true,
        });
        expect(rows).toHaveLength(2);
        expect(rows.map((row) => row.id)).toEqual(["landlock", "seccomp"]);
    });

    it("summarizes combined landlock and seccomp", () => {
        expect(
            sandboxSummaryType({
                landlock_active: true,
                seccomp_active: true,
            })
        ).toBe("about.sandbox_type_landlock_seccomp");
        expect(
            sandboxSummaryActive({
                landlock_active: true,
                seccomp_active: true,
            })
        ).toBe(true);
    });

    it("summarizes inactive sandboxing", () => {
        expect(sandboxSummaryType({})).toBe("about.sandbox_type_none");
        expect(sandboxSummaryActive({})).toBe(false);
    });
});
