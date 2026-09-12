// SPDX-License-Identifier: 0BSD

import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { useNomadNodesList } from "../../meshchatx/src/frontend/js/nomadnet/useNomadNodesList.js";

describe("useNomadNodesList", () => {
    let api;

    beforeEach(() => {
        api = {
            get: vi.fn(async () => ({ data: { announces: [], total_count: 0 } })),
            isCancel: vi.fn(() => false),
        };
        window.api = api;
    });

    afterEach(() => {
        delete window.api;
        vi.useRealTimers();
    });

    it("starts with empty list state", () => {
        const list = useNomadNodesList();
        expect(list.nodes.value).toEqual({});
        expect(list.totalNodesCount.value).toBe(0);
        expect(list.hasMoreNodes.value).toBe(true);
        expect(list.isLoadingMoreNodes.value).toBe(false);
        expect(list.isSearchingNodes.value).toBe(false);
        expect(list.nodesSearchTerm.value).toBe("");
        expect(list.pageSize.value).toBe(50);
    });

    it("fetches announces and populates nodes keyed by destination hash", async () => {
        api.get.mockResolvedValueOnce({
            data: {
                announces: [
                    { destination_hash: "a".repeat(32), display_name: "A" },
                    { destination_hash: "b".repeat(32), display_name: "B" },
                ],
                total_count: 2,
            },
        });
        const list = useNomadNodesList();
        await list.getNomadnetworkNodeAnnounces();
        expect(api.get).toHaveBeenCalledWith(
            "/api/v1/announces",
            expect.objectContaining({
                params: expect.objectContaining({
                    aspect: "nomadnetwork.node",
                    limit: 50,
                    offset: 0,
                    search: "",
                }),
            })
        );
        expect(Object.keys(list.nodes.value)).toHaveLength(2);
        expect(list.nodes.value["a".repeat(32)].display_name).toBe("A");
        expect(list.totalNodesCount.value).toBe(2);
        expect(list.hasMoreNodes.value).toBe(false);
        expect(list.isSearchingNodes.value).toBe(false);
    });

    it("keeps hasMoreNodes true when a full page is returned", async () => {
        const announces = Array.from({ length: 50 }, (_, i) => ({
            destination_hash: `${i}`.padStart(32, "0"),
        }));
        api.get.mockResolvedValueOnce({ data: { announces, total_count: 100 } });
        const list = useNomadNodesList();
        await list.getNomadnetworkNodeAnnounces();
        expect(list.hasMoreNodes.value).toBe(true);
    });

    it("append mode uses the current node count as offset and keeps existing nodes", async () => {
        const list = useNomadNodesList();
        list.updateNodeFromAnnounce({ destination_hash: "x".repeat(32) });
        api.get.mockResolvedValueOnce({
            data: { announces: [{ destination_hash: "y".repeat(32) }], total_count: 2 },
        });
        await list.getNomadnetworkNodeAnnounces(true);
        expect(api.get).toHaveBeenCalledWith(
            "/api/v1/announces",
            expect.objectContaining({
                params: expect.objectContaining({ offset: 1 }),
            })
        );
        expect(Object.keys(list.nodes.value)).toHaveLength(2);
    });

    it("loadMoreNodes appends only when more pages exist", async () => {
        const list = useNomadNodesList();
        list.hasMoreNodes.value = false;
        await list.loadMoreNodes();
        expect(api.get).not.toHaveBeenCalled();

        api.get.mockResolvedValueOnce({ data: { announces: [], total_count: 0 } });
        list.hasMoreNodes.value = true;
        await list.loadMoreNodes();
        expect(api.get).toHaveBeenCalledTimes(1);
        expect(list.isLoadingMoreNodes.value).toBe(false);
    });

    it("debounces search input and forwards the search term", async () => {
        vi.useFakeTimers();
        const list = useNomadNodesList();
        list.onNodesSearchChanged("nodequery");
        expect(list.nodesSearchTerm.value).toBe("nodequery");
        expect(list.isSearchingNodes.value).toBe(true);
        expect(api.get).not.toHaveBeenCalled();

        await vi.advanceTimersByTimeAsync(500);
        expect(api.get).toHaveBeenCalledTimes(1);
        expect(api.get).toHaveBeenCalledWith(
            "/api/v1/announces",
            expect.objectContaining({
                params: expect.objectContaining({ search: "nodequery" }),
            })
        );
        expect(list.isSearchingNodes.value).toBe(false);
    });

    it("resets the debounce when the search term changes quickly", async () => {
        vi.useFakeTimers();
        const list = useNomadNodesList();
        list.onNodesSearchChanged("fi");
        await vi.advanceTimersByTimeAsync(300);
        list.onNodesSearchChanged("final");
        await vi.advanceTimersByTimeAsync(300);
        expect(api.get).not.toHaveBeenCalled();
        await vi.advanceTimersByTimeAsync(200);
        expect(api.get).toHaveBeenCalledTimes(1);
        expect(api.get).toHaveBeenCalledWith(
            "/api/v1/announces",
            expect.objectContaining({
                params: expect.objectContaining({ search: "final" }),
            })
        );
    });

    it("does not clear isSearchingNodes for a stale request superseded by a newer search", async () => {
        const pending = [];
        api.get.mockImplementation(
            () =>
                new Promise((resolve, reject) => {
                    pending.push({ resolve, reject });
                })
        );
        api.isCancel.mockImplementation((e) => e?.isCancelled === true);

        const list = useNomadNodesList();
        const first = list.getNomadnetworkNodeAnnounces();
        const second = list.getNomadnetworkNodeAnnounces();
        expect(pending.length).toBe(2);

        pending[0].reject({ isCancelled: true });
        await first;
        // the newer request is still in flight, so the indicator must stay on
        expect(list.isSearchingNodes.value).toBe(true);

        pending[1].resolve({ data: { announces: [], total_count: 0 } });
        await second;
        expect(list.isSearchingNodes.value).toBe(false);
    });

    it("aborts the previous controller on a non-append fetch", async () => {
        const list = useNomadNodesList();
        const first = list.getNomadnetworkNodeAnnounces();
        const abortedController = list.nodesListAbortController.value;
        const abortSpy = vi.spyOn(abortedController, "abort");
        const second = list.getNomadnetworkNodeAnnounces();
        expect(abortSpy).toHaveBeenCalledTimes(1);
        await Promise.all([first, second]);
    });

    it("swallows cancel errors and logs other failures", async () => {
        const list = useNomadNodesList();
        api.isCancel.mockReturnValueOnce(true);
        api.get.mockRejectedValueOnce(new Error("cancelled"));
        await expect(list.getNomadnetworkNodeAnnounces()).resolves.toBeUndefined();
        expect(list.isSearchingNodes.value).toBe(false);

        const logSpy = vi.spyOn(console, "log").mockImplementation(() => {});
        api.get.mockRejectedValueOnce(new Error("boom"));
        await list.getNomadnetworkNodeAnnounces();
        expect(logSpy).toHaveBeenCalled();
        logSpy.mockRestore();
    });
});
