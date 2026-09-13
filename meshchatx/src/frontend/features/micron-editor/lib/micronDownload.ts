// SPDX-License-Identifier: 0BSD

/**
 * Trigger local browser download for a .mu file.
 */
export function downloadMicronFile(tabName: string, content: string): void {
    const blob = new Blob([content], { type: "text/plain" });
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = `${(tabName || "page").replace(/\s+/g, "_")}.mu`;
    document.body.appendChild(a);
    a.click();
    document.body.removeChild(a);
    URL.revokeObjectURL(url);
}
