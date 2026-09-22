// SPDX-License-Identifier: 0BSD
import { render, cleanup, fireEvent } from "@testing-library/svelte";
import { describe, it, expect, vi, beforeEach, afterEach } from "vitest";
import NomadNetworkSidebar from "@/features/nomadnetwork/components/NomadNetworkSidebar.svelte";

describe("NomadNetworkSidebar.svelte", () => {
    beforeEach(() => {
        vi.clearAllMocks();
    });

    afterEach(() => {
        cleanup();
    });

    it("renders favourites and announces tabs", () => {
        const { getAllByText, getByText } = render(NomadNetworkSidebar, {
            favourites: [{ destination_hash: "aabb", display_name: "Node A" }],
            nodes: {
                ccdd: { destination_hash: "ccdd", display_name: "Node B" },
            },
        });

        expect(getAllByText(/favourites|nomadnet\.favourites/i).length).toBeGreaterThanOrEqual(1);
        expect(getByText(/announces|nomadnet\.announces/i)).toBeTruthy();
    });

    it("triggers onnodeclick when a favourite is clicked", async () => {
        const onnodeclick = vi.fn();
        const fav = { destination_hash: "aabb", display_name: "Node A" };
        const { getByText } = render(NomadNetworkSidebar, {
            favourites: [fav],
            nodes: {},
            onnodeclick,
        });

        const favItem = getByText("Node A");
        await fireEvent.click(favItem);

        expect(onnodeclick).toHaveBeenCalledWith(expect.objectContaining({ destination_hash: "aabb" }));
    });

    it("switches to announces tab and displays announced nodes", async () => {
        const { getByText } = render(NomadNetworkSidebar, {
            favourites: [],
            nodes: {
                ccdd: { destination_hash: "ccdd", display_name: "Announced Node" },
            },
        });

        const announcesTab = getByText(/announces|nomadnet\.announces/i);
        await fireEvent.click(announcesTab);

        expect(getByText("Announced Node")).toBeTruthy();
    });

    it("collapses into icon rail when collapsed is true", () => {
        const { container } = render(NomadNetworkSidebar, {
            favourites: [{ destination_hash: "aabb", display_name: "Node A" }],
            nodes: {},
            collapsed: true,
        });

        expect(container.querySelector(".w-16")).toBeTruthy();
    });

    it("mobile URL input calls onnavigateurl and clears", async () => {
        const onnavigateurl = vi.fn();
        const { getByPlaceholderText } = render(NomadNetworkSidebar, {
            favourites: [],
            nodes: {},
            onnavigateurl,
        });

        const input = getByPlaceholderText("Enter a Nomadnet URL");
        await fireEvent.input(input, {
            target: { value: "abcd1234abcd1234abcd1234abcd1234:/page/index.mu" },
        });
        await fireEvent.keyDown(input, { key: "Enter" });

        expect(onnavigateurl).toHaveBeenCalledWith("abcd1234abcd1234abcd1234abcd1234:/page/index.mu");
        expect(input.value).toBe("");
    });

    it("mobile URL input ignores blank submissions", async () => {
        const onnavigateurl = vi.fn();
        const { getByPlaceholderText } = render(NomadNetworkSidebar, {
            favourites: [],
            nodes: {},
            onnavigateurl,
        });

        const input = getByPlaceholderText("Enter a Nomadnet URL");
        await fireEvent.input(input, { target: { value: "   " } });
        await fireEvent.keyDown(input, { key: "Enter" });

        expect(onnavigateurl).not.toHaveBeenCalled();
    });

    it("keeps the announces list mounted while loading more", async () => {
        const { getByText, container } = render(NomadNetworkSidebar, {
            favourites: [],
            nodes: {
                ccdd: { destination_hash: "ccdd", display_name: "Announced Node" },
            },
            isLoadingMoreNodes: true,
            hasMoreNodes: true,
        });

        const announcesTab = getByText(/announces|nomadnet\.announces/i);
        await fireEvent.click(announcesTab);

        // regression: the loading spinner must not replace the list
        expect(getByText("Announced Node")).toBeTruthy();
        expect(container.querySelector(".animate-spin")).toBeTruthy();
    });

    it("switches announces ordering via the sort select", async () => {
        const { getByText, getByTitle } = render(NomadNetworkSidebar, {
            favourites: [],
            nodes: {
                aaaa: { destination_hash: "aaaa", display_name: "Zebra", announce_count: 1 },
                bbbb: { destination_hash: "bbbb", display_name: "Alpha", announce_count: 9 },
            },
        });

        const announcesTab = getByText(/announces|nomadnet\.announces/i);
        await fireEvent.click(announcesTab);

        const select = getByTitle(/sort announces|nomadnet\.sort_announces/i);
        await fireEvent.change(select, { target: { value: "name" } });

        const rows = [...document.querySelectorAll(".announce-card, [data-destination-hash]")].map(
            (el) => el.textContent
        );
        const alphaIdx = rows.findIndex((txt) => txt.includes("Alpha"));
        const zebraIdx = rows.findIndex((txt) => txt.includes("Zebra"));
        expect(alphaIdx).toBeGreaterThanOrEqual(0);
        expect(alphaIdx).toBeLessThan(zebraIdx);
    });
});
