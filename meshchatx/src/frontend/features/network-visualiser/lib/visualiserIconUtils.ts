// SPDX-License-Identifier: 0BSD

import { getMdiIconPath } from "../../../js/mdiIconNames.js";

/**
 * Yield control back to the browser so it can paint and handle input events
 */
export function yieldToMain(): Promise<void> {
    if (typeof window !== "undefined" && (window as any).scheduler) {
        const sched = (window as any).scheduler;
        if (typeof sched.yield === "function") {
            return sched.yield();
        }
        if (typeof sched.postTask === "function") {
            return new Promise((resolve) => {
                sched.postTask(resolve, { priority: "user-blocking" });
            });
        }
    }
    return new Promise((resolve) => setTimeout(resolve, 0));
}

/**
 * Pick an adaptive chunk size based on hardware concurrency
 */
export function pickAdaptiveChunkSize(): number {
    const cores = (typeof navigator !== "undefined" && navigator.hardwareConcurrency) || 4;
    if (cores <= 2) return 60;
    if (cores <= 4) return 120;
    if (cores <= 6) return 250;
    return 500;
}

export function getMdiIconSvg(iconName: string, foregroundColor: string): string {
    const iconPath = getMdiIconPath(iconName);
    return `<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24"><path fill="${foregroundColor}" d="${iconPath}"/></svg>`;
}

export async function createIconImage(
    iconName: string,
    foregroundColor: string,
    backgroundColor: string,
    size: number = 64,
    iconCache: Record<string, string>,
    signal?: AbortSignal
): Promise<string | null> {
    const cacheKey = `${iconName}-${foregroundColor}-${backgroundColor}-${size}`;
    if (iconCache[cacheKey]) {
        return iconCache[cacheKey];
    }

    const cacheKeys = Object.keys(iconCache);
    if (cacheKeys.length >= 500) {
        const oldKey = cacheKeys[0];
        const oldUrl = iconCache[oldKey];
        if (oldUrl && oldUrl.startsWith("blob:")) {
            const stillUsed = Object.values(iconCache).some(
                (u, i) => u === oldUrl && Object.keys(iconCache)[i] !== oldKey
            );
            if (!stillUsed && typeof URL !== "undefined" && typeof URL.revokeObjectURL === "function") {
                URL.revokeObjectURL(oldUrl);
            }
        }
        delete iconCache[oldKey];
    }

    return new Promise((resolve) => {
        if (typeof document === "undefined") {
            resolve(null);
            return;
        }
        const canvas = document.createElement("canvas");
        canvas.width = size;
        canvas.height = size;
        const ctx = canvas.getContext("2d", { alpha: true });
        if (!ctx) {
            resolve(null);
            return;
        }

        const gradient = ctx.createLinearGradient(0, 0, 0, size);
        gradient.addColorStop(0, backgroundColor);
        gradient.addColorStop(1, backgroundColor);

        ctx.fillStyle = gradient;
        ctx.beginPath();
        ctx.arc(size / 2, size / 2, size / 2 - 2, 0, 2 * Math.PI);
        ctx.fill();

        const innerShadow = ctx.createRadialGradient(size / 2, size / 2, size / 2 - 10, size / 2, size / 2, size / 2);
        innerShadow.addColorStop(0, "rgba(0,0,0,0)");
        innerShadow.addColorStop(1, "rgba(0,0,0,0.15)");
        ctx.fillStyle = innerShadow;
        ctx.fill();

        const highlight = ctx.createLinearGradient(0, 0, 0, size);
        highlight.addColorStop(0, "rgba(255,255,255,0.25)");
        highlight.addColorStop(0.5, "rgba(255,255,255,0)");
        ctx.fillStyle = highlight;
        ctx.beginPath();
        ctx.arc(size / 2, size / 2, size / 2 - 4, 0, 2 * Math.PI);
        ctx.fill();

        ctx.strokeStyle = "rgba(255,255,255,0.2)";
        ctx.lineWidth = 2;
        ctx.stroke();

        const iconSvg = getMdiIconSvg(iconName, foregroundColor);
        const img = new Image();
        const svgBlob = new Blob([iconSvg], { type: "image/svg+xml" });
        const url = URL.createObjectURL(svgBlob);

        img.onload = () => {
            if (signal?.aborted) {
                URL.revokeObjectURL(url);
                resolve(null);
                return;
            }
            ctx.shadowColor = "rgba(0,0,0,0.2)";
            ctx.shadowBlur = 4;
            ctx.shadowOffsetX = 0;
            ctx.shadowOffsetY = 2;

            ctx.drawImage(img, size * 0.22, size * 0.22, size * 0.56, size * 0.56);

            ctx.shadowColor = "transparent";
            ctx.shadowBlur = 0;
            ctx.shadowOffsetX = 0;
            ctx.shadowOffsetY = 0;

            URL.revokeObjectURL(url);

            canvas.toBlob((blob) => {
                if (!blob) {
                    resolve(null);
                    return;
                }
                const blobUrl = URL.createObjectURL(blob);
                iconCache[cacheKey] = blobUrl;
                resolve(blobUrl);
            }, "image/png");
        };

        img.onerror = () => {
            if (signal?.aborted) {
                URL.revokeObjectURL(url);
                resolve(null);
                return;
            }
            URL.revokeObjectURL(url);
            canvas.toBlob((blob) => {
                if (!blob) {
                    resolve(null);
                    return;
                }
                const blobUrl = URL.createObjectURL(blob);
                iconCache[cacheKey] = blobUrl;
                resolve(blobUrl);
            }, "image/png");
        };

        img.src = url;
    });
}
