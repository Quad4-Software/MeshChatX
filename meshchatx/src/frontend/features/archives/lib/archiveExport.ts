// SPDX-License-Identifier: 0BSD

import DownloadUtils from "../../../js/DownloadUtils.js";
import type { ArchiveItem } from "./types.js";

/** Extract safe base filename from archive page path */
export function muExportBasename(archive?: Pick<ArchiveItem, "page_path"> | null): string {
    let base = (archive?.page_path || "page").split("/").pop() || "page";
    base = base.replace(/[\\/:*?"<>|]+/g, "_").trim() || "page";
    return base;
}

/** Determine target filename for export preserving known extensions */
export function muExportFilename(archive?: Pick<ArchiveItem, "page_path"> | null): string {
    const base = muExportBasename(archive);
    const lower = base.toLowerCase();
    const allowed = [".mu", ".md", ".txt", ".html"];
    if (allowed.some((ext) => lower.endsWith(ext))) {
        return base;
    }
    const without = base.includes(".") ? base.replace(/\.[^.]+$/, "") : base;
    return `${without || "page"}.mu`;
}

/** Determine disambiguated export filename with snapshot hash suffix */
export function muExportFilenameDisambiguated(archive?: Pick<ArchiveItem, "page_path" | "hash"> | null): string {
    const name = muExportFilename(archive);
    const match = name.match(/^(.+)(\.[^.]+)$/);
    const stem = match ? match[1] : name.replace(/\.[^.]+$/, "");
    const ext = match ? match[2] : ".mu";
    const short = (archive?.hash || "snap").substring(0, 8);
    return `${stem}_${short}${ext}`;
}

/** Download string content as a plain text file */
export async function downloadTextAsFile(content?: string | null, filename = "page.mu"): Promise<void> {
    const blob = new Blob([content ?? ""], { type: "text/plain;charset=utf-8" });
    await DownloadUtils.downloadFile(filename, blob);
}

/** Export archive content using its computed filename */
export async function exportArchiveAsMu(archive?: ArchiveItem | null): Promise<void> {
    if (!archive) {
        return;
    }
    await downloadTextAsFile(archive.content, muExportFilename(archive));
}
