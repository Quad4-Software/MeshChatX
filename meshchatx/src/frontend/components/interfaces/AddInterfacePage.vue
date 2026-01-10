<template>
    <div
        class="flex flex-col flex-1 overflow-hidden min-w-0 bg-gradient-to-br from-slate-50 via-slate-100 to-white dark:from-zinc-950 dark:via-zinc-900 dark:to-zinc-900"
    >
        <div class="overflow-y-auto p-3 md:p-6 space-y-4 max-w-5xl mx-auto w-full">
            <!-- community interfaces -->
            <div
                v-if="!isEditingInterface && config != null && config.show_suggested_community_interfaces"
                class="bg-white/95 dark:bg-zinc-900/80 backdrop-blur border border-gray-200 dark:border-zinc-800 rounded-3xl shadow-lg divide-y divide-gray-200 dark:divide-zinc-800"
            >
                <div class="flex p-3">
                    <div class="my-auto mr-auto">
                        <div class="text-xs uppercase tracking-wide text-gray-500 dark:text-gray-400">Quick start</div>
                        <div class="font-semibold text-lg text-gray-900 dark:text-white">Community Interfaces</div>
                        <div class="text-sm text-gray-600 dark:text-gray-200">
                            One-click helpers for public TCP relays. Spin up your own when possible to ensure
                            availability.
                        </div>
                    </div>
                    <div class="my-auto ml-2">
                        <button
                            type="button"
                            class="text-gray-700 bg-white border border-gray-200 hover:border-red-300 p-2 rounded-full shadow-sm dark:bg-zinc-800 dark:text-white dark:border-zinc-700 dark:hover:border-red-400"
                            @click="updateConfig({ show_suggested_community_interfaces: false })"
                        >
                            <svg
                                xmlns="http://www.w3.org/2000/svg"
                                viewBox="0 0 20 20"
                                fill="currentColor"
                                class="w-5 h-5"
                            >
                                <path
                                    d="M6.28 5.22a.75.75 0 0 0-1.06 1.06L8.94 10l-3.72 3.72a.75.75 0 1 0 1.06 1.06L10 11.06l3.72 3.72a.75.75 0 1 0 1.06-1.06L11.06 10l3.72-3.72a.75.75 0 0 0-1.06-1.06L10 8.94 6.28 5.22Z"
                                />
                            </svg>
                        </button>
                    </div>
                </div>
                <div class="divide-y divide-gray-200 dark:text-white">
                    <div
                        v-for="communityIface in communityInterfaces"
                        :key="communityIface.name"
                        class="flex px-3 py-2 items-center"
                    >
                        <div class="my-auto mr-auto">
                            <div class="font-semibold text-gray-900 dark:text-gray-100">{{ communityIface.name }}</div>
                            <div class="text-xs text-gray-600 dark:text-gray-300">
                                {{ communityIface.target_host }}:{{ communityIface.target_port }}
                                <span v-if="communityIface.online" class="ml-1 text-green-500 font-bold">Online</span>
                                <span v-else class="ml-1 text-red-500">Offline</span>
                            </div>
                            <div
                                v-if="communityIface.description"
                                class="text-xs text-gray-500 dark:text-gray-400 italic"
                            >
                                {{ communityIface.description }}
                            </div>
                        </div>
                        <div class="ml-2 my-auto">
                            <button
                                type="button"
                                class="inline-flex items-center gap-x-2 rounded-full bg-blue-600/90 px-3 py-1.5 text-xs font-semibold text-white shadow hover:bg-blue-500 focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-blue-500"
                                @click="
                                    newInterfaceName = communityIface.name;
                                    newInterfaceType = communityIface.type;
                                    newInterfaceTargetHost = communityIface.target_host;
                                    newInterfaceTargetPort = communityIface.target_port;
                                "
                            >
                                <span>Use Interface</span>
                            </button>
                        </div>
                    </div>
                </div>
            </div>

            <!-- add interface form -->
            <div
                class="bg-white/95 dark:bg-zinc-900/85 backdrop-blur border border-gray-200 dark:border-zinc-800 rounded-3xl shadow-xl"
            >
                <div class="flex flex-wrap gap-3 items-center p-3 border-b border-gray-200 dark:border-zinc-800">
                    <div>
                        <div class="text-xs uppercase tracking-wide text-gray-500 dark:text-gray-400">
                            {{ isEditingInterface ? "Update" : "Create" }}
                        </div>
                        <div class="text-xl font-semibold text-gray-900 dark:text-white">
                            {{ isEditingInterface ? "Edit Interface" : "Add Interface" }}
                        </div>
                        <div class="text-sm text-gray-600 dark:text-gray-300">
                            Name your connection and select its transport type.
                        </div>
                    </div>
                    <div class="flex-1"></div>
                    <div class="flex gap-2">
                        <button type="button" class="secondary-chip text-xs" @click="loadComports">Reload Ports</button>
                        <RouterLink :to="{ name: 'interfaces' }" class="secondary-chip text-xs"> View All </RouterLink>
                    </div>
                </div>
                <div class="p-3 md:p-5 space-y-4">
                    <!-- iGeneric interface settings -->
                    <!-- interface name -->
                    <div>
                        <FormLabel class="glass-label">Name</FormLabel>
                        <input
                            v-model="newInterfaceName"
                            type="text"
                            :disabled="isEditingInterface"
                            placeholder="New Interface Name"
                            class="input-field"
                            :class="[isEditingInterface ? 'cursor-not-allowed bg-gray-200 dark:bg-zinc-800' : '']"
                        />
                        <FormSubLabel class="text-xs">Interface names must be unique.</FormSubLabel>
                    </div>

                    <!-- interface type -->
                    <div>
                        <FormLabel class="glass-label">Type</FormLabel>
                        <select v-model="newInterfaceType" class="input-field">
                            <option disabled selected>Pick a category…</option>
                            <optgroup label="Automatic">
                                <option value="AutoInterface">Auto Interface</option>
                            </optgroup>
                            <optgroup label="RNodes">
                                <option value="RNodeInterface">RNode Interface</option>
                                <option value="RNodeIPInterface">RNode IP Interface</option>
                                <option value="RNodeMultiInterface">RNode Multi Interface</option>
                            </optgroup>
                            <optgroup label="IP Networks">
                                <option value="TCPClientInterface">TCP Client Interface</option>
                                <option value="TCPServerInterface">TCP Server Interface</option>
                                <option value="UDPInterface">UDP Interface</option>
                                <option value="I2PInterface">I2P Interface</option>
                            </optgroup>
                            <optgroup label="Hardware">
                                <option value="SerialInterface">Serial Interface</option>
                                <option value="KISSInterface">KISS Interface</option>
                                <option value="AX25KISSInterface">AX.25 KISS Interface</option>
                            </optgroup>
                            <optgroup label="Pipelines">
                                <option value="PipeInterface">Pipe Interface</option>
                            </optgroup>
                        </select>
                        <FormSubLabel>
                            Need help?
                            <a class="text-blue-500 underline" href="/reticulum-docs/interfaces.html" target="_blank"
                                >Reticulum Docs: Configuring Interfaces</a
                            >
                        </FormSubLabel>
                    </div>

                    <!-- TCPClientInterface -->
                    <!-- interface target host -->
                    <div v-if="newInterfaceType === 'TCPClientInterface'" class="mb-2">
                        <FormLabel class="mb-1">Target Host</FormLabel>
                        <input
                            v-model="newInterfaceTargetHost"
                            type="text"
                            placeholder="e.g: example.com"
                            class="input-field"
                        />
                    </div>

                    <!-- interface target port -->
                    <div v-if="newInterfaceType === 'TCPClientInterface'" class="mb-2">
                        <FormLabel class="mb-1">Target Port</FormLabel>
                        <input
                            v-model="newInterfaceTargetPort"
                            type="text"
                            placeholder="e.g: 1234"
                            class="input-field"
                        />
                    </div>

                    <!-- TCPServerInterface -->
                    <!-- interface listen ip -->
                    <div
                        v-if="newInterfaceType === 'TCPServerInterface' || newInterfaceType === 'UDPInterface'"
                        class="mb-2"
                    >
                        <FormLabel class="mb-1">Listen IP</FormLabel>
                        <input
                            v-model="newInterfaceListenIp"
                            type="text"
                            placeholder="e.g: 0.0.0.0"
                            class="bg-gray-50 border border-gray-300 text-gray-900 text-sm rounded-lg focus:ring-blue-500 focus:border-blue-500 block w-full p-2.5 dark:bg-zinc-900 dark:border-zinc-600 dark:text-white dark:focus:ring-blue-600 dark:focus:border-blue-600"
                        />
                    </div>

                    <!-- interface listen port -->
                    <div
                        v-if="newInterfaceType === 'TCPServerInterface' || newInterfaceType === 'UDPInterface'"
                        class="mb-2"
                    >
                        <FormLabel class="mb-1">Listen Port</FormLabel>
                        <input
                            v-model="newInterfaceListenPort"
                            type="text"
                            placeholder="e.g: 1234"
                            class="bg-gray-50 border border-gray-300 text-gray-900 text-sm rounded-lg focus:ring-blue-500 focus:border-blue-500 block w-full p-2.5 dark:bg-zinc-900 dark:border-zinc-600 dark:text-white dark:focus:ring-blue-600 dark:focus:border-blue-600"
                        />
                    </div>

                    <!-- UDPInterface -->
                    <!-- interface forward ip -->
                    <div v-if="newInterfaceType === 'UDPInterface'" class="mb-2">
                        <FormLabel class="mb-1">Forward IP</FormLabel>
                        <input
                            v-model="newInterfaceForwardIp"
                            type="text"
                            placeholder="e.g: 255.255.255.255"
                            class="bg-gray-50 border border-gray-300 text-gray-900 text-sm rounded-lg focus:ring-blue-500 focus:border-blue-500 block w-full p-2.5 dark:bg-zinc-900 dark:border-zinc-600 dark:text-white dark:focus:ring-blue-600 dark:focus:border-blue-600"
                        />
                    </div>

                    <!-- interface listen port -->
                    <div v-if="newInterfaceType === 'UDPInterface'" class="mb-2">
                        <FormLabel class="mb-1">Forward Port</FormLabel>
                        <input
                            v-model="newInterfaceForwardPort"
                            type="text"
                            placeholder="e.g: 1234"
                            class="bg-gray-50 border border-gray-300 text-gray-900 text-sm rounded-lg focus:ring-blue-500 focus:border-blue-500 block w-full p-2.5 dark:bg-zinc-900 dark:border-zinc-600 dark:text-white dark:focus:ring-blue-600 dark:focus:border-blue-600"
                        />
                    </div>

                    <!-- I2PInterface -->
                    <!-- peers -->
                    <div v-if="newInterfaceType === 'I2PInterface'">
                        <div class="mb-2 text-sm text-gray-500 dark:text-zinc-300">
                            ⓘ To use the I2P interface, you must have an I2P router running on your system. When the I2P
                            Interface is added for the first time Reticulum will generate a new I2P address for the
                            interface and begin listening for inbound traffic.
                        </div>
                        <FormLabel class="mb-1">Peers</FormLabel>
                        <div class="space-y-2">
                            <div
                                v-for="(peer, index) in I2PSettings.newInterfacePeers"
                                :key="index"
                                class="flex items-center space-x-2"
                            >
                                <input
                                    v-model="I2PSettings.newInterfacePeers[index]"
                                    type="text"
                                    placeholder="Enter peer address (e.g: 5urvjicpzi7q3ybztsef4i5ow2aq4soktfj7zedz53s47r54jnqq.b32.i2p)"
                                    class="bg-gray-50 border border-gray-300 text-gray-900 text-sm rounded-lg focus:ring-blue-500 focus:border-blue-500 block w-full p-2.5 dark:bg-zinc-900 dark:border-zinc-600 dark:text-white dark:focus:ring-blue-600 dark:focus:border-blue-600"
                                />
                                <button
                                    type="button"
                                    class="bg-red-500 hover:bg-red-400 text-white text-sm p-2 rounded-lg"
                                    @click="removeI2PPeer(index)"
                                >
                                    Remove
                                </button>
                            </div>
                            <button
                                type="button"
                                class="bg-green-500 hover:bg-green-400 text-white text-sm px-4 py-2 rounded-lg"
                                @click="addI2PPeer('')"
                            >
                                Add Peer
                            </button>
                        </div>
                    </div>

                    <!-- RNode interface -->
                    <!-- interface port -->
                    <div v-if="['RNodeInterface', 'RNodeIPInterface'].includes(newInterfaceType)" class="mb-2">
                        <div v-if="newInterfaceType === 'RNodeInterface'" class="flex items-center mb-2">
                            <Toggle id="rnode-use-ip" v-model="newInterfaceRNodeUseIP" />
                            <FormLabel for="rnode-use-ip" class="ml-2">Connect over IP</FormLabel>
                        </div>

                        <div v-if="newInterfaceRNodeUseIP || newInterfaceType === 'RNodeIPInterface'" class="space-y-2">
                            <div>
                                <FormLabel class="mb-1">Host</FormLabel>
                                <input
                                    v-model="newInterfaceRNodeIPHost"
                                    type="text"
                                    placeholder="e.g: 10.0.0.1"
                                    class="input-field"
                                />
                            </div>
                            <div>
                                <FormLabel class="mb-1">Port</FormLabel>
                                <input
                                    v-model="newInterfaceRNodeIPPort"
                                    type="text"
                                    placeholder="e.g: 7633"
                                    class="input-field"
                                />
                            </div>
                        </div>
                        <div v-else>
                            <FormLabel class="mb-1">Port</FormLabel>
                            <select
                                v-model="newInterfacePort"
                                class="bg-gray-50 border border-gray-300 text-gray-900 text-sm rounded-lg focus:ring-blue-500 focus:border-blue-500 block w-full p-2.5 dark:bg-zinc-900 dark:border-zinc-600 dark:text-white dark:focus:ring-blue-600 dark:focus:border-blue-600"
                            >
                                <option v-for="comport of comports" :key="comport.device" :value="comport.device">
                                    {{ comport.device }} (Product: {{ comport.product ?? "?" }}, Serial:
                                    {{ comport.serial ?? "?" }})
                                </option>
                            </select>
                            <FormSubLabel>
                                <div class="text-blue-500 underline cursor-pointer" @click="loadComports">
                                    Reload Ports
                                </div>
                            </FormSubLabel>
                        </div>
                    </div>

                    <!-- interface Frequency -->
                    <div v-if="['RNodeInterface', 'RNodeIPInterface'].includes(newInterfaceType)" class="mb-2">
                        <FormLabel class="mb-1">
                            <span>Frequency</span><span v-if="formattedFrequency">: {{ formattedFrequency }}</span>
                        </FormLabel>
                        <div class="flex items-center">
                            <div class="flex flex-col">
                                <input
                                    v-model.number="RNodeGHzValue"
                                    type="number"
                                    min="0"
                                    placeholder="GHz"
                                    class="bg-gray-50 border border-gray-300 text-gray-900 text-sm rounded-l-lg focus:ring-blue-500 focus:border-blue-500 w-full p-2.5 dark:bg-zinc-900 dark:border-zinc-600 dark:text-white dark:focus:ring-blue-600 dark:focus:border-blue-600"
                                />
                                <FormSubLabel class="text-center">GHz</FormSubLabel>
                            </div>
                            <div class="flex flex-col">
                                <input
                                    v-model.number="RNodeMHzValue"
                                    type="number"
                                    min="0"
                                    placeholder="MHz"
                                    class="bg-gray-50 border-y border-gray-300 text-gray-900 text-sm focus:ring-blue-500 focus:border-blue-500 w-full p-2.5 dark:bg-zinc-900 dark:border-zinc-600 dark:text-white dark:focus:ring-blue-600 dark:focus:border-blue-600"
                                />
                                <FormSubLabel class="text-center">MHz</FormSubLabel>
                            </div>
                            <div class="flex flex-col">
                                <input
                                    v-model.number="RNodekHzValue"
                                    type="number"
                                    min="0"
                                    placeholder="kHz"
                                    class="bg-gray-50 border border-gray-300 text-gray-900 text-sm rounded-r-lg focus:ring-blue-500 focus:border-blue-500 w-full p-2.5 dark:bg-zinc-900 dark:border-zinc-600 dark:text-white dark:focus:ring-blue-600 dark:focus:border-blue-600"
                                />
                                <FormSubLabel class="text-center">kHz</FormSubLabel>
                            </div>
                        </div>
                    </div>

                    <!-- interface bandwidth -->
                    <div v-if="['RNodeInterface', 'RNodeIPInterface'].includes(newInterfaceType)" class="mb-2">
                        <FormLabel class="mb-1">Bandwidth</FormLabel>
                        <select
                            v-model="newInterfaceBandwidth"
                            class="bg-gray-50 border border-gray-300 text-gray-900 text-sm rounded-lg focus:ring-blue-500 focus:border-blue-500 block w-full p-2.5 dark:bg-zinc-900 dark:border-zinc-600 dark:text-white dark:focus:ring-blue-600 dark:focus:border-blue-600"
                        >
                            <option
                                v-for="bandwidth in RNodeInterfaceDefaults.bandwidths"
                                :key="bandwidth"
                                :value="bandwidth"
                            >
                                {{ bandwidth / 1000 }} KHz
                            </option>
                        </select>
                    </div>

                    <!-- interface txpower -->
                    <div v-if="['RNodeInterface', 'RNodeIPInterface'].includes(newInterfaceType)" class="mb-2">
                        <FormLabel class="mb-1">Transmit Power (dBm)</FormLabel>
                        <input
                            v-model="newInterfaceTxpower"
                            type="number"
                            class="bg-gray-50 border border-gray-300 text-gray-900 text-sm rounded-lg focus:ring-blue-500 focus:border-blue-500 block w-full p-2.5 dark:bg-zinc-900 dark:border-zinc-600 dark:text-white"
                        />
                    </div>

                    <div
                        v-if="['RNodeInterface', 'RNodeIPInterface'].includes(newInterfaceType)"
                        class="mb-2 flex flex-wrap items-start gap-4"
                    >
                        <!-- interface spreading factor -->
                        <div class="flex-1">
                            <FormLabel class="mb-1">Spreading Factor</FormLabel>
                            <select
                                v-model="newInterfaceSpreadingFactor"
                                class="bg-gray-50 border border-gray-300 text-gray-900 text-sm rounded-lg focus:ring-blue-500 focus:border-blue-500 block w-full p-2.5 dark:bg-zinc-900 dark:border-zinc-600 dark:text-white dark:focus:ring-blue-600 dark:focus:border-blue-500"
                            >
                                <option
                                    v-for="spreadingfactor in RNodeInterfaceDefaults.spreadingfactors"
                                    :key="spreadingfactor"
                                    :value="spreadingfactor"
                                >
                                    {{ spreadingfactor }}
                                </option>
                            </select>
                        </div>

                        <!-- interface coding rate -->
                        <div class="flex-1">
                            <FormLabel class="mb-1">Coding Rate</FormLabel>
                            <select
                                v-model="newInterfaceCodingRate"
                                class="bg-gray-50 border border-gray-300 text-gray-900 text-sm rounded-lg focus:ring-blue-500 focus:border-blue-500 block w-full p-2.5 dark:bg-zinc-900 dark:border-zinc-600 dark:text-white dark:focus:ring-blue-600 dark:focus:border-blue-500"
                            >
                                <option
                                    v-for="codingrate in RNodeInterfaceDefaults.codingrates"
                                    :key="codingrate"
                                    :value="codingrate"
                                >
                                    {{ codingrate }}
                                </option>
                            </select>
                        </div>
                    </div>

                    <!-- RNodeMultiInterface -->
                    <div v-if="newInterfaceType === 'RNodeMultiInterface'" class="mb-2">
                        <p class="text-sm text-gray-600 dark:text-gray-400 mb-3">
                            ⓘ The RNode Multi Interface is used for custom devices with multiple LoRa transceivers such
                            as the openCom XL.
                        </p>
                        <FormLabel class="mb-1">Port</FormLabel>
                        <select
                            v-model="newInterfacePort"
                            class="bg-gray-50 border border-gray-300 text-gray-900 text-sm rounded-lg focus:ring-blue-500 focus:border-blue-500 block w-full p-2.5 dark:bg-zinc-900 dark:border-zinc-600 dark:text-white dark:focus:ring-blue-600 dark:focus:border-blue-600"
                        >
                            <option v-for="comport of comports" :key="comport.device" :value="comport.device">
                                {{ comport.device }} (Product: {{ comport.product ?? "?" }}, Serial:
                                {{ comport.serial ?? "?" }})
                            </option>
                        </select>
                        <FormSubLabel>
                            <div class="text-blue-500 underline cursor-pointer" @click="loadComports">Reload Ports</div>
                        </FormSubLabel>
                    </div>

                    <!-- RNodeMultiInterface: Sub Interfaces -->
                    <div v-if="newInterfaceType === 'RNodeMultiInterface'" class="mb-2">
                        <FormLabel class="mb-1">Sub-Interfaces</FormLabel>
                        <div class="space-y-3">
                            <div
                                v-for="(sub, idx) in RNodeMultiInterface.subInterfaces"
                                :key="idx"
                                class="p-2 space-y-2 border border-gray-200 rounded-lg dark:border-zinc-700"
                            >
                                <input
                                    v-model="sub.name"
                                    type="text"
                                    placeholder="Sub-Interface Name"
                                    class="w-full bg-gray-50 border border-gray-300 text-gray-900 text-sm rounded-lg p-2.5 dark:bg-zinc-900 dark:border-zinc-600 dark:text-white"
                                />

                                <div class="flex gap-2">
                                    <div class="flex-1">
                                        <FormLabel class="mb-1">Frequency (Hz)</FormLabel>
                                        <input
                                            v-model.number="sub.frequency"
                                            type="number"
                                            class="w-full bg-gray-50 border border-gray-300 text-gray-900 text-sm rounded-lg p-2.5 dark:bg-zinc-900 dark:border-zinc-600 dark:text-white"
                                        />
                                    </div>
                                    <div class="flex-1">
                                        <FormLabel class="mb-1">Bandwidth</FormLabel>
                                        <select
                                            v-model="sub.bandwidth"
                                            class="bg-gray-50 border border-gray-300 text-gray-900 text-sm rounded-lg focus:ring-blue-500 focus:border-blue-500 block w-full p-2.5 dark:bg-zinc-900 dark:border-zinc-600 dark:text-white dark:focus:ring-blue-600 dark:focus:border-blue-600"
                                        >
                                            <option
                                                v-for="bandwidth in RNodeInterfaceDefaults.bandwidths"
                                                :key="bandwidth"
                                                :value="bandwidth"
                                            >
                                                {{ bandwidth / 1000 }} KHz
                                            </option>
                                        </select>
                                    </div>
                                </div>

                                <div class="flex gap-2">
                                    <div class="flex-1">
                                        <FormLabel class="mb-1">Spreading Factor</FormLabel>
                                        <select
                                            v-model.number="sub.spreadingfactor"
                                            class="w-full bg-gray-50 border border-gray-300 text-gray-900 text-sm rounded-lg p-2.5 dark:bg-zinc-900 dark:border-zinc-600 dark:text-white"
                                        >
                                            <option
                                                v-for="sf in RNodeInterfaceDefaults.spreadingfactors"
                                                :key="sf"
                                                :value="sf"
                                            >
                                                {{ sf }}
                                            </option>
                                        </select>
                                    </div>
                                    <div class="flex-1">
                                        <FormLabel class="mb-1">Coding Rate</FormLabel>
                                        <select
                                            v-model.number="sub.codingrate"
                                            class="w-full bg-gray-50 border border-gray-300 text-gray-900 text-sm rounded-lg p-2.5 dark:bg-zinc-900 dark:border-zinc-600 dark:text-white"
                                        >
                                            <option
                                                v-for="cr in RNodeInterfaceDefaults.codingrates"
                                                :key="cr"
                                                :value="cr"
                                            >
                                                {{ cr }}
                                            </option>
                                        </select>
                                    </div>
                                </div>

                                <div class="flex gap-2 items-center">
                                    <div class="flex-1">
                                        <FormLabel class="mb-1">TX Power (dBm)</FormLabel>
                                        <input
                                            v-model.number="sub.txpower"
                                            type="number"
                                            class="w-full bg-gray-50 border border-gray-300 text-gray-900 text-sm rounded-lg p-2.5 dark:bg-zinc-900 dark:border-zinc-600 dark:text-white"
                                        />
                                    </div>
                                    <div class="flex-1">
                                        <FormLabel class="mb-1">Virtual Port</FormLabel>
                                        <input
                                            v-model.number="sub.vport"
                                            type="number"
                                            class="w-full bg-gray-50 border border-gray-300 text-gray-900 text-sm rounded-lg p-2.5 dark:bg-zinc-900 dark:border-zinc-600 dark:text-white"
                                        />
                                    </div>
                                </div>

                                <button
                                    type="button"
                                    class="bg-red-500 hover:bg-red-400 text-white text-sm p-2 rounded-lg"
                                    @click="removeSubInterface(idx)"
                                >
                                    Remove Sub-Interface
                                </button>
                            </div>
                            <button
                                type="button"
                                class="bg-green-500 hover:bg-green-400 text-white text-sm px-4 py-2 rounded-lg"
                                @click="addSubInterface"
                            >
                                Add Sub-Interface
                            </button>
                        </div>
                    </div>

                    <!-- Serial, KISS, and AX25Kiss -->
                    <div
                        v-if="['SerialInterface', 'KISSInterface', 'AX25KISSInterface'].includes(newInterfaceType)"
                        class="mb-4"
                    >
                        <div class="mb-2">
                            <FormLabel class="mb-1">Port</FormLabel>
                            <select
                                v-model="newInterfacePort"
                                class="bg-gray-50 border border-gray-300 text-gray-900 text-sm rounded-lg focus:ring-blue-500 focus:border-blue-500 block w-full p-2.5 dark:bg-zinc-900 dark:border-zinc-600 dark:text-white dark:focus:ring-blue-600 dark:focus:border-blue-600"
                            >
                                <option v-for="comport of comports" :key="comport.device" :value="comport.device">
                                    {{ comport.device }} (Product: {{ comport.product ?? "?" }}, Serial:
                                    {{ comport.serial ?? "?" }})
                                </option>
                            </select>
                            <FormSubLabel>
                                <div class="text-blue-500 underline cursor-pointer" @click="loadComports">
                                    Reload Ports
                                </div>
                            </FormSubLabel>
                        </div>

                        <div class="mb-2">
                            <FormLabel class="mb-1">Serial connection baud rate (bps)</FormLabel>
                            <input
                                v-model="newInterfaceSpeed"
                                placeholder="9600"
                                type="number"
                                class="bg-gray-50 border border-gray-300 text-gray-900 text-sm rounded-lg focus:ring-blue-500 focus:border-blue-500 block w-full p-2.5 dark:bg-zinc-900 dark:border-zinc-600 dark:text-white"
                            />
                        </div>

                        <div class="mb-2">
                            <FormLabel class="mb-1">Databits</FormLabel>
                            <input
                                v-model="newInterfaceDatabits"
                                type="number"
                                placeholder="8"
                                class="bg-gray-50 border border-gray-300 text-gray-900 text-sm rounded-lg focus:ring-blue-500 focus:border-blue-500 block w-full p-2.5 dark:bg-zinc-900 dark:border-zinc-600 dark:text-white"
                            />
                        </div>

                        <div class="mb-2">
                            <FormLabel class="mb-1">Parity</FormLabel>
                            <select
                                v-model="newInterfaceParity"
                                class="bg-gray-50 border border-gray-300 text-gray-900 text-sm rounded-lg focus:ring-blue-500 focus:border-blue-500 block w-full p-2.5 dark:bg-zinc-900 dark:border-zinc-600 dark:text-white dark:focus:ring-blue-600 dark:focus:border-blue-600"
                            >
                                <option :value="undefined">None</option>
                                <option value="even">Even</option>
                                <option value="odd">Odd</option>
                            </select>
                        </div>

                        <div>
                            <FormLabel class="mb-1">Stopbits</FormLabel>
                            <input
                                v-model="newInterfaceStopbits"
                                type="number"
                                placeholder="1"
                                class="bg-gray-50 border border-gray-300 text-gray-900 text-sm rounded-lg focus:ring-blue-500 focus:border-blue-500 block w-full p-2.5 dark:bg-zinc-900 dark:border-zinc-600 dark:text-white"
                            />
                        </div>
                    </div>

                    <!-- KISS and AX.25 KISS -->
                    <div v-if="['KISSInterface', 'AX25KISSInterface'].includes(newInterfaceType)" class="mb-4">
                        <div class="flex items-center mb-2">
                            <Toggle
                                id="use-ax25"
                                :model-value="newInterfaceType === 'AX25KISSInterface'"
                                @update:model-value="useKISSAX25"
                            />
                            <FormLabel for="use-ax25" class="ml-2">Enable AX.25 Framing</FormLabel>
                        </div>

                        <div class="grid grid-cols-2 gap-4">
                            <div>
                                <FormLabel class="mb-1">Preamble (milliseconds)</FormLabel>
                                <input
                                    v-model="newInterfacePreamble"
                                    type="number"
                                    placeholder="150"
                                    class="bg-gray-50 border border-gray-300 text-gray-900 text-sm rounded-lg focus:ring-blue-500 focus:border-blue-500 block w-full p-2.5 dark:bg-zinc-900 dark:border-zinc-600 dark:text-white"
                                />
                            </div>
                            <div>
                                <FormLabel class="mb-1">TX Tail (milliseconds)</FormLabel>
                                <input
                                    v-model="newInterfaceTXTail"
                                    type="number"
                                    placeholder="10"
                                    class="bg-gray-50 border border-gray-300 text-gray-900 text-sm rounded-lg focus:ring-blue-500 focus:border-blue-500 block w-full p-2.5 dark:bg-zinc-900 dark:border-zinc-600 dark:text-white"
                                />
                            </div>
                            <div>
                                <FormLabel class="mb-1">CDMA Persistence (milliseconds)</FormLabel>
                                <input
                                    v-model="newInterfacePersistence"
                                    type="number"
                                    placeholder="200"
                                    class="bg-gray-50 border border-gray-300 text-gray-900 text-sm rounded-lg focus:ring-blue-500 focus:border-blue-500 block w-full p-2.5 dark:bg-zinc-900 dark:border-zinc-600 dark:text-white"
                                />
                            </div>
                            <div>
                                <FormLabel class="mb-1">CDMA Slot Time (milliseconds)</FormLabel>
                                <input
                                    v-model="newInterfaceSlotTime"
                                    type="number"
                                    placeholder="20"
                                    class="bg-gray-50 border border-gray-300 text-gray-900 text-sm rounded-lg focus:ring-blue-500 focus:border-blue-500 block w-full p-2.5 dark:bg-zinc-900 dark:border-zinc-600 dark:text-white"
                                />
                            </div>
                        </div>

                        <div class="flex items-center space-x-4 mt-4">
                            <div class="flex-1">
                                <FormLabel class="mb-1">SSID</FormLabel>
                                <input
                                    v-model="newInterfaceSSID"
                                    type="text"
                                    value="0"
                                    placeholder="Enter SSID"
                                    class="bg-gray-50 border border-gray-300 text-gray-900 text-sm rounded-lg focus:ring-blue-500 focus:border-blue-500 block w-full p-2.5 dark:bg-zinc-900 dark:border-zinc-600 dark:text-white"
                                />
                            </div>
                            <div class="flex-1">
                                <FormLabel class="mb-1">Callsign</FormLabel>
                                <input
                                    v-model="newInterfaceCallsign"
                                    type="text"
                                    placeholder="Enter callsign"
                                    class="bg-gray-50 border border-gray-300 text-gray-900 text-sm rounded-lg focus:ring-blue-500 focus:border-blue-500 block w-full p-2.5 dark:bg-zinc-900 dark:border-zinc-600 dark:text-white"
                                />
                            </div>
                            <div class="flex-1">
                                <FormLabel class="mb-1">Callsign ID Interval</FormLabel>
                                <input
                                    v-model="newInterfaceIDInterval"
                                    type="number"
                                    placeholder="Enter interval (seconds)"
                                    class="bg-gray-50 border border-gray-300 text-gray-900 text-sm rounded-lg focus:ring-blue-500 focus:border-blue-500 block w-full p-2.5 dark:bg-zinc-900 dark:border-zinc-600 dark:text-white"
                                />
                            </div>
                        </div>
                    </div>

                    <!-- Pipe Interface -->
                    <div v-if="newInterfaceType === 'PipeInterface'" class="mb-2">
                        <div class="text-sm text-gray-500 dark:text-zinc-300 mb-3">
                            ⓘ Using this interface, Reticulum can use any program as an interface via stdin and stdout.
                            This can be usedto easily create virtual interfaces, or to interface with custom hardware or
                            other systems.
                        </div>

                        <div class="mb-2">
                            <FormLabel class="mb-1">Command</FormLabel>
                            <input
                                v-model="newInterfaceCommand"
                                type="text"
                                placeholder="e.g: netcat -l 5757"
                                class="bg-gray-50 border border-gray-300 text-gray-900 text-sm rounded-lg focus:ring-blue-500 focus:border-blue-500 block w-full p-2.5 dark:bg-zinc-900 dark:border-zinc-600 dark:text-white dark:focus:ring-blue-600 dark:focus:border-blue-600"
                            />
                        </div>

                        <div>
                            <FormLabel class="mb-1">Respawn Delay (seconds)</FormLabel>
                            <input
                                v-model="newInterfaceRespawnDelay"
                                type="number"
                                placeholder="5"
                                class="bg-gray-50 border border-gray-300 text-gray-900 text-sm rounded-lg focus:ring-blue-500 focus:border-blue-500 block w-full p-2.5 dark:bg-zinc-900 dark:border-zinc-600 dark:text-white dark:focus:ring-blue-600 dark:focus:border-blue-600"
                            />
                        </div>
                    </div>
                </div>
            </div>

            <!-- RNodeInterface bitrate & link budget -->
            <ExpandingSection v-if="['RNodeInterface', 'RNodeIPInterface'].includes(newInterfaceType)">
                <template #title>Calculated RNode Bitrate & Link Budget</template>
                <template #content>
                    <div class="p-2 space-y-3">
                        <div>
                            <FormLabel class="mb-1">Antenna Gain (dBi)</FormLabel>
                            <input
                                v-model.number="RNodeInterfaceLoRaParameters.antennaGain"
                                type="number"
                                placeholder="Enter gain"
                                class="bg-gray-50 border border-gray-300 text-gray-900 text-sm rounded-lg focus:ring-blue-500 focus:border-blue-500 block w-full p-2.5 dark:bg-zinc-900 dark:border-zinc-600 dark:text-white"
                            />
                            <p class="text-xs text-gray-600 dark:text-gray-400 mt-1">
                                ⓘ A stub or PCB antenna might have around 1 dBi of gain, where a directional Yagi might
                                have 5 dBi of gain.
                            </p>
                        </div>

                        <div>
                            <FormLabel class="mb-1">On-Air Calculations</FormLabel>
                            <div class="grid grid-cols-1 md:grid-cols-3 gap-2 text-center">
                                <div class="bg-gray-100 p-3 rounded-lg border dark:bg-zinc-800 dark:border-zinc-600">
                                    <div class="text-sm font-medium text-gray-700 dark:text-gray-300">Sensitivity</div>
                                    <div class="text-xl font-bold text-gray-900 dark:text-white">
                                        {{ RNodeInterfaceLoRaParameters.sensitivity ?? "???" }}
                                    </div>
                                </div>
                                <div class="bg-gray-100 p-3 rounded-lg border dark:bg-zinc-800 dark:border-zinc-600">
                                    <div class="text-sm font-medium text-gray-700 dark:text-gray-300">Data Rate</div>
                                    <div class="text-xl font-bold text-gray-900 dark:text-white">
                                        {{ RNodeInterfaceLoRaParameters.dataRate ?? "???" }}
                                    </div>
                                </div>
                                <div class="bg-gray-100 p-3 rounded-lg border dark:bg-zinc-800 dark:border-zinc-600">
                                    <div class="text-sm font-medium text-gray-700 dark:text-gray-300">Link Budget</div>
                                    <div class="text-xl font-bold text-gray-900 dark:text-white">
                                        {{ RNodeInterfaceLoRaParameters.linkBudget ?? "???" }}
                                    </div>
                                </div>
                            </div>
                        </div>
                    </div>
                </template>
            </ExpandingSection>

            <!-- optional AutoInterface settings -->
            <ExpandingSection v-if="newInterfaceType === 'AutoInterface'">
                <template #title>Optional AutoInterface Settings</template>
                <template #content>
                    <div class="p-2 space-y-3">
                        <div class="flex-1">
                            <FormLabel class="mb-1">Group ID</FormLabel>
                            <input
                                v-model="newInterfaceGroupID"
                                type="text"
                                placeholder="reticulum"
                                class="bg-gray-50 border border-gray-300 text-gray-900 text-sm rounded-lg focus:ring-blue-500 focus:border-blue-500 block w-full p-2.5 dark:bg-zinc-900 dark:border-zinc-600 dark:text-white"
                            />
                        </div>

                        <div class="flex-1">
                            <FormLabel class="mb-1">Multicast Address Type</FormLabel>
                            <select
                                v-model="newInterfaceMulticastAddressType"
                                class="bg-gray-50 border border-gray-300 text-gray-900 text-sm rounded-lg focus:ring-blue-500 focus:border-blue-500 block w-full p-2.5 dark:bg-zinc-900 dark:border-zinc-600 dark:text-white dark:focus:ring-blue-600 dark:focus:border-blue-600"
                            >
                                <option :value="undefined">(not set)</option>
                                <option value="permanent">Permanent</option>
                                <option value="temporary">Temporary</option>
                            </select>
                        </div>

                        <div class="flex items-center space-x-4 mt-4">
                            <div class="flex-1">
                                <FormLabel class="mb-1">Network devices</FormLabel>
                                <input
                                    v-model="newInterfaceDevices"
                                    type="text"
                                    placeholder="e.g: wlan0,eth1"
                                    class="bg-gray-50 border border-gray-300 text-gray-900 text-sm rounded-lg focus:ring-blue-500 focus:border-blue-500 block w-full p-2.5 dark:bg-zinc-900 dark:border-zinc-600 dark:text-white"
                                />
                            </div>
                            <div class="flex-1">
                                <FormLabel class="mb-1">Ignored Devices</FormLabel>
                                <input
                                    v-model="newInterfaceIgnoredDevices"
                                    type="text"
                                    placeholder="e.g: tun0,eth0"
                                    class="bg-gray-50 border border-gray-300 text-gray-900 text-sm rounded-lg focus:ring-blue-500 focus:border-blue-500 block w-full p-2.5 dark:bg-zinc-900 dark:border-zinc-600 dark:text-white"
                                />
                            </div>
                        </div>

                        <div class="flex items-center space-x-4 mt-4">
                            <div class="flex-1">
                                <FormLabel class="mb-1">Discovery Scope</FormLabel>
                                <select
                                    v-model="newInterfaceDiscoveryScope"
                                    class="bg-gray-50 border border-gray-300 text-gray-900 text-sm rounded-lg focus:ring-blue-500 focus:border-blue-500 block w-full p-2.5 dark:bg-zinc-900 dark:border-zinc-600 dark:text-white dark:focus:ring-blue-600 dark:focus:border-blue-600"
                                >
                                    <option :value="undefined">(not set)</option>
                                    <option value="global">Global</option>
                                    <option value="admin">Admin</option>
                                    <option value="organisation">Organisation</option>
                                    <option value="site">Site</option>
                                    <option value="link">Link</option>
                                </select>
                            </div>
                            <div class="flex-1">
                                <FormLabel class="mb-1">Discovery Port</FormLabel>
                                <input
                                    v-model="newInterfaceDiscoveryPort"
                                    type="number"
                                    placeholder="48555"
                                    class="bg-gray-50 border border-gray-300 text-gray-900 text-sm rounded-lg focus:ring-blue-500 focus:border-blue-500 block w-full p-2.5 dark:bg-zinc-900 dark:border-zinc-600 dark:text-white"
                                />
                            </div>
                            <div class="flex-1">
                                <FormLabel class="mb-1">Data Port</FormLabel>
                                <input
                                    v-model="newInterfaceDataPort"
                                    type="number"
                                    placeholder="49555"
                                    class="bg-gray-50 border border-gray-300 text-gray-900 text-sm rounded-lg focus:ring-blue-500 focus:border-blue-500 block w-full p-2.5 dark:bg-zinc-900 dark:border-zinc-600 dark:text-white"
                                />
                            </div>
                        </div>
                    </div>
                </template>
            </ExpandingSection>

            <!-- optional TCPClientInterface settings -->
            <ExpandingSection v-if="newInterfaceType === 'TCPClientInterface'">
                <template #title>Optional TCPClientInterface Settings</template>
                <template #content>
                    <div class="p-2 space-y-3">
                        <div class="flex">
                            <div class="flex flex-col mr-auto">
                                <FormLabel for="kiss-framing">Enable KISS Framing</FormLabel>
                                <span class="text-sm text-gray-500 dark:text-zinc-300"
                                    >Enable this when connecting to software that uses KISS framing such as packet radio
                                    sound modems. For KISS connections through serial hardware select "KISS Interface"
                                    as the interface type.</span
                                >
                            </div>
                            <Toggle id="kiss-framing" v-model="newInterfaceKISSFramingEnabled" class="my-auto mx-2" />
                        </div>

                        <div class="flex">
                            <div class="flex flex-col mr-auto">
                                <FormLabel for="i2p-tunneled">Enable I2P tunneling</FormLabel>
                                <span class="text-sm text-gray-500 dark:text-zinc-300"
                                    >Enables tunnelling through an I2P Connection using the TCPClientInterface</span
                                >
                            </div>
                            <Toggle id="i2p-tunneled" v-model="newInterfaceI2PTunnelingEnabled" class="my-auto mx-2" />
                        </div>
                    </div>
                </template>
            </ExpandingSection>

            <!-- optional TCPClientInterface settings -->
            <ExpandingSection v-if="newInterfaceType === 'TCPServerInterface'">
                <template #title>Optional TCPServerInterface settings</template>
                <template #content>
                    <div class="p-2 space-y-3">
                        <div>
                            <FormLabel>Network device</FormLabel>
                            <span class="text-sm text-gray-500 dark:text-zinc-300"
                                >Binds the interface to a specific network interface</span
                            >
                            <input
                                v-model="newInterfaceNetworkDevice"
                                type="text"
                                placeholder="e.g: eth0"
                                class="bg-gray-50 border border-gray-300 text-gray-900 text-sm rounded-lg focus:ring-blue-500 focus:border-blue-500 block w-full p-2.5 dark:bg-zinc-900 dark:border-zinc-600 dark:text-white dark:focus:ring-blue-600 dark:focus:border-blue-600"
                            />
                        </div>

                        <div class="flex items-start">
                            <div class="flex flex-col mr-auto">
                                <FormLabel for="prefer-ipv6">Prefer IPv6</FormLabel>
                                <span class="text-sm text-gray-500 dark:text-zinc-300"
                                    >Binds the TCP Server Interface to an IPv6 address</span
                                >
                            </div>
                            <Toggle id="prefer-ipv6" v-model="newInterfacePreferIPV6" class="my-auto mx-2" />
                        </div>
                    </div>
                </template>
            </ExpandingSection>

            <!-- optional UDPInterface settings -->
            <ExpandingSection v-if="newInterfaceType === 'UDPInterface'">
                <template #title>Optional UDPInterface settings</template>
                <template #content>
                    <div class="p-2 space-y-3">
                        <div>
                            <FormLabel>Network device</FormLabel>
                            <span class="text-sm text-gray-500 dark:text-zinc-300"
                                >Binds the interface to a specific network interface</span
                            >
                            <input
                                v-model="newInterfaceNetworkDevice"
                                type="text"
                                placeholder="e.g: eth0"
                                class="bg-gray-50 border border-gray-300 text-gray-900 text-sm rounded-lg focus:ring-blue-500 focus:border-blue-500 block w-full p-2.5 dark:bg-zinc-900 dark:border-zinc-600 dark:text-white dark:focus:ring-blue-600 dark:focus:border-blue-600"
                            />
                        </div>
                    </div>
                </template>
            </ExpandingSection>

            <!-- optional RNodeInterface settings -->
            <ExpandingSection v-if="['RNodeInterface', 'RNodeIPInterface'].includes(newInterfaceType)">
                <template #title>Optional RNodeInterface Settings</template>
                <template #content>
                    <div class="p-2 space-y-3">
                        <div class="flex items-center space-x-4">
                            <div class="flex-1">
                                <FormLabel class="mb-1">Callsign</FormLabel>
                                <input
                                    v-model="newInterfaceCallsign"
                                    type="text"
                                    placeholder="Enter callsign"
                                    class="bg-gray-50 border border-gray-300 text-gray-900 text-sm rounded-lg focus:ring-blue-500 focus:border-blue-500 block w-full p-2.5 dark:bg-zinc-900 dark:border-zinc-600 dark:text-white"
                                />
                            </div>
                            <div class="flex-1">
                                <FormLabel class="mb-1">Callsign ID Interval</FormLabel>
                                <input
                                    v-model="newInterfaceIDInterval"
                                    type="number"
                                    placeholder="Enter interval (seconds)"
                                    class="bg-gray-50 border border-gray-300 text-gray-900 text-sm rounded-lg focus:ring-blue-500 focus:border-blue-500 block w-full p-2.5 dark:bg-zinc-900 dark:border-zinc-600 dark:text-white"
                                />
                            </div>
                        </div>

                        <div class="flex items-center space-x-4">
                            <div class="flex-1">
                                <FormLabel class="mb-1">Airtime Limit (Short)</FormLabel>
                                <input
                                    v-model="newInterfaceAirtimeLimitShort"
                                    type="number"
                                    placeholder="Enter short airtime limit (% of a rolling 15 seconds window)"
                                    class="bg-gray-50 border border-gray-300 text-gray-900 text-sm rounded-lg focus:ring-blue-500 focus:border-blue-500 block w-full p-2.5 dark:bg-zinc-900 dark:border-zinc-600 dark:text-white"
                                />
                            </div>
                            <div class="flex-1">
                                <FormLabel class="mb-1">Airtime Limit (Long)</FormLabel>
                                <input
                                    v-model="newInterfaceAirtimeLimitLong"
                                    type="number"
                                    placeholder="Enter long airtime limit (% of a rolling 60 minutes window)"
                                    class="bg-gray-50 border border-gray-300 text-gray-900 text-sm rounded-lg focus:ring-blue-500 focus:border-blue-500 block w-full p-2.5 dark:bg-zinc-900 dark:border-zinc-600 dark:text-white"
                                />
                            </div>
                        </div>
                    </div>
                </template>
            </ExpandingSection>

            <!-- optional interface settings -->
            <ExpandingSection>
                <template #title>Optional Interface Settings</template>
                <template #content>
                    <div class="p-2 space-y-3">
                        <div>
                            <FormLabel class="mb-1">Interface Mode</FormLabel>
                            <select
                                v-model="sharedInterfaceSettings.mode"
                                class="bg-gray-50 border border-gray-300 text-gray-900 text-sm rounded-lg focus:ring-blue-500 focus:border-blue-500 block w-full p-2.5 dark:bg-zinc-900 dark:border-zinc-600 dark:text-white"
                            >
                                <option :value="undefined">(not set)</option>
                                <option value="full">Full</option>
                                <option value="gateway">Gateway</option>
                                <option value="access_point">Access Point</option>
                                <option value="roaming">Roaming</option>
                                <option value="boundary">Boundary</option>
                            </select>
                            <FormSubLabel>
                                This setting requires Transport Mode to be enabled.
                                <a
                                    class="text-blue-500 underline"
                                    href="/reticulum-docs/interfaces.html#interface-modes"
                                    target="_blank"
                                    >Reticulum Docs: Interface Modes</a
                                >
                            </FormSubLabel>
                        </div>

                        <div>
                            <FormLabel class="mb-1">Inferred Interface Bitrate</FormLabel>
                            <input
                                v-model="sharedInterfaceSettings.bitrate"
                                type="number"
                                placeholder="Enter inferred bitrate"
                                class="bg-gray-50 border border-gray-300 text-gray-900 text-sm rounded-lg focus:ring-blue-500 focus:border-blue-500 block w-full p-2.5 dark:bg-zinc-900 dark:border-zinc-600 dark:text-white"
                            />
                        </div>
                    </div>
                </template>
            </ExpandingSection>

            <!-- ifac settings -->
            <ExpandingSection>
                <template #title>IFAC Settings</template>
                <template #content>
                    <div class="p-2">
                        <div class="text-sm text-gray-500 dark:text-zinc-300 mb-2">
                            ⓘ Interface Access Code settings are used for creating private networks and can be
                            configured on the interface level.
                        </div>
                        <div class="grid grid-cols-1 lg:grid-cols-3 gap-y-2 lg:gap-x-2">
                            <div>
                                <FormLabel class="mb-1">Network Name</FormLabel>
                                <input
                                    v-model="sharedInterfaceSettings.network_name"
                                    type="text"
                                    placeholder="Enter network name"
                                    class="bg-gray-50 border border-gray-300 text-gray-900 text-sm rounded-lg focus:ring-blue-500 focus:border-blue-500 block w-full p-2.5 dark:bg-zinc-900 dark:border-zinc-600 dark:text-white"
                                />
                            </div>
                            <div>
                                <FormLabel class="mb-1">Passphrase</FormLabel>
                                <input
                                    v-model="sharedInterfaceSettings.passphrase"
                                    type="text"
                                    placeholder="Enter passphrase"
                                    class="bg-gray-50 border border-gray-300 text-gray-900 text-sm rounded-lg focus:ring-blue-500 focus:border-blue-500 block w-full p-2.5 dark:bg-zinc-900 dark:border-zinc-600 dark:text-white"
                                />
                            </div>
                            <div>
                                <FormLabel class="mb-1">IFAC Size</FormLabel>
                                <input
                                    v-model="sharedInterfaceSettings.ifac_size"
                                    type="number"
                                    min="8"
                                    max="512"
                                    placeholder="Enter size (8-512)"
                                    class="bg-gray-50 border border-gray-300 text-gray-900 text-sm rounded-lg focus:ring-blue-500 focus:border-blue-500 block w-full p-2.5 dark:bg-zinc-900 dark:border-zinc-600 dark:text-white"
                                />
                            </div>
                        </div>
                    </div>
                </template>
            </ExpandingSection>

            <ExpandingSection>
                <template #title>Interface Discovery</template>
                <template #content>
                    <div class="p-2 space-y-3">
                        <div class="flex items-center">
                            <div class="flex flex-col mr-auto">
                                <FormLabel class="mb-1">Advertise this Interface</FormLabel>
                                <FormSubLabel>
                                    Broadcasts connection details so peers can find and connect to this interface.
                                </FormSubLabel>
                            </div>
                            <Toggle v-model="discovery.discoverable" class="my-auto mx-2" />
                        </div>

                        <div class="text-sm text-gray-500 dark:text-zinc-300">
                            LXMF must be installed to publish discovery announces. When enabled, Reticulum handles
                            signing, stamping, and periodic announces for this interface.
                        </div>

                        <div v-if="discovery.discoverable" class="space-y-3">
                            <div>
                                <FormLabel class="mb-1">Discovery Name</FormLabel>
                                <input
                                    v-model="discovery.discovery_name"
                                    type="text"
                                    placeholder="Human friendly name"
                                    class="input-field"
                                />
                            </div>
                            <div class="grid grid-cols-1 md:grid-cols-2 gap-3">
                                <div>
                                    <FormLabel class="mb-1">Reachable On</FormLabel>
                                    <input
                                        v-model="discovery.reachable_on"
                                        type="text"
                                        placeholder="Hostname, IP, or resolver script path"
                                        class="input-field"
                                    />
                                </div>
                                <div>
                                    <FormLabel class="mb-1">Announce Interval (minutes)</FormLabel>
                                    <input
                                        v-model.number="discovery.announce_interval"
                                        type="number"
                                        min="5"
                                        class="input-field"
                                    />
                                </div>
                            </div>
                            <div class="grid grid-cols-1 md:grid-cols-2 gap-3">
                                <div>
                                    <FormLabel class="mb-1">Stamp Value</FormLabel>
                                    <input
                                        v-model.number="discovery.discovery_stamp_value"
                                        type="number"
                                        min="1"
                                        class="input-field"
                                    />
                                </div>
                                <div class="flex items-center">
                                    <Toggle id="discovery-encrypt" v-model="discovery.discovery_encrypt" />
                                    <FormLabel for="discovery-encrypt" class="ml-2">Encrypt Announces</FormLabel>
                                </div>
                            </div>
                            <div class="flex items-center">
                                <Toggle id="publish-ifac" v-model="discovery.publish_ifac" />
                                <FormLabel for="publish-ifac" class="ml-2">Include IFAC Credentials</FormLabel>
                            </div>
                            <div class="grid grid-cols-1 md:grid-cols-3 gap-3">
                                <div>
                                    <FormLabel class="mb-1">Latitude</FormLabel>
                                    <input
                                        v-model.number="discovery.latitude"
                                        type="number"
                                        step="0.00001"
                                        class="input-field"
                                    />
                                </div>
                                <div>
                                    <FormLabel class="mb-1">Longitude</FormLabel>
                                    <input
                                        v-model.number="discovery.longitude"
                                        type="number"
                                        step="0.00001"
                                        class="input-field"
                                    />
                                </div>
                                <div>
                                    <FormLabel class="mb-1">Height (m)</FormLabel>
                                    <input v-model.number="discovery.height" type="number" class="input-field" />
                                </div>
                            </div>
                            <div class="grid grid-cols-1 md:grid-cols-3 gap-3">
                                <div>
                                    <FormLabel class="mb-1">Discovery Frequency (Hz)</FormLabel>
                                    <input
                                        v-model.number="discovery.discovery_frequency"
                                        type="number"
                                        class="input-field"
                                    />
                                </div>
                                <div>
                                    <FormLabel class="mb-1">Discovery Bandwidth (Hz)</FormLabel>
                                    <input
                                        v-model.number="discovery.discovery_bandwidth"
                                        type="number"
                                        class="input-field"
                                    />
                                </div>
                                <div>
                                    <FormLabel class="mb-1">Discovery Modulation</FormLabel>
                                    <input
                                        v-model="discovery.discovery_modulation"
                                        type="text"
                                        placeholder="e.g. LoRa"
                                        class="input-field"
                                    />
                                </div>
                            </div>
                            <div class="text-xs text-gray-500 dark:text-zinc-400">
                                If announce encryption is enabled, a valid network identity path is required in the
                                Reticulum configuration.
                            </div>
                        </div>
                    </div>
                </template>
            </ExpandingSection>

            <ExpandingSection>
                <template #title>Discover Interfaces (Peer)</template>
                <template #content>
                    <div class="p-2 space-y-3">
                        <div class="flex items-center">
                            <div class="flex flex-col mr-auto">
                                <FormLabel class="mb-1">Enable Discovery Listener</FormLabel>
                                <FormSubLabel>
                                    Listen for announced interfaces and optionally auto-connect to them.
                                </FormSubLabel>
                            </div>
                            <Toggle v-model="reticulumDiscovery.discover_interfaces" class="my-auto mx-2" />
                        </div>

                        <div class="grid grid-cols-1 md:grid-cols-2 gap-3">
                            <div>
                                <FormLabel class="mb-1">Allowed Sources (comma separated)</FormLabel>
                                <input
                                    v-model="reticulumDiscovery.interface_discovery_sources"
                                    type="text"
                                    placeholder="Identity hashes"
                                    class="input-field"
                                />
                            </div>
                            <div>
                                <FormLabel class="mb-1">Required Stamp Value</FormLabel>
                                <input
                                    v-model.number="reticulumDiscovery.required_discovery_value"
                                    type="number"
                                    min="0"
                                    class="input-field"
                                />
                            </div>
                            <div>
                                <FormLabel class="mb-1">Auto-connect Slots</FormLabel>
                                <input
                                    v-model.number="reticulumDiscovery.autoconnect_discovered_interfaces"
                                    type="number"
                                    min="0"
                                    class="input-field"
                                />
                                <FormSubLabel>Set to 0 to disable auto-connect.</FormSubLabel>
                            </div>
                            <div>
                                <FormLabel class="mb-1">Network Identity Path</FormLabel>
                                <input
                                    v-model="reticulumDiscovery.network_identity"
                                    type="text"
                                    placeholder="~/.reticulum/storage/identities/..."
                                    class="input-field"
                                />
                            </div>
                        </div>

                        <div class="flex justify-end">
                            <button
                                type="button"
                                class="primary-chip text-xs"
                                :disabled="savingDiscovery"
                                @click="saveReticulumDiscoveryConfig"
                            >
                                <MaterialDesignIcon
                                    :icon-name="savingDiscovery ? 'progress-clock' : 'content-save'"
                                    class="w-4 h-4"
                                    :class="{ 'animate-spin-reverse': savingDiscovery }"
                                />
                                <span class="ml-1">Save Discovery Preferences</span>
                            </button>
                        </div>
                    </div>
                </template>
            </ExpandingSection>

            <!-- add/save interface button -->
            <div class="p-2 bg-white rounded shadow divide-y divide-gray-200 dark:bg-zinc-900">
                <button
                    type="button"
                    class="bg-green-500 hover:bg-green-400 focus-visible:outline-green-500 my-auto inline-flex items-center gap-x-1 rounded-md p-2 text-sm font-semibold text-white shadow-sm focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 dark:text-white dark:focus:ring-blue-600 dark:focus:border-blue-600"
                    @click="addInterface"
                >
                    <span v-if="isEditingInterface">Save Interface</span>
                    <span v-else>Add Interface</span>
                </button>
            </div>
        </div>
    </div>
