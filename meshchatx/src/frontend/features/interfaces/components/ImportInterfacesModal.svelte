<!-- SPDX-License-Identifier: 0BSD -->

<script lang="ts">
    import DialogUtils from "../../../js/DialogUtils.js";
    import { t } from "../../../js/i18n.js";
    import { formatFrequency } from "../lib/interfacesFormat.js";
    import { importPreviewInterfacesApi, importInterfacesApi } from "../lib/interfacesApi.js";
    import type { ConfiguredInterface } from "../lib/types.js";
    import Toggle from "./Toggle.svelte";

    interface Props {
        isShowing?: boolean;
        ondismissed?: (imported: boolean) => void;
    }

    let { isShowing = $bindable(false), ondismissed }: Props = $props();

    let fileInputRef: HTMLInputElement | null = $state(null);
    let selectedFile: File | null = $state(null);
    let importableInterfaces: ConfiguredInterface[] = $state([]);
    let selectedInterfaces: string[] = $state([]);

    export function show() {
        isShowing = true;
        selectedFile = null;
        importableInterfaces = [];
        selectedInterfaces = [];
    }

    export function dismiss(result = false) {
        isShowing = false;
        ondismissed?.(result);
    }

    function clearSelectedFile() {
        selectedFile = null;
        if (fileInputRef) {
            fileInputRef.value = "";
        }
    }

    async function onFileSelected(event: Event) {
        const target = event.target as HTMLInputElement;
        const file = target.files?.[0];
        if (!file) return;

        selectedFile = file;
        importableInterfaces = [];
        selectedInterfaces = [];

        try {
            const interfaces = await importPreviewInterfacesApi(await file.text());
            if (!interfaces || interfaces.length === 0) {
                clearSelectedFile();
                DialogUtils.alert(t("interfaces.no_interfaces_found_config"));
                return;
            }

            importableInterfaces = interfaces;
            selectAllInterfaces();
        } catch (e) {
            clearSelectedFile();
            DialogUtils.alert(t("interfaces.failed_parse_config"));
            console.error(e);
        }
    }

    function isInterfaceSelected(name: string): boolean {
        return selectedInterfaces.includes(name);
    }

    function selectInterface(name: string) {
        if (!isInterfaceSelected(name)) {
            selectedInterfaces = [...selectedInterfaces, name];
        }
    }

    function deselectInterface(name: string) {
        selectedInterfaces = selectedInterfaces.filter((n) => n !== name);
    }

    function toggleSelectedInterface(name: string) {
        if (isInterfaceSelected(name)) {
            deselectInterface(name);
        } else {
            selectInterface(name);
        }
    }

    function interfaceDisplayName(iface: ConfiguredInterface): string {
        const raw = iface.name;
        if (typeof raw === "string" && raw) {
            return raw;
        }
        return iface._name || "";
    }

    function selectAllInterfaces() {
        selectedInterfaces = importableInterfaces.map((i) => interfaceDisplayName(i));
    }

    function deselectAllInterfaces() {
        selectedInterfaces = [];
    }

    async function importSelectedInterfaces() {
        if (!selectedFile) {
            DialogUtils.alert(t("interfaces.select_config_file"));
            return;
        }

        if (selectedInterfaces.length === 0) {
            DialogUtils.alert(t("interfaces.select_at_least_one"));
            return;
        }

        try {
            await importInterfacesApi(await selectedFile.text(), selectedInterfaces);
            dismiss(true);
            DialogUtils.alert(t("interfaces.import_success"));
        } catch (e: unknown) {
            const err = e as { response?: { data?: { message?: string } } };
            const message = err.response?.data?.message || t("interfaces.failed_import_all");
            DialogUtils.alert(message);
            console.error(e);
        }
    }
</script>

