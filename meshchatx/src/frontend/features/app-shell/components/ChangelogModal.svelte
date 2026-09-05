<!-- SPDX-License-Identifier: 0BSD -->

<script lang="ts">
    import { onMount, onDestroy } from "svelte";
    import { t } from "../../../js/i18n.js";
    import Modal from "../../../ui/svelte/Modal.svelte";
    import LoadingState from "../../../ui/svelte/LoadingState.svelte";
    import MaterialDesignIcon from "../../../ui/svelte/MaterialDesignIcon.svelte";
    import GlobalEmitter from "../../../js/GlobalEmitter.js";
    import logoUrl from "../../../assets/images/logo.png";

    interface Props {
        open?: boolean;
        appVersion?: string;
        isPage?: boolean;
        onclose?: () => void;
    }

    let { open = $bindable(false), appVersion = "", isPage = false, onclose }: Props = $props();

    let loading = $state(true);
    let error = $state<string | null>(null);
    let changelogHtml = $state("");
    let version = $state("");
    let dontShowAgain = $state(false);
    let dontShowEver = $state(false);
    let windowWidth = $state(typeof window !== "undefined" ? window.innerWidth : 1024);

    const currentVersion = $derived(version || appVersion);
    const dialogFullscreen = $derived(windowWidth < 768);

    function onWindowResize() {
        windowWidth = window.innerWidth;
    }

    onMount(() => {
        window.addEventListener("resize", onWindowResize, { passive: true });
        if (isPage) {
            void fetchChangelog();
        }
    });

    onDestroy(() => {
        if (typeof window !== "undefined") {
            window.removeEventListener("resize", onWindowResize);
        }
    });

    export async function show(): Promise<void> {
        open = true;
        await fetchChangelog();
    }

    export async function fetchChangelog(): Promise<void> {
        loading = true;
        error = null;
        try {
            const api = (
                window as unknown as {
                    api?: { get: (url: string) => Promise<{ data: { version: string; html: string } }> };
                }
            ).api;
            if (!api) return;
            const response = await api.get("/api/v1/app/changelog");
            version = response.data.version;

            let html = response.data.html;
            html = html.replace(/\[(\d+\.\d+\.\d+)\]/g, '<span class="version-tag">$1</span>');
            changelogHtml = html;
        } catch (e) {
            error = "Failed to load changelog.";
            console.error(e);
        } finally {
            loading = false;
        }
    }

    export async function close(): Promise<void> {
        if (!dontShowEver && !dontShowAgain) {
            try {
                const api = (window as unknown as { api?: { post: (url: string, data?: unknown) => Promise<unknown> } })
                    .api;
                if (api) {
                    await api.post("/api/v1/app/changelog/seen", {
                        version: currentVersion || "0.0.0",
                    });
                }
            } catch (e) {
                console.error("Failed to auto-mark changelog as seen:", e);
            }
        } else {
            await markAsSeen();
        }
        open = false;
        onclose?.();
        GlobalEmitter.emit("changelog-closed");
    }

    export async function markAsSeen(): Promise<void> {
        const api = (window as unknown as { api?: { post: (url: string, data?: unknown) => Promise<unknown> } }).api;
        if (!api) return;
        if (dontShowEver) {
            try {
                await api.post("/api/v1/app/changelog/seen", {
                    version: "999.999.999",
                });
            } catch (e) {
                console.error("Failed to mark changelog as seen forever:", e);
            }
        } else if (dontShowAgain) {
            try {
                await api.post("/api/v1/app/changelog/seen", {
                    version: currentVersion,
                });
            } catch (e) {
                console.error("Failed to mark changelog as seen for this version:", e);
            }
        }
    }
</script>

