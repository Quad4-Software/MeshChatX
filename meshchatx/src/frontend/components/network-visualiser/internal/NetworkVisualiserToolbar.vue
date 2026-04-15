<template>
    <div
        class="absolute top-2 left-2 right-2 sm:top-4 sm:left-4 sm:right-4 z-10 flex flex-col sm:flex-row gap-2 pointer-events-none"
    >
        <div
            class="pointer-events-auto border border-gray-200/50 dark:border-zinc-800/50 bg-white/70 dark:bg-zinc-900/70 backdrop-blur-xl rounded-2xl overflow-hidden w-full sm:min-w-[280px] sm:w-auto transition-all duration-300"
        >
            <div
                class="flex items-center px-4 sm:px-5 py-3 sm:py-4 cursor-pointer hover:bg-gray-50/50 dark:hover:bg-zinc-800/50 transition-colors"
                @click="$emit('update:isShowingControls', !isShowingControls)"
            >
                <div class="flex-1 flex flex-col min-w-0 mr-2">
                    <span class="font-bold text-gray-900 dark:text-zinc-100 tracking-tight truncate">{{
                        $t("visualiser.reticulum_mesh")
                    }}</span>
                    <span
                        class="text-[10px] uppercase font-bold text-gray-500 dark:text-zinc-500 tracking-widest truncate"
                        >{{ $t("visualiser.network_visualizer") }}</span
                    >
                </div>
                <div class="flex items-center gap-2">
                    <button
                        type="button"
                        class="inline-flex items-center justify-center w-8 h-8 sm:w-9 sm:h-9 rounded-xl bg-blue-600 hover:bg-blue-700 dark:bg-blue-600 dark:hover:bg-blue-700 text-white transition-all active:scale-95"
                        :disabled="isUpdating || isLoading"
                        @click.stop="$emit('manual-update')"
                    >
                        <svg
                            v-if="!isUpdating && !isLoading"
                            xmlns="http://www.w3.org/2000/svg"
                            fill="none"
                            viewBox="0 0 24 24"
                            stroke-width="2"
                            stroke="currentColor"
                            class="w-4 h-4 sm:w-5 sm:h-5"
                        >
                            <path
                                stroke-linecap="round"
                                stroke-linejoin="round"
                                d="M16.023 9.348h4.992v-.001M2.985 19.644v-4.992m0 0h4.992m-4.993 0 3.181 3.183a8.25 8.25 0 0 0 13.803-3.7M4.031 9.865a8.25 8.25 0 0 1 13.803-3.7l3.181 3.182m0-4.991v4.99"
                            />
                        </svg>
                        <svg
                            v-else
                            class="animate-spin h-4 w-4 sm:w-5 sm:h-5"
                            xmlns="http://www.w3.org/2000/svg"
                            fill="none"
                            viewBox="0 0 24 24"
                        >
                            <circle
                                class="opacity-25"
                                cx="12"
                                cy="12"
                                r="10"
                                stroke="currentColor"
                                stroke-width="4"
                            ></circle>
                            <path
                                class="opacity-75"
                                fill="currentColor"
                                d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"
                            ></path>
                        </svg>
                    </button>
                    <div class="w-5 sm:w-6 flex justify-center">
                        <svg
                            xmlns="http://www.w3.org/2000/svg"
                            viewBox="0 0 20 20"
                            fill="currentColor"
                            class="w-4 h-4 sm:w-5 sm:h-5 text-gray-400 transition-transform duration-300"
                            :class="{ 'rotate-180': isShowingControls }"
                        >
                            <path
                                fill-rule="evenodd"
                                d="M5.22 8.22a.75.75 0 0 1 1.06 0L10 11.94l3.72-3.72a.75.75 0 1 1 1.06 1.06l-4.25 4.25a.75.75 0 0 1-1.06 0L5.22 9.28a.75.75 0 0 1 0-1.06Z"
                                clip-rule="evenodd"
                            />
                        </svg>
                    </div>
                </div>
            </div>

            <div
                v-show="isShowingControls"
                class="px-5 pb-5 space-y-4 animate-in fade-in slide-in-from-top-2 duration-300"
            >
                <div class="h-px bg-gradient-to-r from-transparent via-gray-200 dark:via-zinc-800 to-transparent"></div>

                <div class="flex items-center justify-between">
                    <label
                        for="auto-reload"
                        class="text-sm font-semibold text-gray-700 dark:text-zinc-300 cursor-pointer"
                        >Auto Update</label
                    >
                    <Toggle
                        id="auto-reload"
                        :model-value="autoReload"
                        @update:model-value="$emit('update:autoReload', $event)"
                    />
                </div>

                <div class="flex items-center justify-between">
                    <label
                        for="enable-physics"
                        class="text-sm font-semibold text-gray-700 dark:text-zinc-300 cursor-pointer"
                        >Live Layout</label
                    >
                    <Toggle
                        id="enable-physics"
                        :model-value="enablePhysics"
                        @update:model-value="$emit('update:enablePhysics', $event)"
                    />
                </div>

                <div class="space-y-2">
                    <div class="flex items-center justify-between gap-2">
                        <label
                            for="hop-filter-slider"
                            class="text-sm font-semibold text-gray-700 dark:text-zinc-300 cursor-pointer"
                            >{{ $t("visualiser.max_hops_filter") }}</label
                        >
                        <span
                            class="text-xs font-bold text-blue-600 dark:text-blue-400 tabular-nums min-w-[4rem] text-right"
                            >{{ hopFilterSlider === 0 ? $t("visualiser.all") : hopFilterSlider }}</span
                        >
                    </div>
                    <input
                        id="hop-filter-slider"
                        :value="hopFilterSlider"
                        type="range"
                        min="0"
                        :max="hopSliderMax"
                        step="1"
                        class="w-full h-2 rounded-lg appearance-none cursor-pointer bg-gray-200 dark:bg-zinc-700 accent-blue-600 dark:accent-blue-500"
                        @input="$emit('update:hopFilterSlider', Number($event.target.value))"
                    />
                </div>

                <div class="grid grid-cols-2 gap-3 pt-2">
                    <div
                        class="bg-gray-50/50 dark:bg-zinc-800/50 rounded-xl p-3 border border-gray-100 dark:border-zinc-700/50"
                    >
                        <div
                            class="text-[10px] font-bold text-gray-500 dark:text-zinc-500 uppercase tracking-wider mb-1"
                        >
                            Nodes
                        </div>
                        <div class="text-lg font-bold text-blue-600 dark:text-blue-400">{{ nodeCount }}</div>
                    </div>
                    <div
                        class="bg-gray-50/50 dark:bg-zinc-800/50 rounded-xl p-3 border border-gray-100 dark:border-zinc-700/50"
                    >
                        <div
                            class="text-[10px] font-bold text-gray-500 dark:text-zinc-500 uppercase tracking-wider mb-1"
                        >
                            Links
                        </div>
                        <div class="text-lg font-bold text-emerald-600 dark:text-emerald-400">{{ edgeCount }}</div>
                    </div>
                </div>

                <div
                    class="bg-zinc-950/5 dark:bg-white/5 rounded-xl p-3 border border-gray-100 dark:border-zinc-700/50"
                >
                    <div class="text-[10px] font-bold text-gray-500 dark:text-zinc-500 uppercase tracking-wider mb-2">
                        Interfaces
                    </div>
                    <div class="flex items-center gap-4">
                        <div class="flex items-center gap-1.5">
                            <div class="w-2 h-2 rounded-full bg-emerald-500"></div>
                            <span class="text-xs font-bold text-gray-700 dark:text-zinc-300"
                                >{{ onlineInterfaceCount }} Online</span
                            >
                        </div>
                        <div class="flex items-center gap-1.5">
                            <div class="w-2 h-2 rounded-full bg-red-500"></div>
                            <span class="text-xs font-bold text-gray-700 dark:text-zinc-300"
                                >{{ offlineInterfaceCount }} Offline</span
                            >
                        </div>
                    </div>
                </div>
            </div>
        </div>

        <div class="sm:ml-auto w-full sm:w-auto pointer-events-auto">
            <div class="relative group">
                <div
                    class="absolute inset-y-0 left-0 pl-3 flex items-center pointer-events-none text-gray-400 group-focus-within:text-blue-500 transition-colors"
                >
                    <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 20 20" fill="currentColor" class="w-4 h-4">
                        <path
                            fill-rule="evenodd"
                            d="M9 3.5a6.5 6.5 0 1 0 0 13 6.5 6.5 0 0 0 0-13ZM2.25 10a7.75 7.75 0 1 1 14.03 4.5l3.47 3.47a.75.75 0 0 1-1.06 1.06l-3.47-3.47A7.75 7.75 0 0 1 2.25 10Z"
                            clip-rule="evenodd"
                        />
                    </svg>
                </div>
                <input
                    :value="searchQuery"
                    type="text"
                    :placeholder="`Search nodes (${nodeCount})...`"
                    class="block w-full sm:w-64 pl-9 pr-10 py-2.5 sm:py-3 bg-white/70 dark:bg-zinc-900/70 backdrop-blur-xl border border-gray-200/50 dark:border-zinc-800/50 rounded-2xl text-xs font-semibold focus:outline-none focus:ring-2 focus:ring-blue-500/50 sm:focus:w-80 md:max-lg:focus:w-72 lg:focus:w-80 transition-all dark:text-zinc-100 shadow-sm"
                    @input="$emit('update:searchQuery', $event.target.value)"
                />
                <button
                    v-if="searchQuery"
                    type="button"
                    class="absolute inset-y-0 right-0 pr-3 flex items-center text-gray-400 hover:text-gray-600 dark:hover:text-zinc-200 transition-colors"
                    @click="$emit('update:searchQuery', '')"
                >
                    <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 20 20" fill="currentColor" class="w-4 h-4">
                        <path
                            d="M6.28 5.22a.75.75 0 0 0-1.06 1.06L8.94 10l-3.72 3.72a.75.75 0 1 0 1.06 1.06L10 11.06l3.72 3.72a.75.75 0 1 0 1.06-1.06L11.06 10l3.72-3.72a.75.75 0 0 0-1.06-1.06L10 8.94 6.28 5.22Z"
                        />
                    </svg>
                </button>
            </div>
        </div>
    </div>
</template>

<script>
import Toggle from "../../forms/Toggle.vue";

export default {
    name: "NetworkVisualiserToolbar",
    components: { Toggle },
    props: {
        isShowingControls: { type: Boolean, default: true },
        isUpdating: { type: Boolean, default: false },
        isLoading: { type: Boolean, default: false },
        autoReload: { type: Boolean, default: false },
        enablePhysics: { type: Boolean, default: true },
        hopFilterSlider: { type: Number, default: 0 },
        hopSliderMax: { type: Number, default: 1 },
        nodeCount: { type: Number, default: 0 },
        edgeCount: { type: Number, default: 0 },
        onlineInterfaceCount: { type: Number, default: 0 },
        offlineInterfaceCount: { type: Number, default: 0 },
        searchQuery: { type: String, default: "" },
    },
    emits: [
        "update:isShowingControls",
        "update:autoReload",
        "update:enablePhysics",
        "update:hopFilterSlider",
        "update:searchQuery",
        "manual-update",
    ],
};
</script>
