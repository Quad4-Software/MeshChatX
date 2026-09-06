// SPDX-License-Identifier: 0BSD
import { describe, it, expect } from "vitest";
import { readFileSync } from "fs";
import { join } from "path";

function src(rel) {
    return readFileSync(join(process.cwd(), rel), "utf8");
}

describe("cross-surface identity unread oracle", () => {
    it("identity switch clears unread counters and shell WS handlers refresh them", () => {
        const identity = src("meshchatx/src/frontend/features/app-shell/lib/appShellIdentity.ts");
        const handlers = src("meshchatx/src/frontend/features/app-shell/lib/appShellWsHandlers.ts");
        const nav = src("meshchatx/src/frontend/features/app-shell/lib/appShellNav.ts");
        expect(identity).toContain("GlobalState.unreadConversationsCount = 0");
        expect(identity).toContain("GlobalState.missedCallsCount = 0");
        expect(identity).toContain("GlobalState.relayChatUnreadCount = 0");
        expect(handlers).toContain("createShellWsHandlers");
        expect(nav).toContain("updateUnreadConversationsCount");
        expect(nav).toContain("updateRelayChatUnreadCount");
    });
});
