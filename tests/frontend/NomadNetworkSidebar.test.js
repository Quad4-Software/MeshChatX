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
});
