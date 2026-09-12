// SPDX-License-Identifier: 0BSD

import { describe, expect, it } from "vitest";
import { useInterfaceListFilters } from "../../meshchatx/src/frontend/js/interfaces/useInterfaceListFilters.js";

const enabled = { _name: "rnode", type: "RNodeInterface", enabled: true };
const disabled = { _name: "tcp", type: "TCPClientInterface", enabled: false };

function makeFilters(interfaces = [enabled, disabled]) {
    return useInterfaceListFilters({ getInterfaces: () => interfaces });
}

describe("useInterfaceListFilters", () => {
    it("returns all interfaces with no filters", () => {
        const f = makeFilters();
        // enabled sorts before disabled
        expect(f.filteredInterfaces.value.map((i) => i._name)).toEqual(["rnode", "tcp"]);
    });

    it("filters by enabled status", () => {
        const f = makeFilters();
        f.statusFilter.value = "enabled";
        expect(f.filteredInterfaces.value.map((i) => i._name)).toEqual(["rnode"]);
        f.statusFilter.value = "disabled";
        expect(f.filteredInterfaces.value.map((i) => i._name)).toEqual(["tcp"]);
    });

    it("filters by type", () => {
        const f = makeFilters();
        f.typeFilter.value = "TCPClientInterface";
        expect(f.filteredInterfaces.value.map((i) => i._name)).toEqual(["tcp"]);
    });

    it("searches across name, type, and host fields", () => {
        const f = makeFilters();
        f.searchTerm.value = "rnode";
        expect(f.filteredInterfaces.value.map((i) => i._name)).toEqual(["rnode"]);
        f.searchTerm.value = "tcpclient";
        expect(f.filteredInterfaces.value.map((i) => i._name)).toEqual(["tcp"]);
        f.searchTerm.value = "nothing-matches";
        expect(f.filteredInterfaces.value).toEqual([]);
    });

    it("setStatusFilter updates the filter", () => {
        const f = makeFilters();
        f.setStatusFilter("disabled");
        expect(f.statusFilter.value).toBe("disabled");
    });
});
