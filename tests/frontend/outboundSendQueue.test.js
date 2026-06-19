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

    it("skips cancelled jobs still waiting in the queue", async () => {
        const order = [];
        let releaseFirst;
        const firstGate = new Promise((r) => {
            releaseFirst = r;
        });
        const processJob = vi.fn(async (job) => {
            order.push(`start:${job.id}`);
            if (job.id === "a") {
                await firstGate;
            }
            order.push(`end:${job.id}`);
        });
        const q = createOutboundQueue(processJob);
        q.enqueue({ id: "a" });
        q.enqueue({ id: "b", cancelKey: "peer|reply|hello|" });
        await new Promise((r) => setTimeout(r, 5));
        q.cancelJob({ cancelKey: "peer|reply|hello|" });
        releaseFirst();
        await new Promise((r) => setTimeout(r, 20));
        expect(order).toEqual(["start:a", "end:a"]);
        expect(processJob).toHaveBeenCalledTimes(1);
    });

    it("sets cancelled on the in-flight job for cooperative abort", async () => {
        let inFlightJob;
        let release;
        const gate = new Promise((r) => {
            release = r;
        });
        const q = createOutboundQueue(async (job) => {
            inFlightJob = job;
            await gate;
        });
        q.enqueue({ id: "a", pendingHash: "pending-1" });
        await new Promise((r) => setTimeout(r, 5));
        q.cancelJob({ pendingHash: "pending-1" });
        expect(inFlightJob?.cancelled).toBe(true);
        release();
        await new Promise((r) => setTimeout(r, 10));
    });
});
