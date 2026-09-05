// SPDX-License-Identifier: 0BSD

import type {
    ConfiguredInterface,
    DiscoveryConfig,
    DiscoveredInterface,
    DiscoveredActiveInterface,
    InterfaceModule,
    KernelInterface,
    Comport,
    CommunityInterface,
    InterfaceStats,
} from "./types.js";

export async function fetchInterfaces(): Promise<{
    interfaces: Record<string, ConfiguredInterface>;
}> {
    const response = await window.api.get("/api/v1/reticulum/interfaces");
    return {
        interfaces: response.data?.interfaces || {},
    };
}

export async function fetchInterfaceToEdit(name: string): Promise<Record<string, any>> {
    const response = await window.api.get("/api/v1/reticulum/interfaces");
    const interfaces = response.data?.interfaces || {};
    const iface = interfaces[name] || {};
    return { name, ...iface };
}

export async function fetchAppInfo(): Promise<{ isReticulumRunning: boolean }> {
    const response = await window.api.get("/api/v1/app/info");
    return {
        isReticulumRunning: response.data?.app_info?.is_reticulum_running ?? true,
    };
}

export async function fetchInterfaceStats(): Promise<Record<string, InterfaceStats>> {
    const response = await window.api.get("/api/v1/interface-stats");
    const nextStats: Record<string, InterfaceStats> = {};
    const interfaces = response.data?.interface_stats?.interfaces ?? [];
    for (const iface of interfaces) {
        const key = (iface.interface_name ?? iface.short_name) as string | undefined;
        if (key) {
            nextStats[key] = iface as InterfaceStats;
        }
    }
    return nextStats;
}

export async function enableInterfaceApi(name: string): Promise<void> {
    await window.api.post("/api/v1/reticulum/interfaces/enable", { name });
}

export async function disableInterfaceApi(name: string): Promise<void> {
    await window.api.post("/api/v1/reticulum/interfaces/disable", { name });
}

export async function deleteInterfaceApi(name: string): Promise<void> {
    await window.api.post("/api/v1/reticulum/interfaces/delete", { name });
}

export async function exportAllInterfacesApi(): Promise<Blob> {
    const response = await window.api.post("/api/v1/reticulum/interfaces/export");
    return new Blob([response.data]);
}

export async function exportSingleInterfaceApi(name: string): Promise<Blob> {
    const response = await window.api.post("/api/v1/reticulum/interfaces/export", {
        selected_interface_names: [name],
    });
    return new Blob([response.data]);
}

export { exportSingleInterfaceApi as exportInterfaceApi, fetchAppInfo as fetchAppInfoApi };

export async function fetchDiscoveredInterfacesApi(): Promise<{
    interfaces: DiscoveredInterface[];
    active: DiscoveredActiveInterface[];
}> {
    const response = await window.api.get("/api/v1/reticulum/discovered-interfaces");
    return {
        interfaces: response.data?.interfaces ?? [],
        active: response.data?.active ?? [],
    };
}

export async function fetchDiscoveryConfigApi(): Promise<DiscoveryConfig> {
    const response = await window.api.get("/api/v1/reticulum/discovery");
    const d = response.data?.discovery ?? {};
    const parseBool = (v: unknown) => {
        if (typeof v === "string") {
            return ["true", "yes", "1", "y", "on"].includes(v.toLowerCase());
        }
        return Boolean(v);
    };
    return {
        discover_interfaces: parseBool(d.discover_interfaces),
        interface_discovery_sources: d.interface_discovery_sources ?? "",
        interface_discovery_whitelist: d.interface_discovery_whitelist ?? "",
        interface_discovery_blacklist: d.interface_discovery_blacklist ?? "",
        required_discovery_value:
            d.required_discovery_value !== undefined &&
            d.required_discovery_value !== null &&
            d.required_discovery_value !== ""
                ? Number(d.required_discovery_value)
                : null,
        autoconnect_discovered_interfaces:
            d.autoconnect_discovered_interfaces !== undefined &&
            d.autoconnect_discovered_interfaces !== null &&
            d.autoconnect_discovered_interfaces !== ""
                ? Number(d.autoconnect_discovered_interfaces)
                : null,
        default_gravity:
            d.default_gravity !== undefined && d.default_gravity !== null && d.default_gravity !== ""
                ? Number(d.default_gravity)
                : null,
        autoconnect_interface_mode: d.autoconnect_interface_mode ?? "",
        autoconnect_interface_gravity:
            d.autoconnect_interface_gravity !== undefined &&
            d.autoconnect_interface_gravity !== null &&
            d.autoconnect_interface_gravity !== ""
                ? Number(d.autoconnect_interface_gravity)
                : null,
        autoconnect_announces_to_internal: parseBool(d.autoconnect_announces_to_internal ?? false),
        default_bootstrap_only: parseBool(d.default_bootstrap_only ?? false),
        network_identity: d.network_identity ?? "",
    };
}

