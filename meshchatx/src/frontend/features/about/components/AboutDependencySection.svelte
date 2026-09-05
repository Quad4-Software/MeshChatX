<!-- SPDX-License-Identifier: 0BSD -->

<script lang="ts">
    import logoUrl from "../../../assets/images/logo.png";
    import { t } from "../../../js/i18n.js";
    import MaterialDesignIcon from "../../../ui/svelte/MaterialDesignIcon.svelte";
    import { formatDisplayVersion } from "../lib/aboutFormat.js";
    import type { AppInfo } from "../lib/types.js";

    interface Props {
        appInfo?: AppInfo | null;
        electronVersion?: string | null;
        chromeVersion?: string | null;
        nodeVersion?: string | null;
    }

    let { appInfo = null, electronVersion = null, chromeVersion = null, nodeVersion = null }: Props = $props();

    const aboutDisplayVersion = $derived(formatDisplayVersion(appInfo));
    const backendDeps = $derived(
        appInfo?.dependencies && typeof appInfo.dependencies === "object" ? Object.entries(appInfo.dependencies) : []
    );
</script>

{#if appInfo}
    <div class="w-full border-b border-gray-200/60 dark:border-zinc-800/60 py-6 sm:py-8 last:border-0">
        <div class="text-xs font-black text-blue-500 uppercase tracking-[0.2em] mb-8 flex items-center gap-2">
            <MaterialDesignIcon iconName="link-variant" class="size-3.5" />
            {t("about.dependency_chain")}
        </div>
        <div class="grid grid-cols-1 lg:grid-cols-2 gap-8 lg:gap-12 relative min-w-0">
            <!-- Left: Dependency chain visual -->
            <div class="flex flex-col space-y-8 min-w-0">
                <div class="flex items-center gap-5">
                    <div
                        class="w-12 h-12 rounded-2xl bg-blue-500/10 flex items-center justify-center border border-blue-500/20 shadow-xs"
                    >
                        <img src={logoUrl} class="w-7 h-7 object-contain" alt="" />
                    </div>
                    <div>
                        <div class="text-sm font-black text-sem-fg">
                            {t("about.app_name")}
                        </div>
                        <div class="text-xs font-mono font-bold text-gray-400">
                            v{aboutDisplayVersion}
                        </div>
                    </div>
                </div>

                <div class="flex items-center gap-5 pl-5 border-l-2 border-zinc-100 dark:border-zinc-800 ml-6 relative">
                    <div
                        class="absolute left-[-2px] top-0 bottom-0 w-[2px] bg-linear-to-b from-blue-500 to-emerald-500"
                    ></div>
                    <div
                        class="w-12 h-12 rounded-2xl bg-emerald-500/10 flex items-center justify-center border border-emerald-500/20 text-emerald-600 shadow-xs"
                    >
                        <MaterialDesignIcon iconName="robot" class="size-6" />
                    </div>
                    <div>
                        <div class="text-sm font-black text-sem-fg leading-tight">LXMFy</div>
                        <div class="text-xs font-mono font-bold text-gray-400 mt-1">
                            v{(appInfo.dependencies && appInfo.dependencies.lxmfy) || "unknown"}
                        </div>
                    </div>
                </div>

                <div class="flex items-center gap-5 pl-5 border-l-2 border-zinc-100 dark:border-zinc-800 ml-6 relative">
                    <div
                        class="absolute left-[-2px] top-0 bottom-0 w-[2px] bg-linear-to-b from-emerald-500 to-purple-500"
                    ></div>
                    <div
                        class="w-12 h-12 rounded-2xl bg-purple-500/10 flex items-center justify-center border border-purple-500/20 text-purple-600 shadow-xs"
                    >
                        <MaterialDesignIcon iconName="message-text" class="size-6" />
                    </div>
                    <div>
                        <div class="text-sm font-black text-sem-fg leading-tight">LXMF</div>
                        <div class="text-xs font-mono font-bold text-gray-400 mt-1">
                            v{appInfo.lxmf_version}
                        </div>
                    </div>
                </div>

                {#if appInfo.lxst_version}
                    <div
                        class="flex items-center gap-5 pl-5 border-l-2 border-zinc-100 dark:border-zinc-800 ml-6 relative"
                    >
                        <div
                            class="absolute left-[-2px] top-0 bottom-0 w-[2px] bg-linear-to-b from-purple-500 to-rose-500"
                        ></div>
                        <div
                            class="w-12 h-12 rounded-2xl bg-rose-500/10 flex items-center justify-center border border-rose-500/20 text-rose-600 shadow-xs"
                        >
                            <MaterialDesignIcon iconName="phone" class="size-6" />
                        </div>
                        <div>
                            <div class="text-sm font-black text-sem-fg leading-tight">LXST</div>
                            <div class="text-xs font-mono font-bold text-gray-400 mt-1">
                                v{appInfo.lxst_version}
                            </div>
                        </div>
                    </div>
                {/if}

                <div class="flex items-center gap-5 pl-5 border-l-2 border-zinc-100 dark:border-zinc-800 ml-6 relative">
                    <div
                        class="absolute left-[-2px] top-0 bottom-0 w-[2px] bg-linear-to-b from-rose-500 to-indigo-500"
                    ></div>
                    <div
                        class="w-12 h-12 rounded-2xl bg-indigo-500/10 flex items-center justify-center border border-indigo-500/20 text-indigo-600 shadow-xs"
                    >
                        <MaterialDesignIcon iconName="lan" class="size-6" />
                    </div>
                    <div>
                        <div class="text-sm font-black text-sem-fg leading-tight">RNS</div>
                        <div class="flex flex-wrap items-center gap-2 mt-1 min-w-0">
                            <div class="text-xs font-mono font-bold text-gray-400 shrink-0">
                                v{appInfo.rns_version}
                            </div>
                            <div
                                class="text-[8px] font-black uppercase tracking-wider px-1.5 py-0.5 rounded-xs border max-w-full break-words {appInfo.is_connected_to_shared_instance
                                    ? 'bg-blue-500/10 text-blue-500 border-blue-500/20'
                                    : 'bg-emerald-500/10 text-emerald-500 border-emerald-500/20'}"
                            >
                                {appInfo.is_connected_to_shared_instance
                                    ? t("about.shared_instance_badge", {
                                          address: appInfo.shared_instance_address || t("about.path_unknown"),
                                      })
                                    : t("about.main_instance_badge")}
                            </div>
                        </div>
                    </div>
                </div>
            </div>

            <!-- Right: Core runtime & backend stack -->
            <div class="space-y-8 min-w-0">
                {#if electronVersion || chromeVersion || nodeVersion}
                    <div
                        class="py-4 sm:p-5 border-t border-gray-200/60 dark:border-zinc-800/80 sm:border sm:rounded-2xl sm:bg-black/2 dark:sm:bg-white/2 min-w-0"
                    >
                        <div class="text-[10px] font-black text-black dark:text-white uppercase tracking-[0.2em] mb-4">
                            {t("about.core_runtime")}
                        </div>
                        <div class="grid grid-cols-2 gap-x-6 gap-y-4">
                            {#if electronVersion}
                                <div class="flex flex-col">
                                    <span
                                        class="text-[9px] font-black text-black dark:text-white uppercase leading-none"
                                    >
                                        {t("about.electron_runtime")}
                                    </span>
                                    <span
                                        class="text-[11px] font-mono font-bold mt-1.5 text-black dark:text-white tracking-tight"
                                    >
                                        v{electronVersion}
                                    </span>
                                </div>
                            {/if}
                            {#if chromeVersion}
                                <div class="flex flex-col">
                                    <span
                                        class="text-[9px] font-black text-black dark:text-white uppercase leading-none"
                                    >
                                        {t("about.chrome_runtime")}
                                    </span>
                                    <span
                                        class="text-[11px] font-mono font-bold mt-1.5 text-black dark:text-white tracking-tight"
                                    >
                                        v{chromeVersion}
                                    </span>
                                </div>
                            {/if}
                            {#if nodeVersion}
                                <div class="flex flex-col">
                                    <span
                                        class="text-[9px] font-black text-black dark:text-white uppercase leading-none"
                                    >
                                        {t("about.nodejs_runtime")}
                                    </span>
                                    <span
                                        class="text-[11px] font-mono font-bold mt-1.5 text-black dark:text-white tracking-tight"
                                    >
                                        v{nodeVersion}
                                    </span>
                                </div>
                            {/if}
                        </div>
                    </div>
                {/if}

                {#if backendDeps.length}
                    <div class="pt-2">
                        <div class="text-[10px] font-black text-black dark:text-white uppercase tracking-[0.2em] mb-4">
                            {t("about.backend_stack")}
                        </div>
                        <div class="grid grid-cols-2 sm:grid-cols-3 gap-x-6 gap-y-4">
                            {#each backendDeps as [name, version] (name)}
                                <div class="flex flex-col">
                                    <span
                                        class="text-[9px] font-black text-black dark:text-white uppercase truncate leading-none"
                                    >
                                        {name.replace("_", " ")}
                                    </span>
                                    <span
                                        class="text-[10px] font-mono font-bold mt-1.5 text-black dark:text-white tracking-tight"
                                    >
                                        v{version}
                                    </span>
                                </div>
                            {/each}
                        </div>
                    </div>
                {/if}
            </div>
        </div>
    </div>
{/if}
