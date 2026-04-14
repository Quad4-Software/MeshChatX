<template>
    <div class="flex flex-col flex-1 overflow-hidden min-w-0 bg-slate-50 dark:bg-zinc-950">
        <div class="overflow-y-auto flex-1 min-h-0">
            <div class="w-full max-w-[1920px] mx-auto px-4 md:px-5 lg:px-8 py-4 md:py-6 lg:py-8 space-y-6">
                <!-- Header Section -->
                <div class="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
                    <div class="min-w-0">
                        <h1 class="text-2xl font-bold text-gray-900 dark:text-white flex items-center gap-2">
                            <MaterialDesignIcon
                                :icon-name="isEditingInterface ? 'pencil' : 'plus-circle-outline'"
                                class="size-7 text-blue-500"
                            />
                            {{ isEditingInterface ? $t("interfaces.edit_interface") : $t("interfaces.add_interface") }}
                        </h1>
                        <p class="text-sm text-gray-600 dark:text-zinc-400 mt-1">
                            {{
                                isEditingInterface
                                    ? "Update existing connection settings."
                                    : "Create a new connection to the Reticulum network."
                            }}
                        </p>
                    </div>
                    <div class="flex gap-2 shrink-0">
                        <RouterLink :to="{ name: 'interfaces' }" class="secondary-chip">
                            <MaterialDesignIcon icon-name="arrow-left" class="size-4" />
                            Back to List
                        </RouterLink>
                    </div>
                </div>

                <div class="flex flex-col-reverse gap-8 xl:flex-row xl:items-start xl:gap-10">
                    <div class="flex-1 min-w-0 space-y-6 xl:max-w-4xl 2xl:max-w-5xl">
                        <!-- Main Form Card -->
                        <div class="glass-card space-y-8">
                            <div class="grid grid-cols-1 lg:grid-cols-2 gap-8">
                                <!-- Basic Info Column -->
                                <div class="space-y-6">
                                    <div
                                        class="flex items-center gap-2 pb-2 border-b border-gray-100 dark:border-zinc-800"
                                    >
                                        <MaterialDesignIcon
                                            icon-name="information-outline"
                                            class="size-5 text-gray-400"
                                        />
                                        <h3 class="font-bold text-gray-900 dark:text-white">Basic Configuration</h3>
                                    </div>

                                    <div>
                                        <FormLabel class="glass-label">Interface Name</FormLabel>
                                        <input
                                            v-model="newInterfaceName"
                                            type="text"
                                            :disabled="isEditingInterface"
                                            placeholder="e.g. Home Node or Mobile TCP"
                                            class="input-field"
                                            :class="[isEditingInterface ? 'cursor-not-allowed opacity-60' : '']"
                                        />
                                    </div>

                                    <div>
                                        <FormLabel class="glass-label">Transport Type</FormLabel>

                                        <!-- Visual Transport Selection -->
                                        <div class="grid grid-cols-2 gap-2">
                                            <button
                                                v-for="type in [
                                                    {
                                                        id: 'TCPClientInterface',
                                                        name: 'TCP Client',
                                                        icon: 'lan-connect',
                                                        color: 'text-blue-500',
                                                    },
                                                    {
                                                        id: 'BackboneInterface',
                                                        name: 'Backbone',
                                                        icon: 'transit-connection-variant',
                                                        color: 'text-sky-500',
                                                    },
                                                    {
                                                        id: 'TCPServerInterface',
                                                        name: 'TCP Server',
                                                        icon: 'server-network',
                                                        color: 'text-indigo-500',
                                                    },
                                                    {
                                                        id: 'UDPInterface',
                                                        name: 'UDP',
                                                        icon: 'broadcast',
                                                        color: 'text-cyan-500',
                                                    },
                                                    {
                                                        id: 'RNodeInterface',
                                                        name: 'RNode (LoRa)',
                                                        icon: 'radio-handheld',
                                                        color: 'text-emerald-500',
                                                    },
                                                    {
                                                        id: 'I2PInterface',
                                                        name: 'I2P Tunnel',
                                                        icon: 'tunnel',
                                                        color: 'text-purple-500',
                                                    },
                                                    {
                                                        id: 'SerialInterface',
                                                        name: 'Serial (Generic)',
                                                        icon: 'serial-port',
                                                        color: 'text-amber-500',
                                                    },
                                                    {
                                                        id: 'KISSInterface',
                                                        name: 'KISS (TNC)',
                                                        icon: 'radio-tower',
                                                        color: 'text-orange-500',
                                                    },
                                                    {
                                                        id: 'AutoInterface',
                                                        name: 'Auto (Local)',
                                                        icon: 'auto-fix',
                                                        color: 'text-pink-500',
                                                    },
                                                ]"
                                                :key="type.id"
                                                type="button"
                                                class="flex flex-col items-center justify-center p-3 rounded-2xl border transition-all duration-200 text-center gap-1 group"
                                                :class="[
                                                    newInterfaceType === type.id
                                                        ? 'bg-blue-500/10 border-blue-500 ring-1 ring-blue-500/50'
                                                        : 'bg-gray-50/50 dark:bg-zinc-800/30 border-gray-100 dark:border-zinc-800 hover:border-gray-300 dark:hover:border-zinc-600',
                                                ]"
                                                @click="newInterfaceType = type.id"
                                            >
                                                <MaterialDesignIcon
                                                    :icon-name="type.icon"
                                                    class="size-6 transition-transform group-hover:scale-110"
                                                    :class="[
                                                        newInterfaceType === type.id ? 'text-blue-500' : type.color,
                                                    ]"
                                                />
                                                <span
                                                    class="text-[10px] font-bold uppercase tracking-tight"
                                                    :class="[
                                                        newInterfaceType === type.id
                                                            ? 'text-blue-700 dark:text-blue-400'
                                                            : 'text-gray-600 dark:text-zinc-400',
                                                    ]"
                                                >
                                                    {{ type.name }}
                                                </span>
                                            </button>
                                        </div>

                                        <!-- Fallback/More select for less common types -->
                                        <div class="mt-3">
                                            <select
                                                v-model="newInterfaceType"
                                                class="input-field appearance-none pr-10 !py-1.5 !text-[11px] opacity-70 hover:opacity-100"
                                            >
                                                <option :value="null">More options...</option>
                                                <option value="AX25KISSInterface">AX.25 KISS (Amateur Radio)</option>
                                                <option value="LocalInterface">Local Interface (Loopback)</option>
                                                <option value="PipeInterface">Pipe Interface (External)</option>
                                                <option value="RNodeIPInterface">RNode over IP</option>
                                                <option value="BackboneInterface">Backbone (public relay)</option>
                                            </select>
                                        </div>
                                    </div>
                                </div>

                                <!-- Dynamic Interface Specific Settings Column -->
                                <div class="space-y-6">
                                    <div
                                        class="flex items-center gap-2 pb-2 border-b border-gray-100 dark:border-zinc-800"
                                    >
                                        <MaterialDesignIcon icon-name="cog-outline" class="size-5 text-gray-400" />
                                        <h3 class="font-bold text-gray-900 dark:text-white">Connection Details</h3>
                                    </div>

                                    <!-- No selection placeholder -->
                                    <div
                                        v-if="!newInterfaceType"
                                        class="h-48 flex flex-col items-center justify-center text-center p-6 border-2 border-dashed border-gray-100 dark:border-zinc-800 rounded-3xl"
                                    >
                                        <MaterialDesignIcon
                                            icon-name="arrow-left-bold"
                                            class="size-10 text-gray-200 dark:text-zinc-800 animate-bounce-left"
                                        />
                                        <p class="text-sm text-gray-400 dark:text-zinc-600 mt-2">
                                            Select an interface type to configure connection settings.
                                        </p>
                                    </div>

                                    <!-- Interface Specific Fields -->
                                    <div v-else class="space-y-6 animate-in fade-in slide-in-from-right-4 duration-300">
                                        <!-- TCP Client -->
                                        <div v-if="newInterfaceType === 'TCPClientInterface'" class="space-y-4">
                                            <div>
                                                <FormLabel class="glass-label">Target Host</FormLabel>
                                                <input
                                                    v-model="newInterfaceTargetHost"
                                                    type="text"
                                                    placeholder="e.g. 1.2.3.4 or example.com"
                                                    class="input-field"
                                                />
                                            </div>
                                            <div>
                                                <FormLabel class="glass-label">Target Port</FormLabel>
                                                <input
                                                    v-model="newInterfaceTargetPort"
                                                    type="number"
                                                    placeholder="4242"
                                                    class="input-field"
                                                />
                                            </div>
                                        </div>

                                        <div v-if="newInterfaceType === 'BackboneInterface'" class="space-y-4">
                                            <div>
                                                <FormLabel class="glass-label">Remote host</FormLabel>
                                                <input
                                                    v-model="newInterfaceTargetHost"
                                                    type="text"
                                                    placeholder="e.g. example.com or 1.2.3.4"
                                                    class="input-field"
                                                />
                                            </div>
                                            <div>
                                                <FormLabel class="glass-label">Target port</FormLabel>
                                                <input
                                                    v-model="newInterfaceTargetPort"
                                                    type="number"
                                                    placeholder="4242"
                                                    class="input-field"
                                                />
                                            </div>
                                            <div>
                                                <FormLabel class="glass-label">Transport identity (hex)</FormLabel>
                                                <input
                                                    v-model="newInterfaceTransportIdentity"
                                                    type="text"
                                                    placeholder="32 hex chars from the directory"
                                                    class="input-field font-mono text-xs"
                                                />
                                            </div>
                                        </div>

                                        <!-- TCP Server / UDP -->
                                        <div
                                            v-if="['TCPServerInterface', 'UDPInterface'].includes(newInterfaceType)"
                                            class="space-y-4"
                                        >
                                            <div>
                                                <FormLabel class="glass-label">Listen IP (Optional)</FormLabel>
                                                <input
                                                    v-model="newInterfaceListenIp"
                                                    type="text"
                                                    placeholder="0.0.0.0"
                                                    class="input-field"
                                                />
                                            </div>
                                            <div>
                                                <FormLabel class="glass-label">Listen Port</FormLabel>
                                                <input
                                                    v-model="newInterfaceListenPort"
                                                    type="number"
                                                    placeholder="4242"
                                                    class="input-field"
                                                />
                                            </div>
                                        </div>

                                        <!-- UDP Extras -->
                                        <div v-if="newInterfaceType === 'UDPInterface'" class="grid grid-cols-2 gap-4">
                                            <div>
                                                <FormLabel class="glass-label">Forward IP</FormLabel>
                                                <input
                                                    v-model="newInterfaceForwardIp"
                                                    type="text"
                                                    placeholder="255.255.255.255"
                                                    class="input-field"
                                                />
                                            </div>
                                            <div>
                                                <FormLabel class="glass-label">Forward Port</FormLabel>
                                                <input
                                                    v-model="newInterfaceForwardPort"
                                                    type="number"
                                                    placeholder="4242"
                                                    class="input-field"
                                                />
                                            </div>
                                        </div>

                                        <!-- I2P Interface -->
                                        <div v-if="newInterfaceType === 'I2PInterface'" class="space-y-4">
                                            <div
                                                class="bg-blue-50/50 dark:bg-blue-900/10 p-3 rounded-2xl border border-blue-100 dark:border-blue-900/20 text-xs text-blue-800 dark:text-blue-300"
                                            >
                                                ⓘ To use the I2P interface, you must have an I2P router running on your
                                                system.
                                            </div>
                                            <div>
                                                <FormLabel class="glass-label">Initial Peers (Optional)</FormLabel>
                                                <div class="space-y-2">
                                                    <div
                                                        v-for="(peer, index) in I2PSettings.newInterfacePeers"
                                                        :key="index"
                                                        class="flex items-center gap-2"
                                                    >
                                                        <input
                                                            v-model="I2PSettings.newInterfacePeers[index]"
                                                            type="text"
                                                            placeholder="b32.i2p address"
                                                            class="input-field"
                                                        />
                                                        <button
                                                            type="button"
                                                            class="text-red-500 hover:text-red-400 p-1"
                                                            @click="removeI2PPeer(index)"
                                                        >
                                                            <MaterialDesignIcon
                                                                icon-name="trash-can-outline"
                                                                class="size-5"
                                                            />
                                                        </button>
                                                    </div>
                                                    <button
                                                        type="button"
                                                        class="secondary-chip !py-1 !px-3 !text-[10px]"
                                                        @click="addI2PPeer('')"
                                                    >
                                                        <MaterialDesignIcon icon-name="plus" class="size-3" /> Add Peer
                                                    </button>
                                                </div>
                                            </div>
                                        </div>

                                        <!-- RNode / Hardware -->
                                        <div
                                            v-if="
                                                [
                                                    'RNodeInterface',
                                                    'RNodeIPInterface',
                                                    'SerialInterface',
                                                    'KISSInterface',
                                                    'AX25KISSInterface',
                                                ].includes(newInterfaceType)
                                            "
                                            class="space-y-4"
                                        >
                                            <div
                                                v-if="newInterfaceType === 'RNodeInterface'"
                                                class="flex items-center gap-2 pb-2"
                                            >
                                                <Toggle id="rnode-use-ip" v-model="newInterfaceRNodeUseIP" />
                                                <FormLabel for="rnode-use-ip" class="cursor-pointer !mb-0 text-sm"
                                                    >Connect over network (IP)</FormLabel
                                                >
                                            </div>

                                            <div
                                                v-if="newInterfaceRNodeUseIP || newInterfaceType === 'RNodeIPInterface'"
                                                class="grid grid-cols-2 gap-4"
                                            >
                                                <div>
                                                    <FormLabel class="glass-label">Host</FormLabel>
                                                    <input
                                                        v-model="newInterfaceRNodeIPHost"
                                                        type="text"
                                                        placeholder="10.0.0.1"
                                                        class="input-field"
                                                    />
                                                </div>
                                                <div>
                                                    <FormLabel class="glass-label">Port</FormLabel>
                                                    <input
                                                        v-model="newInterfaceRNodeIPPort"
                                                        type="number"
                                                        placeholder="7633"
                                                        class="input-field"
                                                    />
                                                </div>
                                            </div>
                                            <div v-else>
                                                <FormLabel class="glass-label">Serial Port</FormLabel>
                                                <div class="relative">
                                                    <select
                                                        v-model="newInterfacePort"
                                                        class="input-field appearance-none pr-10"
                                                    >
                                                        <option :value="null" disabled>Select a port...</option>
                                                        <option
                                                            v-for="port in comports"
                                                            :key="port.device"
                                                            :value="port.device"
                                                        >
                                                            {{ port.device }} ({{ port.product ?? "?" }})
                                                        </option>
                                                    </select>
                                                    <div
                                                        class="absolute inset-y-0 right-0 flex items-center px-3 pointer-events-none text-gray-400"
                                                    >
                                                        <MaterialDesignIcon icon-name="chevron-down" class="size-5" />
                                                    </div>
                                                </div>
                                                <div class="mt-2 flex justify-end">
                                                    <button
                                                        type="button"
                                                        class="text-[10px] uppercase font-bold text-blue-500 hover:text-blue-600 tracking-wider"
                                                        @click="loadComports"
                                                    >
                                                        Refresh Ports
                                                    </button>
                                                </div>
                                            </div>
                                        </div>

                                        <!-- RNode Radio Parameters -->
                                        <div
                                            v-if="['RNodeInterface', 'RNodeIPInterface'].includes(newInterfaceType)"
                                            class="space-y-4 pt-4 border-t border-gray-100 dark:border-zinc-800"
                                        >
                                            <div>
                                                <FormLabel class="glass-label">Frequency (Hz)</FormLabel>
                                                <div class="flex items-center gap-2">
                                                    <div class="flex-1">
                                                        <input
                                                            v-model.number="RNodeGHzValue"
                                                            type="number"
                                                            min="0"
                                                            class="input-field text-center"
                                                        />
                                                        <div class="text-[10px] text-center text-gray-400 mt-1">
                                                            GHz
                                                        </div>
                                                    </div>
                                                    <div class="flex-1">
                                                        <input
                                                            v-model.number="RNodeMHzValue"
                                                            type="number"
                                                            min="0"
                                                            class="input-field text-center"
                                                        />
                                                        <div class="text-[10px] text-center text-gray-400 mt-1">
                                                            MHz
                                                        </div>
                                                    </div>
                                                    <div class="flex-1">
                                                        <input
                                                            v-model.number="RNodekHzValue"
                                                            type="number"
                                                            min="0"
                                                            class="input-field text-center"
                                                        />
                                                        <div class="text-[10px] text-center text-gray-400 mt-1">
                                                            kHz
                                                        </div>
                                                    </div>
                                                </div>
                                                <div
                                                    v-if="formattedFrequency"
                                                    class="mt-2 text-center text-sm font-mono text-blue-500 font-bold"
                                                >
                                                    {{ formattedFrequency }}
                                                </div>
                                            </div>
                                            <div class="grid grid-cols-2 gap-4">
                                                <div>
                                                    <FormLabel class="glass-label">Bandwidth</FormLabel>
                                                    <select v-model="newInterfaceBandwidth" class="input-field">
                                                        <option
                                                            v-for="bw in RNodeInterfaceDefaults.bandwidths"
                                                            :key="bw"
                                                            :value="bw"
                                                        >
                                                            {{ bw / 1000 }} kHz
                                                        </option>
                                                    </select>
                                                </div>
                                                <div>
                                                    <FormLabel class="glass-label">Power (dBm)</FormLabel>
                                                    <input
                                                        v-model="newInterfaceTxpower"
                                                        type="number"
                                                        class="input-field"
                                                    />
                                                </div>
                                            </div>
                                        </div>

                                        <!-- Pipe Interface -->
                                        <div v-if="newInterfaceType === 'PipeInterface'" class="space-y-4">
                                            <div
                                                class="bg-gray-50/50 dark:bg-zinc-800/30 p-3 rounded-2xl border border-gray-100 dark:border-zinc-800 text-xs text-gray-600 dark:text-zinc-400"
                                            >
                                                ⓘ Interface with external programs via stdin/stdout.
                                            </div>
                                            <div>
                                                <FormLabel class="glass-label">Command</FormLabel>
                                                <input
                                                    v-model="newInterfaceCommand"
                                                    type="text"
                                                    placeholder="e.g. netcat -l 5757"
                                                    class="input-field"
                                                />
                                            </div>
                                            <div>
                                                <FormLabel class="glass-label">Respawn Delay (s)</FormLabel>
                                                <input
                                                    v-model="newInterfaceRespawnDelay"
                                                    type="number"
                                                    placeholder="5"
                                                    class="input-field"
                                                />
                                            </div>
                                        </div>
                                    </div>
                                </div>
                            </div>

                            <!-- Advanced Sections -->
                            <div class="space-y-4 pt-4">
                                <!-- RNode Advanced Tools -->
                                <ExpandingSection
                                    v-if="['RNodeInterface', 'RNodeIPInterface'].includes(newInterfaceType)"
                                    class="glass-card !p-0 overflow-hidden"
                                >
                                    <template #title
                                        ><span class="text-sm font-bold">Calculated Parameters</span></template
                                    >
                                    <template #content>
                                        <div class="p-6 space-y-6">
                                            <div>
                                                <FormLabel class="glass-label">Antenna Gain (dBi)</FormLabel>
                                                <input
                                                    v-model.number="RNodeInterfaceLoRaParameters.antennaGain"
                                                    type="number"
                                                    class="input-field"
                                                />
                                            </div>
                                            <div class="grid grid-cols-3 gap-3">
                                                <div
                                                    class="bg-blue-500/5 p-3 rounded-2xl border border-blue-500/10 text-center"
                                                >
                                                    <div class="text-[10px] uppercase font-bold text-blue-500 mb-1">
                                                        Sensitivity
                                                    </div>
                                                    <div class="text-lg font-mono font-bold">
                                                        {{ RNodeInterfaceLoRaParameters.sensitivity ?? "???" }}
                                                    </div>
                                                </div>
                                                <div
                                                    class="bg-blue-500/5 p-3 rounded-2xl border border-blue-500/10 text-center"
                                                >
                                                    <div class="text-[10px] uppercase font-bold text-blue-500 mb-1">
                                                        Data Rate
                                                    </div>
                                                    <div class="text-lg font-mono font-bold">
                                                        {{ RNodeInterfaceLoRaParameters.dataRate ?? "???" }}
                                                    </div>
                                                </div>
                                                <div
                                                    class="bg-blue-500/5 p-3 rounded-2xl border border-blue-500/10 text-center"
                                                >
                                                    <div class="text-[10px] uppercase font-bold text-blue-500 mb-1">
                                                        Link Budget
                                                    </div>
                                                    <div class="text-lg font-mono font-bold">
                                                        {{ RNodeInterfaceLoRaParameters.linkBudget ?? "???" }}
                                                    </div>
                                                </div>
                                            </div>
                                        </div>
                                    </template>
                                </ExpandingSection>

                                <!-- Interface Discovery Settings -->
                                <ExpandingSection class="glass-card !p-0 overflow-hidden">
                                    <template #title
                                        ><span class="text-sm font-bold">Interface Discovery</span></template
                                    >
                                    <template #content>
                                        <div class="p-6 space-y-6">
                                            <div class="flex items-center justify-between">
                                                <div class="max-w-md">
                                                    <FormLabel class="glass-label !mb-0"
                                                        >Publish Discovery Announce</FormLabel
                                                    >
                                                    <p class="text-xs text-gray-400">
                                                        Makes your node visible to others on the network.
                                                    </p>
                                                </div>
                                                <Toggle v-model="discovery.discoverable" />
                                            </div>
                                            <div
                                                v-if="discovery.discoverable"
                                                class="space-y-4 pt-4 border-t border-gray-100 dark:border-zinc-800 animate-in fade-in slide-in-from-top-2"
                                            >
                                                <div>
                                                    <FormLabel class="glass-label">Discovery Name</FormLabel>
                                                    <input
                                                        v-model="discovery.discovery_name"
                                                        type="text"
                                                        placeholder="Human-friendly name"
                                                        class="input-field"
                                                    />
                                                </div>
                                                <div class="grid grid-cols-2 gap-4">
                                                    <div>
                                                        <FormLabel class="glass-label">Announce Interval (m)</FormLabel>
                                                        <input
                                                            v-model.number="discovery.announce_interval"
                                                            type="number"
                                                            class="input-field"
                                                        />
                                                    </div>
                                                    <div>
                                                        <FormLabel class="glass-label">Reachable On</FormLabel>
                                                        <input
                                                            v-model="discovery.reachable_on"
                                                            type="text"
                                                            placeholder="IP or Hostname"
                                                            class="input-field"
                                                        />
                                                    </div>
                                                </div>
                                                <div class="grid grid-cols-1 md:grid-cols-3 gap-4">
                                                    <div>
                                                        <FormLabel class="glass-label">Latitude (optional)</FormLabel>
                                                        <input
                                                            v-model="discovery.latitude"
                                                            type="text"
                                                            inputmode="decimal"
                                                            autocomplete="off"
                                                            aria-required="false"
                                                            placeholder="Leave blank if unknown"
                                                            class="input-field"
                                                        />
                                                    </div>
                                                    <div>
                                                        <FormLabel class="glass-label">Longitude (optional)</FormLabel>
                                                        <input
                                                            v-model="discovery.longitude"
                                                            type="text"
                                                            inputmode="decimal"
                                                            autocomplete="off"
                                                            aria-required="false"
                                                            placeholder="Leave blank if unknown"
                                                            class="input-field"
                                                        />
                                                    </div>
                                                    <div>
                                                        <FormLabel class="glass-label"
                                                            >Height in metres (optional)</FormLabel
                                                        >
                                                        <input
                                                            v-model="discovery.height"
                                                            type="text"
                                                            inputmode="decimal"
                                                            autocomplete="off"
                                                            aria-required="false"
                                                            placeholder="Leave blank if unknown"
                                                            class="input-field"
                                                        />
                                                    </div>
                                                </div>
                                                <div class="grid grid-cols-2 gap-4">
                                                    <div>
                                                        <FormLabel class="glass-label">Discovery stamp value</FormLabel>
                                                        <input
                                                            v-model.number="discovery.discovery_stamp_value"
                                                            type="number"
                                                            min="1"
                                                            class="input-field"
                                                        />
                                                    </div>
                                                </div>
                                                <div class="flex flex-wrap items-center justify-between gap-4">
                                                    <div class="flex items-center justify-between gap-4 max-w-md">
                                                        <FormLabel class="glass-label !mb-0"
                                                            >Encrypt discovery</FormLabel
                                                        >
                                                        <Toggle v-model="discovery.discovery_encrypt" />
                                                    </div>
                                                    <div class="flex items-center justify-between gap-4 max-w-md">
                                                        <FormLabel class="glass-label !mb-0"
                                                            >Publish IFAC in announce</FormLabel
                                                        >
                                                        <Toggle v-model="discovery.publish_ifac" />
                                                    </div>
                                                </div>
                                            </div>
                                        </div>
                                    </template>
                                </ExpandingSection>

                                <!-- Global Discovery Settings -->
                                <ExpandingSection class="glass-card !p-0 overflow-hidden">
                                    <template #title
                                        ><span class="text-sm font-bold">Discovery Listener (Peer)</span></template
                                    >
                                    <template #content>
                                        <div class="p-6 space-y-6">
                                            <div class="flex items-center justify-between">
                                                <div class="max-w-md">
                                                    <FormLabel class="glass-label !mb-0"
                                                        >Enable Discovery Listener</FormLabel
                                                    >
                                                    <p class="text-xs text-gray-400">
                                                        Listen for announced interfaces and optionally auto-connect.
                                                    </p>
                                                </div>
                                                <Toggle v-model="reticulumDiscovery.discover_interfaces" />
                                            </div>
                                            <div
                                                v-if="reticulumDiscovery.discover_interfaces"
                                                class="space-y-4 pt-4 border-t border-gray-100 dark:border-zinc-800 animate-in fade-in slide-in-from-top-2"
                                            >
                                                <div class="grid grid-cols-1 md:grid-cols-2 gap-4">
                                                    <input
                                                        v-model="reticulumDiscovery.interface_discovery_whitelist"
                                                        type="text"
                                                        placeholder="Whitelist (names, hosts, IDs)"
                                                        class="input-field"
                                                    />
                                                    <input
                                                        v-model="reticulumDiscovery.interface_discovery_blacklist"
                                                        type="text"
                                                        placeholder="Blacklist (names, hosts, IDs)"
                                                        class="input-field"
                                                    />
                                                </div>
                                                <div class="flex justify-end">
                                                    <button
                                                        type="button"
                                                        class="primary-chip !text-[10px]"
                                                        :disabled="savingDiscovery"
                                                        @click="saveReticulumDiscoveryConfig"
                                                    >
                                                        <MaterialDesignIcon icon-name="content-save" class="size-3" />
                                                        Save Listener Prefs
                                                    </button>
                                                </div>
                                            </div>
                                        </div>
                                    </template>
                                </ExpandingSection>

                                <!-- Shared Advanced Settings -->
                                <ExpandingSection class="glass-card !p-0 overflow-hidden">
                                    <template #title
                                        ><span class="text-sm font-bold"
                                            >Advanced Parameters (IFAC, Mode)</span
                                        ></template
                                    >
                                    <template #content>
                                        <div class="p-6 space-y-6">
                                            <div class="grid grid-cols-2 gap-4">
                                                <div>
                                                    <FormLabel class="glass-label">Interface Mode</FormLabel>
                                                    <select v-model="sharedInterfaceSettings.mode" class="input-field">
                                                        <option :value="undefined">Default (Full)</option>
                                                        <option value="full">Full</option>
                                                        <option value="gateway">Gateway</option>
                                                        <option value="access_point">Access Point</option>
                                                        <option value="roaming">Roaming</option>
                                                        <option value="boundary">Boundary</option>
                                                    </select>
                                                </div>
                                                <div>
                                                    <FormLabel class="glass-label">Forced Bitrate</FormLabel>
                                                    <input
                                                        v-model="sharedInterfaceSettings.bitrate"
                                                        type="number"
                                                        placeholder="bps"
                                                        class="input-field"
                                                    />
                                                </div>
                                            </div>
                                            <div class="space-y-4 pt-4 border-t border-gray-100 dark:border-zinc-800">
                                                <FormLabel class="glass-label">Interface Access Code (IFAC)</FormLabel>
                                                <div class="grid grid-cols-1 md:grid-cols-2 gap-4">
                                                    <input
                                                        v-model="sharedInterfaceSettings.network_name"
                                                        type="text"
                                                        placeholder="Network Name"
                                                        class="input-field"
                                                    />
                                                    <input
                                                        v-model="sharedInterfaceSettings.passphrase"
                                                        type="text"
                                                        placeholder="Passphrase"
                                                        class="input-field"
                                                    />
                                                </div>
                                            </div>
                                        </div>
                                    </template>
                                </ExpandingSection>
                            </div>

                            <!-- Footer Save Action -->
                            <div
                                class="pt-8 flex items-center justify-between gap-4 border-t border-gray-200 dark:border-zinc-800"
                            >
                                <button
                                    type="button"
                                    class="secondary-chip !px-10 !py-3 !text-sm"
                                    @click="$router.push({ name: 'interfaces' })"
                                >
                                    Cancel
                                </button>
                                <button
                                    type="button"
                                    class="primary-chip !px-16 !py-3 !text-sm"
                                    :disabled="isSaving"
                                    @click="saveInterface"
                                >
                                    <MaterialDesignIcon
                                        :icon-name="isSaving ? 'loading' : isEditingInterface ? 'content-save' : 'plus'"
                                        class="size-5"
                                        :class="{ 'animate-spin': isSaving }"
                                    />
                                    {{ isEditingInterface ? "Update Connection" : "Create Connection" }}
                                </button>
                            </div>
                        </div>
                    </div>

                    <aside
                        class="w-full shrink-0 space-y-4 xl:w-96 xl:sticky xl:top-4 xl:self-start xl:max-h-[min(calc(100dvh-6rem),920px)] xl:overflow-y-auto xl:border-l border-gray-200/80 dark:border-zinc-800 xl:pl-8"
                        :aria-label="$t('interfaces.add_interface_sidebar_a11y')"
                    >
                        <div
                            v-if="!isEditingInterface && communityPresetsEnabled && communityInterfaces.length > 0"
                            class="glass-card !p-0 overflow-hidden"
                        >
                            <div
                                class="bg-gray-50/50 dark:bg-zinc-800/50 p-4 border-b border-gray-200 dark:border-zinc-800 flex items-center justify-between gap-2"
                            >
                                <div class="min-w-0">
                                    <h2 class="font-bold text-gray-900 dark:text-white flex items-center gap-2 text-sm">
                                        <MaterialDesignIcon icon-name="lightning-bolt" class="size-5 text-yellow-500" />
                                        {{ $t("interfaces.community_quick_start") }}
                                    </h2>
                                    <p class="text-xs text-gray-500 dark:text-zinc-400 mt-0.5">
                                        {{ $t("interfaces.community_quick_start_hint") }}
                                    </p>
                                </div>
                                <button
                                    type="button"
                                    class="text-gray-400 hover:text-gray-600 dark:hover:text-zinc-200 transition-colors p-1 shrink-0"
                                    :title="$t('interfaces.community_quick_start_hide')"
                                    @click="updateConfig({ show_suggested_community_interfaces: false })"
                                >
                                    <MaterialDesignIcon icon-name="close" class="size-5" />
                                </button>
                            </div>

                            <div
                                class="divide-y divide-gray-100 dark:divide-zinc-800 max-h-[min(50vh,28rem)] overflow-y-auto"
                            >
                                <div
                                    v-for="communityIface in communityInterfaces"
                                    :key="
                                        communityIface.name +
                                        (communityIface.target_host || '') +
                                        (communityIface.target_port || '')
                                    "
                                    class="flex p-3 sm:p-4 items-center gap-2 hover:bg-gray-50/30 dark:hover:bg-zinc-800/20 transition-colors"
                                >
                                    <div class="min-w-0 flex-1">
                                        <div class="font-bold text-sm text-gray-900 dark:text-zinc-100">
                                            {{ communityIface.name }}
                                        </div>
                                        <div
                                            class="text-[10px] font-mono text-gray-500 dark:text-zinc-400 mt-0.5 flex flex-wrap items-center gap-2"
                                        >
                                            <MaterialDesignIcon icon-name="server-network" class="size-3 shrink-0" />
                                            <template v-if="communityIface.type === 'I2PInterface'">
                                                {{ communityIface.target_host }}
                                            </template>
                                            <template v-else>
                                                {{ communityIface.target_host }}:{{ communityIface.target_port }}
                                            </template>
                                            <span
                                                v-if="communityIface.online === true"
                                                class="text-green-500 flex items-center gap-1"
                                            >
                                                <span class="size-1.5 rounded-full bg-green-500 animate-pulse"></span>
                                                Online
                                            </span>
                                            <span v-else-if="communityIface.online === false" class="text-red-500"
                                                >Offline</span
                                            >
                                        </div>
                                        <div
                                            v-if="communityIface.description"
                                            class="text-[10px] text-gray-400 dark:text-zinc-500 mt-1 italic line-clamp-2"
                                        >
                                            {{ communityIface.description }}
                                        </div>
                                    </div>
                                    <button
                                        type="button"
                                        class="primary-chip !py-1.5 !px-2 !text-[10px] shrink-0"
                                        @click="
                                            newInterfaceName = communityIface.name;
                                            newInterfaceType = communityIface.type;
                                            newInterfaceTargetHost = communityIface.target_host;
                                            newInterfaceTargetPort = communityIface.target_port;
                                            newInterfaceTransportIdentity = communityIface.transport_identity || null;
                                            I2PSettings.newInterfacePeers =
                                                communityIface.type === 'I2PInterface' && communityIface.i2p_peers
                                                    ? [...communityIface.i2p_peers]
                                                    : [];
                                        "
                                    >
                                        {{ $t("interfaces.community_use_preset") }}
                                    </button>
                                </div>
                            </div>
                        </div>

                        <div
                            v-else-if="
                                !isEditingInterface && communityPresetsDismissed && communityInterfaces.length > 0
                            "
                            class="glass-card p-4 space-y-3"
                        >
                            <p class="text-sm text-gray-600 dark:text-zinc-400">
                                {{ $t("interfaces.community_presets_hidden_hint") }}
                            </p>
                            <button
                                type="button"
                                class="primary-chip !py-2 !px-4 !text-xs w-full"
                                @click="updateConfig({ show_suggested_community_interfaces: true })"
                            >
                                {{ $t("interfaces.community_presets_show_again") }}
                            </button>
                        </div>

                        <div
                            v-else-if="
                                !isEditingInterface &&
                                communityPresetsEnabled &&
                                communityInterfacesFetchDone &&
                                communityInterfaces.length === 0
                            "
                            class="glass-card p-4 text-sm text-gray-500 dark:text-zinc-400"
                        >
                            {{ $t("interfaces.community_presets_empty") }}
                        </div>

                        <div class="grid grid-cols-1 gap-4">
                            <div
                                class="glass-card flex items-center gap-4 bg-blue-50/30 dark:bg-blue-900/10 border-blue-100 dark:border-blue-900/30"
                            >
                                <div
                                    class="size-10 rounded-2xl bg-blue-500/10 flex items-center justify-center text-blue-500 shrink-0"
                                >
                                    <MaterialDesignIcon icon-name="map-search-outline" class="size-6" />
                                </div>
                                <div class="flex-1 min-w-0">
                                    <h3 class="text-sm font-bold text-gray-900 dark:text-white">
                                        {{ $t("interfaces.find_more_nodes") }}
                                    </h3>
                                    <div class="flex flex-wrap gap-2 mt-1">
                                        <a
                                            href="https://directory.rns.recipes/"
                                            target="_blank"
                                            rel="noopener noreferrer"
                                            class="secondary-chip !py-1 !px-2 !text-[9px]"
                                            >rns.recipes</a
                                        >
                                        <a
                                            href="https://rmap.world/"
                                            target="_blank"
                                            rel="noopener noreferrer"
                                            class="secondary-chip !py-1 !px-2 !text-[9px]"
                                            >rmap.world</a
                                        >
                                    </div>
                                </div>
                            </div>

                            <div
                                class="glass-card flex flex-col gap-2 !p-4 bg-emerald-50/20 dark:bg-emerald-900/5 border-emerald-100 dark:border-emerald-900/20"
                            >
                                <div class="flex items-center justify-between gap-2">
                                    <h3
                                        class="text-xs font-bold text-emerald-600 dark:text-emerald-500 uppercase tracking-widest flex items-center gap-2"
                                    >
                                        <MaterialDesignIcon icon-name="import" class="size-4" />
                                        {{ $t("interfaces.quick_import") }}
                                    </h3>
                                    <span class="text-[10px] text-gray-400 shrink-0">{{
                                        $t("interfaces.quick_import_paste_hint")
                                    }}</span>
                                </div>
                                <textarea
                                    v-model="rawConfigInput"
                                    :placeholder="$t('interfaces.quick_import_placeholder')"
                                    class="w-full h-20 bg-white/50 dark:bg-zinc-900/50 border border-emerald-100/50 dark:border-emerald-900/30 rounded-xl p-2 text-[10px] font-mono focus:ring-1 focus:ring-emerald-500 outline-none transition"
                                    @input="handleRawConfigInput"
                                ></textarea>

                                <div v-if="detectedConfigs.length > 1" class="flex flex-wrap gap-2 mt-1">
                                    <button
                                        v-for="cfg in detectedConfigs"
                                        :key="cfg.name"
                                        type="button"
                                        class="bg-emerald-500/10 hover:bg-emerald-500/20 border border-emerald-500/20 rounded-lg px-2 py-1 text-[9px] font-bold text-emerald-600 dark:text-emerald-400 transition"
                                        @click="applyConfig(cfg)"
                                    >
                                        {{ $t("interfaces.quick_import_apply", { name: cfg.name }) }}
                                    </button>
                                </div>
                            </div>
                        </div>
                    </aside>
                </div>
            </div>
        </div>
    </div>
