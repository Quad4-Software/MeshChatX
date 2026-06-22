import { describe, it, expect, vi, beforeEach, afterEach } from "vitest";
import { handleRichHtmlLinkClick, openExternalHttpUrl } from "@/js/NomadRichHtmlLinks.js";

function clickEvent(target) {
    const ev = new MouseEvent("click", { bubbles: true, cancelable: true });
    Object.defineProperty(ev, "target", { value: target });
    return ev;
}

describe("NomadRichHtmlLinks", () => {
    describe("openExternalHttpUrl", () => {
        it("opens http(s) in a new window", () => {
            const opener = vi.fn();
            openExternalHttpUrl("https://example.com", opener);
            expect(opener).toHaveBeenCalledWith("https://example.com", "_blank", "noopener,noreferrer");
        });

        it("ignores empty urls", () => {
            const opener = vi.fn();
            openExternalHttpUrl("", opener);
            openExternalHttpUrl(null, opener);
            expect(opener).not.toHaveBeenCalled();
        });
    });

    describe("handleRichHtmlLinkClick", () => {
        let holder;

        beforeEach(() => {
            holder = document.createElement("div");
            document.body.appendChild(holder);
        });

        afterEach(() => {
            document.body.removeChild(holder);
        });

        it("routes nomadnet links through onNomadUrl", () => {
            holder.innerHTML = '<a class="nomadnet-link" data-nomadnet-url="abc123:/page/index.mu">n</a>';
            const onNomadUrl = vi.fn();
            const ev = clickEvent(holder.querySelector("a"));
            expect(handleRichHtmlLinkClick(ev, { onNomadUrl })).toBe(true);
            expect(onNomadUrl).toHaveBeenCalledWith("abc123:/page/index.mu");
            expect(ev.defaultPrevented).toBe(true);
        });

        it("opens http links externally", () => {
            holder.innerHTML = '<a href="https://example.com">x</a>';
            const openExternalHttp = vi.fn();
            const ev = clickEvent(holder.querySelector("a"));
            expect(handleRichHtmlLinkClick(ev, { openExternalHttp })).toBe(true);
            expect(openExternalHttp).toHaveBeenCalledWith("https://example.com/");
            expect(ev.defaultPrevented).toBe(true);
        });

        it("scrolls fragment anchors within scrollRoot", () => {
            holder.innerHTML = '<div id="target">t</div><a href="#target">f</a>';
            const target = holder.querySelector("#target");
            target.scrollIntoView = vi.fn();
            const ev = clickEvent(holder.querySelector("a"));
            expect(handleRichHtmlLinkClick(ev, { scrollRoot: holder })).toBe(true);
            expect(target.scrollIntoView).toHaveBeenCalled();
            expect(ev.defaultPrevented).toBe(true);
        });

        it("blocks unhandled anchor navigation by default", () => {
            holder.innerHTML = '<a href="javascript:alert(1)">bad</a>';
            const openExternalHttp = vi.fn();
            const ev = clickEvent(holder.querySelector("a"));
            expect(handleRichHtmlLinkClick(ev, { openExternalHttp })).toBe(true);
            expect(ev.defaultPrevented).toBe(true);
            expect(openExternalHttp).not.toHaveBeenCalled();
        });

        it("routes lxmf links through onLxmfAddress for valid 32-char hex", () => {
            const hash = "a".repeat(32);
            holder.innerHTML = `<a class="lxmf-link" data-lxmf-address="${hash}">lx</a>`;
            const onLxmfAddress = vi.fn();
            const ev = clickEvent(holder.querySelector("a"));
            expect(handleRichHtmlLinkClick(ev, { onLxmfAddress })).toBe(true);
            expect(onLxmfAddress).toHaveBeenCalledWith(hash);
            expect(ev.defaultPrevented).toBe(true);
        });

        it("rejects invalid lxmf addresses", () => {
            holder.innerHTML = '<a class="lxmf-link" data-lxmf-address="not-a-valid-hash">lx</a>';
            const onLxmfAddress = vi.fn();
            const ev = clickEvent(holder.querySelector("a"));
            expect(handleRichHtmlLinkClick(ev, { onLxmfAddress })).toBe(true);
            expect(onLxmfAddress).not.toHaveBeenCalled();
            expect(ev.defaultPrevented).toBe(true);
        });

        it("routes openNode actions through onOpenNode", () => {
            holder.innerHTML = '<span data-action="openNode" data-destination="deadbeef:/page/x.mu">go</span>';
            const onOpenNode = vi.fn();
            const ev = clickEvent(holder.querySelector("[data-action=openNode]"));
            expect(handleRichHtmlLinkClick(ev, { onOpenNode })).toBe(true);
            expect(onOpenNode).toHaveBeenCalledWith("deadbeef:/page/x.mu", null);
            expect(ev.defaultPrevented).toBe(true);
        });

        it("returns false for unrelated clicks", () => {
            holder.innerHTML = "<span>plain text</span>";
            const ev = clickEvent(holder.querySelector("span"));
            expect(handleRichHtmlLinkClick(ev, {})).toBe(false);
            expect(ev.defaultPrevented).toBe(false);
        });
    });
});
