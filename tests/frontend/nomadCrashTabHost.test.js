// SPDX-License-Identifier: 0BSD
import { describe, expect, it } from "vitest";
import {
    shouldShowCrashTabHost,
    resolveCrashTabPageContent,
    canRetryCrashTabRender,
    resolveNomadCrashTabContentClass,
} from "../../meshchatx/src/frontend/features/nomadnetwork/lib/nomadCrashTabHost.js";

const node = { destination_hash: "aabbccddeeff00112233445566778899" };

describe("nomadCrashTabHost", () => {
    it("keeps the crash-tab host mounted while downloading (warm iframe)", () => {
        expect(
            shouldShowCrashTabHost({
                selectedNode: node,
                nodePagePath: `${node.destination_hash}:/page/index.mu`,
                showCancelledPageState: false,
                nodePageContent: null,
                showEmptyPageState: false,
            })
        ).toBe(true);
    });

    it("hides the crash-tab host for cancelled, failed, and empty states", () => {
        expect(
            shouldShowCrashTabHost({
                selectedNode: node,
                nodePagePath: `${node.destination_hash}:/page/index.mu`,
                showCancelledPageState: true,
                nodePageContent: "nomadnet.page_download_cancelled",
                showEmptyPageState: false,
            })
        ).toBe(false);

        expect(
            shouldShowCrashTabHost({
                selectedNode: node,
                nodePagePath: `${node.destination_hash}:/page/index.mu`,
                showCancelledPageState: false,
                nodePageContent: "Failed loading page: timeout",
                showEmptyPageState: false,
            })
        ).toBe(false);

        expect(
            shouldShowCrashTabHost({
                selectedNode: node,
                nodePagePath: `${node.destination_hash}:/page/index.mu`,
                showCancelledPageState: false,
                nodePageContent: "",
                showEmptyPageState: true,
            })
        ).toBe(false);
    });

    it("clears crash-tab content while loading or on status text", () => {
        expect(
            resolveCrashTabPageContent({
                isLoadingNodePage: true,
                nodePageContent: ">#!\n# Hi",
            })
        ).toBe("");
        expect(
            resolveCrashTabPageContent({
                isLoadingNodePage: false,
                nodePageContent: "nomadnet.page_download_cancelled",
            })
        ).toBe("");
        expect(
            resolveCrashTabPageContent({
                isLoadingNodePage: false,
                nodePageContent: ">#!\n# Hi",
            })
        ).toBe(">#!\n# Hi");
    });

    it("allows retry only after crash-tab paint abort with real page content", () => {
        expect(
            canRetryCrashTabRender({
                pageRenderAborted: true,
                nodePageContent: ">#!\n# Hi",
            })
        ).toBe(true);
        expect(
            canRetryCrashTabRender({
                pageRenderAborted: true,
                nodePageContent: "nomadnet.page_download_cancelled",
            })
        ).toBe(false);
        expect(
            canRetryCrashTabRender({
                pageRenderAborted: false,
                nodePageContent: ">#!\n# Hi",
            })
        ).toBe(false);
    });

    it("builds micron content classes for the isolated renderer", () => {
        expect(
            resolveNomadCrashTabContentClass({
                nodePagePath: "aabb:/page/index.mu",
                isShowingNodePageSource: false,
            })
        ).toContain("nomad-page-rich");
        expect(
            resolveNomadCrashTabContentClass({
                nodePagePath: "aabb:/page/index.mu",
                isShowingNodePageSource: true,
            })
        ).toBe("source bg-black");
    });
});
