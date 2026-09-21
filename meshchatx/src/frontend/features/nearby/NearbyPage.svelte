<!-- SPDX-License-Identifier: 0BSD -->

<script lang="ts">
    import { onMount, tick } from "svelte";
    import MaterialDesignIcon from "../../ui/svelte/MaterialDesignIcon.svelte";
    import ToolsPageHeader from "../../ui/svelte/ToolsPageHeader.svelte";
    import AndroidBridge from "../../js/rnode/AndroidBridge.js";
    import { apiPath } from "../../js/constants.js";
    import { t } from "../../js/i18n.js";
    import {
        attachStreamToVideo,
        decodeQrFromVideo,
        describeCameraError as describeQrCameraError,
        isCameraSupported,
        startCameraStream,
    } from "../../js/qrScannerUtils.js";
    import {
        createNearbyState,
        createNearbyTimers,
        capabilityBadges,
        satelliteEnabled,
        canUseHotspot,
        canUseP2p,
        canUseAware,
        canUseNfc,
        awareActive,
        nfcSharePayload,
        nfcPayloadJoinable,
        joinConnected,
        refreshAll,
        loadCapabilities,
        requestNearbyPermission,
        startHotspot,
        stopHotspot,
        rotateHotspot,
        copyValue,
        onQrScanned,
        confirmJoin,
        joinManual,
        leaveNetwork,
        stopJoinPolling,
    } from "./lib/nearbyActions.js";
    import {
        loadP2pStatus,
        loadAwareStatus,
        loadNfcStatus,
        startP2p,
        stopP2p,
        startAware,
        stopAware,
        stopAwarePolling,
        startNfcShare,
        stopNfcShare,
        startNfcRead,
        stopNfcRead,
        stopNfcPolling,
        joinFromNfc,
    } from "./lib/nearbyTransports.js";

    let page = $state(createNearbyState());
    const timers = createNearbyTimers();
    const androidBridge = new AndroidBridge();
    const cameraSupported = isCameraSupported();

    let scannerVideoEl = $state<HTMLVideoElement | null>(null);
    let scannerStream: MediaStream | null = null;
    let scannerAnimationFrame: number | null = null;

    const badges = $derived(capabilityBadges(page));
    const satelliteActive = $derived(satelliteEnabled(page));
    const hotspotUsable = $derived(canUseHotspot(page));
    const p2pUsable = $derived(canUseP2p(page));
    const awareUsable = $derived(canUseAware(page));
    const nfcUsable = $derived(canUseNfc(page));
    const awareOn = $derived(awareActive(page));
    const nfcPayload = $derived(nfcSharePayload(page));
    const nfcJoinable = $derived(nfcPayloadJoinable(page));
    const joinOn = $derived(joinConnected(page));

    function onAndroidPermissionEvent(event: Event) {
        const detail = (event as CustomEvent)?.detail;
        if (detail?.group === "nearby_wifi") {
            page.nearbyWifiGranted = Boolean(detail.granted);
            void loadCapabilities(page, androidBridge);
        }
    }

    onMount(() => {
        window.addEventListener("meshchatx-android-permission", onAndroidPermissionEvent);
        void (async () => {
            await refreshAll(page, androidBridge);
            await Promise.all([loadP2pStatus(page), loadAwareStatus(page), loadNfcStatus(page)]);
        })();
        return () => {
            stopScanner();
            stopJoinPolling(timers);
            stopAwarePolling(timers);
            stopNfcPolling(timers);
            window.removeEventListener("meshchatx-android-permission", onAndroidPermissionEvent);
            // NFC emits only while this screen is open.
            if (page.nfcSharing) {
                void window.api.post(apiPath("/locallink/nfc/share"), { payload: null }).catch(() => {});
            }
            if (page.nfcReading) {
                void window.api.post(apiPath("/locallink/nfc/read/stop"), {}).catch(() => {});
            }
        };
    });

    async function openScannerDialog() {
        page.isScannerDialogOpen = true;
        page.scannerError = null;
        await tick();
        await startScanner();
    }

    async function startScanner() {
        if (!cameraSupported) {
            page.scannerError = t("tools.nearby.camera_not_supported");
            return;
        }
        try {
            const stream = await startCameraStream();
            if (!stream.getVideoTracks().length) {
                page.scannerError = t("tools.nearby.camera_not_found");
                stream.getTracks().forEach((track) => track.stop());
                return;
            }
            scannerStream = stream;
            if (!(await attachStreamToVideo(stream, scannerVideoEl))) {
                return;
            }
            detectQrLoop();
        } catch (e) {
            page.scannerError = describeQrCameraError(e, {
                permissionDenied: t("tools.nearby.camera_denied"),
                notFound: t("tools.nearby.camera_not_found"),
                failed: t("tools.nearby.camera_failed"),
            });
        }
    }

    function detectQrLoop() {
        if (!page.isScannerDialogOpen) return;
        decodeQrFromVideo(scannerVideoEl)
            .then((qr) => {
                if (!page.isScannerDialogOpen) return;
                if (qr) {
                    handleQrDecoded(qr);
                    return;
                }
                scannerAnimationFrame = requestAnimationFrame(() => detectQrLoop());
            })
            .catch(() => {
                if (page.isScannerDialogOpen) {
                    scannerAnimationFrame = requestAnimationFrame(() => detectQrLoop());
                }
            });
    }

    function handleQrDecoded(raw: string) {
        // A rejected payload keeps the scan loop alive for another try.
        if (onQrScanned(page, raw)) {
            closeScannerDialog();
        } else {
            scannerAnimationFrame = requestAnimationFrame(() => detectQrLoop());
        }
    }

    function stopScanner() {
        if (scannerAnimationFrame) {
            cancelAnimationFrame(scannerAnimationFrame);
            scannerAnimationFrame = null;
        }
        if (scannerStream) {
            scannerStream.getTracks().forEach((track) => track.stop());
            scannerStream = null;
        }
    }

    function closeScannerDialog() {
        page.isScannerDialogOpen = false;
        stopScanner();
    }
