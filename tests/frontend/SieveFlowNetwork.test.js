import { render, cleanup } from "@testing-library/svelte";
import { describe, expect, it, vi, afterEach } from "vitest";
import SieveFlowNetwork from "../../meshchatx/src/frontend/features/sieve-filters/components/SieveFlowNetwork.svelte";

vi.mock("vis-data", () => ({
    DataSet: vi.fn((items) => items),
}));

vi.mock("vis-network", () => ({
    Network: vi.fn(() => {
        throw new Error("graph init failed");
    }),
}));

describe("SieveFlowNetwork.svelte", () => {
    afterEach(() => {
        cleanup();
    });

    it("does not throw when graph backend fails", async () => {
        const warnSpy = vi.spyOn(console, "warn").mockImplementation(() => {});
        const { container } = render(SieveFlowNetwork, {
            props: {
                filters: [{ id: "r1", enabled: true, terms: ["spam"], action: "hide" }],
                folders: [],
                labels: {},
            },
        });

        await Promise.resolve();

        expect(container).toBeTruthy();
        expect(warnSpy).toHaveBeenCalledWith("SieveFlowNetwork rebuild failed:", expect.any(Error));
        warnSpy.mockRestore();
    });
});
