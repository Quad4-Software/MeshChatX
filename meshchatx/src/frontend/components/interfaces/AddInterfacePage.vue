<!-- SPDX-License-Identifier: 0BSD AND MIT -->

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
                                            <div class="flex items-center gap-2">
                                                <Toggle
                                                    id="tcp-kiss-framing"
                                                    v-model="newInterfaceKISSFramingEnabled"
                                                />
                                                <FormLabel for="tcp-kiss-framing" class="cursor-pointer !mb-0 text-sm"
                                                    >Use KISS framing (legacy compatibility)</FormLabel
                                                >
                                            </div>
                                            <div class="flex items-center gap-2">
                                                <Toggle
                                                    id="tcp-i2p-tunneled"
                                                    v-model="newInterfaceI2PTunnelingEnabled"
                                                />
                                                <FormLabel for="tcp-i2p-tunneled" class="cursor-pointer !mb-0 text-sm"
                                                    >I2P Tunneled (target is an I2P b32)</FormLabel
                                                >
                                            </div>
                                            <div class="grid grid-cols-3 gap-3">
                                                <div>
                                                    <FormLabel class="glass-label">Connect Timeout (s)</FormLabel>
                                                    <input
                                                        v-model="newInterfaceConnectTimeout"
                                                        type="number"
                                                        min="0"
                                                        placeholder="default"
                                                        class="input-field"
                                                    />
                                                </div>
                                                <div>
                                                    <FormLabel class="glass-label">Max Reconnect Tries</FormLabel>
                                                    <input
                                                        v-model="newInterfaceMaxReconnectTries"
                                                        type="number"
                                                        min="0"
                                                        placeholder="default"
                                                        class="input-field"
                                                    />
                                                </div>
                                                <div>
                                                    <FormLabel class="glass-label">Fixed MTU</FormLabel>
                                                    <input
                                                        v-model="newInterfaceFixedMTU"
                                                        type="number"
                                                        min="0"
                                                        placeholder="auto"
                                                        class="input-field"
                                                    />
                                                </div>
                                            </div>
                                        </div>

                                        <div v-if="newInterfaceType === 'BackboneInterface'" class="space-y-4">
                                            <div class="flex items-center gap-2">
                                                <Toggle
                                                    id="backbone-listen-mode"
                                                    v-model="newInterfaceBackboneListenMode"
                                                />
                                                <FormLabel
                                                    for="backbone-listen-mode"
                                                    class="cursor-pointer !mb-0 text-sm"
                                                    >Listener mode (host this backbone)</FormLabel
                                                >
                                            </div>
                                            <div v-if="!newInterfaceBackboneListenMode" class="space-y-4">
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
                                            <div v-else class="space-y-4">
                                                <div>
                                                    <FormLabel class="glass-label">Listen IP (Optional)</FormLabel>
                                                    <input
                                                        v-model="newInterfaceBackboneListenIp"
                                                        type="text"
                                                        placeholder="0.0.0.0"
                                                        class="input-field"
                                                    />
                                                </div>
                                                <div>
                                                    <FormLabel class="glass-label">Listen Port</FormLabel>
                                                    <input
                                                        v-model="newInterfaceBackboneListenPort"
                                                        type="number"
                                                        placeholder="4242"
                                                        class="input-field"
                                                    />
                                                </div>
                                                <div>
                                                    <FormLabel class="glass-label">Device (optional)</FormLabel>
                                                    <input
                                                        v-model="newInterfaceBackboneListenDevice"
                                                        type="text"
                                                        placeholder="e.g. eth0"
                                                        class="input-field"
                                                    />
                                                </div>
                                                <div class="flex items-center gap-2">
                                                    <Toggle
                                                        id="backbone-listen-ipv6"
                                                        v-model="newInterfacePreferIPV6"
                                                    />
                                                    <FormLabel
                                                        for="backbone-listen-ipv6"
                                                        class="cursor-pointer !mb-0 text-sm"
                                                        >Prefer IPv6</FormLabel
                                                    >
                                                </div>
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
                                            <div>
                                                <FormLabel class="glass-label">Device (optional)</FormLabel>
                                                <input
                                                    v-model="newInterfaceNetworkDevice"
                                                    type="text"
                                                    placeholder="e.g. eth0 (overrides Listen IP)"
                                                    class="input-field"
                                                />
                                            </div>
                                            <div
                                                v-if="newInterfaceType === 'TCPServerInterface'"
                                                class="flex flex-wrap items-center gap-4"
                                            >
                                                <div class="flex items-center gap-2">
                                                    <Toggle id="tcp-server-ipv6" v-model="newInterfacePreferIPV6" />
                                                    <FormLabel
                                                        for="tcp-server-ipv6"
                                                        class="cursor-pointer !mb-0 text-sm"
                                                        >Prefer IPv6</FormLabel
                                                    >
                                                </div>
                                                <div class="flex items-center gap-2">
                                                    <Toggle
                                                        id="tcp-server-i2p"
                                                        v-model="newInterfaceI2PTunnelingEnabled"
                                                    />
                                                    <FormLabel for="tcp-server-i2p" class="cursor-pointer !mb-0 text-sm"
                                                        >I2P Tunneled</FormLabel
                                                    >
                                                </div>
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
                                            <div class="flex items-center gap-2">
                                                <Toggle id="i2p-connectable" v-model="newInterfaceConnectable" />
                                                <FormLabel for="i2p-connectable" class="cursor-pointer !mb-0 text-sm"
                                                    >Allow incoming peers (connectable)</FormLabel
                                                >
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
                                            <div class="grid grid-cols-2 gap-4">
                                                <div>
                                                    <FormLabel class="glass-label">Spreading Factor</FormLabel>
                                                    <select v-model="newInterfaceSpreadingFactor" class="input-field">
                                                        <option
                                                            v-for="sf in RNodeInterfaceDefaults.spreadingfactors"
                                                            :key="sf"
                                                            :value="sf"
                                                        >
                                                            SF{{ sf }}
                                                        </option>
                                                    </select>
                                                </div>
                                                <div>
                                                    <FormLabel class="glass-label">Coding Rate</FormLabel>
                                                    <select v-model="newInterfaceCodingRate" class="input-field">
                                                        <option
                                                            v-for="cr in RNodeInterfaceDefaults.codingrates"
                                                            :key="cr"
                                                            :value="cr"
                                                        >
                                                            4:{{ cr }}
                                                        </option>
                                                    </select>
                                                </div>
                                            </div>
                                            <div class="flex items-center gap-2">
                                                <Toggle id="rnode-flow-control" v-model="newInterfaceFlowControl" />
                                                <FormLabel for="rnode-flow-control" class="cursor-pointer !mb-0 text-sm"
                                                    >Hardware flow control</FormLabel
                                                >
                                            </div>
                                            <div class="grid grid-cols-2 gap-4">
                                                <div>
                                                    <FormLabel class="glass-label">Station ID Callsign</FormLabel>
                                                    <input
                                                        v-model="newInterfaceIDCallsign"
                                                        type="text"
                                                        placeholder="e.g. NOCALL"
                                                        class="input-field"
                                                    />
                                                </div>
                                                <div>
                                                    <FormLabel class="glass-label">ID Interval (s)</FormLabel>
                                                    <input
                                                        v-model="newInterfaceIDInterval"
                                                        type="number"
                                                        min="0"
                                                        placeholder="600"
                                                        class="input-field"
                                                    />
                                                </div>
                                            </div>
                                            <div class="grid grid-cols-2 gap-4">
                                                <div>
                                                    <FormLabel class="glass-label">Airtime Limit Long (%)</FormLabel>
                                                    <input
                                                        v-model="newInterfaceAirtimeLimitLong"
                                                        type="number"
                                                        min="0"
                                                        max="100"
                                                        step="0.1"
                                                        placeholder="optional"
                                                        class="input-field"
                                                    />
                                                </div>
                                                <div>
                                                    <FormLabel class="glass-label">Airtime Limit Short (%)</FormLabel>
                                                    <input
                                                        v-model="newInterfaceAirtimeLimitShort"
                                                        type="number"
                                                        min="0"
                                                        max="100"
                                                        step="0.1"
                                                        placeholder="optional"
                                                        class="input-field"
                                                    />
                                                </div>
                                            </div>
                                        </div>

                                        <!-- Serial port settings (Serial/KISS/AX25KISS) -->
                                        <div
                                            v-if="
                                                ['SerialInterface', 'KISSInterface', 'AX25KISSInterface'].includes(
                                                    newInterfaceType
                                                )
                                            "
                                            class="space-y-4 pt-4 border-t border-gray-100 dark:border-zinc-800"
                                        >
                                            <div class="grid grid-cols-2 gap-4">
                                                <div>
                                                    <FormLabel class="glass-label">Baud Rate</FormLabel>
                                                    <input
                                                        v-model="newInterfaceSpeed"
                                                        type="number"
                                                        min="0"
                                                        placeholder="9600"
                                                        class="input-field"
                                                    />
                                                </div>
                                                <div>
                                                    <FormLabel class="glass-label">Data Bits</FormLabel>
                                                    <select v-model="newInterfaceDatabits" class="input-field">
                                                        <option :value="null">Default (8)</option>
                                                        <option :value="5">5</option>
                                                        <option :value="6">6</option>
                                                        <option :value="7">7</option>
                                                        <option :value="8">8</option>
                                                    </select>
                                                </div>
                                            </div>
                                            <div class="grid grid-cols-2 gap-4">
                                                <div>
                                                    <FormLabel class="glass-label">Parity</FormLabel>
                                                    <select v-model="newInterfaceParity" class="input-field">
                                                        <option :value="null">Default (none)</option>
                                                        <option value="N">None</option>
                                                        <option value="E">Even</option>
                                                        <option value="O">Odd</option>
                                                    </select>
                                                </div>
                                                <div>
                                                    <FormLabel class="glass-label">Stop Bits</FormLabel>
                                                    <select v-model="newInterfaceStopbits" class="input-field">
                                                        <option :value="null">Default (1)</option>
                                                        <option :value="1">1</option>
                                                        <option :value="2">2</option>
                                                    </select>
                                                </div>
                                            </div>
                                        </div>

                                        <!-- KISS framing parameters (KISS/AX25KISS) -->
                                        <div
                                            v-if="['KISSInterface', 'AX25KISSInterface'].includes(newInterfaceType)"
                                            class="space-y-4 pt-4 border-t border-gray-100 dark:border-zinc-800"
                                        >
                                            <div class="grid grid-cols-2 gap-4">
                                                <div>
                                                    <FormLabel class="glass-label">Preamble (ms)</FormLabel>
                                                    <input
                                                        v-model="newInterfacePreamble"
                                                        type="number"
                                                        min="0"
                                                        placeholder="350"
                                                        class="input-field"
                                                    />
                                                </div>
                                                <div>
                                                    <FormLabel class="glass-label">TX Tail (ms)</FormLabel>
                                                    <input
                                                        v-model="newInterfaceTXTail"
                                                        type="number"
                                                        min="0"
                                                        placeholder="20"
                                                        class="input-field"
                                                    />
                                                </div>
                                                <div>
                                                    <FormLabel class="glass-label">Persistence (0-255)</FormLabel>
                                                    <input
                                                        v-model="newInterfacePersistence"
                                                        type="number"
                                                        min="0"
                                                        max="255"
                                                        placeholder="64"
                                                        class="input-field"
                                                    />
                                                </div>
                                                <div>
                                                    <FormLabel class="glass-label">Slot Time (ms)</FormLabel>
                                                    <input
                                                        v-model="newInterfaceSlotTime"
                                                        type="number"
                                                        min="0"
                                                        placeholder="20"
                                                        class="input-field"
                                                    />
                                                </div>
                                            </div>
                                            <div class="flex items-center gap-2">
                                                <Toggle id="kiss-flow-control" v-model="newInterfaceFlowControl" />
                                                <FormLabel for="kiss-flow-control" class="cursor-pointer !mb-0 text-sm"
                                                    >Hardware flow control</FormLabel
                                                >
                                            </div>
                                            <div class="grid grid-cols-2 gap-4">
                                                <div>
                                                    <FormLabel class="glass-label">Beacon Callsign</FormLabel>
                                                    <input
                                                        v-model="newInterfaceIDCallsign"
                                                        type="text"
                                                        placeholder="optional"
                                                        class="input-field"
                                                    />
                                                </div>
                                                <div>
                                                    <FormLabel class="glass-label">Beacon Interval (s)</FormLabel>
                                                    <input
                                                        v-model="newInterfaceIDInterval"
                                                        type="number"
                                                        min="0"
                                                        placeholder="optional"
                                                        class="input-field"
                                                    />
                                                </div>
                                            </div>
                                        </div>

                                        <!-- AX.25 KISS extras -->
                                        <div
                                            v-if="newInterfaceType === 'AX25KISSInterface'"
                                            class="space-y-4 pt-4 border-t border-gray-100 dark:border-zinc-800"
                                        >
                                            <div class="grid grid-cols-2 gap-4">
                                                <div>
                                                    <FormLabel class="glass-label">AX.25 Callsign</FormLabel>
                                                    <input
                                                        v-model="newInterfaceCallsign"
                                                        type="text"
                                                        placeholder="e.g. NOCALL"
                                                        class="input-field"
                                                    />
                                                </div>
                                                <div>
                                                    <FormLabel class="glass-label">SSID (0-15)</FormLabel>
                                                    <input
                                                        v-model="newInterfaceSSID"
                                                        type="number"
                                                        min="0"
                                                        max="15"
                                                        placeholder="0"
                                                        class="input-field"
                                                    />
                                                </div>
                                            </div>
                                        </div>

                                        <!-- AutoInterface -->
                                        <div v-if="newInterfaceType === 'AutoInterface'" class="space-y-4">
                                            <div
                                                class="bg-pink-50/50 dark:bg-pink-900/10 p-3 rounded-2xl border border-pink-100 dark:border-pink-900/20 text-xs text-pink-800 dark:text-pink-300"
                                            >
                                                ⓘ Auto Interface auto-discovers peers on connected networks via IPv6
                                                multicast.
                                            </div>
                                            <div>
                                                <FormLabel class="glass-label">Group ID (optional)</FormLabel>
                                                <input
                                                    v-model="newInterfaceGroupID"
                                                    type="text"
                                                    placeholder="reticulum"
                                                    class="input-field"
                                                />
                                                <p class="text-[10px] text-gray-400 mt-1">
                                                    Only peers sharing the same group_id will discover each other.
                                                </p>
                                            </div>
                                            <div class="grid grid-cols-2 gap-4">
                                                <div>
                                                    <FormLabel class="glass-label">Discovery Scope</FormLabel>
                                                    <select v-model="newInterfaceDiscoveryScope" class="input-field">
                                                        <option :value="null">Default (link)</option>
                                                        <option value="link">Link (local segment)</option>
                                                        <option value="admin">Administrative</option>
                                                        <option value="site">Site</option>
                                                        <option value="organisation">Organisation</option>
                                                        <option value="global">Global</option>
                                                    </select>
                                                </div>
                                                <div>
                                                    <FormLabel class="glass-label">Multicast Address Type</FormLabel>
                                                    <select
                                                        v-model="newInterfaceMulticastAddressType"
                                                        class="input-field"
                                                    >
                                                        <option :value="null">Default (temporary)</option>
                                                        <option value="temporary">Temporary</option>
                                                        <option value="permanent">Permanent</option>
                                                    </select>
                                                </div>
                                            </div>
                                            <div class="grid grid-cols-2 gap-4">
                                                <div>
                                                    <FormLabel class="glass-label">Discovery Port</FormLabel>
                                                    <input
                                                        v-model="newInterfaceDiscoveryPort"
                                                        type="number"
                                                        min="1"
                                                        max="65535"
                                                        placeholder="29716"
                                                        class="input-field"
                                                    />
                                                </div>
                                                <div>
                                                    <FormLabel class="glass-label">Data Port</FormLabel>
                                                    <input
                                                        v-model="newInterfaceDataPort"
                                                        type="number"
                                                        min="1"
                                                        max="65535"
                                                        placeholder="42671"
                                                        class="input-field"
                                                    />
                                                </div>
                                            </div>
                                            <div>
                                                <FormLabel class="glass-label"
                                                    >Allowed Devices (comma separated)</FormLabel
                                                >
                                                <input
                                                    v-model="newInterfaceDevices"
                                                    type="text"
                                                    placeholder="e.g. eth0, wlan0"
                                                    class="input-field"
                                                />
                                            </div>
                                            <div>
                                                <FormLabel class="glass-label"
                                                    >Ignored Devices (comma separated)</FormLabel
                                                >
                                                <input
                                                    v-model="newInterfaceIgnoredDevices"
                                                    type="text"
                                                    placeholder="e.g. tun0, docker0"
                                                    class="input-field"
                                                />
                                            </div>
                                            <div>
                                                <FormLabel class="glass-label">Configured Bitrate (bps)</FormLabel>
                                                <input
                                                    v-model="newInterfaceConfiguredBitrate"
                                                    type="number"
                                                    min="0"
                                                    placeholder="optional override"
                                                    class="input-field"
                                                />
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
                                        @click="quickAddInterfaceFromConfig(communityIface)"
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
                                        @click="quickAddInterfaceFromConfig(cfg)"
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
            newInterfacePreferIPV6: false,
            newInterfaceKISSFramingEnabled: false,
            newInterfaceI2PTunnelingEnabled: false,
            newInterfaceConnectTimeout: null,
            newInterfaceMaxReconnectTries: null,
            newInterfaceFixedMTU: null,
            newInterfaceConfiguredBitrate: null,
            newInterfaceConnectable: true,
            newInterfaceBackboneListenMode: false,
            newInterfaceBackboneListenPort: null,
            newInterfaceBackboneListenIp: null,
            newInterfaceBackboneListenDevice: null,

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

            // AX25 KISS only
            newInterfaceSSID: null,

            // RNode and KISS
            newInterfaceCallsign: null,
            newInterfaceIDCallsign: null,
            newInterfaceIDInterval: null,
            newInterfaceFlowControl: false,
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

        // check if we have a discovered interface prefill payload
        if (this.$route.query.from_discovered) {
            this.applyDiscoveredInterfacePrefill();
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
                this.newInterfaceForwardIp = iface.forward_ip;
                this.newInterfaceForwardPort = iface.forward_port;
                this.newInterfaceNetworkDevice = iface.device;
                this.newInterfacePreferIPV6 = this.parseBool(iface.prefer_ipv6);
                this.newInterfaceKISSFramingEnabled = this.parseBool(iface.kiss_framing);
                this.newInterfaceI2PTunnelingEnabled = this.parseBool(iface.i2p_tunneled);
                this.newInterfaceConnectTimeout = iface.connect_timeout ?? null;
                this.newInterfaceMaxReconnectTries = iface.max_reconnect_tries ?? null;
                this.newInterfaceFixedMTU = iface.fixed_mtu ?? null;
                this.newInterfaceConnectable =
                    iface.connectable === undefined ? true : this.parseBool(iface.connectable);

                if (iface.type === "BackboneInterface") {
                    this.newInterfaceBackboneListenMode = iface.listen_port != null && iface.listen_port !== "";
                    this.newInterfaceBackboneListenIp = iface.listen_ip ?? null;
                    this.newInterfaceBackboneListenPort = iface.listen_port ?? null;
                    this.newInterfaceBackboneListenDevice = iface.device ?? null;
                }

                this.newInterfaceGroupID = iface.group_id ?? null;
                this.newInterfaceMulticastAddressType = iface.multicast_address_type ?? null;
                this.newInterfaceDevices = iface.devices ?? null;
                this.newInterfaceIgnoredDevices = iface.ignored_devices ?? null;
                this.newInterfaceDiscoveryScope = iface.discovery_scope ?? null;
                this.newInterfaceDiscoveryPort = iface.discovery_port ?? null;
                this.newInterfaceDataPort = iface.data_port ?? null;
                this.newInterfaceConfiguredBitrate = iface.configured_bitrate ?? null;

                this.newInterfaceFlowControl = this.parseBool(iface.flow_control);
                this.newInterfaceCallsign = iface.callsign ?? null;
                this.newInterfaceIDCallsign = iface.id_callsign ?? null;
                this.newInterfaceIDInterval = iface.id_interval ?? null;
                this.newInterfaceAirtimeLimitLong = iface.airtime_limit_long ?? null;
                this.newInterfaceAirtimeLimitShort = iface.airtime_limit_short ?? null;
                this.newInterfaceSSID = iface.ssid ?? null;
                this.newInterfaceSpeed = iface.speed ?? null;
                this.newInterfaceDatabits = iface.databits ?? null;
                this.newInterfaceParity = iface.parity ?? null;
                this.newInterfaceStopbits = iface.stopbits ?? null;
                this.newInterfacePreamble = iface.preamble ?? null;
                this.newInterfaceTXTail = iface.txtail ?? null;
                this.newInterfacePersistence = iface.persistence ?? null;
                this.newInterfaceSlotTime = iface.slottime ?? null;

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

            // if only one config, auto-import it directly
            if (configs.length === 1) {
                this.quickAddInterfaceFromConfig(configs[0]);
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
            if (config.id_callsign) this.newInterfaceIDCallsign = config.id_callsign;
            if (config.id_interval) this.newInterfaceIDInterval = Number(config.id_interval);
            if (config.flow_control !== undefined) this.newInterfaceFlowControl = this.parseBool(config.flow_control);
            if (config.preamble) this.newInterfacePreamble = Number(config.preamble);
            if (config.txtail) this.newInterfaceTXTail = Number(config.txtail);
            if (config.persistence) this.newInterfacePersistence = Number(config.persistence);
            if (config.slottime) this.newInterfaceSlotTime = Number(config.slottime);
            if (config.speed) this.newInterfaceSpeed = Number(config.speed);
            if (config.databits) this.newInterfaceDatabits = Number(config.databits);
            if (config.parity) this.newInterfaceParity = config.parity;
            if (config.stopbits) this.newInterfaceStopbits = Number(config.stopbits);

            // AutoInterface
            if (config.group_id) this.newInterfaceGroupID = config.group_id;
            if (config.discovery_scope) this.newInterfaceDiscoveryScope = config.discovery_scope;
            if (config.discovery_port) this.newInterfaceDiscoveryPort = Number(config.discovery_port);
            if (config.data_port) this.newInterfaceDataPort = Number(config.data_port);
            if (config.multicast_address_type) this.newInterfaceMulticastAddressType = config.multicast_address_type;
            if (config.devices) this.newInterfaceDevices = config.devices;
            if (config.ignored_devices) this.newInterfaceIgnoredDevices = config.ignored_devices;
            if (config.configured_bitrate) this.newInterfaceConfiguredBitrate = Number(config.configured_bitrate);

            // TCP / Network extras
            if (config.kiss_framing !== undefined)
                this.newInterfaceKISSFramingEnabled = this.parseBool(config.kiss_framing);
            if (config.i2p_tunneled !== undefined)
                this.newInterfaceI2PTunnelingEnabled = this.parseBool(config.i2p_tunneled);
            if (config.connect_timeout) this.newInterfaceConnectTimeout = Number(config.connect_timeout);
            if (config.max_reconnect_tries) this.newInterfaceMaxReconnectTries = Number(config.max_reconnect_tries);
            if (config.fixed_mtu) this.newInterfaceFixedMTU = Number(config.fixed_mtu);
            if (config.device) this.newInterfaceNetworkDevice = config.device;
            if (config.prefer_ipv6 !== undefined) this.newInterfacePreferIPV6 = this.parseBool(config.prefer_ipv6);
            if (config.connectable !== undefined) this.newInterfaceConnectable = this.parseBool(config.connectable);

            // RNode airtime / id callsign
            if (config.airtime_limit_long) this.newInterfaceAirtimeLimitLong = Number(config.airtime_limit_long);
            if (config.airtime_limit_short) this.newInterfaceAirtimeLimitShort = Number(config.airtime_limit_short);

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
        buildPayloadFromImportedConfig(config) {
            const discoveryEnabled =
                config.discoverable !== undefined && config.discoverable !== null && config.discoverable !== ""
                    ? this.parseBool(config.discoverable)
                    : false;
            const i2pPeers =
                config.type === "I2PInterface"
                    ? Array.isArray(config.i2p_peers)
                        ? config.i2p_peers.map((p) => String(p).trim()).filter(Boolean)
                        : Array.isArray(config.peers)
                          ? config.peers.map((p) => String(p).trim()).filter(Boolean)
                          : []
                    : undefined;
            return {
                allow_overwriting_interface: false,
                name: config.name,
                type: config.type,
                target_host: config.target_host || config.remote || null,
                target_port: this.numOrNull(config.target_port),
                transport_identity: config.transport_identity || null,
                peers: i2pPeers,
                listen_ip: config.listen_ip || null,
                listen_port: this.numOrNull(config.listen_port),
                port: config.port || null,
                frequency: this.numOrNull(config.frequency),
                bandwidth: this.numOrNull(config.bandwidth),
                txpower: this.numOrNull(config.txpower),
                spreadingfactor: this.numOrNull(config.spreadingfactor),
                codingrate: this.numOrNull(config.codingrate),
                command: config.command || null,
                respawn_delay: this.numOrNull(config.respawn_delay),
                discoverable: discoveryEnabled ? "yes" : null,
                discovery_name: discoveryEnabled ? config.discovery_name || config.name || null : null,
                announce_interval: discoveryEnabled ? (this.numOrNull(config.announce_interval) ?? 360) : null,
                reachable_on: discoveryEnabled ? config.reachable_on || config.target_host || null : null,
                discovery_stamp_value: discoveryEnabled ? (this.numOrNull(config.discovery_stamp_value) ?? 14) : null,
                discovery_encrypt: discoveryEnabled
                    ? config.discovery_encrypt !== undefined
                        ? this.parseBool(config.discovery_encrypt)
                        : false
                    : null,
                publish_ifac: discoveryEnabled
                    ? config.publish_ifac !== undefined
                        ? this.parseBool(config.publish_ifac)
                        : false
                    : null,
                latitude: discoveryEnabled ? this.numOrNull(config.latitude) : null,
                longitude: discoveryEnabled ? this.numOrNull(config.longitude) : null,
                height: discoveryEnabled ? this.numOrNull(config.height) : null,
                discovery_frequency: discoveryEnabled ? this.numOrNull(config.discovery_frequency) : null,
                discovery_bandwidth: discoveryEnabled ? this.numOrNull(config.discovery_bandwidth) : null,
                discovery_modulation: discoveryEnabled ? this.numOrNull(config.discovery_modulation) : null,
                mode: config.mode || null,
                bitrate: this.numOrNull(config.bitrate),
                network_name: config.network_name || null,
                passphrase: config.passphrase || null,
                forward_ip: config.forward_ip || null,
                forward_port: this.numOrNull(config.forward_port),
                device: config.device || null,
                prefer_ipv6:
                    config.prefer_ipv6 !== undefined && config.prefer_ipv6 !== null && config.prefer_ipv6 !== ""
                        ? this.parseBool(config.prefer_ipv6)
                        : null,
                kiss_framing:
                    config.kiss_framing !== undefined && config.kiss_framing !== null && config.kiss_framing !== ""
                        ? this.parseBool(config.kiss_framing)
                        : null,
                i2p_tunneled:
                    config.i2p_tunneled !== undefined && config.i2p_tunneled !== null && config.i2p_tunneled !== ""
                        ? this.parseBool(config.i2p_tunneled)
                        : null,
                connect_timeout: this.numOrNull(config.connect_timeout),
                max_reconnect_tries: this.numOrNull(config.max_reconnect_tries),
                fixed_mtu: this.numOrNull(config.fixed_mtu),
                connectable:
                    config.type === "I2PInterface"
                        ? config.connectable !== undefined && config.connectable !== null && config.connectable !== ""
                            ? this.parseBool(config.connectable)
                            : true
                        : null,
                group_id: config.group_id || null,
                multicast_address_type: config.multicast_address_type || null,
                devices: config.devices || null,
                ignored_devices: config.ignored_devices || null,
                discovery_scope: config.discovery_scope || null,
                discovery_port: this.numOrNull(config.discovery_port),
                data_port: this.numOrNull(config.data_port),
                configured_bitrate: this.numOrNull(config.configured_bitrate),
                callsign: config.callsign || null,
                id_callsign: config.id_callsign || null,
                id_interval: this.numOrNull(config.id_interval),
                ssid: this.numOrNull(config.ssid),
                airtime_limit_long: this.numOrNull(config.airtime_limit_long),
                airtime_limit_short: this.numOrNull(config.airtime_limit_short),
                speed: this.numOrNull(config.speed),
                databits: this.numOrNull(config.databits),
                parity: config.parity || null,
                stopbits: this.numOrNull(config.stopbits),
                preamble: this.numOrNull(config.preamble),
                txtail: this.numOrNull(config.txtail),
                persistence: this.numOrNull(config.persistence),
                slottime: this.numOrNull(config.slottime),
                flow_control:
                    config.flow_control !== undefined && config.flow_control !== null && config.flow_control !== ""
                        ? this.parseBool(config.flow_control)
                        : null,
            };
        },
        applyDiscoveredInterfacePrefill() {
            let prefill = null;
            try {
                if (typeof sessionStorage !== "undefined") {
                    const raw = sessionStorage.getItem("meshchatx.discoveredInterfacePrefill");
                    if (raw) {
                        prefill = JSON.parse(raw);
                        sessionStorage.removeItem("meshchatx.discoveredInterfacePrefill");
                    }
                }
            } catch (e) {
                console.log(e);
            }
            if (!prefill) return;

            if (prefill.config_entry) {
                this.rawConfigInput = prefill.config_entry;
                this.handleRawConfigInput();
                return;
            }

            const config = {
                name: prefill.name || "Discovered Interface",
                type: prefill.type || "BackboneInterface",
                target_host: prefill.target_host || null,
                target_port: prefill.target_port != null ? String(prefill.target_port) : null,
                transport_identity: prefill.transport_identity || null,
                network_name: prefill.network_name || null,
                passphrase: prefill.passphrase || null,
                frequency: prefill.frequency ?? null,
                bandwidth: prefill.bandwidth ?? null,
                spreadingfactor: prefill.spreadingfactor ?? null,
                codingrate: prefill.codingrate ?? null,
                latitude: prefill.latitude ?? null,
                longitude: prefill.longitude ?? null,
                height: prefill.height ?? null,
            };
            this.applyConfig(config);
            ToastUtils.success(this.$t("interfaces.discovered_prefill_applied"));
        },
        async quickAddInterfaceFromConfig(config) {
            if (!config || !config.type || !config.name || this.isSaving) {
                return;
            }
            this.isSaving = true;
            try {
                const response = await window.api.post(
                    `/api/v1/reticulum/interfaces/add`,
                    this.buildPayloadFromImportedConfig(config)
                );
                ToastUtils.success(response.data?.message || `Imported interface "${config.name}"`);
                GlobalState.hasPendingInterfaceChanges = true;
                GlobalState.modifiedInterfaceNames.add(config.name);
                this.rawConfigInput = "";
                this.detectedConfigs = [];
                this.$router.push({ name: "interfaces" });
            } catch (e) {
                const message = e.response?.data?.message ?? `Failed to import "${config.name}"`;
                ToastUtils.error(message);
                console.log(e);
            } finally {
                this.isSaving = false;
            }
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

                const isBackboneListener =
                    this.newInterfaceType === "BackboneInterface" && this.newInterfaceBackboneListenMode === true;

                const payload = {
                    allow_overwriting_interface: this.isEditingInterface,
                    name: this.newInterfaceName,
                    type: this.newInterfaceType,
                    target_host: isBackboneListener ? null : this.newInterfaceTargetHost,
                    target_port: isBackboneListener ? null : this.newInterfaceTargetPort,
                    transport_identity: isBackboneListener ? null : this.newInterfaceTransportIdentity,
                    peers: i2pPeers,
                    listen_ip: isBackboneListener
                        ? this.newInterfaceBackboneListenIp || null
                        : this.newInterfaceListenIp,
                    listen_port: isBackboneListener
                        ? this.newInterfaceBackboneListenPort || null
                        : this.newInterfaceListenPort,
                    forward_ip: this.newInterfaceForwardIp,
                    forward_port: this.newInterfaceForwardPort,
                    device: isBackboneListener
                        ? this.newInterfaceBackboneListenDevice || null
                        : this.newInterfaceNetworkDevice,
                    prefer_ipv6: this.newInterfacePreferIPV6 === true,
                    kiss_framing: this.newInterfaceKISSFramingEnabled === true,
                    i2p_tunneled: this.newInterfaceI2PTunnelingEnabled === true,
                    connect_timeout: this.numOrNull(this.newInterfaceConnectTimeout),
                    max_reconnect_tries: this.numOrNull(this.newInterfaceMaxReconnectTries),
                    fixed_mtu: this.numOrNull(this.newInterfaceFixedMTU),
                    connectable:
                        this.newInterfaceType === "I2PInterface" ? this.newInterfaceConnectable === true : null,
                    port: this.newInterfaceRNodeUseIP
                        ? `tcp://${this.newInterfaceRNodeIPHost}:${this.newInterfaceRNodeIPPort}`
                        : this.newInterfacePort,
                    frequency: freqHz,
                    bandwidth: this.newInterfaceBandwidth,
                    txpower: this.newInterfaceTxpower,
                    spreadingfactor: this.newInterfaceSpreadingFactor,
                    codingrate: this.newInterfaceCodingRate,
                    flow_control: this.newInterfaceFlowControl === true,
                    callsign: this.newInterfaceCallsign,
                    id_callsign: this.newInterfaceIDCallsign,
                    id_interval: this.numOrNull(this.newInterfaceIDInterval),
                    airtime_limit_long: this.numOrNull(this.newInterfaceAirtimeLimitLong),
                    airtime_limit_short: this.numOrNull(this.newInterfaceAirtimeLimitShort),
                    ssid: this.numOrNull(this.newInterfaceSSID),
                    speed: this.numOrNull(this.newInterfaceSpeed),
                    databits: this.numOrNull(this.newInterfaceDatabits),
                    parity: this.newInterfaceParity,
                    stopbits: this.numOrNull(this.newInterfaceStopbits),
                    preamble: this.numOrNull(this.newInterfacePreamble),
                    txtail: this.numOrNull(this.newInterfaceTXTail),
                    persistence: this.numOrNull(this.newInterfacePersistence),
                    slottime: this.numOrNull(this.newInterfaceSlotTime),
                    group_id: this.newInterfaceGroupID,
                    multicast_address_type: this.newInterfaceMulticastAddressType,
                    devices: this.newInterfaceDevices,
                    ignored_devices: this.newInterfaceIgnoredDevices,
                    discovery_scope: this.newInterfaceDiscoveryScope,
                    discovery_port: this.numOrNull(this.newInterfaceDiscoveryPort),
                    data_port: this.numOrNull(this.newInterfaceDataPort),
                    configured_bitrate: this.numOrNull(this.newInterfaceConfiguredBitrate),
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
                    mode: this.sharedInterfaceSettings.mode || null,
                    bitrate: this.sharedInterfaceSettings.bitrate,
                    network_name: this.sharedInterfaceSettings.network_name,
                    passphrase: this.sharedInterfaceSettings.passphrase,
                };

                const response = await window.api.post(`/api/v1/reticulum/interfaces/add`, payload);

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
