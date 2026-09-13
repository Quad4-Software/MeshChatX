// SPDX-License-Identifier: 0BSD

import { render, fireEvent, cleanup, screen } from "@testing-library/svelte";
import { describe, it, expect, afterEach, vi } from "vitest";
import PublishSiteModal from "../../meshchatx/src/frontend/features/micron-editor/components/PublishSiteModal.svelte";
import {
    buildPublishSiteEntries,
    buildSiteIndexPage,
    defaultPublishFilename,
    sanitizePublishFilename,
} from "../../meshchatx/src/frontend/features/micron-editor/lib/micronPublish.ts";

const TABS = [
    { id: 1, name: "Home", content: "h" },
    { id: 2, name: "About Us", content: "a" },
    { id: 3, name: "", content: "e" },
];

describe("micron publish-site helpers", () => {
    it("builds page entries from tabs with .mu filenames", () => {
        const entries = buildPublishSiteEntries(TABS);
        expect(entries.map((e) => e.filename)).toEqual(["Home.mu", "About_Us.mu", "page_3.mu"]);
        expect(entries.every((e) => e.include)).toBe(true);
    });

    it("sanitizes filenames on input", () => {
        expect(sanitizePublishFilename("My Page!.mu")).toBe("My_Page.mu");
        expect(sanitizePublishFilename("../evil")).toBe("evil");
        expect(sanitizePublishFilename("a/b")).toBe("ab");
    });

    it("keeps an existing allowed extension", () => {
        expect(defaultPublishFilename({ id: 1, name: "guide.md", content: "" }, 0)).toBe("guide.md");
        expect(defaultPublishFilename({ id: 2, name: "  ", content: "" }, 1)).toBe("page_2.mu");
    });

    it("builds an index page with links to each page", () => {
        const html = buildSiteIndexPage("aabb", [
            { name: "Home.mu", label: "Home" },
            { name: "About.mu", label: "About" },
        ]);
        expect(html).toContain(">Links");
        expect(html).toContain("[Home`aabb:/page/Home.mu]");
        expect(html).toContain("[About`aabb:/page/About.mu]");
    });
});

describe("PublishSiteModal.svelte", () => {
    afterEach(() => {
        cleanup();
    });

    it("emits publish with included pages only", async () => {
        const onpublish = vi.fn();
        render(PublishSiteModal, {
            props: {
                show: true,
                tabs: TABS,
                pageNodes: [{ node_id: "n1", name: "Srv", running: true }],
                onpublish,
            },
        });

        // Uncheck the second page.
        const checkboxes = screen.getAllByRole("checkbox");
        await fireEvent.click(checkboxes[1]);
        // Also uncheck index generation to keep the payload assertion simple.
        await fireEvent.click(checkboxes[checkboxes.length - 1]);

        const publishBtn = screen.getByText((_, el) => el?.textContent === "Publish 2 pages");
        await fireEvent.click(publishBtn);

        expect(onpublish).toHaveBeenCalledTimes(1);
        const payload = onpublish.mock.calls[0][0];
        expect(payload.nodeId).toBe("n1");
        expect(payload.generateIndex).toBe(false);
        expect(payload.pages.map((p) => p.name)).toEqual(["Home.mu", "page_3.mu"]);
    });

    it("requires a server name when creating a new server", async () => {
        const onpublish = vi.fn();
        render(PublishSiteModal, {
            props: {
                show: true,
                tabs: TABS,
                pageNodes: [],
                onpublish,
            },
        });

        const select = screen.getByLabelText("Mesh server");
        expect(select.value).toBe("__new");
        const publishBtn = screen.getByText((_, el) => el?.textContent === "Publish 3 pages");
        expect(publishBtn.disabled).toBe(true);

        const nameInput = screen.getByPlaceholderText("New server name");
        await fireEvent.input(nameInput, { target: { value: "Fresh" } });
        expect(publishBtn.disabled).toBe(false);
    });
});
