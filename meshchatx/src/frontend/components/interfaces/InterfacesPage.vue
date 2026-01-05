<template>
    <div
        class="flex flex-col flex-1 overflow-hidden min-w-0 bg-gradient-to-br from-slate-50 via-slate-100 to-white dark:from-zinc-950 dark:via-zinc-900 dark:to-zinc-900"
    >
        <div class="flex-1 overflow-y-auto w-full">
            <div class="p-3 md:p-6 space-y-4 max-w-6xl mx-auto w-full flex-1">
                <div
                    v-if="showRestartReminder"
                    class="bg-gradient-to-r from-amber-500 to-orange-500 text-white rounded-3xl shadow-xl p-4 flex flex-wrap gap-3 items-center"
                >
                    <div class="flex items-center gap-3">
                        <MaterialDesignIcon icon-name="alert" class="w-6 h-6" />
                        <div>
                            <div class="text-lg font-semibold">{{ $t("interfaces.restart_required") }}</div>
                            <div class="text-sm">{{ $t("interfaces.restart_description") }}</div>
                        </div>
                    </div>
                    <button
                        v-if="isElectron"
                        type="button"
                        class="ml-auto inline-flex items-center gap-2 rounded-full border border-white/40 px-4 py-1.5 text-sm font-semibold text-white hover:bg-white/10 transition"
                        @click="relaunch"
                    >
                        <MaterialDesignIcon icon-name="restart" class="w-4 h-4" />
                        {{ $t("interfaces.restart_now") }}
                    </button>
                </div>

                <div class="glass-card space-y-4">
                    <div class="flex flex-wrap gap-3 items-center">
                        <div class="flex-1">
                            <div class="text-xs uppercase tracking-wide text-gray-500 dark:text-gray-400">
                                {{ $t("interfaces.manage") }}
                            </div>
                            <div class="text-xl font-semibold text-gray-900 dark:text-white">
                                {{ $t("interfaces.title") }}
                            </div>
                            <div class="text-sm text-gray-600 dark:text-gray-300">
                                {{ $t("interfaces.description") }}
                            </div>
                        </div>
                        <div class="flex flex-wrap gap-2">
                            <RouterLink :to="{ name: 'interfaces.add' }" class="primary-chip px-4 py-2 text-sm">
                                <MaterialDesignIcon icon-name="plus" class="w-4 h-4" />
                                {{ $t("interfaces.add_interface") }}
                            </RouterLink>
                            <button type="button" class="secondary-chip text-sm" @click="showImportInterfacesModal">
                                <MaterialDesignIcon icon-name="import" class="w-4 h-4" />
                                {{ $t("interfaces.import") }}
                            </button>
                            <button type="button" class="secondary-chip text-sm" @click="exportInterfaces">
                                <MaterialDesignIcon icon-name="export" class="w-4 h-4" />
                                {{ $t("interfaces.export_all") }}
                            </button>
                            <!--
                        <button
                            type="button"
                            class="secondary-chip text-sm bg-amber-500/10 hover:bg-amber-500/20 text-amber-600 dark:text-amber-400 border-amber-500/30"
                            :disabled="reloadingRns"
                            @click="reloadRns"
                        >
                            <MaterialDesignIcon
                                :icon-name="reloadingRns ? 'refresh' : 'restart'"
                                class="w-4 h-4"
                                :class="{ 'animate-spin-reverse': reloadingRns }"
                            />
                            {{ reloadingRns ? $t("app.reloading_rns") : $t("app.reload_rns") }}
                        </button>
                        --></div>
                    </div>
                    <div class="flex flex-wrap gap-3 items-center">
                        <div class="flex-1">
                            <input
                                v-model="searchTerm"
                                type="text"
                                :placeholder="$t('interfaces.search_placeholder')"
                                class="input-field"
                            />
                        </div>
                        <div class="flex gap-2 flex-wrap">
                            <button
                                type="button"
                                :class="filterChipClass(statusFilter === 'all')"
                                @click="setStatusFilter('all')"
                            >
                                {{ $t("interfaces.all") }}
                            </button>
                            <button
                                type="button"
                                :class="filterChipClass(statusFilter === 'enabled')"
                                @click="setStatusFilter('enabled')"
                            >
                                {{ $t("app.enabled") }}
                            </button>
                            <button
                                type="button"
                                :class="filterChipClass(statusFilter === 'disabled')"
                                @click="setStatusFilter('disabled')"
                            >
                                {{ $t("app.disabled") }}
                            </button>
                        </div>
                        <div class="w-full sm:w-60">
                            <select v-model="typeFilter" class="input-field">
                                <option value="all">{{ $t("interfaces.all_types") }}</option>
                                <option v-for="type in sortedInterfaceTypes" :key="type" :value="type">
                                    {{ type }}
                                </option>
                            </select>
                        </div>
                    </div>
                </div>

                <div
                    v-if="filteredInterfaces.length === 0"
                    class="glass-card text-center py-10 text-gray-500 dark:text-gray-300"
                >
                    <MaterialDesignIcon icon-name="lan-disconnect" class="w-10 h-10 mx-auto mb-3" />
                    <div class="text-lg font-semibold">{{ $t("interfaces.no_interfaces_found") }}</div>
                    <div class="text-sm">{{ $t("interfaces.no_interfaces_description") }}</div>
                </div>

                <div v-else class="grid gap-4 xl:grid-cols-2">
                    <Interface
                        v-for="iface of filteredInterfaces"
                        :key="iface._name"
                        :iface="iface"
                        :is-reticulum-running="isReticulumRunning"
                        @enable="enableInterface(iface._name)"
                        @disable="disableInterface(iface._name)"
                        @edit="editInterface(iface._name)"
                        @export="exportInterface(iface._name)"
                        @delete="deleteInterface(iface._name)"
                    />
                </div>
            </div>
        </div>
    </div>

    <ImportInterfacesModal ref="import-interfaces-modal" @dismissed="onImportInterfacesModalDismissed" />