</script>

<div class="flex flex-col flex-1 overflow-hidden min-w-0 bg-sem-canvas">
    <ToolsPageHeader
        icon="access-point-network"
        title={t("tools.nearby.title")}
        description={t("tools.nearby.description")}
        accent="teal"
    >
        <button
            type="button"
            class="secondary-chip py-1! px-3!"
            disabled={page.loading}
            onclick={() => void refreshAll(page, androidBridge)}
        >
            <MaterialDesignIcon iconName="refresh" class="w-3.5 h-3.5" />
            <span class="hidden sm:inline">{t("tools.nearby.refresh")}</span>
        </button>
    </ToolsPageHeader>

    <div class="flex-1 min-h-0 overflow-y-auto w-full px-3 sm:px-5 py-4 pb-[max(1rem,env(safe-area-inset-bottom))]">
        <div class="space-y-4 w-full min-w-0 max-w-3xl mx-auto">
            <!-- capability banner -->
            <div class="rounded-xl border border-sem-border bg-sem-surface p-4">
                <div class="flex flex-wrap items-center gap-2">
                    <span class="text-sm font-medium text-sem-fg">{t("tools.nearby.capabilities")}</span>
                    {#each badges as cap (cap.key)}
                        <span
                            class="inline-flex items-center gap-1 rounded-full px-2.5 py-0.5 text-xs font-medium {cap.ok
                                ? 'bg-emerald-100 text-emerald-700 dark:bg-emerald-900/30 dark:text-emerald-300'
                                : 'bg-zinc-100 text-sem-fg-muted dark:bg-zinc-800'}"
                        >
                            <MaterialDesignIcon iconName={cap.ok ? "check" : "minus"} class="w-3 h-3" />
                            {cap.label}
                        </span>
                    {/each}
                    {#if satelliteActive}
                        <span
                            class="inline-flex items-center gap-1 rounded-full px-2.5 py-0.5 text-xs font-medium bg-sky-100 text-sky-700 dark:bg-sky-900/30 dark:text-sky-300"
                        >
                            <MaterialDesignIcon iconName="satellite-variant" class="w-3 h-3" />
                            {t("tools.nearby.satellite_active")}
                        </span>
                    {/if}
                </div>
            </div>

            <!-- unsupported (desktop) notice -->
            {#if !page.loading && page.capabilities && page.capabilities.supported === false}
                <div
                    class="rounded-xl border border-amber-500/30 bg-amber-50 dark:bg-amber-900/10 p-4 text-sm text-sem-fg"
                >
                    <div class="flex items-start gap-3">
                        <MaterialDesignIcon iconName="information-outline" class="w-5 h-5 text-amber-500 shrink-0" />
                        <p>{t("tools.nearby.android_only")}</p>
                    </div>
                </div>
            {/if}

            <!-- permission banner -->
            {#if page.capabilities && page.capabilities.supported && !page.nearbyWifiGranted}
                <div class="rounded-xl border border-amber-500/30 bg-amber-50 dark:bg-amber-900/10 p-4">
                    <div class="flex flex-wrap items-center gap-3">
                        <MaterialDesignIcon iconName="shield-alert-outline" class="w-5 h-5 text-amber-500" />
                        <p class="flex-1 text-sm text-sem-fg min-w-0">{t("tools.nearby.permission_hint")}</p>
                        <button
                            type="button"
                            class="primary-chip py-1! px-3!"
                            disabled={page.requestingPermission}
                            onclick={() => void requestNearbyPermission(page, androidBridge)}
                        >
                            {t("tools.nearby.grant_permission")}
                        </button>
                    </div>
                </div>
            {/if}

            <!-- host card -->
            <div class="rounded-xl border border-sem-border bg-sem-surface p-4 sm:p-5 space-y-4">
                <div class="flex items-center gap-3">
                    <div class="p-2 rounded-lg bg-teal-100 dark:bg-teal-900/30">
                        <MaterialDesignIcon iconName="access-point" class="w-5 h-5 text-teal-600 dark:text-teal-400" />
                    </div>
                    <div>
                        <h2 class="text-base font-bold text-sem-fg">{t("tools.nearby.host_title")}</h2>
                        <p class="text-sm text-sem-fg-muted">{t("tools.nearby.host_description")}</p>
                    </div>
                </div>

                {#if !page.hotspotActive}
                    <div>
                        <button
                            type="button"
                            class="primary-chip py-1.5! px-4!"
                            disabled={page.startingHotspot || !hotspotUsable}
                            onclick={() => void startHotspot(page)}
                        >
                            <MaterialDesignIcon iconName="access-point-plus" class="w-4 h-4" />
                            {page.startingHotspot ? t("tools.nearby.starting") : t("tools.nearby.start_hotspot")}
                        </button>
                    </div>
                {:else}
                    <div class="space-y-4">
                        <div class="flex flex-col sm:flex-row gap-4">
                            {#if page.wifiQrDataUrl}
                                <div class="shrink-0 self-center sm:self-start">
                                    <img
                                        src={page.wifiQrDataUrl}
                                        alt={t("tools.nearby.qr_alt")}
                                        class="w-44 h-44 rounded-lg border border-sem-border bg-white p-2"
                                    />
                                </div>
                            {/if}
                            <div class="space-y-2 min-w-0 flex-1">
                                <div class="text-sm">
                                    <span class="text-sem-fg-muted">{t("tools.nearby.ssid")}:</span>
                                    <span class="font-mono font-medium text-sem-fg break-all">{page.hotspotSsid}</span>
                                    <button
                                        type="button"
                                        class="ml-1 text-sem-fg-muted hover:text-sem-fg align-middle"
                                        title={t("common.copy")}
                                        onclick={() => void copyValue(page.hotspotSsid)}
                                    >
                                        <MaterialDesignIcon iconName="content-copy" class="w-3.5 h-3.5" />
                                    </button>
                                </div>
                                <div class="text-sm">
                                    <span class="text-sem-fg-muted">{t("tools.nearby.passphrase")}:</span>
                                    <span class="font-mono font-medium text-sem-fg break-all"
                                        >{page.hotspotPassphrase}</span
                                    >
                                    <button
                                        type="button"
                                        class="ml-1 text-sem-fg-muted hover:text-sem-fg align-middle"
                                        title={t("common.copy")}
                                        onclick={() => void copyValue(page.hotspotPassphrase)}
                                    >
                                        <MaterialDesignIcon iconName="content-copy" class="w-3.5 h-3.5" />
                                    </button>
                                </div>
                                <p class="text-xs text-sem-fg-muted">{t("tools.nearby.qr_hint")}</p>
                            </div>
                        </div>
                        <div class="flex flex-wrap gap-2">
                            <button
                                type="button"
                                class="secondary-chip py-1! px-3!"
                                disabled={page.startingHotspot}
                                onclick={() => void rotateHotspot(page)}
                            >
                                <MaterialDesignIcon iconName="refresh" class="w-3.5 h-3.5" />
                                {t("tools.nearby.rotate")}
                            </button>
                            <button
                                type="button"
                                class="secondary-chip py-1! px-3! text-red-500! hover:bg-red-50! dark:hover:bg-red-900/20!"
                                onclick={() => void stopHotspot(page)}
                            >
                                <MaterialDesignIcon iconName="access-point-remove" class="w-3.5 h-3.5" />
                                {t("tools.nearby.stop_hotspot")}
                            </button>
                        </div>
                    </div>
                {/if}
            </div>

            <!-- join card -->
            <div class="rounded-xl border border-sem-border bg-sem-surface p-4 sm:p-5 space-y-4">
                <div class="flex items-center gap-3">
                    <div class="p-2 rounded-lg bg-sky-100 dark:bg-sky-900/30">
                        <MaterialDesignIcon iconName="wifi-plus" class="w-5 h-5 text-sky-600 dark:text-sky-400" />
                    </div>
                    <div>
                        <h2 class="text-base font-bold text-sem-fg">{t("tools.nearby.join_title")}</h2>
                        <p class="text-sm text-sem-fg-muted">{t("tools.nearby.join_description")}</p>
                    </div>
                </div>

                {#if joinOn}
                    <div
                        class="rounded-lg border border-emerald-500/30 bg-emerald-50 dark:bg-emerald-900/10 p-3 flex flex-wrap items-center gap-3"
                    >
                        <MaterialDesignIcon iconName="wifi-check" class="w-5 h-5 text-emerald-500" />
                        <p class="flex-1 text-sm text-sem-fg min-w-0">{t("tools.nearby.join_connected")}</p>
                        <button
                            type="button"
                            class="secondary-chip py-1! px-3! text-red-500! hover:bg-red-50! dark:hover:bg-red-900/20!"
                            onclick={() => void leaveNetwork(page, timers, androidBridge)}
                        >
                            {t("tools.nearby.leave")}
                        </button>
                    </div>
                    <p class="text-xs text-sem-fg-muted -mt-2">
                        {t("tools.nearby.join_internet_note")}
                    </p>
                {/if}

                <div class="flex flex-wrap gap-2">
                    <button
                        type="button"
                        class="primary-chip py-1.5! px-4!"
                        disabled={!cameraSupported || page.joining}
                        onclick={() => void openScannerDialog()}
                    >
                        <MaterialDesignIcon iconName="qrcode-scan" class="w-4 h-4" />
                        {t("tools.nearby.scan_qr")}
                    </button>
                </div>
                {#if page.joinStatus === "requested" && !joinOn}
                    <p class="text-xs text-sem-fg-muted">
                        {t("tools.nearby.join_waiting")}
                    </p>
                {/if}

                <details class="group">
                    <summary class="text-sm text-sem-fg-muted cursor-pointer select-none hover:text-sem-fg">
                        {t("tools.nearby.manual_entry")}
                    </summary>
                    <div class="mt-3 space-y-3">
                        <input
                            bind:value={page.joinSsid}
                            type="text"
                            class="w-full rounded-lg border border-sem-border bg-sem-canvas px-3 py-2 text-sm text-sem-fg"
                            placeholder={t("tools.nearby.ssid")}
                            maxlength="32"
                        />
                        <input
                            bind:value={page.joinPassphrase}
                            type="password"
                            class="w-full rounded-lg border border-sem-border bg-sem-canvas px-3 py-2 text-sm text-sem-fg"
                            placeholder={t("tools.nearby.passphrase")}
                            maxlength="63"
                        />
                        <button
                            type="button"
                            class="primary-chip py-1! px-3!"
                            disabled={!page.joinSsid || page.joining}
                            onclick={() => void joinManual(page)}
                        >
                            {page.joining ? t("tools.nearby.joining") : t("tools.nearby.join")}
                        </button>
                    </div>
                </details>
            </div>

            <!-- wifi direct card -->
            <div class="rounded-xl border border-sem-border bg-sem-surface p-4 sm:p-5 space-y-4">
                <div class="flex items-center gap-3">
                    <div class="p-2 rounded-lg bg-violet-100 dark:bg-violet-900/30">
                        <MaterialDesignIcon
                            iconName="wifi-tethering"
                            class="w-5 h-5 text-violet-600 dark:text-violet-400"
                        />
                    </div>
                    <div>
                        <h2 class="text-base font-bold text-sem-fg">{t("tools.nearby.p2p_title")}</h2>
                        <p class="text-sm text-sem-fg-muted">{t("tools.nearby.p2p_description")}</p>
                    </div>
                </div>

                {#if !page.p2pActive}
                    <div>
                        <button
                            type="button"
                            class="primary-chip py-1.5! px-4!"
                            disabled={page.startingP2p || !p2pUsable}
                            onclick={() => void startP2p(page)}
                        >
                            <MaterialDesignIcon iconName="wifi-tethering" class="w-4 h-4" />
                            {page.startingP2p ? t("tools.nearby.starting") : t("tools.nearby.start_group")}
                        </button>
                    </div>
                {:else}
                    <div class="space-y-4">
                        <div class="flex flex-col sm:flex-row gap-4">
                            {#if page.p2pQrDataUrl}
                                <div class="shrink-0 self-center sm:self-start">
                                    <img
                                        src={page.p2pQrDataUrl}
                                        alt={t("tools.nearby.qr_alt")}
                                        class="w-44 h-44 rounded-lg border border-sem-border bg-white p-2"
                                    />
                                </div>
                            {/if}
                            <div class="space-y-2 min-w-0 flex-1">
                                <div class="text-sm">
                                    <span class="text-sem-fg-muted">{t("tools.nearby.ssid")}:</span>
                                    <span class="font-mono font-medium text-sem-fg break-all">{page.p2pSsid}</span>
                                    <button
                                        type="button"
                                        class="ml-1 text-sem-fg-muted hover:text-sem-fg align-middle"
                                        title={t("common.copy")}
                                        onclick={() => void copyValue(page.p2pSsid)}
                                    >
                                        <MaterialDesignIcon iconName="content-copy" class="w-3.5 h-3.5" />
                                    </button>
                                </div>
                                <div class="text-sm">
                                    <span class="text-sem-fg-muted">{t("tools.nearby.passphrase")}:</span>
                                    <span class="font-mono font-medium text-sem-fg break-all">{page.p2pPassphrase}</span
                                    >
                                    <button
                                        type="button"
                                        class="ml-1 text-sem-fg-muted hover:text-sem-fg align-middle"
                                        title={t("common.copy")}
                                        onclick={() => void copyValue(page.p2pPassphrase)}
                                    >
                                        <MaterialDesignIcon iconName="content-copy" class="w-3.5 h-3.5" />
                                    </button>
                                </div>
                                <p class="text-xs text-sem-fg-muted">{t("tools.nearby.qr_hint")}</p>
                            </div>
                        </div>
                        <button
                            type="button"
                            class="secondary-chip py-1! px-3! text-red-500! hover:bg-red-50! dark:hover:bg-red-900/20!"
                            onclick={() => void stopP2p(page)}
                        >
                            <MaterialDesignIcon iconName="wifi-off" class="w-3.5 h-3.5" />
                            {t("tools.nearby.stop_group")}
                        </button>
                    </div>
                {/if}
            </div>

            <!-- wifi aware card -->
            <div class="rounded-xl border border-sem-border bg-sem-surface p-4 sm:p-5 space-y-4">
                <div class="flex items-center gap-3">
                    <div class="p-2 rounded-lg bg-emerald-100 dark:bg-emerald-900/30">
                        <MaterialDesignIcon iconName="radar" class="w-5 h-5 text-emerald-600 dark:text-emerald-400" />
                    </div>
                    <div>
                        <h2 class="text-base font-bold text-sem-fg">{t("tools.nearby.aware_title")}</h2>
                        <p class="text-sm text-sem-fg-muted">{t("tools.nearby.aware_description")}</p>
                    </div>
                </div>

                {#if !awareOn}
                    <div class="space-y-3">
                        <div class="flex flex-wrap gap-3 text-sm text-sem-fg">
                            <label class="inline-flex items-center gap-2 cursor-pointer">
                                <input
                                    bind:group={page.awareMode}
                                    type="radio"
                                    value="subscribe"
                                    class="accent-sem-accent"
                                />
                                {t("tools.nearby.aware_subscribe")}
                            </label>
                            <label class="inline-flex items-center gap-2 cursor-pointer">
                                <input
                                    bind:group={page.awareMode}
                                    type="radio"
                                    value="publish"
                                    class="accent-sem-accent"
                                />
                                {t("tools.nearby.aware_publish")}
                            </label>
                        </div>
                        <button
                            type="button"
                            class="primary-chip py-1.5! px-4!"
                            disabled={page.startingAware || !awareUsable}
                            onclick={() => void startAware(page, timers)}
                        >
                            <MaterialDesignIcon iconName="radar" class="w-4 h-4" />
                            {page.startingAware ? t("tools.nearby.starting") : t("tools.nearby.aware_start")}
                        </button>
                        <p class="text-xs text-sem-fg-muted">{t("tools.nearby.aware_hint")}</p>
                    </div>
                {:else}
                    <div class="space-y-3">
                        <div class="flex flex-wrap items-center gap-2 text-sm text-sem-fg">
                            <span
                                class="inline-flex items-center gap-1.5 rounded-full bg-emerald-100 dark:bg-emerald-900/30 px-2.5 py-0.5 text-xs font-medium text-emerald-700 dark:text-emerald-300"
                            >
                                <MaterialDesignIcon iconName="radar" class="w-3 h-3" />
                                {page.awareStatus.role}
                            </span>
                            <span class="text-sem-fg-muted">
                                {t("tools.nearby.aware_peers", {
                                    peers: page.awareStatus.peers,
                                    links: page.awareStatus.links,
                                })}
                            </span>
                        </div>
                        <button
                            type="button"
                            class="secondary-chip py-1! px-3! text-red-500! hover:bg-red-50! dark:hover:bg-red-900/20!"
                            onclick={() => void stopAware(page, timers)}
                        >
                            <MaterialDesignIcon iconName="stop" class="w-3.5 h-3.5" />
                            {t("tools.nearby.aware_stop")}
                        </button>
                    </div>
                {/if}
            </div>

            <!-- nfc card -->
            <div class="rounded-xl border border-sem-border bg-sem-surface p-4 sm:p-5 space-y-4">
                <div class="flex items-center gap-3">
                    <div class="p-2 rounded-lg bg-orange-100 dark:bg-orange-900/30">
                        <MaterialDesignIcon
                            iconName="nfc-variant"
                            class="w-5 h-5 text-orange-600 dark:text-orange-400"
                        />
                    </div>
                    <div>
                        <h2 class="text-base font-bold text-sem-fg">{t("tools.nearby.nfc_title")}</h2>
                        <p class="text-sm text-sem-fg-muted">{t("tools.nearby.nfc_description")}</p>
                    </div>
                </div>

                <div class="space-y-3">
                    <div class="flex flex-wrap items-center gap-3">
                        {#if !page.nfcSharing}
                            <button
                                type="button"
                                class="secondary-chip py-1! px-3!"
                                disabled={!nfcPayload || !nfcUsable}
                                onclick={() => void startNfcShare(page)}
                            >
                                <MaterialDesignIcon iconName="nfc-variant" class="w-3.5 h-3.5" />
                                {t("tools.nearby.nfc_share_credentials")}
                            </button>
                        {:else}
                            <button
                                type="button"
                                class="secondary-chip py-1! px-3! text-red-500! hover:bg-red-50! dark:hover:bg-red-900/20!"
                                onclick={() => void stopNfcShare(page)}
                            >
                                <MaterialDesignIcon iconName="nfc-variant-off" class="w-3.5 h-3.5" />
                                {t("tools.nearby.nfc_share_stop")}
                            </button>
                        {/if}
                        {#if !page.nfcReading}
                            <button
                                type="button"
                                class="secondary-chip py-1! px-3!"
                                disabled={!nfcUsable}
                                onclick={() => void startNfcRead(page, timers)}
                            >
                                <MaterialDesignIcon iconName="cellphone-nfc" class="w-3.5 h-3.5" />
                                {t("tools.nearby.nfc_read_start")}
                            </button>
                        {:else}
                            <button
                                type="button"
                                class="secondary-chip py-1! px-3! text-red-500! hover:bg-red-50! dark:hover:bg-red-900/20!"
                                onclick={() => void stopNfcRead(page, timers)}
                            >
                                {t("tools.nearby.nfc_read_stop")}
                            </button>
                        {/if}
                    </div>
                    {#if !nfcPayload}
                        <p class="text-xs text-sem-fg-muted">
                            {t("tools.nearby.nfc_no_credentials")}
                        </p>
                    {:else if page.nfcSharing}
                        <p class="text-xs text-amber-600 dark:text-amber-400">
                            {t("tools.nearby.nfc_sharing_note")}
                        </p>
                    {/if}
                    {#if page.nfcReading}
                        <p class="text-xs text-sem-fg-muted">
                            {t("tools.nearby.nfc_reading")}
                        </p>
                    {/if}
                    {#if page.nfcLastPayload}
                        <div class="rounded-lg border border-sem-border bg-sem-canvas p-3 space-y-2">
                            <p class="text-xs font-mono text-sem-fg break-all">{page.nfcLastPayload}</p>
                            {#if nfcJoinable}
                                <button
                                    type="button"
                                    class="primary-chip py-1! px-3!"
                                    onclick={() => joinFromNfc(page)}
                                >
                                    {t("tools.nearby.nfc_join_this")}
                                </button>
                            {/if}
                        </div>
                    {/if}
                </div>
            </div>

            <!-- satellite posture hint -->
            {#if page.capabilities?.satellite?.feature}
                <div
                    class="rounded-xl border border-sem-border bg-sem-surface p-4 text-sm text-sem-fg-muted flex items-start gap-3"
                >
                    <MaterialDesignIcon iconName="satellite-variant" class="w-5 h-5 text-sem-fg-muted shrink-0" />
                    <p>{t("tools.nearby.satellite_hint")}</p>
                </div>
            {/if}

            <!-- autointerface hint -->
            {#if page.autoInterfaceHint}
                <div
                    class="rounded-xl border border-sem-border bg-sem-surface p-4 text-sm text-sem-fg-muted flex items-start gap-3"
                >
                    <MaterialDesignIcon iconName="information-outline" class="w-5 h-5 text-sem-fg-muted shrink-0" />
                    <p>
                        {t("tools.nearby.autointerface_hint")}
                        <a href="#/interfaces/add" class="text-sem-accent hover:underline">
                            {t("tools.nearby.autointerface_link")}
                        </a>
                    </p>
                </div>
            {/if}
        </div>
    </div>

    <!-- QR scanner dialog -->
    {#if page.isScannerDialogOpen}
        <div
            class="fixed inset-0 z-220 flex items-center justify-center p-4 bg-black/70 backdrop-blur-xs"
            role="presentation"
            onclick={(e) => {
                if (e.target === e.currentTarget) closeScannerDialog();
            }}
        >
            <div class="w-full max-w-xl rounded-2xl bg-sem-surface shadow-2xl overflow-hidden">
                <div class="px-5 py-4 border-b border-sem-border flex items-center justify-between">
                    <h3 class="text-lg font-bold text-sem-fg">{t("tools.nearby.scan_qr")}</h3>
                    <button
                        type="button"
                        class="text-sem-fg-muted hover:text-sem-fg"
                        aria-label={t("common.close")}
                        onclick={closeScannerDialog}
                    >
                        <MaterialDesignIcon iconName="close" class="size-5" />
                    </button>
                </div>
                <div class="p-5 space-y-3">
                    <video
                        bind:this={scannerVideoEl}
                        class="w-full rounded-xl bg-black max-h-[60vh]"
                        autoplay
                        playsinline
                        muted
                    ></video>
                    <div class="text-sm text-sem-fg-muted">
                        {page.scannerError || t("tools.nearby.scanner_hint")}
                    </div>
                </div>
            </div>
        </div>
    {/if}

    <!-- join confirm dialog -->
    {#if page.pendingJoin}
        <div
            class="fixed inset-0 z-230 flex items-center justify-center p-4 bg-black/70 backdrop-blur-xs"
            role="presentation"
            onclick={(e) => {
                if (e.target === e.currentTarget) page.pendingJoin = null;
            }}
        >
            <div class="w-full max-w-md rounded-2xl bg-sem-surface shadow-2xl overflow-hidden">
                <div class="px-5 py-4 border-b border-sem-border">
                    <h3 class="text-lg font-bold text-sem-fg">{t("tools.nearby.confirm_join_title")}</h3>
                </div>
                <div class="p-5 space-y-4">
                    <p class="text-sm text-sem-fg">
                        {t("tools.nearby.confirm_join_body", { ssid: page.pendingJoin.ssid })}
                    </p>
                    <div class="flex justify-end gap-2">
                        <button
                            type="button"
                            class="secondary-chip py-1! px-3!"
                            onclick={() => (page.pendingJoin = null)}
                        >
                            {t("common.cancel")}
                        </button>
                        <button
                            type="button"
                            class="primary-chip py-1! px-3!"
                            disabled={page.joining}
                            onclick={() => void confirmJoin(page)}
                        >
                            {t("tools.nearby.join")}
                        </button>
                    </div>
                </div>
            </div>
        </div>
    {/if}
</div>
