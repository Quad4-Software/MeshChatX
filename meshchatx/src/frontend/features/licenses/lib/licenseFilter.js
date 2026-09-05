// SPDX-License-Identifier: 0BSD

/**
 * @param {Array<{ name?: string, version?: string, author?: string, license?: string }>} rows
 * @param {string} query
 * @returns {typeof rows}
 */
export function filterLicenseRows(rows, query) {
    const q = String(query || "")
        .trim()
        .toLowerCase();
    if (!q) {
        return rows;
    }
    return rows.filter((r) => {
        const blob = `${r.name} ${r.version} ${r.author} ${r.license}`.toLowerCase();
        return blob.includes(q);
    });
}