{#if !isPage}
    <Modal
        bind:open
        maxWidth={dialogFullscreen ? "100%" : 800}
        showClose={true}
        panelClass="border-0"
        bodyClass="min-h-0 flex-1 overflow-y-auto overscroll-contain px-4 py-6 sm:px-6 sm:py-8"
        onClose={close}
    >
        {#snippet header()}
            <div class="flex min-w-0 flex-1 items-center">
                <img src={logoUrl} class="mr-3 size-8 object-contain" alt="Logo" />
                <h2 class="text-xl font-bold tracking-tight text-sem-fg">
                    {t("app.changelog_title")}
                </h2>
                {#if version}
                    <span
                        class="ml-3 inline-flex h-5 items-center rounded-xs bg-blue-600 px-2 text-[10px] font-black uppercase tracking-tighter text-white"
                    >
                        v{version}
                    </span>
                {/if}
            </div>
        {/snippet}

        {#if loading}
            <LoadingState message="Loading changelog..." />
        {:else if error}
            <div class="flex flex-col items-center justify-center space-y-4 py-10 text-center">
                <MaterialDesignIcon iconName="alert-circle-outline" class="size-16 text-red-500" />
                <div class="text-lg font-bold text-red-500">{error}</div>
                <button type="button" class="primary-chip px-6!" onclick={fetchChangelog}>Retry</button>
            </div>
        {:else}
            <div class="changelog-content prose max-w-none dark:prose-invert text-sem-fg">
                <!-- eslint-disable-next-line svelte/no-at-html-tags -->
                {@html changelogHtml}
            </div>
        {/if}

        {#snippet footer()}
            <div class="flex w-full flex-wrap items-center gap-y-2 pb-[max(0.75rem,env(safe-area-inset-bottom))]">
                <div class="flex flex-col gap-1">
                    <label class="flex items-center gap-2 text-sm font-medium text-sem-fg-muted">
                        <input
                            bind:checked={dontShowAgain}
                            type="checkbox"
                            class="rounded-xs border-gray-300 text-blue-600 focus:ring-blue-500"
                        />
                        {t("app.do_not_show_again")}
                    </label>
                    <label class="flex items-center gap-2 text-sm font-medium text-sem-fg-muted">
                        <input
                            bind:checked={dontShowEver}
                            type="checkbox"
                            class="rounded-xs border-gray-300 text-red-600 focus:ring-red-500"
                        />
                        {t("app.do_not_show_ever")}
                    </label>
                </div>
                <div class="flex-1"></div>
                <button type="button" class="primary-chip h-10! rounded-xl! px-8!" onclick={close}>
                    {t("common.close")}
                </button>
            </div>
        {/snippet}
    </Modal>
{:else}
    <div class="flex h-full flex-col overflow-hidden bg-sem-surface">
        <div class="flex-1 overflow-y-auto px-6 py-10 md:px-12">
            <div class="mx-auto max-w-4xl">
                <div class="mb-8 flex items-center gap-4">
                    <img src={logoUrl} class="size-16 object-contain" alt="Logo" />
                    <div>
                        <h1 class="mb-1 text-4xl font-black uppercase tracking-tighter text-sem-fg">
                            {t("app.changelog_title")}
                        </h1>
                        <div class="flex items-center gap-2">
                            <span
                                class="inline-flex h-5 items-center rounded-xs bg-blue-600 px-2 text-[10px] font-black text-white"
                            >
                                v{version}
                            </span>
                            <span class="text-sm font-medium text-gray-500">Full release history</span>
                        </div>
                    </div>
                </div>

                {#if loading}
                    <div class="py-20">
                        <LoadingState />
                    </div>
                {:else if error}
                    <div class="flex flex-col items-center justify-center space-y-4 py-20 text-center">
                        <MaterialDesignIcon iconName="alert-circle-outline" class="size-16 text-red-500" />
                        <div class="text-lg font-bold text-red-500">{error}</div>
                        <button type="button" class="primary-chip px-6!" onclick={fetchChangelog}>Retry</button>
                    </div>
                {:else}
                    <div class="changelog-content prose max-w-none pb-20 dark:prose-invert">
                        <!-- eslint-disable-next-line svelte/no-at-html-tags -->
                        {@html changelogHtml}
                    </div>
                {/if}
            </div>
        </div>
    </div>
{/if}

<style>
    :global(.changelog-content) {
        line-height: 1.625;
    }

    :global(.changelog-content h1) {
        font-size: 1.875rem;
        font-weight: 900;
        margin-top: 0.5rem;
        margin-bottom: 1.5rem;
        letter-spacing: -0.025em;
        text-transform: uppercase;
        border-bottom-width: 2px;
        padding-bottom: 0.5rem;
    }

    :global(.changelog-content h2) {
        display: flex;
        align-items: center;
        gap: 0.75rem;
        font-size: 1.25rem;
        font-weight: 700;
        margin-top: 2rem;
        margin-bottom: 1rem;
        padding: 0.5rem 1rem;
        border-radius: 0.375rem;
    }

    :global(.changelog-content h2::before) {
        content: "VERSION";
        font-size: 10px;
        font-weight: 900;
        background-color: #3b82f6;
        color: white;
        padding: 0.125rem 0.375rem;
        border-radius: 2px;
        letter-spacing: -0.05em;
    }

    :global(.changelog-content h3) {
        font-size: 1.125rem;
        font-weight: 700;
        margin-top: 1.5rem;
        margin-bottom: 0.75rem;
        display: flex;
        align-items: center;
        gap: 0.5rem;
    }

    :global(.changelog-content h3::before) {
        content: "•";
        color: #3b82f6;
        font-weight: 900;
    }

    :global(.changelog-content p) {
        margin-top: 1rem;
        margin-bottom: 1rem;
        line-height: 1.625;
    }

    :global(.changelog-content ul) {
        margin-top: 1.5rem;
        margin-bottom: 1.5rem;
        list-style-type: disc;
        padding-left: 1.5rem;
    }

    :global(.changelog-content strong) {
        font-weight: 700;
    }

    :global(.changelog-content hr) {
        margin-top: 2.5rem;
        margin-bottom: 2.5rem;
    }

    :global(.changelog-content .version-tag) {
        background-color: #2563eb;
        color: white;
        padding: 0.125rem 0.5rem;
        border-radius: 2px;
        font-weight: 900;
        font-size: 0.875rem;
        letter-spacing: -0.05em;
    }
</style>