</template>

<script>
import Utils from "../../js/Utils";
import DialogUtils from "../../js/DialogUtils";
import ToastUtils from "../../js/ToastUtils";
import ExpandingSection from "./ExpandingSection.vue";
import FormLabel from "../forms/FormLabel.vue";
import FormSubLabel from "../forms/FormSubLabel.vue";
import Toggle from "../forms/Toggle.vue";
import GlobalState from "../../js/GlobalState";
import MaterialDesignIcon from "../MaterialDesignIcon.vue";

export default {
    name: "AddInterfacePage",
    components: {
        MaterialDesignIcon,
        FormSubLabel,
        FormLabel,
        ExpandingSection,
        Toggle,
    },
    data() {
        return {
            isEditingInterface: false,

            config: null,

            communityInterfaces: [],

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
                const response = await window.axios.get(`/api/v1/config`);
                this.config = response.data.config;
            } catch (e) {
                // do nothing if failed to load config
                console.log(e);
            }
        },
        async updateConfig(config) {
            try {
                const response = await window.axios.patch("/api/v1/config", config);
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
        async loadReticulumDiscoveryConfig() {
            try {
                const response = await window.axios.get(`/api/v1/reticulum/discovery`);
                const discovery = response.data?.discovery ?? {};
                this.reticulumDiscovery.discover_interfaces = this.parseBool(discovery.discover_interfaces);
                this.reticulumDiscovery.interface_discovery_sources = discovery.interface_discovery_sources ?? "";
                this.reticulumDiscovery.required_discovery_value =
                    discovery.required_discovery_value !== undefined &&
                    discovery.required_discovery_value !== null &&
                    discovery.required_discovery_value !== ""
                        ? Number(discovery.required_discovery_value)
                        : null;
                this.reticulumDiscovery.autoconnect_discovered_interfaces =
                    discovery.autoconnect_discovered_interfaces !== undefined &&
                    discovery.autoconnect_discovered_interfaces !== null &&
                    discovery.autoconnect_discovered_interfaces !== ""
                        ? Number(discovery.autoconnect_discovered_interfaces)
                        : 0;
                this.reticulumDiscovery.network_identity = discovery.network_identity ?? "";
            } catch (e) {
                // safe to ignore if discovery config cannot be loaded
                console.log(e);
            }
        },
        async saveReticulumDiscoveryConfig() {
            if (this.savingDiscovery) return;
            this.savingDiscovery = true;
            try {
                const payload = {
                    discover_interfaces: this.reticulumDiscovery.discover_interfaces,
                    interface_discovery_sources: this.reticulumDiscovery.interface_discovery_sources || null,
                    required_discovery_value:
                        this.reticulumDiscovery.required_discovery_value === null ||
                        this.reticulumDiscovery.required_discovery_value === ""
                            ? null
                            : Number(this.reticulumDiscovery.required_discovery_value),
                    autoconnect_discovered_interfaces:
                        this.reticulumDiscovery.autoconnect_discovered_interfaces === null ||
                        this.reticulumDiscovery.autoconnect_discovered_interfaces === ""
                            ? 0
                            : Number(this.reticulumDiscovery.autoconnect_discovered_interfaces),
                    network_identity: this.reticulumDiscovery.network_identity || null,
                };

                await window.axios.patch(`/api/v1/reticulum/discovery`, payload);
                ToastUtils.success(this.$t("interfaces.discovery_settings_saved"));
                await this.loadReticulumDiscoveryConfig();
            } catch (e) {
                ToastUtils.error(this.$t("interfaces.failed_save_discovery"));
                console.log(e);
            } finally {
                this.savingDiscovery = false;
            }
        },
        async loadComports() {
            try {
                const response = await window.axios.get(`/api/v1/comports`);
                this.comports = response.data.comports;
            } catch {
                // do nothing if failed to load interfaces
            }
        },
        async loadCommunityInterfaces() {
            try {
                const response = await window.axios.get(`/api/v1/community-interfaces`);
                this.communityInterfaces = response.data.interfaces;
            } catch {
                // do nothing if failed to load interfaces
            }
        },
        async loadInterfaceToEdit(interfaceName) {
            try {
                // fetch interfaces
                const response = await window.axios.get(`/api/v1/reticulum/interfaces`);
                const interfaces = response.data.interfaces;

                // find interface, else show error and redirect to interfaces
                const iface = interfaces[interfaceName];
                if (!iface) {
                    DialogUtils.alert(this.$t("interfaces.interface_not_found"));
                    this.$router.push({
                        name: "interfaces",
                    });
                    return;
                }

                // set form values
                this.newInterfaceName = interfaceName;
                this.newInterfaceType = iface.type;

                // AutoInterface additional settings
                this.newInterfaceGroupID = iface.group_id;
                this.newInterfaceMulticastAddressType = iface.multicast_address_type;
                this.newInterfaceDevices = iface.devices;
                this.newInterfaceIgnoredDevices = iface.ignored_devices;
                this.newInterfaceDiscoveryScope = iface.discovery_scope;
                this.newInterfaceDiscoveryPort = iface.discovery_port;
                this.newInterfaceDataPort = iface.data_port;

                // tcp client interface
                this.newInterfaceTargetHost = iface.target_host;
                this.newInterfaceTargetPort = iface.target_port;

                if (iface.kiss_framing) {
                    this.newInterfaceKISSFramingEnabled = true;
                }
                if (iface.i2p_tunneled) {
                    this.newInterfaceI2PTunnelingEnabled = true;
                }
                if (iface.prefer_ipv6) {
                    this.newInterfacePreferIPV6 = true;
                }

                // tcp server interface & udp interface
                this.newInterfaceNetworkDevice = iface.device;
                this.newInterfaceListenIp = iface.listen_ip;
                this.newInterfaceListenPort = iface.listen_port;

                // I2P Interface
                if (iface.peers) {
                    const peersToAdd = iface.peers.split(",");
                    for (const address of peersToAdd) {
                        this.addI2PPeer(address);
                    }
                }

                // udp interface
                this.newInterfaceForwardIp = iface.forward_ip;
                this.newInterfaceForwardPort = iface.forward_port;

                // Port (For RNode, Serial, and KISS)
                this.newInterfacePort = iface.port;
                if (iface.type === "RNodeInterface" && iface.port && iface.port.startsWith("tcp://")) {
                    this.newInterfaceType = "RNodeIPInterface";
                    this.newInterfaceRNodeUseIP = true;
                    const address = iface.port.replace("tcp://", "");
                    const parts = address.split(":");
                    this.newInterfaceRNodeIPHost = parts[0];
                    this.newInterfaceRNodeIPPort = parts[1] || "7633";
                }

                // RNode Interface
                this.newInterfaceFrequency = iface.frequency;
                this.RNodeGHzValue = Math.floor(iface.frequency / 1e9);
                this.RNodeMHzValue = Math.floor((iface.frequency % 1e9) / 1e6);
                this.RNodekHzValue = Math.floor((iface.frequency % 1e6) / 1e3);
                this.newInterfaceBandwidth = iface.bandwidth;
                this.newInterfaceTxpower = iface.txpower;
                this.newInterfaceSpreadingFactor = iface.spreadingfactor;
                this.newInterfaceCodingRate = iface.codingrate;

                // RNode Multi Interface
                this.RNodeMultiInterface.subInterfaces = iface.sub_interfaces;

                // Serial, KISS, and AX25KISS
                this.newInterfaceSpeed = iface.speed;
                this.newInterfaceDatabits = iface.databits;
                this.newInterfaceParity = iface.parity;
                this.newInterfaceStopbits = iface.stopbits;

                this.newInterfacePreamble = iface.preamble;
                this.newInterfaceTXTail = iface.txtail;
                this.newInterfacePersistence = iface.persistence;
                this.newInterfaceSlotTime = iface.slottime;

                this.newInterfaceCallsign = iface.callsign;
                this.newInterfaceIDInterval = iface.id_interval;
                this.newInterfaceSSID = iface.ssid;

                // Airtime limit
                this.newInterfaceAirtimeLimitLong = iface.airtime_limit_long;
                this.newInterfaceAirtimeLimitShort = iface.airtime_limit_short;

                // Pipe Interface
                this.newInterfaceCommand = iface.command;
                this.newInterfaceRespawnDelay = iface.respawn_delay;

                // Shared interface settings
                this.sharedInterfaceSettings.mode = iface.mode;
                this.sharedInterfaceSettings.bitrate = iface.bitrate;
                this.sharedInterfaceSettings.network_name = iface.network_name;
                this.sharedInterfaceSettings.passphrase = iface.passphrase;
                this.sharedInterfaceSettings.ifac_size = iface.ifac_size;

                // interface discovery
                this.discovery.discoverable = this.parseBool(iface.discoverable);
                this.discovery.discovery_name = iface.discovery_name ?? "";
                this.discovery.announce_interval = iface.announce_interval ?? this.discovery.announce_interval;
                this.discovery.reachable_on = iface.reachable_on ?? "";
                this.discovery.discovery_stamp_value =
                    iface.discovery_stamp_value ?? this.discovery.discovery_stamp_value;
                this.discovery.discovery_encrypt = this.parseBool(iface.discovery_encrypt);
                this.discovery.publish_ifac = this.parseBool(iface.publish_ifac);
                this.discovery.latitude = iface.latitude !== undefined ? Number(iface.latitude) : null;
                this.discovery.longitude = iface.longitude !== undefined ? Number(iface.longitude) : null;
                this.discovery.height = iface.height !== undefined ? Number(iface.height) : null;
                this.discovery.discovery_frequency = iface.discovery_frequency ?? null;
                this.discovery.discovery_bandwidth = iface.discovery_bandwidth ?? null;
                this.discovery.discovery_modulation = iface.discovery_modulation ?? null;
            } catch {
                // do nothing if failed to load interfaces
            }
        },
        async addInterface() {
            try {
                // process sub interfaces for RNodeMultiInterface
                let subInterfacesData = null;
                if (this.newInterfaceType === "RNodeMultiInterface") {
                    subInterfacesData = this.RNodeMultiInterface.subInterfaces.map((subInterface) => {
                        return {
                            name: subInterface.name,
                            frequency: subInterface.frequency,
                            bandwidth: subInterface.bandwidth,
                            txpower: subInterface.txpower,
                            spreadingfactor: subInterface.spreadingfactor,
                            codingrate: subInterface.codingrate,
                            vport: subInterface.vport,
                        };
                    });
                }

                const discoveryEnabled = this.discovery.discoverable === true;
                const isRadioInterface = ["RNodeInterface", "RNodeIPInterface"].includes(this.newInterfaceType);
                const fallbackDiscoveryFrequency =
                    this.discovery.discovery_frequency ??
                    (discoveryEnabled && isRadioInterface ? this.calculateFrequencyInHz() : null);
                const fallbackDiscoveryBandwidth =
                    this.discovery.discovery_bandwidth ??
                    (discoveryEnabled && isRadioInterface ? this.newInterfaceBandwidth : null);

                // add interface
                const response = await window.axios.post(`/api/v1/reticulum/interfaces/add`, {
                    allow_overwriting_interface: this.isEditingInterface,

                    // required values
                    name: this.newInterfaceName,
                    type: this.newInterfaceType,

                    // AutoInterface
                    group_id: this.newInterfaceGroupID,
                    multicast_address_type: this.newInterfaceMulticastAddressType,
                    devices: this.newInterfaceDevices,
                    ignored_devices: this.newInterfaceIgnoredDevices,
                    discovery_scope: this.newInterfaceDiscoveryScope,
                    discovery_port: this.newInterfaceDiscoveryPort,
                    data_port: this.newInterfaceDataPort,

                    // tcp client interface
                    target_host: this.newInterfaceTargetHost,
                    target_port: this.newInterfaceTargetPort,

                    // TCP Client & Server interface
                    kiss_framing: this.newInterfaceKISSFramingEnabled,
                    i2p_tunneled: this.newInterfaceI2PTunnelingEnabled,

                    // tcp server interface & udp interface
                    listen_ip: this.newInterfaceListenIp,
                    listen_port: this.newInterfaceListenPort,
                    device: this.newInterfaceNetworkDevice,
                    prefer_ipv6: this.newInterfacePreferIPV6,

                    // udp interface
                    forward_ip: this.newInterfaceForwardIp,
                    forward_port: this.newInterfaceForwardPort,

                    //  I2P Interface
                    peers: this.I2PSettings.newInterfacePeers.join(","),

                    // rnode interface
                    port:
                        this.newInterfaceRNodeUseIP || this.newInterfaceType === "RNodeIPInterface"
                            ? `tcp://${this.newInterfaceRNodeIPHost}:${this.newInterfaceRNodeIPPort}`
                            : this.newInterfacePort,
                    frequency: this.calculateFrequencyInHz(),
                    bandwidth: this.newInterfaceBandwidth,
                    txpower: this.newInterfaceTxpower,
                    spreadingfactor: this.newInterfaceSpreadingFactor,
                    codingrate: this.newInterfaceCodingRate,

                    // RNode Multi Interface
                    sub_interfaces: subInterfacesData,

                    // Seiral, KISS, and AX25KISS
                    speed: this.newInterfaceSpeed,
                    databits: this.newInterfaceDatabits,
                    parity: this.newInterfaceParity,
                    stopbits: this.newInterfaceStopbits,

                    // KISS and AX25KISS
                    preamble: this.newInterfacePreamble,
                    txtail: this.newInterfaceTXTail,
                    persistence: this.newInterfacePersistence,
                    slottime: this.newInterfaceSlotTime,

                    callsign: this.newInterfaceCallsign,
                    id_interval: this.newInterfaceIDInterval,
                    ssid: this.newInterfaceSSID,

                    // Pipe interface
                    command: this.newInterfaceCommand,
                    respawn_delay: this.newInterfaceRespawnDelay,

                    // Airtime limit
                    airtime_limit_long: this.newInterfaceAirtimeLimitLong,
                    airtime_limit_short: this.newInterfaceAirtimeLimitShort,

                    // discovery options
                    discoverable: discoveryEnabled ? "yes" : null,
                    discovery_name: discoveryEnabled ? this.discovery.discovery_name : null,
                    announce_interval:
                        discoveryEnabled && this.discovery.announce_interval !== null
                            ? Number(this.discovery.announce_interval)
                            : null,
                    reachable_on: discoveryEnabled ? this.discovery.reachable_on : null,
                    discovery_stamp_value:
                        discoveryEnabled && this.discovery.discovery_stamp_value !== null
                            ? Number(this.discovery.discovery_stamp_value)
                            : null,
                    discovery_encrypt: discoveryEnabled ? this.discovery.discovery_encrypt : null,
                    publish_ifac: discoveryEnabled ? this.discovery.publish_ifac : null,
                    latitude:
                        discoveryEnabled && this.discovery.latitude !== null ? Number(this.discovery.latitude) : null,
                    longitude:
                        discoveryEnabled && this.discovery.longitude !== null ? Number(this.discovery.longitude) : null,
                    height: discoveryEnabled && this.discovery.height !== null ? Number(this.discovery.height) : null,
                    discovery_frequency: discoveryEnabled ? fallbackDiscoveryFrequency : null,
                    discovery_bandwidth: discoveryEnabled ? fallbackDiscoveryBandwidth : null,
                    discovery_modulation:
                        discoveryEnabled && this.discovery.discovery_modulation
                            ? this.discovery.discovery_modulation
                            : null,

                    // settings that can be added to any interface type
                    mode: this.sharedInterfaceSettings.mode || "full",
                    bitrate: this.sharedInterfaceSettings.bitrate,
                    network_name: this.sharedInterfaceSettings.network_name,
                    passphrase: this.sharedInterfaceSettings.passphrase,
                    ifac_size: this.sharedInterfaceSettings.ifac_size,
                });

                // show success message
                if (response.data.message) {
                    DialogUtils.alert(response.data.message);
                }

                // track change
                GlobalState.hasPendingInterfaceChanges = true;
                GlobalState.modifiedInterfaceNames.add(this.newInterfaceName);

                // go to interfaces page
                this.$router.push({
                    name: "interfaces",
                });
            } catch (e) {
                const message = e.response?.data?.message ?? "failed to add interface";
                DialogUtils.alert(message);
                console.log(e);
            }
        },
        formatFrequency(hz) {
            return Utils.formatFrequency(hz);
        },
        calculateFrequencyInHz() {
            const ghzToHz = this.RNodeGHzValue * 1e9;
            const mhzToHz = this.RNodeMHzValue * 1e6;
            const khzToHz = this.RNodekHzValue * 1e3;
            return ghzToHz + mhzToHz + khzToHz;
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
            if (!bandwidth || !spreadingFactor || !codingRate) {
                this.RNodeInterfaceLoRaParameters.dataRate = "0 bps";
                this.RNodeInterfaceLoRaParameters.sensitivity = "??? dBm";
                this.RNodeInterfaceLoRaParameters.linkBudget = "??? dB";
                return;
            }

            // https://unsigned.io/understanding-lora-parameters/
            // "SX1272/3/6/7/8 LoRa Modem Design Guide" https://www.openhacks.com/uploadsproductos/loradesignguide_std.pdf
            // 4:5 - 4:8
            const crn = {
                5: 1,
                6: 2,
                7: 3,
                8: 4,
            };

            codingRate = crn[codingRate];

            const sfn = {
                5: -2.5,
                6: -5,
                7: -7.5,
                8: -10,
                9: -12.5,
                10: -15,
                11: -17.5,
                12: -20,
            };

            let dataRate =
                spreadingFactor * (4 / (4 + codingRate) / (Math.pow(2, spreadingFactor) / (bandwidth / 1000))) * 1000;

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
            if (this.newInterfaceType === "AX25KISSInterface") {
                this.newInterfaceType = "KISSInterface";
            } else {
                this.newInterfaceType = "AX25KISSInterface";
            }
        },
        removeSubInterface(idx) {
            this.RNodeMultiInterface.subInterfaces.splice(idx, 1);
        },
    },
};
</script>

<style scoped>
.glass-card {
    @apply bg-white/95 dark:bg-zinc-900/85 backdrop-blur border border-gray-200 dark:border-zinc-800 rounded-3xl shadow-xl;
}
.input-field {
    @apply bg-gray-50/90 dark:bg-zinc-900/80 border border-gray-200 dark:border-zinc-700 text-sm rounded-2xl focus:ring-2 focus:ring-blue-400 focus:border-blue-400 dark:focus:ring-blue-500 dark:focus:border-blue-500 block w-full p-2.5 text-gray-900 dark:text-gray-100 transition;
}
.glass-label {
    @apply mb-1 text-sm font-semibold text-gray-800 dark:text-gray-200;
}
.glass-field {
    @apply space-y-1;
}
</style>