export async function saveDiscoveryConfigApi(payload: Record<string, unknown>): Promise<void> {
    await window.api.patch("/api/v1/reticulum/discovery", payload);
}

export async function reloadRnsApi(): Promise<{ message: string }> {
    const response = await window.api.post("/api/v1/reticulum/reload");
    return {
        message: response.data?.message ?? "RNS reloaded",
    };
}

export async function fetchConfigApi(): Promise<Record<string, unknown>> {
    const response = await window.api.get("/api/v1/config");
    return response.data?.config ?? {};
}

export async function patchConfigApi(config: Record<string, unknown>): Promise<Record<string, unknown>> {
    const response = await window.api.patch("/api/v1/config", config);
    return response.data?.config ?? {};
}

export async function fetchReticulumInstanceApi(): Promise<Record<string, unknown>> {
    const response = await window.api.get("/api/v1/reticulum/instance");
    return response.data?.instance ?? {};
}

export async function fetchComportsApi(): Promise<Comport[]> {
    const response = await window.api.get("/api/v1/comports");
    return response.data?.comports ?? [];
}

export async function fetchKernelInterfacesApi(): Promise<{
    interfaces: KernelInterface[];
    unavailable_reason: string | null;
}> {
    const response = await window.api.get("/api/v1/system/network-interfaces");
    return {
        interfaces: response.data?.interfaces || [],
        unavailable_reason: response.data?.unavailable_reason || null,
    };
}

export async function fetchCommunityInterfacesApi(): Promise<CommunityInterface[]> {
    const response = await window.api.get("/api/v1/community-interfaces");
    return response.data?.interfaces ?? [];
}

export async function fetchInterfaceModulesApi(): Promise<{
    interfacepath: string;
    interface_path: string;
    modules: InterfaceModule[];
}> {
    const response = await window.api.get("/api/v1/reticulum/interface-modules");
    const path = response.data?.interface_path || response.data?.interfacepath || "";
    return {
        interfacepath: path,
        interface_path: path,
        modules: Array.isArray(response.data?.modules) ? response.data.modules : [],
    };
}

export async function uploadInterfaceModuleApi(
    file: File,
    overwrite = false
): Promise<{ message?: string; type?: string }> {
    const formData = new FormData();
    formData.append("file", file);
    if (overwrite) {
        formData.append("overwrite", "true");
    }
    const response = await window.api.post("/api/v1/reticulum/interface-modules", formData);
    return response.data ?? {};
}

export async function installInterfaceModuleApi(formData: FormData): Promise<{
    message?: string;
    type?: string;
}> {
    const response = await window.api.post("/api/v1/reticulum/interface-modules", formData);
    return response.data ?? {};
}

export async function deleteInterfaceModuleApi(typeName: string): Promise<{ message?: string }> {
    const response = await window.api.delete(`/api/v1/reticulum/interface-modules/${encodeURIComponent(typeName)}`);
    return response.data ?? {};
}

export async function saveInterfaceApi(
    nameOrPayload: string | Record<string, unknown>,
    payload?: Record<string, unknown>,
    isEditing = false
): Promise<{ message?: string }> {
    let body: Record<string, unknown>;
    if (typeof nameOrPayload === "string") {
        body = {
            name: nameOrPayload,
            allow_overwriting_interface: isEditing,
            ...(payload || {}),
        };
    } else {
        body = nameOrPayload;
    }
    const response = await window.api.post("/api/v1/reticulum/interfaces/add", body);
    return response.data ?? {};
}

export async function importPreviewInterfacesApi(configText: string): Promise<ConfiguredInterface[]> {
    const response = await window.api.post("/api/v1/reticulum/interfaces/import-preview", {
        config: configText,
    });
    return response.data?.interfaces || [];
}

export async function importInterfacesApi(configText: string, names: string[]): Promise<void> {
    await window.api.post("/api/v1/reticulum/interfaces/import", {
        config: configText,
        selected_interface_names: names,
    });
}
