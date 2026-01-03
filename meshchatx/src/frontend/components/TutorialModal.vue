<template>
    <v-dialog
        v-if="!isPage"
        v-model="visible"
        :fullscreen="isMobile"
        max-width="800"
        transition="dialog-bottom-transition"
        class="tutorial-dialog"
        @update:model-value="onVisibleUpdate"
    >
        <v-card class="flex flex-col h-full bg-white dark:bg-zinc-950 border-0 overflow-hidden">
            <!-- Progress Bar -->
            <div class="w-full h-1.5 bg-gray-100 dark:bg-zinc-900 overflow-hidden flex">
                <div
                    v-for="step in totalSteps"
                    :key="step"
                    class="h-full transition-all duration-500 ease-out"
                    :class="[
                        currentStep >= step ? 'bg-blue-500' : 'bg-transparent',
                        currentStep === step ? 'flex-[2]' : 'flex-1',
                    ]"
                    :style="{ borderRight: step < totalSteps ? '1px solid rgba(0,0,0,0.05)' : 'none' }"
                ></div>
            </div>

            <!-- Content Area -->
            <v-card-text class="flex-1 overflow-y-auto px-6 md:px-12 py-10 relative">
                <transition name="fade-slide" mode="out-in">
                    <!-- Step 1: Welcome -->
                    <div v-if="currentStep === 1" key="step1" class="flex flex-col items-center text-center space-y-6">
                        <div class="relative">
                            <div class="w-24 h-24 bg-blue-500/10 rounded-3xl rotate-12 absolute -inset-2"></div>
                            <img :src="logoUrl" class="w-24 h-24 relative z-10 p-2" />
                        </div>
                        <div class="space-y-2">
                            <h1 class="text-4xl font-black tracking-tight text-gray-900 dark:text-white">
                                Welcome to <span class="text-blue-500">MeshChatX</span>
                            </h1>
                            <p class="text-lg text-gray-600 dark:text-zinc-400 max-w-md mx-auto">
                                The future of off-grid communication. Secure, decentralized, and unstoppable.
                            </p>
                        </div>
                        <div class="grid grid-cols-1 md:grid-cols-2 gap-4 w-full mt-8">
                            <div
                                class="flex items-start gap-4 p-4 rounded-2xl bg-gray-50 dark:bg-zinc-900 text-left border border-gray-100 dark:border-zinc-800"
                            >
                                <v-icon icon="mdi-shield-lock" color="blue" size="32"></v-icon>
                                <div>
                                    <div class="font-bold text-gray-900 dark:text-white">Security & Performance</div>
                                    <div class="text-sm text-gray-500">
                                        Massive improvements in speed, security, and crash recovery.
                                    </div>
                                </div>
                            </div>
                            <div
                                class="flex items-start gap-4 p-4 rounded-2xl bg-gray-50 dark:bg-zinc-900 text-left border border-gray-100 dark:border-zinc-800"
                            >
                                <v-icon icon="mdi-map-marker-path" color="purple" size="32"></v-icon>
                                <div>
                                    <div class="font-bold text-gray-900 dark:text-white">Enhanced Maps</div>
                                    <div class="text-sm text-gray-500">
                                        OpenLayers w/ MBTiles support and custom API endpoints.
                                    </div>
                                </div>
                            </div>
                            <div
                                class="flex items-start gap-4 p-4 rounded-2xl bg-gray-50 dark:bg-zinc-900 text-left border border-gray-100 dark:border-zinc-800"
                            >
                                <v-icon icon="mdi-phone-voip" color="green" size="32"></v-icon>
                                <div>
                                    <div class="font-bold text-gray-900 dark:text-white">Full LXST Voice</div>
                                    <div class="text-sm text-gray-500">
                                        Voicemail, ringtones, phonebook, and contact sharing.
                                    </div>
                                </div>
                            </div>
                            <div
                                class="flex items-start gap-4 p-4 rounded-2xl bg-gray-50 dark:bg-zinc-900 text-left border border-gray-100 dark:border-zinc-800"
                            >
                                <v-icon icon="mdi-tools" color="orange" size="32"></v-icon>
                                <div>
                                    <div class="font-bold text-gray-900 dark:text-white">Advanced Tools</div>
                                    <div class="text-sm text-gray-500">
                                        Micron, Paper Messages, RNS tools, Crawler & Archiver.
                                    </div>
                                </div>
                            </div>
                            <div
                                class="flex items-start gap-4 p-4 rounded-2xl bg-gray-50 dark:bg-zinc-900 text-left border border-gray-100 dark:border-zinc-800"
                            >
                                <v-icon icon="mdi-keyboard-outline" color="red" size="32"></v-icon>
                                <div>
                                    <div class="font-bold text-gray-900 dark:text-white">Command Palette</div>
                                    <div class="text-sm text-gray-500">
                                        Navigate everything instantly with a few keystrokes.
                                    </div>
                                </div>
                            </div>
                            <div
                                class="flex items-start gap-4 p-4 rounded-2xl bg-gray-50 dark:bg-zinc-900 text-left border border-gray-100 dark:border-zinc-800"
                            >
                                <v-icon icon="mdi-translate" color="cyan" size="32"></v-icon>
                                <div>
                                    <div class="font-bold text-gray-900 dark:text-white">i18n Support</div>
                                    <div class="text-sm text-gray-500">Available in English, German, and Russian.</div>
                                </div>
                            </div>
                        </div>
                    </div>

                    <!-- Step 2: Add Interface -->
                    <div v-else-if="currentStep === 2" key="step2" class="space-y-6">
                        <div class="text-center space-y-2">
                            <h2 class="text-2xl font-bold text-gray-900 dark:text-white">Connect to the Mesh</h2>
                            <p class="text-gray-600 dark:text-zinc-400">
                                To send messages, you need to connect to a Reticulum interface.
                            </p>
                        </div>

                        <div v-if="!showCustomForm" class="space-y-4">
                            <!-- Community Interfaces -->
                            <div
                                class="bg-gray-50 dark:bg-zinc-900 rounded-3xl p-4 border border-gray-100 dark:border-zinc-800"
                            >
                                <div class="flex items-center gap-2 mb-4 px-2">
                                    <v-icon icon="mdi-web" color="blue"></v-icon>
                                    <span class="font-bold text-gray-900 dark:text-white">Suggested Public Relays</span>
                                </div>
                                <div class="space-y-2 max-h-[300px] overflow-y-auto pr-2">
                                    <div
                                        v-for="iface in communityInterfaces"
                                        :key="iface.name"
                                        class="flex items-center justify-between p-3 bg-white dark:bg-zinc-800 rounded-2xl border border-gray-100 dark:border-zinc-700 hover:border-blue-400 transition-colors cursor-pointer"
                                        @click="selectCommunityInterface(iface)"
                                    >
                                        <div class="flex flex-col">
                                            <span class="font-bold text-gray-900 dark:text-white">{{
                                                iface.name
                                            }}</span>
                                            <span class="text-xs text-gray-500"
                                                >{{ iface.target_host }}:{{ iface.target_port }}</span
                                            >
                                        </div>
                                        <div class="flex items-center gap-3">
                                            <span
                                                v-if="iface.online"
                                                class="flex items-center gap-1 text-[10px] font-bold text-green-500 uppercase tracking-wider"
                                            >
                                                <span
                                                    class="w-1.5 h-1.5 rounded-full bg-green-500 animate-pulse"
                                                ></span>
                                                Online
                                            </span>
                                            <v-btn
                                                size="small"
                                                variant="flat"
                                                color="#3b82f6"
                                                rounded="lg"
                                                class="font-bold text-white"
                                                @click.stop="selectCommunityInterface(iface)"
                                                >Use</v-btn
                                            >
                                        </div>
                                    </div>
                                    <div v-if="loadingInterfaces" class="flex justify-center py-4">
                                        <v-progress-circular indeterminate color="blue" size="24"></v-progress-circular>
                                    </div>
                                </div>
                            </div>

                            <div class="text-center text-sm text-gray-500 dark:text-zinc-500">OR</div>

                            <!-- Custom Interface -->
                            <v-btn
                                block
                                variant="outlined"
                                color="blue"
                                rounded="xl"
                                class="font-bold h-12 dark:text-blue-400"
                                prepend-icon="mdi-plus"
                                @click="showCustomInterfacePrompt"
                            >
                                Manual Configuration
                            </v-btn>
                        </div>

                        <!-- Custom Interface Form -->
                        <div v-else class="space-y-4 animate-in fade-in slide-in-from-bottom-4 duration-300">
                            <div
                                class="bg-gray-50 dark:bg-zinc-900 rounded-3xl p-6 border border-gray-100 dark:border-zinc-800 space-y-4"
                            >
                                <div class="flex items-center justify-between mb-2">
                                    <span class="font-bold text-gray-900 dark:text-white">Custom Interface</span>
                                    <v-btn size="small" variant="text" color="gray" @click="showCustomForm = false"
                                        >Cancel</v-btn
                                    >
                                </div>

                                <v-select
                                    v-model="newInterface.type"
                                    :items="interfaceTypes"
                                    label="Interface Type"
                                    variant="outlined"
                                    density="comfortable"
                                    rounded="lg"
                                    hide-details
                                    class="bg-white dark:bg-zinc-800"
                                ></v-select>

                                <v-text-field
                                    v-model="newInterface.name"
                                    label="Interface Name"
                                    placeholder="e.g. My Relay"
                                    variant="outlined"
                                    density="comfortable"
                                    rounded="lg"
                                    hide-details
                                    class="bg-white dark:bg-zinc-800"
                                ></v-text-field>

                                <!-- TCP Client Fields -->
                                <template v-if="newInterface.type === 'TCPClientInterface'">
                                    <v-text-field
                                        v-model="newInterface.target_host"
                                        label="Target Host"
                                        placeholder="e.g. 1.2.3.4 or example.com"
                                        variant="outlined"
                                        density="comfortable"
                                        rounded="lg"
                                        hide-details
                                        class="bg-white dark:bg-zinc-800"
                                    ></v-text-field>
                                    <v-text-field
                                        v-model="newInterface.target_port"
                                        label="Target Port"
                                        type="number"
                                        placeholder="4242"
                                        variant="outlined"
                                        density="comfortable"
                                        rounded="lg"
                                        hide-details
                                        class="bg-white dark:bg-zinc-800"
                                    ></v-text-field>
                                </template>

                                <!-- Server/UDP Fields -->
                                <template
                                    v-if="
                                        newInterface.type === 'TCPServerInterface' ||
                                        newInterface.type === 'UDPInterface'
                                    "
                                >
                                    <v-text-field
                                        v-model="newInterface.listen_ip"
                                        label="Listen IP"
                                        placeholder="0.0.0.0"
                                        variant="outlined"
                                        density="comfortable"
                                        rounded="lg"
                                        hide-details
                                        class="bg-white dark:bg-zinc-800"
                                    ></v-text-field>
                                    <v-text-field
                                        v-model="newInterface.listen_port"
                                        label="Listen Port"
                                        type="number"
                                        placeholder="4242"
                                        variant="outlined"
                                        density="comfortable"
                                        rounded="lg"
                                        hide-details
                                        class="bg-white dark:bg-zinc-800"
                                    ></v-text-field>
                                </template>

                                <!-- RNode/Serial/KISS Fields -->
                                <template
                                    v-if="
                                        [
                                            'RNodeInterface',
                                            'RNodeMultiInterface',
                                            'SerialInterface',
                                            'KISSInterface',
                                            'AX25KISSInterface',
                                        ].includes(newInterface.type)
                                    "
                                >
                                    <v-select
                                        v-model="newInterface.port"
                                        :items="comports"
                                        item-title="device"
                                        item-value="device"
                                        label="Serial Port"
                                        variant="outlined"
                                        density="comfortable"
                                        rounded="lg"
                                        hide-details
                                        class="bg-white dark:bg-zinc-800"
                                    ></v-select>
                                    <v-text-field
                                        v-if="
                                            ['SerialInterface', 'KISSInterface', 'AX25KISSInterface'].includes(
                                                newInterface.type
                                            )
                                        "
                                        v-model="newInterface.speed"
                                        label="Baud Rate"
                                        type="number"
                                        variant="outlined"
                                        density="comfortable"
                                        rounded="lg"
                                        hide-details
                                        class="bg-white dark:bg-zinc-800"
                                    ></v-text-field>
                                </template>

                                <!-- Pipe Interface Fields -->
                                <template v-if="newInterface.type === 'PipeInterface'">
                                    <v-text-field
                                        v-model="newInterface.command"
                                        label="Command"
                                        placeholder="e.g. netcat -l 5757"
                                        variant="outlined"
                                        density="comfortable"
                                        rounded="lg"
                                        hide-details
                                        class="bg-white dark:bg-zinc-800"
                                    ></v-text-field>
                                </template>

                                <v-btn
                                    block
                                    color="blue"
                                    variant="flat"
                                    rounded="lg"
                                    class="font-bold h-12 text-white mt-4"
                                    @click="addCustomInterface"
                                >
                                    Add Interface
                                </v-btn>
                                <p class="text-[10px] text-center text-gray-500">
                                    More advanced options are available in the full Interface settings after setup.
                                </p>
                            </div>
                        </div>
                    </div>

                    <!-- Step 3: Documentation & Tools -->
                    <div v-else-if="currentStep === 3" key="step3" class="space-y-6">
                        <div class="text-center space-y-2">
                            <h2 class="text-2xl font-bold text-gray-900 dark:text-white">Learn & Create</h2>
                            <p class="text-gray-600 dark:text-zinc-400">
                                Discover how to use MeshChatX to its full potential.
                            </p>
                        </div>

                        <div class="grid grid-cols-1 gap-4">
                            <div
                                class="flex items-start gap-4 p-4 rounded-2xl bg-gray-50 dark:bg-zinc-900 text-left border border-gray-100 dark:border-zinc-800"
                            >
                                <v-icon icon="mdi-book-open-variant" color="blue" size="32"></v-icon>
                                <div>
                                    <div class="font-bold text-gray-900 dark:text-white">Documentation</div>
                                    <div class="text-sm text-gray-500 mb-2">
                                        Read the official MeshChatX and Reticulum documentation.
                                    </div>
                                    <div class="flex gap-2">
                                        <v-btn
                                            size="x-small"
                                            variant="tonal"
                                            color="blue"
                                            href="/meshchatx-docs/index.html"
                                            target="_blank"
                                            >MeshChatX Docs</v-btn
                                        >
                                        <v-btn
                                            size="x-small"
                                            variant="tonal"
                                            color="purple"
                                            href="https://reticulum.network/manual/"
                                            target="_blank"
                                            >Reticulum Docs</v-btn
                                        >
                                    </div>
                                </div>
                            </div>

                            <div
                                class="flex items-start gap-4 p-4 rounded-2xl bg-gray-50 dark:bg-zinc-900 text-left border border-gray-100 dark:border-zinc-800"
                            >
                                <v-icon icon="mdi-file-document-edit-outline" color="orange" size="32"></v-icon>
                                <div>
                                    <div class="font-bold text-gray-900 dark:text-white">Micron Editor</div>
                                    <div class="text-sm text-gray-500 mb-2">
                                        Take a look at the Micron Editor for a guide on creating mesh-native pages.
                                    </div>
                                    <v-btn
                                        size="x-small"
                                        variant="tonal"
                                        color="orange"
                                        @click="
                                            $router.push({ name: 'micron-editor' });
                                            visible = false;
                                        "
                                        >Open Micron Editor</v-btn
                                    >
                                </div>
                            </div>
                        </div>
                    </div>

                    <!-- Step 4: Finish -->
                    <div
                        v-else-if="currentStep === 4"
                        key="step4"
                        class="flex flex-col items-center text-center space-y-8 py-10"
                    >
                        <div class="w-32 h-32 bg-green-500/10 rounded-full flex items-center justify-center relative">
                            <v-icon icon="mdi-check-decagram" color="green" size="80"></v-icon>
                            <div class="absolute inset-0 bg-green-500/20 rounded-full animate-ping opacity-20"></div>
                        </div>
                        <div class="space-y-3">
                            <h2 class="text-3xl font-black text-gray-900 dark:text-white">Ready to Roll!</h2>
                            <p class="text-lg text-gray-600 dark:text-zinc-400 max-w-md mx-auto">
                                Everything is set up. You need to restart the application for the changes to take
                                effect.
                            </p>
                        </div>
                        <div
                            class="p-4 bg-amber-50 dark:bg-amber-900/20 rounded-2xl border border-amber-100 dark:border-amber-900/30 text-amber-700 dark:text-amber-400 text-sm flex gap-3 max-w-md text-left"
                        >
                            <v-icon icon="mdi-information-outline" class="shrink-0"></v-icon>
                            <span
                                >If you're running in Docker, make sure your container auto-restarts or start it
                                manually after it stops.</span
                            >
                        </div>
                    </div>
                </transition>
            </v-card-text>

            <!-- Footer -->
            <v-divider class="dark:border-zinc-900"></v-divider>
            <v-card-actions class="px-6 py-6 bg-gray-50 dark:bg-zinc-950/50 flex justify-between">
                <v-btn
                    v-if="currentStep > 1 && currentStep < totalSteps"
                    variant="text"
                    color="gray"
                    class="font-bold text-gray-700 dark:text-zinc-300"
                    @click="currentStep--"
                    >Back</v-btn
                >
                <div v-else></div>

                <div class="flex gap-3">
                    <v-btn
                        v-if="currentStep < totalSteps"
                        variant="text"
                        color="gray"
                        class="font-bold opacity-50 hover:opacity-100 text-gray-700 dark:text-zinc-300"
                        @click="skipTutorial"
                        >Skip</v-btn
                    >

                    <v-btn
                        v-if="currentStep < totalSteps"
                        variant="flat"
                        color="#3b82f6"
                        class="px-8 font-black tracking-wide h-12 text-white"
                        rounded="xl"
                        @click="nextStep"
                        >Next</v-btn
                    >

                    <v-btn
                        v-else
                        variant="flat"
                        color="#22c55e"
                        class="px-8 font-black tracking-wide h-12 text-white"
                        rounded="xl"
                        @click="finishAndRestart"
                        >Restart & Start Chatting</v-btn
                    >
                </div>
            </v-card-actions>
        </v-card>
    </v-dialog>

    <div v-else class="flex flex-col h-full bg-white dark:bg-zinc-950 overflow-hidden">
        <!-- Progress Bar -->
        <div class="w-full h-1.5 bg-gray-100 dark:bg-zinc-900 overflow-hidden flex">
            <div
                v-for="step in totalSteps"
                :key="step"
                class="h-full transition-all duration-500 ease-out"
                :class="[
                    currentStep >= step ? 'bg-blue-500' : 'bg-transparent',
                    currentStep === step ? 'flex-[2]' : 'flex-1',
                ]"
                :style="{ borderRight: step < totalSteps ? '1px solid rgba(0,0,0,0.05)' : 'none' }"
            ></div>
        </div>

        <div class="flex-1 overflow-y-auto px-6 md:px-12 py-10">
            <div class="max-w-4xl mx-auto h-full flex flex-col justify-between">
                <transition name="fade-slide" mode="out-in">
                    <!-- Step 1: Welcome -->
                    <div
                        v-if="currentStep === 1"
                        key="step1"
                        class="flex flex-col items-center text-center space-y-8 py-10"
                    >
                        <div class="relative">
                            <div class="w-32 h-32 bg-blue-500/10 rounded-3xl rotate-12 absolute -inset-2"></div>
                            <img :src="logoUrl" class="w-32 h-32 relative z-10 p-2" />
                        </div>
                        <div class="space-y-4">
                            <h1 class="text-5xl font-black tracking-tight text-gray-900 dark:text-white">
                                Welcome to <span class="text-blue-500">MeshChatX</span>
                            </h1>
                            <p class="text-xl text-gray-600 dark:text-zinc-400 max-w-2xl mx-auto">
                                The future of off-grid communication. Secure, decentralized, and unstoppable.
                            </p>
                        </div>
                        <div class="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6 w-full mt-12">
                            <div
                                class="flex items-start gap-6 p-6 rounded-3xl bg-gray-50 dark:bg-zinc-900 text-left border border-gray-100 dark:border-zinc-800 transition-transform hover:scale-[1.02]"
                            >
                                <v-icon icon="mdi-shield-lock" color="blue" size="40"></v-icon>
                                <div>
                                    <div class="font-bold text-xl text-gray-900 dark:text-white">
                                        Security & Performance
                                    </div>
                                    <div class="text-gray-500">
                                        Massive improvements in speed, security, and integrity with built-in crash
                                        recovery.
                                    </div>
                                </div>
                            </div>
                            <div
                                class="flex items-start gap-6 p-6 rounded-3xl bg-gray-50 dark:bg-zinc-900 text-left border border-gray-100 dark:border-zinc-800 transition-transform hover:scale-[1.02]"
                            >
                                <v-icon icon="mdi-map-marker-path" color="purple" size="40"></v-icon>
                                <div>
                                    <div class="font-bold text-xl text-gray-900 dark:text-white">Enhanced Maps</div>
                                    <div class="text-gray-500">
                                        OpenLayers support with offline MBTiles and custom API endpoints for online
                                        maps.
                                    </div>
                                </div>
                            </div>
                            <div
                                class="flex items-start gap-6 p-6 rounded-3xl bg-gray-50 dark:bg-zinc-900 text-left border border-gray-100 dark:border-zinc-800 transition-transform hover:scale-[1.02]"
                            >
                                <v-icon icon="mdi-phone-voip" color="green" size="40"></v-icon>
                                <div>
                                    <div class="font-bold text-xl text-gray-900 dark:text-white">Full LXST Voice</div>
                                    <div class="text-gray-500">
                                        Crystal clear voice calls over mesh. Voicemail, custom ringtones, and phonebook
                                        discovery.
                                    </div>
                                </div>
                            </div>
                            <div
                                class="flex items-start gap-6 p-6 rounded-3xl bg-gray-50 dark:bg-zinc-900 text-left border border-gray-100 dark:border-zinc-800 transition-transform hover:scale-[1.02]"
                            >
                                <v-icon icon="mdi-tools" color="orange" size="40"></v-icon>
                                <div>
                                    <div class="font-bold text-xl text-gray-900 dark:text-white">Advanced Tools</div>
                                    <div class="text-gray-500">
                                        Micron editor, paper messages, RNS tools, network Crawler and Archiver.
                                    </div>
                                </div>
                            </div>
                            <div
                                class="flex items-start gap-6 p-6 rounded-3xl bg-gray-50 dark:bg-zinc-900 text-left border border-gray-100 dark:border-zinc-800 transition-transform hover:scale-[1.02]"
                            >
                                <v-icon icon="mdi-keyboard-outline" color="red" size="40"></v-icon>
                                <div>
                                    <div class="font-bold text-xl text-gray-900 dark:text-white">Command Palette</div>
                                    <div class="text-gray-500">
                                        Navigate the entire application and access tools instantly with a single
                                        shortcut.
                                    </div>
                                </div>
                            </div>
                            <div
                                class="flex items-start gap-6 p-6 rounded-3xl bg-gray-50 dark:bg-zinc-900 text-left border border-gray-100 dark:border-zinc-800 transition-transform hover:scale-[1.02]"
                            >
                                <v-icon icon="mdi-translate" color="cyan" size="40"></v-icon>
                                <div>
                                    <div class="font-bold text-xl text-gray-900 dark:text-white">i18n Support</div>
                                    <div class="text-gray-500">
                                        Full internationalization support for English, German, and Russian languages.
                                    </div>
                                </div>
                            </div>
                        </div>
                    </div>

                    <!-- Step 2: Add Interface -->
                    <div v-else-if="currentStep === 2" key="step2" class="space-y-8 py-10">
                        <div class="text-center space-y-4">
                            <h2 class="text-4xl font-black text-gray-900 dark:text-white">Connect to the Mesh</h2>
                            <p class="text-xl text-gray-600 dark:text-zinc-400 max-w-2xl mx-auto">
                                To send messages and make calls, you need to connect to a Reticulum interface.
                            </p>
                        </div>

                        <div class="grid grid-cols-1 lg:grid-cols-2 gap-8">
                            <!-- Community Interfaces -->
                            <div
                                class="bg-gray-50 dark:bg-zinc-900 rounded-[2rem] p-8 border border-gray-100 dark:border-zinc-800"
                            >
                                <div class="flex items-center gap-3 mb-6">
                                    <v-icon icon="mdi-web" color="blue" size="28"></v-icon>
                                    <span class="text-xl font-bold text-gray-900 dark:text-white"
                                        >Suggested Public Relays</span
                                    >
                                </div>
                                <div class="space-y-3 max-h-[400px] overflow-y-auto pr-4 custom-scrollbar">
                                    <div
                                        v-for="iface in communityInterfaces"
                                        :key="iface.name"
                                        class="flex items-center justify-between p-4 bg-white dark:bg-zinc-800 rounded-2xl border border-gray-100 dark:border-zinc-700 hover:border-blue-400 transition-all cursor-pointer group shadow-sm hover:shadow-md"
                                        @click="selectCommunityInterface(iface)"
                                    >
                                        <div class="flex flex-col">
                                            <span
                                                class="font-bold text-gray-900 dark:text-white text-lg group-hover:text-blue-500 transition-colors"
                                                >{{ iface.name }}</span
                                            >
                                            <span class="text-sm text-gray-500 font-mono"
                                                >{{ iface.target_host }}:{{ iface.target_port }}</span
                                            >
                                        </div>
                                        <div class="flex items-center gap-4">
                                            <span
                                                v-if="iface.online"
                                                class="flex items-center gap-1.5 text-[10px] font-bold text-green-500 uppercase tracking-widest"
                                            >
                                                <span class="w-2 h-2 rounded-full bg-green-500 animate-pulse"></span>
                                                Online
                                            </span>
                                            <v-btn
                                                variant="flat"
                                                color="#3b82f6"
                                                rounded="xl"
                                                class="font-black px-6 text-white"
                                                @click.stop="selectCommunityInterface(iface)"
                                                >Use</v-btn
                                            >
                                        </div>
                                    </div>
                                    <div v-if="loadingInterfaces" class="flex justify-center py-10">
                                        <v-progress-circular indeterminate color="blue" size="40"></v-progress-circular>
                                    </div>
                                </div>
                            </div>

                            <div v-if="!showCustomForm" class="flex flex-col justify-center space-y-8">
                                <div class="relative py-4">
                                    <div class="absolute inset-0 flex items-center">
                                        <div class="w-full border-t border-gray-200 dark:border-zinc-800"></div>
                                    </div>
                                    <div
                                        class="relative flex justify-center text-sm font-black uppercase tracking-widest"
                                    >
                                        <span class="bg-white dark:bg-zinc-950 px-4 text-gray-400">Custom Setup</span>
                                    </div>
                                </div>

                                <div class="space-y-4">
                                    <p class="text-gray-500 text-center px-6 text-lg">
                                        Already have a private relay or hardware RNode? Add it manually to connect to
                                        your own mesh.
                                    </p>
                                    <v-btn
                                        block
                                        variant="outlined"
                                        color="blue"
                                        rounded="2xl"
                                        class="font-black h-20 text-xl border-2 dark:text-blue-400"
                                        prepend-icon="mdi-plus"
                                        @click="showCustomInterfacePrompt"
                                    >
                                        Manual Configuration
                                    </v-btn>
                                </div>
                            </div>

                            <!-- Custom Interface Form (Page Mode) -->
                            <div
                                v-else
                                class="space-y-6 animate-in fade-in slide-in-from-right-4 duration-500 bg-gray-50 dark:bg-zinc-900 rounded-[2rem] p-8 border border-gray-100 dark:border-zinc-800"
                            >
                                <div class="flex items-center justify-between">
                                    <h3 class="text-2xl font-bold text-gray-900 dark:text-white">Custom Interface</h3>
                                    <v-btn variant="text" color="gray" @click="showCustomForm = false"
                                        >Back to suggested</v-btn
                                    >
                                </div>

                                <div class="space-y-5">
                                    <v-select
                                        v-model="newInterface.type"
                                        :items="interfaceTypes"
                                        label="Interface Type"
                                        variant="outlined"
                                        density="comfortable"
                                        rounded="xl"
                                        class="bg-white dark:bg-zinc-800"
                                    ></v-select>

                                    <v-text-field
                                        v-model="newInterface.name"
                                        label="Interface Name"
                                        placeholder="e.g. My Relay"
                                        variant="outlined"
                                        density="comfortable"
                                        rounded="xl"
                                        class="bg-white dark:bg-zinc-800"
                                    ></v-text-field>

                                    <!-- TCP Client Fields -->
                                    <template v-if="newInterface.type === 'TCPClientInterface'">
                                        <div class="grid grid-cols-2 gap-4">
                                            <v-text-field
                                                v-model="newInterface.target_host"
                                                label="Target Host"
                                                placeholder="e.g. 1.2.3.4"
                                                variant="outlined"
                                                density="comfortable"
                                                rounded="xl"
                                                class="bg-white dark:bg-zinc-800"
                                            ></v-text-field>
                                            <v-text-field
                                                v-model="newInterface.target_port"
                                                label="Target Port"
                                                type="number"
                                                variant="outlined"
                                                density="comfortable"
                                                rounded="xl"
                                                class="bg-white dark:bg-zinc-800"
                                            ></v-text-field>
                                        </div>
                                    </template>

                                    <!-- Server/UDP Fields -->
                                    <template
                                        v-if="
                                            newInterface.type === 'TCPServerInterface' ||
                                            newInterface.type === 'UDPInterface'
                                        "
                                    >
                                        <div class="grid grid-cols-2 gap-4">
                                            <v-text-field
                                                v-model="newInterface.listen_ip"
                                                label="Listen IP"
                                                variant="outlined"
                                                density="comfortable"
                                                rounded="xl"
                                                class="bg-white dark:bg-zinc-800"
                                            ></v-text-field>
                                            <v-text-field
                                                v-model="newInterface.listen_port"
                                                label="Listen Port"
                                                type="number"
                                                variant="outlined"
                                                density="comfortable"
                                                rounded="xl"
                                                class="bg-white dark:bg-zinc-800"
                                            ></v-text-field>
                                        </div>
                                    </template>

                                    <!-- RNode/Serial/KISS Fields -->
                                    <template
                                        v-if="
                                            [
                                                'RNodeInterface',
                                                'RNodeMultiInterface',
                                                'SerialInterface',
                                                'KISSInterface',
                                                'AX25KISSInterface',
                                            ].includes(newInterface.type)
                                        "
                                    >
                                        <v-select
                                            v-model="newInterface.port"
                                            :items="comports"
                                            item-title="device"
                                            item-value="device"
                                            label="Serial Port"
                                            variant="outlined"
                                            density="comfortable"
                                            rounded="xl"
                                            class="bg-white dark:bg-zinc-800"
                                        >
                                            <template #item="{ props, item }">
                                                <v-list-item v-bind="props" :subtitle="item.raw.product"></v-list-item>
                                            </template>
                                        </v-select>
                                        <v-text-field
                                            v-if="
                                                ['SerialInterface', 'KISSInterface', 'AX25KISSInterface'].includes(
                                                    newInterface.type
                                                )
                                            "
                                            v-model="newInterface.speed"
                                            label="Baud Rate"
                                            type="number"
                                            variant="outlined"
                                            density="comfortable"
                                            rounded="xl"
                                            class="bg-white dark:bg-zinc-800"
                                        ></v-text-field>
                                    </template>

                                    <!-- Pipe Interface Fields -->
                                    <template v-if="newInterface.type === 'PipeInterface'">
                                        <v-text-field
                                            v-model="newInterface.command"
                                            label="Command"
                                            placeholder="e.g. netcat -l 5757"
                                            variant="outlined"
                                            density="comfortable"
                                            rounded="xl"
                                            class="bg-white dark:bg-zinc-800"
                                        ></v-text-field>
                                    </template>

                                    <v-btn
                                        block
                                        color="blue"
                                        variant="flat"
                                        rounded="xl"
                                        class="h-16 text-lg font-bold text-white mt-4"
                                        @click="addCustomInterface"
                                    >
                                        Add & Connect
                                    </v-btn>
                                    <p class="text-sm text-center text-gray-500">
                                        Additional configuration like frequencies, encryption, and modes can be adjusted
                                        in the full Interface settings later.
                                    </p>
                                </div>
                            </div>
                        </div>
                    </div>

                    <!-- Step 3: Documentation & Tools -->
                    <div v-else-if="currentStep === 3" key="step3" class="space-y-8 py-10">
                        <div class="text-center space-y-4">
                            <h2 class="text-4xl font-black text-gray-900 dark:text-white">Learn & Create</h2>
                            <p class="text-xl text-gray-600 dark:text-zinc-400 max-w-2xl mx-auto">
                                Discover how to use MeshChatX to its full potential and create your own content.
                            </p>
                        </div>

                        <div class="grid grid-cols-1 md:grid-cols-2 gap-8">
                            <div
                                class="flex flex-col items-center gap-6 p-8 rounded-[2rem] bg-gray-50 dark:bg-zinc-900 text-center border border-gray-100 dark:border-zinc-800"
                            >
                                <v-icon icon="mdi-book-open-variant" color="blue" size="64"></v-icon>
                                <div>
                                    <div class="font-bold text-2xl text-gray-900 dark:text-white mb-2">
                                        Documentation
                                    </div>
                                    <p class="text-gray-500 mb-6">
                                        Comprehensive guides for MeshChatX and the underlying Reticulum Network Stack.
                                    </p>
                                    <div class="flex flex-col gap-3">
                                        <v-btn
                                            block
                                            variant="flat"
                                            color="blue"
                                            class="h-12 font-bold text-white"
                                            rounded="xl"
                                            href="/meshchatx-docs/index.html"
                                            target="_blank"
                                            >Read MeshChatX Docs</v-btn
                                        >
                                        <v-btn
                                            block
                                            variant="outlined"
                                            color="purple"
                                            class="h-12 font-bold"
                                            rounded="xl"
                                            href="https://reticulum.network/manual/"
                                            target="_blank"
                                            >Reticulum Network Manual</v-btn
                                        >
                                    </div>
                                </div>
                            </div>

                            <div
                                class="flex flex-col items-center gap-6 p-8 rounded-[2rem] bg-gray-50 dark:bg-zinc-900 text-center border border-gray-100 dark:border-zinc-800"
                            >
                                <v-icon icon="mdi-file-document-edit-outline" color="orange" size="64"></v-icon>
                                <div>
                                    <div class="font-bold text-2xl text-gray-900 dark:text-white mb-2">
                                        Micron Editor
                                    </div>
                                    <p class="text-gray-500 mb-6">
                                        Learn how to create mesh-native pages and interactive content using the Micron
                                        markup language.
                                    </p>
                                    <v-btn
                                        block
                                        variant="flat"
                                        color="orange"
                                        class="h-12 font-bold text-white"
                                        rounded="xl"
                                        @click="$router.push({ name: 'micron-editor' })"
                                        >Open Micron Editor</v-btn
                                    >
                                </div>
                            </div>
                        </div>
                    </div>

                    <!-- Step 4: Finish -->
                    <div
                        v-else-if="currentStep === 4"
                        key="step4"
                        class="flex flex-col items-center text-center space-y-10 py-20"
                    >
                        <div class="w-48 h-48 bg-green-500/10 rounded-full flex items-center justify-center relative">
                            <v-icon icon="mdi-check-decagram" color="green" size="120"></v-icon>
                            <div class="absolute inset-0 bg-green-500/20 rounded-full animate-ping opacity-20"></div>
                        </div>
                        <div class="space-y-4">
                            <h2 class="text-5xl font-black text-gray-900 dark:text-white">Ready to Roll!</h2>
                            <p class="text-xl text-gray-600 dark:text-zinc-400 max-w-2xl mx-auto">
                                MeshChatX is now configured. You need to restart the application to finalize the
                                connection.
                            </p>
                        </div>
                        <div
                            class="p-6 bg-amber-50 dark:bg-amber-900/20 rounded-3xl border border-amber-100 dark:border-amber-900/30 text-amber-700 dark:text-amber-400 flex gap-4 max-w-xl text-left"
                        >
                            <v-icon icon="mdi-information-outline" size="32" class="shrink-0"></v-icon>
                            <div class="space-y-1">
                                <div class="font-bold text-lg">Restart Required</div>
                                <div class="opacity-90">
                                    If you're running in Docker, ensure your container auto-restarts. Native apps will
                                    relaunch automatically.
                                </div>
                            </div>
                        </div>
                    </div>
                </transition>

                <!-- Navigation Buttons (Page Mode) -->
                <div class="flex justify-between items-center mt-12 border-t dark:border-zinc-900 pt-8">
                    <v-btn
                        v-if="currentStep > 1 && currentStep < totalSteps"
                        variant="text"
                        color="gray"
                        class="font-black h-12 px-8 text-gray-700 dark:text-zinc-300"
                        @click="currentStep--"
                        >Back</v-btn
                    >
                    <div v-else></div>

                    <div class="flex gap-4">
                        <v-btn
                            v-if="currentStep < totalSteps"
                            variant="text"
                            color="gray"
                            class="font-black h-12 px-8 opacity-50 hover:opacity-100 text-gray-700 dark:text-zinc-300"
                            @click="skipTutorial"
                            >Skip Setup</v-btn
                        >

                        <v-btn
                            v-if="currentStep < totalSteps"
                            variant="flat"
                            color="#3b82f6"
                            class="px-12 font-black tracking-wide h-14 text-lg text-white"
                            rounded="2xl"
                            @click="nextStep"
                            >Continue</v-btn
                        >

                        <v-btn
                            v-else
                            variant="flat"
                            color="#22c55e"
                            class="px-12 font-black tracking-wide h-14 text-lg text-white"
                            rounded="2xl"
                            @click="finishAndRestart"
                            >Restart & Start Chatting</v-btn
                        >
                    </div>
                </div>
            </div>
        </div>
    </div>
