// SPDX-License-Identifier: 0BSD

import { describe, it, expect } from "vitest";
import {
    buildDisplayGroupsNewestFirst,
    prependDisplayGroupsNewestFirst,
    displayGroupHashesOldestFirst,
    incrementalPrependMatchesFullRebuild,
} from "@/features/messages/lib/conversationDisplayGroups.ts";

function mulberry32(seed) {
    let t = seed >>> 0;
    return () => {
        t += 0x6d2b79f5;
        let r = Math.imul(t ^ (t >>> 15), 1 | t);
        r ^= r + Math.imul(r ^ (r >>> 7), 61 | r);
        return ((r ^ (r >>> 14)) >>> 0) / 4294967296;
    };
}

function chatItem(hash, opts = {}) {
    const { outbound = false, image = false, failed = false, spam = false, caption = "", reply = false } = opts;
    const fields = {};
    if (image) {
        fields.image = { image_type: "png" };
    }
    return {
        type: "lxmf_message",
        is_outbound: outbound,
        lxmf_message: {
            hash,
            content: caption,
            state: failed ? "failed" : "delivered",
            is_spam: spam ? 1 : 0,
            reply_to_hash: reply ? "parent" : null,
            fields,
        },
    };
}

function productionMergePredicate(item) {
    const m = item?.lxmf_message;
    if (!m) {
        return false;
    }
    if (m.is_spam) {
        return false;
    }
    if (["cancelled", "failed", "rejected"].includes(m.state)) {
        return false;
    }
    if (!m.fields?.image) {
        return false;
    }
    if (m.reply_to_hash) {
        return false;
    }
    const c = (m.content || "").trim();
    if (c && !/\.(jpe?g|png|gif|webp)$/i.test(c)) {
        return false;
    }
    if (m.fields?.audio || m.fields?.file_attachments?.length) {
        return false;
    }
    return true;
}

function randomItems(rng, count) {
    const items = [];
    for (let i = 0; i < count; i++) {
        const image = rng() < 0.35;
        const outbound = rng() < 0.5;
        const failed = rng() < 0.05;
        items.push(
            chatItem(`h${i}`, {
                outbound,
                image,
                failed,
                caption: image && rng() < 0.2 ? "photo.jpg" : "",
            })
        );
    }
    return items;
}

describe("conversationDisplayGroups oracle", () => {
    it("incremental prepend keys match full rebuild across random paginated loads", () => {
        const rng = mulberry32(0xdecafbad);
        for (let trial = 0; trial < 80; trial++) {
            const n = 5 + Math.floor(rng() * 120);
            const items = randomItems(rng, n);
            const pages = [];
            let count = 0;
            while (count < n) {
                const step = 1 + Math.floor(rng() * 25);
                count = Math.min(n, count + step);
                pages.push(count);
            }
            expect(incrementalPrependMatchesFullRebuild(items, pages, productionMergePredicate)).toBe(true);
        }
    });

    it("image strip spanning prepend boundary matches full rebuild", () => {
        const existing = [
            chatItem("m1", { image: true, outbound: true }),
            chatItem("m2", { image: true, outbound: true }),
            chatItem("m3"),
        ];
        const prepended = [
            chatItem("p1", { image: true, outbound: true }),
            chatItem("p2", { image: true, outbound: true }),
        ];
        const all = prepended.concat(existing);
        const full = buildDisplayGroupsNewestFirst(all, productionMergePredicate);
        const base = buildDisplayGroupsNewestFirst(existing, productionMergePredicate);
        const inc = prependDisplayGroupsNewestFirst(base, prepended, productionMergePredicate);
        expect(inc.map((g) => g.key)).toEqual(full.map((g) => g.key));
        expect(displayGroupHashesOldestFirst(inc)).toEqual(displayGroupHashesOldestFirst(full));
    });

    it("splitting outbound direction at boundary does not cross-merge strips", () => {
        const existing = [chatItem("m1", { image: true, outbound: true }), chatItem("m2")];
        const prepended = [chatItem("p1", { image: true, outbound: false })];
        const all = prepended.concat(existing);
        const full = buildDisplayGroupsNewestFirst(all, productionMergePredicate);
        const inc = prependDisplayGroupsNewestFirst(
            buildDisplayGroupsNewestFirst(existing, productionMergePredicate),
            prepended,
            productionMergePredicate
        );
        expect(inc.map((g) => g.key)).toEqual(full.map((g) => g.key));
    });

    it("every visible item hash appears exactly once in flattened groups", () => {
        const items = randomItems(mulberry32(42), 60);
        const groups = buildDisplayGroupsNewestFirst(items, productionMergePredicate);
        const flat = displayGroupHashesOldestFirst(groups);
        expect(flat).toHaveLength(items.length);
        expect(new Set(flat).size).toBe(items.length);
    });

    it("failed image state breaks strip grouping in full rebuild oracle", () => {
        const items = [chatItem("a", { image: true, outbound: true }), chatItem("b", { image: true, outbound: true })];
        const grouped = buildDisplayGroupsNewestFirst(items, productionMergePredicate);
        expect(grouped.some((g) => g.type === "imageGroup")).toBe(true);

        items[0].lxmf_message.state = "failed";
        const ungrouped = buildDisplayGroupsNewestFirst(items, productionMergePredicate);
        expect(ungrouped.every((g) => g.type === "single")).toBe(true);
    });
});
