// SPDX-License-Identifier: 0BSD

import { copyTextToClipboard } from "./clipboardUtils.js";
import { formatFatalErrorReport, reportBootFailure, type FatalErrorRecord } from "./fatalErrorState.js";

export type BootSplashFatalPayload = Partial<FatalErrorRecord> & {
    kind: "frontend" | "backend";
    message: string;
};

export function showBootSplashFatalError(payload: BootSplashFatalPayload): FatalErrorRecord {
    const record = reportBootFailure({
        ...payload,
        timestamp: payload.timestamp || Date.now(),
    });

    const splash = typeof document !== "undefined" ? document.getElementById("meshchatx-boot-splash") : null;
    if (!splash) {
        return record;
    }

    splash.setAttribute("data-state", "error");
    splash.setAttribute("aria-busy", "false");

    const line = splash.querySelector("[data-boot-line]");
    if (line) {
        line.textContent = record.message;
    }

    const title = splash.querySelector<HTMLElement>("[data-boot-title]");
    if (title && record.title) {
        title.textContent = record.title;
        title.hidden = false;
    }

    const details = splash.querySelector<HTMLElement>("[data-boot-details]");
    if (details) {
        const detailText = [record.details, record.stack].filter(Boolean).join("\n\n");
        if (detailText) {
            details.textContent = detailText;
            details.hidden = false;
        }
    }

    const actions = splash.querySelector<HTMLElement>("[data-boot-actions]");
    if (actions) {
        actions.hidden = false;
    }

    wireBootSplashActions(splash, record);
    return record;
}

function wireBootSplashActions(splash: HTMLElement, record: FatalErrorRecord): void {
    const reloadBtn = splash.querySelector<HTMLElement>("[data-boot-reload]");
    if (reloadBtn && !reloadBtn.dataset.wired) {
        reloadBtn.dataset.wired = "1";
        reloadBtn.addEventListener("click", () => {
            window.location.reload();
        });
    }

    const copyBtn = splash.querySelector<HTMLElement>("[data-boot-copy]");
    if (copyBtn && !copyBtn.dataset.wired) {
        copyBtn.dataset.wired = "1";
        copyBtn.addEventListener("click", async () => {
            const report = formatFatalErrorReport(record);
            const ok = await copyTextToClipboard(report);
            copyBtn.setAttribute("data-copied", ok ? "1" : "0");
            if (ok) {
                const label = copyBtn.querySelector("[data-boot-copy-label]");
                if (label) {
                    const previous = label.textContent;
                    label.textContent = label.getAttribute("data-copied-label") || "Copied";
                    window.setTimeout(() => {
                        label.textContent = previous;
                    }, 1800);
                }
            }
        });
    }
}