</template>

<script>
import DialogUtils from "../../js/DialogUtils";
import ElectronUtils from "../../js/ElectronUtils";
import Interface from "./Interface.vue";
import Utils from "../../js/Utils";
import ImportInterfacesModal from "./ImportInterfacesModal.vue";
import DownloadUtils from "../../js/DownloadUtils";
import MaterialDesignIcon from "../MaterialDesignIcon.vue";
import ToastUtils from "../../js/ToastUtils";
import GlobalState from "../../js/GlobalState";

export default {
    name: "InterfacesPage",
    components: {
        ImportInterfacesModal,
        Interface,
        MaterialDesignIcon,
    },
    data() {
        return {
            interfaces: {},
            interfaceStats: {},
            reloadInterval: null,
            searchTerm: "",
            statusFilter: "all",
            typeFilter: "all",
            reloadingRns: false,
            isReticulumRunning: true,
        };
    },
    computed: {
        hasPendingInterfaceChanges() {
            return GlobalState.hasPendingInterfaceChanges;
        },
        modifiedInterfaceNames() {
            return GlobalState.modifiedInterfaceNames;
        },
        isElectron() {
            return ElectronUtils.isElectron();
        },
        showRestartReminder() {
            return this.hasPendingInterfaceChanges;
        },
        interfacesWithStats() {
            const results = [];
            for (const [interfaceName, iface] of Object.entries(this.interfaces)) {
                iface._name = interfaceName;
                iface._stats = this.interfaceStats[interfaceName];
                iface._restart_required = this.modifiedInterfaceNames.has(interfaceName);
                results.push(iface);
            }
            return results;
        },
        enabledInterfaces() {
            return this.interfacesWithStats.filter((iface) => this.isInterfaceEnabled(iface));
        },
        disabledInterfaces() {
            return this.interfacesWithStats.filter((iface) => !this.isInterfaceEnabled(iface));
        },
        filteredInterfaces() {
            const search = this.searchTerm.toLowerCase().trim();
            return this.interfacesWithStats
                .filter((iface) => {
                    if (this.statusFilter === "enabled" && !this.isInterfaceEnabled(iface)) {
                        return false;
                    }
                    if (this.statusFilter === "disabled" && this.isInterfaceEnabled(iface)) {
                        return false;
                    }
                    if (this.typeFilter !== "all" && iface.type !== this.typeFilter) {
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
                    const enabledDiff = Number(this.isInterfaceEnabled(b)) - Number(this.isInterfaceEnabled(a));
                    if (enabledDiff !== 0) return enabledDiff;
                    return a._name.localeCompare(b._name);
                });
        },
        sortedInterfaceTypes() {
            const types = new Set();
            this.interfacesWithStats.forEach((iface) => types.add(iface.type));
            return Array.from(types).sort();
        },
    },
    beforeUnmount() {
        clearInterval(this.reloadInterval);
    },
    mounted() {
        this.loadInterfaces();
        this.updateInterfaceStats();

        // update info every few seconds
        this.reloadInterval = setInterval(() => {
            this.updateInterfaceStats();
        }, 1000);
    },
    methods: {
        relaunch() {
            ElectronUtils.relaunch();
        },
        trackInterfaceChange(interfaceName = null) {
            GlobalState.hasPendingInterfaceChanges = true;
            if (interfaceName) {
                GlobalState.modifiedInterfaceNames.add(interfaceName);
            }
        },
        isInterfaceEnabled: function (iface) {
            return Utils.isInterfaceEnabled(iface);
        },
        async loadInterfaces() {
            try {
                const response = await window.axios.get(`/api/v1/reticulum/interfaces`);
                this.interfaces = response.data.interfaces;

                // also check app info for running state
                const appInfoResponse = await window.axios.get(`/api/v1/app/info`);
                this.isReticulumRunning = appInfoResponse.data.app_info.is_reticulum_running;
            } catch {
                // do nothing if failed to load interfaces
            }
        },
        async updateInterfaceStats() {
            try {
                // fetch interface stats
                const response = await window.axios.get(`/api/v1/interface-stats`);

                // update data
                const interfaces = response.data.interface_stats?.interfaces ?? [];
                for (const iface of interfaces) {
                    this.interfaceStats[iface.short_name] = iface;
                }
            } catch {
                // do nothing if failed to load interfaces
            }
        },
        async enableInterface(interfaceName) {
            // enable interface
            try {
                await window.axios.post(`/api/v1/reticulum/interfaces/enable`, {
                    name: interfaceName,
                });
                this.trackInterfaceChange(interfaceName);
            } catch (e) {
                DialogUtils.alert("failed to enable interface");
                console.log(e);
            }

            // reload interfaces
            await this.loadInterfaces();
        },
        async disableInterface(interfaceName) {
            // disable interface
            try {
                await window.axios.post(`/api/v1/reticulum/interfaces/disable`, {
                    name: interfaceName,
                });
                this.trackInterfaceChange(interfaceName);
            } catch (e) {
                DialogUtils.alert("failed to disable interface");
                console.log(e);
            }

            // reload interfaces
            await this.loadInterfaces();
        },
        async editInterface(interfaceName) {
            this.$router.push({
                name: "interfaces.edit",
                query: {
                    interface_name: interfaceName,
                },
            });
        },
        async deleteInterface(interfaceName) {
            // ask user to confirm deleting conversation history
            if (
                !(await DialogUtils.confirm("Are you sure you want to delete this interface? This can not be undone!"))
            ) {
                return;
            }

            // delete interface
            try {
                await window.axios.post(`/api/v1/reticulum/interfaces/delete`, {
                    name: interfaceName,
                });
                this.trackInterfaceChange(interfaceName);
            } catch (e) {
                DialogUtils.alert("failed to delete interface");
                console.log(e);
            }

            // reload interfaces
            await this.loadInterfaces();
        },
        async exportInterfaces() {
            try {
                // fetch exported interfaces
                const response = await window.axios.post("/api/v1/reticulum/interfaces/export");

                // download file to browser
                DownloadUtils.downloadFile("meshchat_interfaces.txt", new Blob([response.data]));
            } catch (e) {
                DialogUtils.alert("Failed to export interfaces");
                console.error(e);
            }
        },
        async exportInterface(interfaceName) {
            try {
                // fetch exported interfaces
                const response = await window.axios.post("/api/v1/reticulum/interfaces/export", {
                    selected_interface_names: [interfaceName],
                });

                // download file to browser
                DownloadUtils.downloadFile(`${interfaceName}.txt`, new Blob([response.data]));
            } catch (e) {
                DialogUtils.alert("Failed to export interface");
                console.error(e);
            }
        },
        showImportInterfacesModal() {
            this.$refs["import-interfaces-modal"].show();
        },
        onImportInterfacesModalDismissed(imported = false) {
            // reload interfaces as something may have been imported
            this.loadInterfaces();
            if (imported) {
                this.trackInterfaceChange();
            }
        },
        setStatusFilter(value) {
            this.statusFilter = value;
        },
        filterChipClass(isActive) {
            return isActive ? "primary-chip text-xs" : "secondary-chip text-xs";
        },
        async reloadRns() {
            if (this.reloadingRns) return;

            try {
                this.reloadingRns = true;
                const response = await window.axios.post("/api/v1/reticulum/reload");
                ToastUtils.success(response.data.message);
                GlobalState.hasPendingInterfaceChanges = false;
                GlobalState.modifiedInterfaceNames.clear();
                await this.loadInterfaces();
            } catch (e) {
                ToastUtils.error(e.response?.data?.error || "Failed to reload Reticulum!");
                console.error(e);
            } finally {
                this.reloadingRns = false;
            }
        },
    },
};
</script>