{#if isShowing}
    <!-- svelte-ignore a11y_click_events_have_key_events -->
    <!-- svelte-ignore a11y_no_static_element_interactions -->
    <div
        class="fixed inset-0 bg-black/50 transition-opacity flex items-center justify-center z-50"
        onclick={() => dismiss(false)}
    >
        <div class="flex w-full h-full p-4 overflow-y-auto" onclick={(e) => e.stopPropagation()}>
            <div class="my-auto mx-auto w-full bg-sem-surface rounded-lg shadow-xl max-w-2xl text-sem-fg">
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
                                bind:this={fileInputRef}
                                type="file"
                                accept="*"
                                class="w-full text-sm text-sem-fg-muted"
                                onchange={onFileSelected}
                            />
                        </div>
                        {#if !selectedFile}
                            <div class="mt-2 text-sm text-sem-fg-secondary">
                                <ul class="list-disc list-inside">
                                    <li>You can import interfaces from a ~/.reticulum/config file.</li>
                                    <li>You can import interfaces from an exported interfaces file.</li>
                                    <li>{t("interfaces.i2p_import_forbidden")}</li>
                                </ul>
                            </div>
                        {/if}
                    </div>

                    <!-- select interfaces -->
                    {#if importableInterfaces.length > 0}
                        <div class="divide-y divide-sem-border">
                            <div class="flex p-2">
                                <div class="my-auto mr-auto text-sm font-medium text-sem-fg-secondary">
                                    Select Interfaces to Import
                                </div>
                                <div class="my-auto space-x-2">
                                    <button
                                        class="text-sm text-sem-accent hover:underline"
                                        onclick={selectAllInterfaces}
                                    >
                                        Select All
                                    </button>
                                    <button
                                        class="text-sm text-sem-accent hover:underline"
                                        onclick={deselectAllInterfaces}
                                    >
                                        Deselect All
                                    </button>
                                </div>
                            </div>
                            <div class="bg-sem-surface-muted p-2 space-y-2 max-h-80 overflow-y-auto">
                                {#each importableInterfaces as iface (interfaceDisplayName(iface))}
                                    {@const ifaceName = interfaceDisplayName(iface)}
                                    <div
                                        class="bg-sem-surface cursor-pointer flex items-center p-2 border border-sem-border rounded-sm shadow-sm"
                                    >
                                        <div
                                            class="mr-auto text-sm flex-1"
                                            onclick={() => toggleSelectedInterface(ifaceName)}
                                        >
                                            <div class="font-semibold text-sem-fg">{ifaceName}</div>
                                            <div class="text-sm text-sem-fg-muted">
                                                {#if iface.type === "AutoInterface"}
                                                    <div>{iface.type}</div>
                                                    <div>Ethernet and WiFi</div>
                                                {:else if iface.type === "TCPClientInterface"}
                                                    <div>{iface.type}</div>
                                                    <div>{iface.target_host}:{iface.target_port}</div>
                                                {:else if iface.type === "TCPServerInterface"}
                                                    <div>{iface.type}</div>
                                                    <div>{iface.listen_ip}:{iface.listen_port}</div>
                                                {:else if iface.type === "UDPInterface"}
                                                    <div>{iface.type}</div>
                                                    <div>Listen: {iface.listen_ip}:{iface.listen_port}</div>
                                                    <div>Forward: {iface.forward_ip}:{iface.forward_port}</div>
                                                {:else if iface.type === "RNodeInterface"}
                                                    <div>{iface.type}</div>
                                                    <div>Port: {iface.port}</div>
                                                    <div>Frequency: {formatFrequency(iface.frequency)}</div>
                                                    <div>Bandwidth: {formatFrequency(iface.bandwidth)}</div>
                                                    <div>Spreading Factor: {iface.spreadingfactor}</div>
                                                    <div>Coding Rate: {iface.codingrate}</div>
                                                    <div>Transmit Power: {iface.txpower}dBm</div>
                                                {:else}
                                                    <div>{iface.type}</div>
                                                {/if}
                                            </div>
                                        </div>
                                        <div onclick={(e) => e.stopPropagation()}>
                                            <Toggle
                                                id="import-interface-{ifaceName}"
                                                checked={selectedInterfaces.includes(ifaceName)}
                                                onchange={(val) => {
                                                    if (val) selectInterface(ifaceName);
                                                    else deselectInterface(ifaceName);
                                                }}
                                            />
                                        </div>
                                    </div>
                                {/each}
                            </div>
                        </div>
                    {/if}
                </div>

                <!-- actions -->
                <div class="p-4 border-t border-sem-border flex justify-end space-x-2">
                    <button
                        type="button"
                        class="px-4 py-2 text-sm font-medium text-sem-fg bg-sem-surface border border-sem-border rounded-md hover:bg-sem-surface-muted"
                        onclick={() => dismiss(false)}
                    >
                        Cancel
                    </button>
                    <button
                        type="button"
                        class="px-4 py-2 text-sm font-medium text-white bg-sem-accent rounded-md hover:opacity-90"
                        onclick={importSelectedInterfaces}
                    >
                        Import Selected
                    </button>
                </div>
            </div>
        </div>
    </div>
{/if}
