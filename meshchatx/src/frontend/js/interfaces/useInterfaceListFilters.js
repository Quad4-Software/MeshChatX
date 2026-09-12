// @ts-check

import { computed, onMounted, ref, watch } from "vue";

import { STORAGE_KEYS } from "../constants.js";
import Utils from "../Utils.js";

/**
 * Search/status/type filters for the interfaces list on InterfacesPage.
 * Owns the persisted status filter (localStorage) and the derived
 * filteredInterfaces list. options.getInterfaces supplies the host's
 * interfacesWithStats computed.
 */
export function useInterfaceListFilters(options = {}) {
    const getInterfaces = options.getInterfaces || (() => []);

    const searchTerm = ref("");
    const statusFilter = ref("all");
    const typeFilter = ref("all");

    const filteredInterfaces = computed(() => {
        const search = searchTerm.value.toLowerCase().trim();
        return getInterfaces()
            .filter((iface) => {
                if (statusFilter.value === "enabled" && !Utils.isInterfaceEnabled(iface)) {
                    return false;
                }
                if (statusFilter.value === "disabled" && Utils.isInterfaceEnabled(iface)) {
                    return false;
                }
                if (typeFilter.value !== "all" && iface.type !== typeFilter.value) {
                    return false;
                }
                if (!search) {
                    return true;
                }
                const haystack = [
                    iface._name,
                    iface.type,
                    iface.target_host,
                    iface.target_port,
                    iface.listen_ip,
                    iface.listen_port,
                ]
                    .filter(Boolean)
                    .join(" ")
                    .toLowerCase();
                return haystack.includes(search);
            })
            .sort((a, b) => {
                const enabledDiff = Number(Utils.isInterfaceEnabled(b)) - Number(Utils.isInterfaceEnabled(a));
                if (enabledDiff !== 0) return enabledDiff;
                return a._name.localeCompare(b._name);
            });
    });

    watch(statusFilter, (value) => {
        try {
            localStorage.setItem(STORAGE_KEYS.INTERFACES_STATUS_FILTER, value);
        } catch {
            /* ignore */
        }
    });

    onMounted(() => {
        try {
            const sf = localStorage.getItem(STORAGE_KEYS.INTERFACES_STATUS_FILTER);
            if (sf === "all" || sf === "enabled" || sf === "disabled") {
                statusFilter.value = sf;
            }
        } catch {
            /* ignore */
        }
    });

    function setStatusFilter(value) {
        statusFilter.value = value;
    }

    return {
        searchTerm,
        statusFilter,
        typeFilter,
        filteredInterfaces,
        setStatusFilter,
    };
}
