<!-- SPDX-License-Identifier: 0BSD -->

<script lang="ts">
    import MaterialDesignIcon from "../../../ui/svelte/MaterialDesignIcon.svelte";
    import { transportSuggestionKeys, TRANSPORT_SERIAL, TRANSPORT_BLUETOOTH } from "../../../js/rnode/Capabilities.js";
    import { t } from "../../../js/i18n.js";

    interface ActionItem {
        id: string;
        icon: string;
        labelKey: string;
    }

    interface WarningItem {
        id: string;
        icon: string;
        titleKey: string;
        suggestionKeys: string[];
        actions: ActionItem[];
    }

    interface Props {
        capabilities: any;
        androidAvailable?: boolean;
        onaction?: (actionId: string) => void;
    }

    let { capabilities, androidAvailable = false, onaction }: Props = $props();

    function serialActions(serial: any): ActionItem[] {
        const actions: ActionItem[] = [];
        if (serial?.reason === "polyfill_not_loaded") {
            actions.push({
                id: "load-polyfill",
                icon: "download",
                labelKey: "tools.rnode_flasher.support.actions.load_polyfill",
            });
        }
        if (androidAvailable) {
            actions.push({
                id: "open-native-flasher",
                icon: "usb",
                labelKey: "tools.rnode_flasher.support.actions.open_native",
            });
        }
        return actions;
    }

    function bluetoothActions(): ActionItem[] {
        const actions: ActionItem[] = [];
        const bluetooth = capabilities?.transports?.[TRANSPORT_BLUETOOTH];
        if (androidAvailable) {
            const needsPermission = bluetooth?.reason === "android_bluetooth_permission_required";
            if (needsPermission) {
                actions.push({
                    id: "request-bluetooth",
                    icon: "bluetooth-settings",
                    labelKey: "tools.rnode_flasher.support.actions.request_bluetooth",
                });
                actions.push({
                    id: "open-bluetooth-settings",
                    icon: "cog",
                    labelKey: "tools.rnode_flasher.support.actions.open_settings",
                });
            } else {
                actions.push({
                    id: "open-native-flasher",
                    icon: "usb",
                    labelKey: "tools.rnode_flasher.support.actions.open_native",
                });
                actions.push({
                    id: "open-bluetooth-settings",
                    icon: "cog",
                    labelKey: "tools.rnode_flasher.support.actions.open_settings",
                });
            }
            return actions;
        }
        actions.push({
            id: "probe-bluetooth",
            icon: "bluetooth-connect",
            labelKey: "tools.rnode_flasher.support.actions.probe_bluetooth",
        });
        actions.push({
            id: "recheck-capabilities",
            icon: "refresh",
            labelKey: "tools.rnode_flasher.support.actions.recheck_capabilities",
        });
        return actions;
    }

    let warnings = $derived.by(() => {
        const list: WarningItem[] = [];
        const serial = capabilities?.transports?.[TRANSPORT_SERIAL];
        const bluetooth = capabilities?.transports?.[TRANSPORT_BLUETOOTH];

        if (serial && !serial.available) {
            list.push({
                id: "serial",
                icon: "usb-port",
                titleKey: "tools.rnode_flasher.support.serial.title",
                suggestionKeys: transportSuggestionKeys(capabilities, TRANSPORT_SERIAL),
                actions: serialActions(serial),
            });
        }
        if (bluetooth && !bluetooth.available) {
            list.push({
                id: "bluetooth",
                icon: "bluetooth",
                titleKey: "tools.rnode_flasher.support.bluetooth.title",
                suggestionKeys: transportSuggestionKeys(capabilities, TRANSPORT_BLUETOOTH),
                actions: bluetoothActions(),
            });
        }
        return list;
    });
</script>

{#if warnings.length > 0}
    <div class="space-y-2">
        {#each warnings as warning (warning.id)}
            <div
                class="flex items-start gap-3 rounded-xl border border-amber-200 dark:border-amber-900/40 bg-amber-50 dark:bg-amber-900/10 px-4 py-3"
            >
                <MaterialDesignIcon
                    iconName={warning.icon}
                    class="size-5 mt-0.5 shrink-0 text-amber-600 dark:text-amber-400"
                />
                <div class="flex-1 min-w-0 space-y-1">
                    <div class="text-sm font-semibold text-amber-800 dark:text-amber-200">
                        {t(warning.titleKey)}
                    </div>
                    <ul class="text-xs text-amber-700 dark:text-amber-300 list-disc pl-4 space-y-0.5">
                        {#each warning.suggestionKeys as key (key)}
                            <li>{t(key)}</li>
                        {/each}
                    </ul>
                    {#if warning.actions && warning.actions.length > 0}
                        <div class="pt-1 flex flex-wrap gap-2">
                            {#each warning.actions as action (action.id)}
                                <button
                                    type="button"
                                    class="inline-flex items-center gap-1.5 rounded-lg border border-amber-300 dark:border-amber-700 bg-white dark:bg-amber-900/30 px-2.5 py-1 text-xs font-bold text-amber-700 dark:text-amber-200 hover:bg-amber-100 dark:hover:bg-amber-900/50 transition-colors cursor-pointer"
                                    onclick={() => onaction?.(action.id)}
                                >
                                    <MaterialDesignIcon iconName={action.icon} class="size-3.5" />
                                    <span>{t(action.labelKey)}</span>
                                </button>
                            {/each}
                        </div>
                    {/if}
                </div>
            </div>
        {/each}
    </div>
{/if}
