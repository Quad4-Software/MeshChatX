<!-- SPDX-License-Identifier: 0BSD AND MIT -->

<template>
    <div v-if="isShowing" class="fixed inset-0 bg-black/50 transition-opacity flex items-center justify-center">
        <div class="flex w-full h-full p-4 overflow-y-auto">
            <div
                v-click-outside="dismiss"
                class="my-auto mx-auto w-full bg-sem-surface rounded-lg shadow-xl max-w-2xl text-sem-fg"
            >
                <!-- title -->
                <div class="p-4 border-b border-sem-border">
                    <h3 class="text-lg font-semibold text-sem-fg">Import Interfaces</h3>
                </div>

                <!-- content -->
                <div class="divide-y divide-sem-border">
                    <!-- file input -->
                    <div class="p-2">
                        <div>
                            <input
                                ref="import-interfaces-file-input"
                                type="file"
                                accept="*"
                                class="w-full text-sm text-sem-fg-muted"
                                @change="onFileSelected"
                            />
                        </div>
                        <div v-if="!selectedFile" class="mt-2 text-sm text-sem-fg-secondary">
                            <ul class="list-disc list-inside">
                                <li>You can import interfaces from a ~/.reticulum/config file.</li>
                                <li>You can import interfaces from an exported interfaces file.</li>
                                <li>{{ $t("interfaces.i2p_import_forbidden") }}</li>
                            </ul>
                        </div>
                    </div>

                    <!-- select interfaces -->
                    <div v-if="importableInterfaces.length > 0" class="divide-y divide-sem-border">
                        <div class="flex p-2">
                            <div class="my-auto mr-auto text-sm font-medium text-sem-fg-secondary">
                                Select Interfaces to Import
                            </div>
                            <div class="my-auto space-x-2">
                                <button class="text-sm text-sem-accent hover:underline" @click="selectAllInterfaces">
                                    Select All
                                </button>
                                <button class="text-sm text-sem-accent hover:underline" @click="deselectAllInterfaces">
                                    Deselect All
                                </button>
                            </div>
                        </div>
                        <div class="bg-sem-surface-muted p-2 space-y-2 max-h-80 overflow-y-auto">
                            <div
                                v-for="iface in importableInterfaces"
                                :key="iface.name"
                                class="bg-sem-surface cursor-pointer flex items-center p-2 border border-sem-border rounded-sm shadow-sm"
                            >
                                <div class="mr-auto text-sm flex-1" @click="toggleSelectedInterface(iface.name)">
                                    <div class="font-semibold text-sem-fg">{{ iface.name }}</div>
                                    <div class="text-sm text-sem-fg-muted">
                                        <!-- auto interface -->
                                        <div v-if="iface.type === 'AutoInterface'">
                                            <div>{{ iface.type }}</div>
                                            <div>Ethernet and WiFi</div>
                                        </div>

                                        <!-- tcp client interface -->
                                        <div v-else-if="iface.type === 'TCPClientInterface'">
                                            <div>{{ iface.type }}</div>
                                            <div>{{ iface.target_host }}:{{ iface.target_port }}</div>
                                        </div>

                                        <!-- tcp server interface -->
                                        <div v-else-if="iface.type === 'TCPServerInterface'">
                                            <div>{{ iface.type }}</div>
                                            <div>{{ iface.listen_ip }}:{{ iface.listen_port }}</div>
                                        </div>

                                        <!-- udp interface -->
                                        <div v-else-if="iface.type === 'UDPInterface'">
                                            <div>{{ iface.type }}</div>
                                            <div>Listen: {{ iface.listen_ip }}:{{ iface.listen_port }}</div>
                                            <div>Forward: {{ iface.forward_ip }}:{{ iface.forward_port }}</div>
                                        </div>

                                        <!-- rnode interface details -->
                                        <div v-else-if="iface.type === 'RNodeInterface'">
                                            <div>{{ iface.type }}</div>
                                            <div>Port: {{ iface.port }}</div>
                                            <div>Frequency: {{ formatFrequency(iface.frequency) }}</div>
                                            <div>Bandwidth: {{ formatFrequency(iface.bandwidth) }}</div>
                                            <div>Spreading Factor: {{ iface.spreadingfactor }}</div>
                                            <div>Coding Rate: {{ iface.codingrate }}</div>
                                            <div>Transmit Power: {{ iface.txpower }}dBm</div>
                                        </div>

                                        <!-- other interface types -->
                                        <div v-else>{{ iface.type }}</div>
                                    </div>
                                </div>
                                <div @click.stop>
                                    <Toggle
                                        :id="`import-interface-${iface.name}`"
                                        :model-value="selectedInterfaces.includes(iface.name)"
                                        @update:model-value="
                                            (value) => {
                                                if (value && !selectedInterfaces.includes(iface.name))
                                                    selectInterface(iface.name);
                                                else if (!value && selectedInterfaces.includes(iface.name))
                                                    deselectInterface(iface.name);
                                            }
                                        "
                                    />
                                </div>
                            </div>
                        </div>
                    </div>
                </div>

                <!-- actions -->
                <div class="p-4 border-t border-sem-border flex justify-end space-x-2">
                    <button
                        class="px-4 py-2 text-sm font-medium text-sem-fg bg-sem-surface border border-sem-border rounded-md hover:bg-sem-surface-muted"
                        @click="dismiss"
                    >
                        Cancel
                    </button>
                    <button
                        class="px-4 py-2 text-sm font-medium text-white bg-sem-accent rounded-md hover:opacity-90"
                        @click="importSelectedInterfaces"
                    >
                        Import Selected
                    </button>
                </div>
            </div>
        </div>
    </div>
