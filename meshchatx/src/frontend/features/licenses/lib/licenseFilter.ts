// SPDX-License-Identifier: 0BSD

export type LicenseRow = {
    name?: string;
    version?: string;
    author?: string;
    license?: string;
};

export function filterLicenseRows(rows: LicenseRow[], query: string): LicenseRow[] {
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
