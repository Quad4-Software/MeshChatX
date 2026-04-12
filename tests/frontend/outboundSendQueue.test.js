import { describe, it, expect, vi } from "vitest";
import { createOutboundQueue } from "@/js/outboundSendQueue";

describe("outboundSendQueue", () => {
    it("runs jobs one at a time so the second waits for the first", async () => {
        const order = [];
        const processJob = vi.fn(async (job) => {
            order.push(`start:${job.id}`);
            await new Promise((r) => setTimeout(r, 2));
            order.push(`end:${job.id}`);
        });
        const q = createOutboundQueue(processJob);
        q.enqueue({ id: "a" });
        q.enqueue({ id: "b" });
        await new Promise((r) => setTimeout(r, 30));
        expect(order).toEqual(["start:a", "end:a", "start:b", "end:b"]);
        expect(processJob).toHaveBeenCalledTimes(2);
    });

    it("does not start a second runner while the first is active", async () => {
        let concurrent = 0;
        let maxConcurrent = 0;
        const q = createOutboundQueue(async () => {
            concurrent += 1;
            maxConcurrent = Math.max(maxConcurrent, concurrent);
            await new Promise((r) => setTimeout(r, 5));
            concurrent -= 1;
        });
        q.enqueue({});
        q.enqueue({});
        q.enqueue({});
        await new Promise((r) => setTimeout(r, 40));
        expect(maxConcurrent).toBe(1);
    });
});