</template>

<script>
import DialogUtils from "../../js/DialogUtils";
import Utils from "../../js/Utils";
import Toggle from "../forms/Toggle.vue";

export default {
    name: "ImportInterfacesModal",
    components: {
        Toggle,
    },
    emits: ["dismissed"],
    data() {
        return {
            isShowing: false,
            selectedFile: null,
            importableInterfaces: [],
            selectedInterfaces: [],
        };
    },
    methods: {
        show() {
            this.isShowing = true;
            this.selectedFile = null;
            this.importableInterfaces = [];
            this.selectedInterfaces = [];
        },
        dismiss(result = false) {
            this.isShowing = false;
            const imported = result === true;
            this.$emit("dismissed", imported);
        },
        clearSelectedFile() {
            this.selectedFile = null;
            this.$refs["import-interfaces-file-input"].value = null;
        },
        async onFileSelected(event) {
            // get selected file
            const file = event.target.files[0];
            if (!file) {
                return;
            }

            // update ui
            this.selectedFile = file;
            this.importableInterfaces = [];
            this.selectedInterfaces = [];

            try {
                // fetch preview of interfaces to import
                const response = await window.api.post("/api/v1/reticulum/interfaces/import-preview", {
                    config: await file.text(),
                });

                // ensure there are some interfaces available to import
                if (!response.data.interfaces || response.data.interfaces.length === 0) {
                    this.clearSelectedFile();
                    DialogUtils.alert(this.$t("interfaces.no_interfaces_found_config"));
                    return;
                }

                // update ui
                this.importableInterfaces = response.data.interfaces;

                // auto select all interfaces
                this.selectAllInterfaces();
            } catch (e) {
                this.clearSelectedFile();
                DialogUtils.alert(this.$t("interfaces.failed_parse_config"));
                console.error(e);
            }
        },
        isInterfaceSelected(name) {
            return this.selectedInterfaces.includes(name);
        },
        selectInterface(name) {
            if (!this.isInterfaceSelected(name)) {
                this.selectedInterfaces.push(name);
            }
        },
        deselectInterface(name) {
            this.selectedInterfaces = this.selectedInterfaces.filter((selectedInterfaceName) => {
                return selectedInterfaceName !== name;
            });
        },
        toggleSelectedInterface(name) {
            if (this.isInterfaceSelected(name)) {
                this.deselectInterface(name);
            } else {
                this.selectInterface(name);
            }
        },
        selectAllInterfaces() {
            this.selectedInterfaces = this.importableInterfaces.map((i) => i.name);
        },
        deselectAllInterfaces() {
            this.selectedInterfaces = [];
        },
        async importSelectedInterfaces() {
            // ensure user selected a file to import from
            if (!this.selectedFile) {
                DialogUtils.alert(this.$t("interfaces.select_config_file"));
                return;
            }

            // ensure user selected some interfaces
            if (this.selectedInterfaces.length === 0) {
                DialogUtils.alert(this.$t("interfaces.select_at_least_one"));
                return;
            }

            try {
                // import interfaces
                await window.api.post("/api/v1/reticulum/interfaces/import", {
                    config: await this.selectedFile.text(),
                    selected_interface_names: this.selectedInterfaces,
                });

                // dismiss modal
                this.dismiss(true);

                // tell user interfaces were imported
                DialogUtils.alert(this.$t("interfaces.import_success"));
            } catch (e) {
                const message = e.response?.data?.message || this.$t("interfaces.failed_import_all");
                DialogUtils.alert(message);
                console.error(e);
            }
        },
        formatFrequency(hz) {
            return Utils.formatFrequency(hz);
        },
    },
};
</script>
