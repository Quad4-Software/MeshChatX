// SPDX-License-Identifier: 0BSD

/**
 * Oracle tests for RRC available-rooms refresh sync.
 *
 * Guarantee: a hub /list snapshot fully replaces available_rooms. The
 * Available Rooms UI shows only unjoined rooms from that map.
 */
import { describe, expect, it } from "vitest";
import { applyAvailableRoomsSnapshot, diffAvailableRooms, unjoinedAvailableRooms } from "@/js/rrcAvailableRooms.js";

/** Independent oracle for unjoined sidebar rows. */
function oracleUnjoined(availableRooms, knownRooms) {
    const known = new Set(Array.isArray(knownRooms) ? knownRooms : []);
    if (!availableRooms || typeof availableRooms !== "object") {
        return [];
    }
    return Object.keys(availableRooms)
        .filter((name) => typeof name === "string" && name && !known.has(name))
        .sort()
        .map((name) => {
            const topic = availableRooms[name];
            return {
                name,
                topic: typeof topic === "string" && topic ? topic : null,
            };
        });
}

/** Independent oracle for add/remove/topic-update after a list replace. */
function oracleDiff(previous, next) {
    const prev = previous && typeof previous === "object" && !Array.isArray(previous) ? previous : {};
    const nxt = next && typeof next === "object" && !Array.isArray(next) ? next : {};
    const added = Object.keys(nxt)
        .filter((k) => !(k in prev))
        .sort();
    const removed = Object.keys(prev)
        .filter((k) => !(k in nxt))
        .sort();
    const updated = Object.keys(nxt)
        .filter((k) => k in prev && (prev[k] || null) !== (nxt[k] || null))
        .sort();
    return { added, removed, updated };
}

describe("rrcAvailableRooms oracles", () => {
    it("oracle: unjoined rooms exclude known rooms and sort by name", () => {
        const available = { zebra: null, lobby: "Main", alpha: "A" };
        const known = ["lobby"];
        expect(unjoinedAvailableRooms(available, known)).toEqual(oracleUnjoined(available, known));
        expect(unjoinedAvailableRooms(available, known)).toEqual([
            { name: "alpha", topic: "A" },
            { name: "zebra", topic: null },
        ]);
    });

    it("oracle: empty or invalid available maps yield no unjoined rooms", () => {
        expect(unjoinedAvailableRooms(null, ["lobby"])).toEqual([]);
        expect(unjoinedAvailableRooms(undefined, ["lobby"])).toEqual([]);
        expect(unjoinedAvailableRooms([], ["lobby"])).toEqual([]);
        expect(unjoinedAvailableRooms({ lobby: "Main" }, ["lobby"])).toEqual([]);
    });

    it("oracle: list refresh replace adds new rooms and removes gone ones", () => {
        const previous = { lobby: "Main", gone: null, kept: "Old" };
        const next = { lobby: "Renamed", kept: "Old", fresh: null };
        const applied = applyAvailableRoomsSnapshot(previous, next);
        expect(applied).toEqual(next);
        expect(diffAvailableRooms(previous, applied)).toEqual(oracleDiff(previous, applied));
        expect(diffAvailableRooms(previous, applied)).toEqual({
            added: ["fresh"],
            removed: ["gone"],
            updated: ["lobby"],
        });
    });

    it("oracle: empty list snapshot clears all available rooms", () => {
        const previous = { lobby: "Main", random: null };
        const applied = applyAvailableRoomsSnapshot(previous, {});
        expect(applied).toEqual({});
        expect(diffAvailableRooms(previous, applied)).toEqual({
            added: [],
            removed: ["lobby", "random"],
            updated: [],
        });
    });

    it("fuzz: random maps match independent unjoined and diff oracles", () => {
        const names = ["a", "b", "c", "d", "e", "f"];
        for (let i = 0; i < 80; i++) {
            const available = {};
            const known = [];
            const next = {};
            for (const name of names) {
                if (Math.random() < 0.5) {
                    available[name] = Math.random() < 0.5 ? `t-${name}` : null;
                }
                if (Math.random() < 0.35) {
                    known.push(name);
                }
                if (Math.random() < 0.5) {
                    next[name] = Math.random() < 0.5 ? `n-${name}` : null;
                }
            }
            expect(unjoinedAvailableRooms(available, known)).toEqual(oracleUnjoined(available, known));
            const applied = applyAvailableRoomsSnapshot(available, next);
            expect(diffAvailableRooms(available, applied)).toEqual(oracleDiff(available, applied));
            for (const name of Object.keys(available)) {
                if (!(name in next)) {
                    expect(applied).not.toHaveProperty(name);
                }
            }
            for (const name of Object.keys(next)) {
                expect(applied[name]).toBe(next[name]);
            }
        }
    });
});