</template>

<script>
import logoUrl from "../assets/images/logo.png";
import ToastUtils from "../js/ToastUtils";
import DialogUtils from "../js/DialogUtils";
import ElectronUtils from "../js/ElectronUtils";

export default {
    name: "TutorialModal",
    data() {
        return {
            visible: false,
            currentStep: 1,
            totalSteps: 4,
            logoUrl,
            communityInterfaces: [],
            loadingInterfaces: false,
            showCustomForm: false,
            comports: [],
            newInterface: {
                name: "",
                type: "TCPClientInterface",
                target_host: "",
                target_port: 4242,
                listen_ip: "0.0.0.0",
                listen_port: 4242,
                device: "",
                port: "",
                speed: 115200,
            },
            interfaceTypes: [
                { title: "TCP Client", value: "TCPClientInterface" },
                { title: "TCP Server", value: "TCPServerInterface" },
                { title: "UDP Interface", value: "UDPInterface" },
                { title: "RNode Interface", value: "RNodeInterface" },
                { title: "RNode Multi", value: "RNodeMultiInterface" },
                { title: "Serial Interface", value: "SerialInterface" },
                { title: "KISS Interface", value: "KISSInterface" },
                { title: "AX.25 KISS", value: "AX25KISSInterface" },
                { title: "I2P Interface", value: "I2PInterface" },
                { title: "Auto Interface", value: "AutoInterface" },
                { title: "Pipe Interface", value: "PipeInterface" },
            ],
        };
    },
    computed: {
        isPage() {
            return this.$route?.meta?.isPage === true;
        },
        isMobile() {
            return window.innerWidth < 640;
        },
    },
    mounted() {
        if (this.isPage) {
            this.loadCommunityInterfaces();
            this.loadComports();
        }
    },
    methods: {
        async show() {
            this.visible = true;
            this.currentStep = 1;
            await this.loadCommunityInterfaces();
            await this.loadComports();
        },
        async loadComports() {
            try {
                const response = await window.axios.get("/api/v1/comports");
                this.comports = response.data.comports;
            } catch (e) {
                console.error("Failed to load comports:", e);
            }
        },
        async loadCommunityInterfaces() {
            this.loadingInterfaces = true;
            try {
                const response = await window.axios.get("/api/v1/community-interfaces");
                this.communityInterfaces = response.data.interfaces;
            } catch (e) {
                console.error("Failed to load community interfaces:", e);
            } finally {
                this.loadingInterfaces = false;
            }
        },
        async selectCommunityInterface(iface) {
            try {
                await window.axios.post("/api/v1/reticulum/interfaces/add", {
                    name: iface.name,
                    type: iface.type,
                    target_host: iface.target_host,
                    target_port: iface.target_port,
                    enabled: true,
                });
                ToastUtils.success(`Added interface: ${iface.name}`);
                this.nextStep();
            } catch (e) {
                console.error(e);
                ToastUtils.error(e.response?.data?.message || "Failed to add interface");
            }
        },
        showCustomInterfacePrompt() {
            this.showCustomForm = true;
        },
        async addCustomInterface() {
            if (!this.newInterface.name) {
                ToastUtils.error("Please enter an interface name");
                return;
            }

            try {
                const payload = {
                    name: this.newInterface.name,
                    type: this.newInterface.type,
                    enabled: true,
                };

                if (this.newInterface.type === "TCPClientInterface") {
                    payload.target_host = this.newInterface.target_host;
                    payload.target_port = parseInt(this.newInterface.target_port);
                } else if (
                    this.newInterface.type === "TCPServerInterface" ||
                    this.newInterface.type === "UDPInterface"
                ) {
                    payload.listen_ip = this.newInterface.listen_ip;
                    payload.listen_port = parseInt(this.newInterface.listen_port);
                    if (this.newInterface.type === "UDPInterface") {
                        payload.forward_ip = "255.255.255.255";
                        payload.forward_port = parseInt(this.newInterface.listen_port);
                    }
                } else if (
                    [
                        "RNodeInterface",
                        "RNodeMultiInterface",
                        "SerialInterface",
                        "KISSInterface",
                        "AX25KISSInterface",
                    ].includes(this.newInterface.type)
                ) {
                    payload.port = this.newInterface.port;
                    if (["SerialInterface", "KISSInterface", "AX25KISSInterface"].includes(this.newInterface.type)) {
                        payload.speed = parseInt(this.newInterface.speed);
                    }
                } else if (this.newInterface.type === "PipeInterface") {
                    payload.command = this.newInterface.command;
                }

                await window.axios.post("/api/v1/reticulum/interfaces/add", payload);
                ToastUtils.success(`Added interface: ${this.newInterface.name}`);
                this.nextStep();
            } catch (e) {
                console.error(e);
                ToastUtils.error(e.response?.data?.message || "Failed to add interface");
            }
        },
        nextStep() {
            if (this.currentStep < this.totalSteps) {
                this.currentStep++;
            }
        },
        async skipTutorial() {
            if (
                await DialogUtils.confirm(
                    "Are you sure you want to skip the setup? You'll need to manually add interfaces later."
                )
            ) {
                await this.markSeen();
                this.visible = false;
            }
        },
        async markSeen() {
            try {
                await window.axios.post("/api/v1/app/tutorial/seen");
            } catch (e) {
                console.error("Failed to mark tutorial as seen:", e);
            }
        },
        async finishAndRestart() {
            await this.markSeen();
            if (ElectronUtils.isElectron()) {
                ElectronUtils.relaunch();
            } else {
                ToastUtils.info("Restart the application/container to apply changes.");
                this.visible = false;
            }
        },
        async onVisibleUpdate(val) {
            if (!val) {
                // if closed by clicking away, mark as seen so it doesn't pop up again
                await this.markSeen();
            }
        },
    },
};
</script>

<style scoped>
.tutorial-dialog .v-overlay__content {
    border-radius: 2rem !important;
    overflow: hidden;
}

.fade-slide-enter-active,
.fade-slide-leave-active {
    transition: all 0.4s cubic-bezier(0.4, 0, 0.2, 1);
}

.fade-slide-enter-from {
    opacity: 0;
    transform: translateX(30px);
}

.fade-slide-leave-to {
    opacity: 0;
    transform: translateX(-30px);
}
</style>