</template>

<script>
import DialogUtils from "../../js/DialogUtils";
import ToastUtils from "../../js/ToastUtils";
import { numOrNull } from "../../js/interfaceDiscoveryUtils";
import ExpandingSection from "./ExpandingSection.vue";
import FormLabel from "../forms/FormLabel.vue";
import Toggle from "../forms/Toggle.vue";
import GlobalState from "../../js/GlobalState";
import MaterialDesignIcon from "../MaterialDesignIcon.vue";

export default {
    name: "AddInterfacePage",
    components: {
        MaterialDesignIcon,
        FormLabel,
        ExpandingSection,
        Toggle,
    },
    data() {
        return {
            rawConfigInput: "",
            detectedConfigs: [],
            isSaving: false,
            isEditingInterface: false,

            config: null,

            communityInterfaces: [],
            communityInterfacesFetchDone: false,

            comports: [],

            newInterfaceName: null,
            newInterfaceType: null,

            newInterfaceGroupID: null,
            newInterfaceMulticastAddressType: null,
            newInterfaceDevices: null,
            newInterfaceIgnoredDevices: null,
            newInterfaceDiscoveryScope: null,
            newInterfaceDiscoveryPort: null,
            newInterfaceDataPort: null,

            newInterfaceTargetHost: null,
            newInterfaceTargetPort: null,
            newInterfaceTransportIdentity: null,

            newInterfaceListenIp: null,
            newInterfaceListenPort: null,
            newInterfaceNetworkDevice: null,
            newInterfacePreferIPV6: null,
            newInterfaceKISSFramingEnabled: null,
            newInterfaceI2PTunnelingEnabled: null,

            sharedInterfaceSettings: {
                mode: null,
                network_name: null,
                passphrase: null,
                ifac_size: null,
                bitrate: null,
            },

            discovery: {
                discoverable: false,
                discovery_name: "",
                announce_interval: 360,
                reachable_on: "",
                discovery_stamp_value: 14,
                discovery_encrypt: false,
                publish_ifac: false,
                latitude: null,
                longitude: null,
                height: null,
                discovery_frequency: null,
                discovery_bandwidth: null,
                discovery_modulation: null,
            },

            reticulumDiscovery: {
                discover_interfaces: false,
                interface_discovery_sources: "",
                interface_discovery_whitelist: "",
                interface_discovery_blacklist: "",
                required_discovery_value: null,
                autoconnect_discovered_interfaces: 0,
                network_identity: "",
            },

            savingDiscovery: false,

            newInterfaceForwardIp: null,
            newInterfaceForwardPort: null,

            I2PSettings: {
                newInterfacePeers: [],
            },

            RNodeMultiInterface: {
                port: null,
                subInterfaces: [],
            },

            newInterfacePort: null,
            newInterfaceRNodeUseIP: false,
            newInterfaceRNodeIPHost: "localhost",
            newInterfaceRNodeIPPort: "7633",
            RNodeGHzValue: 0,
            RNodeMHzValue: 0,
            RNodekHzValue: 0,
            newInterfaceFrequency: null,
            newInterfaceBandwidth: 125000,
            newInterfaceTxpower: 7,
            newInterfaceSpreadingFactor: 12,
            newInterfaceCodingRate: 5,

            // Serial, KISS, and AX25KISS options
            newInterfaceSpeed: null,
            newInterfaceDatabits: null,
            newInterfaceParity: null,
            newInterfaceStopbits: null,

            // KISS and AX25KISS
            newInterfacePreamble: null,
            newInterfaceTXTail: null,
            newInterfacePersistence: null,
            newInterfaceSlotTime: null,

            // RNode and KISS
            newInterfaceCallsign: null,
            newInterfaceIDInterval: null,
            newInterfaceFlowControl: null,
            newInterfaceAirtimeLimitLong: null,
            newInterfaceAirtimeLimitShort: null,

            // Pipe interface
            newInterfaceCommand: null,
            newInterfaceRespawnDelay: null,

            RNodeInterfaceDefaults: {
                // bandwidth in hz
                bandwidths: [
                    7800, // 7.8 kHz
                    10400, // 10.4 kHz
                    15600, // 15.6 kHz
                    20800, // 20.8 kHz
                    31250, // 31.25 kHz
                    41700, // 41.7 kHz
                    62500, // 62.5 kHz
                    125000, // 125 kHz
                    250000, // 250 kHz
                    500000, // 500 kHz
                    1625000, // 1625 kHz (for 2.4 GHz SX1280)
                ],
                codingrates: [
                    5, // 4:5
                    6, // 4:6
                    7, // 4:7
                    8, // 4:8
                ],
                spreadingfactors: [5, 6, 7, 8, 9, 10, 11, 12],
            },

            RNodeInterfaceLoRaParameters: {
                antennaGain: 0,
                noiseFloor: 5,
                sensitivity: null,
                dataRate: null,
                linkBudget: null,
            },
        };
    },
    computed: {
        communityPresetsEnabled() {
            if (this.isEditingInterface) {
                return false;
            }
            const c = this.config;
            if (!c) {
                return true;
            }
            const v = c.show_suggested_community_interfaces;
            if (v === undefined || v === null) {
                return true;
            }
            return this.parseBool(v);
        },
        communityPresetsDismissed() {
            if (this.isEditingInterface || !this.config) {
                return false;
            }
            const v = this.config.show_suggested_community_interfaces;
            if (v === undefined || v === null) {
                return false;
            }
            return !this.parseBool(v);
        },
        formattedFrequency() {
            const totalHz = this.calculateFrequencyInHz();
            if (totalHz >= 1e9) {
                return `${(totalHz / 1e9).toFixed(3)} GHz`;
            } else if (totalHz >= 1e6) {
                return `${(totalHz / 1e6).toFixed(3)} MHz`;
            } else if (totalHz >= 1e3) {
                return `${(totalHz / 1e3).toFixed(3)} kHz`;
            }
            return `${totalHz} Hz`;
        },
    },
    watch: {
        newInterfaceBandwidth: "updateRNodeCalculations",
        newInterfaceSpreadingFactor: "updateRNodeCalculations",
        newInterfaceCodingRate: "updateRNodeCalculations",
        newInterfaceTxpower: "updateRNodeCalculations",
        "RNodeInterfaceLoRaParameters.antennaGain": "updateRNodeCalculations",
    },
    mounted() {
        this.getConfig();
        this.loadReticulumDiscoveryConfig();
        this.loadComports();
        this.loadCommunityInterfaces();

        // check if we are editing an interface
        const interfaceName = this.$route.query.interface_name;
        if (interfaceName != null) {
            this.isEditingInterface = true;
            this.loadInterfaceToEdit(interfaceName);
        }
    },
    methods: {
        async getConfig() {
            try {
                const response = await window.api.get(`/api/v1/config`);
                this.config = response.data.config;
            } catch (e) {
                console.log(e);
            }
        },
        async updateConfig(config) {
            try {
                const response = await window.api.patch("/api/v1/config", config);
                this.config = response.data.config;
            } catch (e) {
                ToastUtils.error(this.$t("common.save_failed"));
                console.log(e);
            }
        },
        parseBool(value) {
            if (typeof value === "string") {
                return ["true", "yes", "1", "y", "on"].includes(value.toLowerCase());
            }
            return Boolean(value);
        },
        numOrNull,
        async loadReticulumDiscoveryConfig() {
            try {
                const response = await window.api.get(`/api/v1/reticulum/discovery`);
                const discovery = response.data?.discovery ?? {};
                this.reticulumDiscovery.discover_interfaces = this.parseBool(discovery.discover_interfaces);
                this.reticulumDiscovery.interface_discovery_whitelist = discovery.interface_discovery_whitelist ?? "";
                this.reticulumDiscovery.interface_discovery_blacklist = discovery.interface_discovery_blacklist ?? "";
            } catch (e) {
                console.log(e);
            }
        },
        async saveReticulumDiscoveryConfig() {
            if (this.savingDiscovery) return;
            this.savingDiscovery = true;
            try {
                const payload = {
                    discover_interfaces: this.reticulumDiscovery.discover_interfaces,
                    interface_discovery_whitelist: this.reticulumDiscovery.interface_discovery_whitelist || null,
                    interface_discovery_blacklist: this.reticulumDiscovery.interface_discovery_blacklist || null,
                };
                await window.api.patch(`/api/v1/reticulum/discovery`, payload);
                ToastUtils.success("Discovery listener preferences saved.");
            } catch (e) {
                ToastUtils.error("Failed to save discovery preferences.");
                console.log(e);
            } finally {
                this.savingDiscovery = false;
            }
        },
        async loadComports() {
            try {
                const response = await window.api.get(`/api/v1/comports`);
                this.comports = response.data.comports;
            } catch (e) {
                console.log(e);
            }
        },
        async loadCommunityInterfaces() {
            try {
                const response = await window.api.get(`/api/v1/community-interfaces`);
                this.communityInterfaces = response.data.interfaces ?? [];
            } catch (e) {
                console.log(e);
                this.communityInterfaces = [];
            } finally {
                this.communityInterfacesFetchDone = true;
            }
        },
        async loadInterfaceToEdit(interfaceName) {
            try {
                const response = await window.api.get(`/api/v1/reticulum/interfaces`);
                const interfaces = response.data.interfaces;
                const iface = interfaces[interfaceName];
                if (!iface) {
                    DialogUtils.alert(this.$t("interfaces.interface_not_found"));
                    this.$router.push({ name: "interfaces" });
                    return;
                }

                this.newInterfaceName = interfaceName;
                this.newInterfaceType = iface.type;
                this.newInterfaceTargetHost = iface.target_host ?? iface.remote ?? null;
                this.newInterfaceTargetPort = iface.target_port ?? null;
                this.newInterfaceTransportIdentity = iface.transport_identity ?? null;
                if (iface.type === "I2PInterface" && Array.isArray(iface.peers)) {
                    this.I2PSettings.newInterfacePeers = [...iface.peers];
                }
                this.newInterfaceListenIp = iface.listen_ip;
                this.newInterfaceListenPort = iface.listen_port;
                this.newInterfacePort = iface.port;
                this.newInterfaceRNodeUseIP = false;
                if (iface.port && String(iface.port).startsWith("tcp://")) {
                    const addr = String(iface.port).replace("tcp://", "");
                    const parts = addr.split(":");
                    this.newInterfaceRNodeIPHost = parts[0] || "localhost";
                    this.newInterfaceRNodeIPPort = parts[1] || "7633";
                    this.newInterfaceRNodeUseIP = true;
                }
                this.newInterfaceFrequency = iface.frequency;
                this.newInterfaceBandwidth = iface.bandwidth;
                this.newInterfaceTxpower = iface.txpower;
                this.newInterfaceSpreadingFactor = iface.spreadingfactor;
                this.newInterfaceCodingRate = iface.codingrate;
                this.newInterfaceCommand = iface.command;
                this.newInterfaceRespawnDelay = iface.respawn_delay;
                this.sharedInterfaceSettings.mode = iface.mode;
                this.sharedInterfaceSettings.bitrate = iface.bitrate;
                this.sharedInterfaceSettings.network_name = iface.network_name;
                this.sharedInterfaceSettings.passphrase = iface.passphrase;

                if (iface.frequency) {
                    this.RNodeGHzValue = Math.floor(iface.frequency / 1e9);
                    this.RNodeMHzValue = Math.floor((iface.frequency % 1e9) / 1e6);
                    this.RNodekHzValue = Math.floor((iface.frequency % 1e6) / 1e3);
                }

                this.discovery.discoverable = this.parseBool(iface.discoverable);
                this.discovery.discovery_name = iface.discovery_name ?? "";
                this.discovery.announce_interval =
                    iface.announce_interval != null && iface.announce_interval !== ""
                        ? Number(iface.announce_interval)
                        : 360;
                this.discovery.reachable_on = iface.reachable_on ?? "";
                this.discovery.discovery_stamp_value =
                    iface.discovery_stamp_value != null && iface.discovery_stamp_value !== ""
                        ? Number(iface.discovery_stamp_value)
                        : 14;
                this.discovery.discovery_encrypt = this.parseBool(iface.discovery_encrypt);
                this.discovery.publish_ifac = this.parseBool(iface.publish_ifac);
                this.discovery.latitude =
                    iface.latitude != null && iface.latitude !== "" ? Number(iface.latitude) : null;
                this.discovery.longitude =
                    iface.longitude != null && iface.longitude !== "" ? Number(iface.longitude) : null;
                this.discovery.height = iface.height != null && iface.height !== "" ? Number(iface.height) : null;
                this.discovery.discovery_frequency =
                    iface.discovery_frequency != null && iface.discovery_frequency !== ""
                        ? Number(iface.discovery_frequency)
                        : null;
                this.discovery.discovery_bandwidth =
                    iface.discovery_bandwidth != null && iface.discovery_bandwidth !== ""
                        ? Number(iface.discovery_bandwidth)
                        : null;
                this.discovery.discovery_modulation =
                    iface.discovery_modulation != null && iface.discovery_modulation !== ""
                        ? Number(iface.discovery_modulation)
                        : null;
            } catch (e) {
                console.log(e);
            }
        },
        handleRawConfigInput() {
            if (!this.rawConfigInput.trim()) {
                this.detectedConfigs = [];
                return;
            }

            const configs = [];
            const sections = this.rawConfigInput.split(/\[\[(.*?)\]\]/);

            // sections[0] is everything before the first [[...]]
            for (let i = 1; i < sections.length; i += 2) {
                const name = sections[i].trim();
                const content = sections[i + 1] || "";
                const config = { name };

                // simple key-value extraction
                const lines = content.split("\n");
                for (const line of lines) {
                    const match = line.match(/^\s*(\w+)\s*=\s*(.*?)\s*$/);
                    if (match) {
                        const key = match[1].trim();
                        let value = match[2].trim();

                        // clean up quotes if present
                        if (
                            (value.startsWith('"') && value.endsWith('"')) ||
                            (value.startsWith("'") && value.endsWith("'"))
                        ) {
                            value = value.substring(1, value.length - 1);
                        }

                        config[key] = value;
                    }
                }

                if (config.type) {
                    configs.push(config);
                }
            }

            this.detectedConfigs = configs;

            // if only one config, auto-apply it
            if (configs.length === 1) {
                this.applyConfig(configs[0]);
            }
        },
        applyConfig(config) {
            if (!config) return;

            this.newInterfaceName = config.name || this.newInterfaceName;
            this.newInterfaceType = config.type;

            // Map raw config keys to component data
            if (config.target_host) this.newInterfaceTargetHost = config.target_host;
            if (config.target_port) this.newInterfaceTargetPort = Number(config.target_port);
            if (config.listen_ip) this.newInterfaceListenIp = config.listen_ip;
            if (config.listen_port) this.newInterfaceListenPort = Number(config.listen_port);
            if (config.forward_ip) this.newInterfaceForwardIp = config.forward_ip;
            if (config.forward_port) this.newInterfaceForwardPort = Number(config.forward_port);
            if (config.port) {
                this.newInterfacePort = config.port;
                if (config.port.startsWith("tcp://")) {
                    const addr = config.port.replace("tcp://", "");
                    const [host, port] = addr.split(":");
                    this.newInterfaceRNodeIPHost = host;
                    this.newInterfaceRNodeIPPort = port || "7633";
                    this.newInterfaceRNodeUseIP = true;
                }
            }

            // Radio params
            if (config.frequency) {
                const freq = Number(config.frequency);
                this.RNodeGHzValue = Math.floor(freq / 1e9);
                this.RNodeMHzValue = Math.floor((freq % 1e9) / 1e6);
                this.RNodekHzValue = Math.floor((freq % 1e6) / 1e3);
            }
            if (config.bandwidth) this.newInterfaceBandwidth = Number(config.bandwidth);
            if (config.txpower) this.newInterfaceTxpower = Number(config.txpower);
            if (config.spreadingfactor) this.newInterfaceSpreadingFactor = Number(config.spreadingfactor);
            if (config.codingrate) this.newInterfaceCodingRate = Number(config.codingrate);

            // KISS/AX.25
            if (config.callsign) this.newInterfaceCallsign = config.callsign;
            if (config.ssid) this.newInterfaceSSID = config.ssid;

            // Advanced
            if (config.mode) this.sharedInterfaceSettings.mode = config.mode;
            if (config.bitrate) this.sharedInterfaceSettings.bitrate = Number(config.bitrate);
            if (config.network_name) this.sharedInterfaceSettings.network_name = config.network_name;
            if (config.passphrase) this.sharedInterfaceSettings.passphrase = config.passphrase;

            if (config.discoverable !== undefined && config.discoverable !== null && config.discoverable !== "") {
                this.discovery.discoverable = this.parseBool(config.discoverable);
            }
            if (config.discovery_name) this.discovery.discovery_name = config.discovery_name;
            if (config.announce_interval) this.discovery.announce_interval = Number(config.announce_interval);
            if (config.reachable_on) this.discovery.reachable_on = config.reachable_on;
            if (config.discovery_stamp_value)
                this.discovery.discovery_stamp_value = Number(config.discovery_stamp_value);
            if (config.discovery_encrypt !== undefined)
                this.discovery.discovery_encrypt = this.parseBool(config.discovery_encrypt);
            if (config.publish_ifac !== undefined) this.discovery.publish_ifac = this.parseBool(config.publish_ifac);
            if (config.latitude) this.discovery.latitude = Number(config.latitude);
            if (config.longitude) this.discovery.longitude = Number(config.longitude);
            if (config.height) this.discovery.height = Number(config.height);

            ToastUtils.success(`Imported configuration for "${config.name}"`);

            // clear input if applied
            this.rawConfigInput = "";
            this.detectedConfigs = [];
        },
        async saveInterface() {
            if (this.isSaving) return;
            this.isSaving = true;
            try {
                const discoveryEnabled = this.discovery.discoverable === true;
                const freqHz = this.calculateFrequencyInHz();

                const i2pPeers =
                    this.newInterfaceType === "I2PInterface"
                        ? (this.I2PSettings.newInterfacePeers || []).map((p) => String(p).trim()).filter(Boolean)
                        : undefined;

                const response = await window.api.post(`/api/v1/reticulum/interfaces/add`, {
                    allow_overwriting_interface: this.isEditingInterface,
                    name: this.newInterfaceName,
                    type: this.newInterfaceType,
                    target_host: this.newInterfaceTargetHost,
                    target_port: this.newInterfaceTargetPort,
                    transport_identity: this.newInterfaceTransportIdentity,
                    peers: i2pPeers,
                    listen_ip: this.newInterfaceListenIp,
                    listen_port: this.newInterfaceListenPort,
                    port: this.newInterfaceRNodeUseIP
                        ? `tcp://${this.newInterfaceRNodeIPHost}:${this.newInterfaceRNodeIPPort}`
                        : this.newInterfacePort,
                    frequency: freqHz,
                    bandwidth: this.newInterfaceBandwidth,
                    txpower: this.newInterfaceTxpower,
                    spreadingfactor: this.newInterfaceSpreadingFactor,
                    codingrate: this.newInterfaceCodingRate,
                    command: this.newInterfaceCommand,
                    respawn_delay: this.newInterfaceRespawnDelay,
                    discoverable: discoveryEnabled ? "yes" : null,
                    discovery_name: discoveryEnabled ? this.discovery.discovery_name : null,
                    announce_interval: discoveryEnabled
                        ? (this.numOrNull(this.discovery.announce_interval) ?? 360)
                        : null,
                    reachable_on: discoveryEnabled ? this.discovery.reachable_on : null,
                    discovery_stamp_value: discoveryEnabled
                        ? (this.numOrNull(this.discovery.discovery_stamp_value) ?? 14)
                        : null,
                    discovery_encrypt: discoveryEnabled ? this.discovery.discovery_encrypt === true : null,
                    publish_ifac: discoveryEnabled ? this.discovery.publish_ifac === true : null,
                    latitude: discoveryEnabled ? this.numOrNull(this.discovery.latitude) : null,
                    longitude: discoveryEnabled ? this.numOrNull(this.discovery.longitude) : null,
                    height: discoveryEnabled ? this.numOrNull(this.discovery.height) : null,
                    discovery_frequency: discoveryEnabled ? this.numOrNull(this.discovery.discovery_frequency) : null,
                    discovery_bandwidth: discoveryEnabled ? this.numOrNull(this.discovery.discovery_bandwidth) : null,
                    discovery_modulation: discoveryEnabled ? this.numOrNull(this.discovery.discovery_modulation) : null,
                    mode: this.sharedInterfaceSettings.mode || "full",
                    bitrate: this.sharedInterfaceSettings.bitrate,
                    network_name: this.sharedInterfaceSettings.network_name,
                    passphrase: this.sharedInterfaceSettings.passphrase,
                });

                if (response.data.message) ToastUtils.success(response.data.message);
                GlobalState.hasPendingInterfaceChanges = true;
                GlobalState.modifiedInterfaceNames.add(this.newInterfaceName);
                this.$router.push({ name: "interfaces" });
            } catch (e) {
                const message = e.response?.data?.message ?? "Failed to save interface connection.";
                ToastUtils.error(message);
                console.log(e);
            } finally {
                this.isSaving = false;
            }
        },
        calculateFrequencyInHz() {
            return this.RNodeGHzValue * 1e9 + this.RNodeMHzValue * 1e6 + this.RNodekHzValue * 1e3;
        },
        updateRNodeCalculations() {
            this.calculateRNodeParameters(
                this.newInterfaceBandwidth,
                this.newInterfaceSpreadingFactor,
                this.newInterfaceCodingRate,
                this.RNodeInterfaceLoRaParameters.noiseFloor,
                this.RNodeInterfaceLoRaParameters.antennaGain,
                this.newInterfaceTxpower
            );
        },
        calculateRNodeParameters(bandwidth, spreadingFactor, codingRate, noiseFloor, antennaGain, transmitPower) {
            if (!bandwidth || !spreadingFactor || !codingRate) return;
            const crn = { 5: 1, 6: 2, 7: 3, 8: 4 };
            const cr = crn[codingRate];
            const sfn = { 5: -2.5, 6: -5, 7: -7.5, 8: -10, 9: -12.5, 10: -15, 11: -17.5, 12: -20 };
            let dataRate =
                spreadingFactor * (4 / (4 + cr) / (Math.pow(2, spreadingFactor) / (bandwidth / 1000))) * 1000;
            let sensitivity = -174 + 10 * Math.log10(bandwidth) + noiseFloor + (sfn[spreadingFactor] || 0);
            if (bandwidth === 203125 || bandwidth === 406250 || bandwidth > 500000) {
                sensitivity = -165.6 + 10 * Math.log10(bandwidth) + noiseFloor + (sfn[spreadingFactor] || 0);
            }
            let linkBudget = transmitPower - sensitivity + antennaGain;
            this.RNodeInterfaceLoRaParameters.dataRate =
                dataRate < 1000 ? `${dataRate.toFixed(0)} bps` : `${(dataRate / 1000).toFixed(2)} kbps`;
            this.RNodeInterfaceLoRaParameters.linkBudget = `${linkBudget.toFixed(1)} dB`;
            this.RNodeInterfaceLoRaParameters.sensitivity = `${sensitivity.toFixed(1)} dBm`;
        },
        addI2PPeer(address = "") {
            this.I2PSettings.newInterfacePeers.push(address);
        },
        removeI2PPeer(index) {
            this.I2PSettings.newInterfacePeers.splice(index, 1);
        },
        addSubInterface() {
            this.RNodeMultiInterface.subInterfaces.push({
                name: "",
                frequency: null,
                bandwidth: null,
                txpower: null,
                spreadingfactor: null,
                codingrate: null,
                vport: null,
            });
        },
        useKISSAX25() {
            this.newInterfaceType =
                this.newInterfaceType === "AX25KISSInterface" ? "KISSInterface" : "AX25KISSInterface";
        },
        removeSubInterface(idx) {
            this.RNodeMultiInterface.subInterfaces.splice(idx, 1);
        },
    },
};
</script>

<style scoped>
.glass-card {
    @apply bg-white/95 dark:bg-zinc-900/85 backdrop-blur border border-gray-200 dark:border-zinc-800 rounded-3xl shadow-xl p-6;
}
.input-field {
    @apply bg-gray-50/90 dark:bg-zinc-900/80 border border-gray-200 dark:border-zinc-700 text-sm rounded-2xl focus:ring-2 focus:ring-blue-400 focus:border-blue-400 dark:focus:ring-blue-500 dark:focus:border-blue-500 block w-full p-2.5 text-gray-900 dark:text-gray-100 transition;
}
.glass-label {
    @apply mb-1.5 block text-xs uppercase font-bold text-gray-500 dark:text-zinc-400 tracking-wider;
}
.glass-field {
    @apply space-y-1;
}
</style>
