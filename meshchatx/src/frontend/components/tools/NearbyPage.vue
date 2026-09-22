<!-- SPDX-License-Identifier: 0BSD -->

<template>
    <div class="flex flex-col flex-1 overflow-hidden min-w-0 bg-sem-canvas">
        <ToolsPageHeader
            icon="access-point-network"
            :title="$t('tools.nearby.title')"
            :description="$t('tools.nearby.description')"
            accent="teal"
        >
            <template #actions>
                <button type="button" class="secondary-chip py-1! px-3!" :disabled="loading" @click="refreshAll">
                    <MaterialDesignIcon icon-name="refresh" class="w-3.5 h-3.5" />
                    <span class="hidden sm:inline">{{ $t("tools.nearby.refresh") }}</span>
                </button>
            </template>
        </ToolsPageHeader>

        <div class="flex-1 min-h-0 overflow-y-auto w-full px-3 sm:px-5 py-4 pb-[max(1rem,env(safe-area-inset-bottom))]">
            <div class="space-y-4 w-full min-w-0 max-w-3xl mx-auto">
                <!-- capability banner -->
                <div class="rounded-xl border border-sem-border bg-sem-surface p-4">
                    <div class="flex flex-wrap items-center gap-2">
                        <span class="text-sm font-medium text-sem-fg">{{ $t("tools.nearby.capabilities") }}</span>
                        <span
                            v-for="cap in capabilityBadges"
                            :key="cap.key"
                            class="inline-flex items-center gap-1 rounded-full px-2.5 py-0.5 text-xs font-medium"
                            :class="
                                cap.ok
                                    ? 'bg-emerald-100 text-emerald-700 dark:bg-emerald-900/30 dark:text-emerald-300'
                                    : 'bg-zinc-100 text-sem-fg-muted dark:bg-zinc-800'
                            "
                        >
                            <MaterialDesignIcon :icon-name="cap.ok ? 'check' : 'minus'" class="w-3 h-3" />
                            {{ cap.label }}
                        </span>
                        <span
                            v-if="satelliteEnabled"
                            class="inline-flex items-center gap-1 rounded-full px-2.5 py-0.5 text-xs font-medium bg-sky-100 text-sky-700 dark:bg-sky-900/30 dark:text-sky-300"
                        >
                            <MaterialDesignIcon icon-name="satellite-variant" class="w-3 h-3" />
                            {{ $t("tools.nearby.satellite_active") }}
                        </span>
                    </div>
                </div>

                <!-- unsupported (desktop) notice -->
                <div
                    v-if="!loading && capabilities && capabilities.supported === false"
                    class="rounded-xl border border-amber-500/30 bg-amber-50 dark:bg-amber-900/10 p-4 text-sm text-sem-fg"
                >
                    <div class="flex items-start gap-3">
                        <MaterialDesignIcon icon-name="information-outline" class="w-5 h-5 text-amber-500 shrink-0" />
                        <p>{{ $t("tools.nearby.android_only") }}</p>
                    </div>
                </div>

                <!-- permission banner -->
                <div
                    v-if="capabilities && capabilities.supported && !nearbyWifiGranted"
                    class="rounded-xl border border-amber-500/30 bg-amber-50 dark:bg-amber-900/10 p-4"
                >
                    <div class="flex flex-wrap items-center gap-3">
                        <MaterialDesignIcon icon-name="shield-alert-outline" class="w-5 h-5 text-amber-500" />
                        <p class="flex-1 text-sm text-sem-fg min-w-0">{{ $t("tools.nearby.permission_hint") }}</p>
                        <button
                            type="button"
                            class="primary-chip py-1! px-3!"
                            :disabled="requestingPermission"
                            @click="requestNearbyPermission"
                        >
                            {{ $t("tools.nearby.grant_permission") }}
                        </button>
                    </div>
                </div>

                <!-- host card -->
                <div class="rounded-xl border border-sem-border bg-sem-surface p-4 sm:p-5 space-y-4">
                    <div class="flex items-center gap-3">
                        <div class="p-2 rounded-lg bg-teal-100 dark:bg-teal-900/30">
                            <MaterialDesignIcon
                                icon-name="access-point"
                                class="w-5 h-5 text-teal-600 dark:text-teal-400"
                            />
                        </div>
                        <div>
                            <h2 class="text-base font-bold text-sem-fg">{{ $t("tools.nearby.host_title") }}</h2>
                            <p class="text-sm text-sem-fg-muted">{{ $t("tools.nearby.host_description") }}</p>
                        </div>
                    </div>

                    <div v-if="!hotspotActive">
                        <button
                            type="button"
                            class="primary-chip py-1.5! px-4!"
                            :disabled="startingHotspot || !canUseHotspot"
                            @click="startHotspot"
                        >
                            <MaterialDesignIcon icon-name="access-point-plus" class="w-4 h-4" />
                            {{ startingHotspot ? $t("tools.nearby.starting") : $t("tools.nearby.start_hotspot") }}
                        </button>
                    </div>

                    <div v-else class="space-y-4">
                        <div class="flex flex-col sm:flex-row gap-4">
                            <div v-if="wifiQrDataUrl" class="shrink-0 self-center sm:self-start">
                                <img
                                    :src="wifiQrDataUrl"
                                    :alt="$t('tools.nearby.qr_alt')"
                                    class="w-44 h-44 rounded-lg border border-sem-border bg-white p-2"
                                />
                            </div>
                            <div class="space-y-2 min-w-0 flex-1">
                                <div class="text-sm">
                                    <span class="text-sem-fg-muted">{{ $t("tools.nearby.ssid") }}:</span>
                                    <span class="font-mono font-medium text-sem-fg break-all">{{ hotspotSsid }}</span>
                                    <button
                                        type="button"
                                        class="ml-1 text-sem-fg-muted hover:text-sem-fg align-middle"
                                        :title="$t('common.copy')"
                                        @click="copyValue(hotspotSsid)"
                                    >
                                        <MaterialDesignIcon icon-name="content-copy" class="w-3.5 h-3.5" />
                                    </button>
                                </div>
                                <div class="text-sm">
                                    <span class="text-sem-fg-muted">{{ $t("tools.nearby.passphrase") }}:</span>
                                    <span class="font-mono font-medium text-sem-fg break-all">{{
                                        hotspotPassphrase
                                    }}</span>
                                    <button
                                        type="button"
                                        class="ml-1 text-sem-fg-muted hover:text-sem-fg align-middle"
                                        :title="$t('common.copy')"
                                        @click="copyValue(hotspotPassphrase)"
                                    >
                                        <MaterialDesignIcon icon-name="content-copy" class="w-3.5 h-3.5" />
                                    </button>
                                </div>
                                <p class="text-xs text-sem-fg-muted">{{ $t("tools.nearby.qr_hint") }}</p>
                            </div>
                        </div>
                        <div class="flex flex-wrap gap-2">
                            <button
                                type="button"
                                class="secondary-chip py-1! px-3!"
                                :disabled="startingHotspot"
                                @click="rotateHotspot"
                            >
                                <MaterialDesignIcon icon-name="refresh" class="w-3.5 h-3.5" />
                                {{ $t("tools.nearby.rotate") }}
                            </button>
                            <button
                                type="button"
                                class="secondary-chip py-1! px-3! text-red-500! hover:bg-red-50! dark:hover:bg-red-900/20!"
                                @click="stopHotspot"
                            >
                                <MaterialDesignIcon icon-name="access-point-remove" class="w-3.5 h-3.5" />
                                {{ $t("tools.nearby.stop_hotspot") }}
                            </button>
                        </div>
                    </div>
                </div>

                <!-- join card -->
                <div class="rounded-xl border border-sem-border bg-sem-surface p-4 sm:p-5 space-y-4">
                    <div class="flex items-center gap-3">
                        <div class="p-2 rounded-lg bg-sky-100 dark:bg-sky-900/30">
                            <MaterialDesignIcon icon-name="wifi-plus" class="w-5 h-5 text-sky-600 dark:text-sky-400" />
                        </div>
                        <div>
                            <h2 class="text-base font-bold text-sem-fg">{{ $t("tools.nearby.join_title") }}</h2>
                            <p class="text-sm text-sem-fg-muted">{{ $t("tools.nearby.join_description") }}</p>
                        </div>
                    </div>

                    <div
                        v-if="joinConnected"
                        class="rounded-lg border border-emerald-500/30 bg-emerald-50 dark:bg-emerald-900/10 p-3 flex flex-wrap items-center gap-3"
                    >
                        <MaterialDesignIcon icon-name="wifi-check" class="w-5 h-5 text-emerald-500" />
                        <p class="flex-1 text-sm text-sem-fg min-w-0">{{ $t("tools.nearby.join_connected") }}</p>
                        <button
                            type="button"
                            class="secondary-chip py-1! px-3! text-red-500! hover:bg-red-50! dark:hover:bg-red-900/20!"
                            @click="leaveNetwork"
                        >
                            {{ $t("tools.nearby.leave") }}
                        </button>
                    </div>
                    <p v-if="joinConnected" class="text-xs text-sem-fg-muted -mt-2">
                        {{ $t("tools.nearby.join_internet_note") }}
                    </p>

                    <div class="flex flex-wrap gap-2">
                        <button
                            type="button"
                            class="primary-chip py-1.5! px-4!"
                            :disabled="!cameraSupported || joining"
                            @click="openScannerDialog"
                        >
                            <MaterialDesignIcon icon-name="qrcode-scan" class="w-4 h-4" />
                            {{ $t("tools.nearby.scan_qr") }}
                        </button>
                    </div>
                    <p v-if="joinStatus === 'requested' && !joinConnected" class="text-xs text-sem-fg-muted">
                        {{ $t("tools.nearby.join_waiting") }}
                    </p>

                    <details class="group">
                        <summary class="text-sm text-sem-fg-muted cursor-pointer select-none hover:text-sem-fg">
                            {{ $t("tools.nearby.manual_entry") }}
                        </summary>
                        <div class="mt-3 space-y-3">
                            <input
                                v-model="joinSsid"
                                type="text"
                                class="w-full rounded-lg border border-sem-border bg-sem-canvas px-3 py-2 text-sm text-sem-fg"
                                :placeholder="$t('tools.nearby.ssid')"
                                maxlength="32"
                            />
                            <input
                                v-model="joinPassphrase"
                                type="password"
                                class="w-full rounded-lg border border-sem-border bg-sem-canvas px-3 py-2 text-sm text-sem-fg"
                                :placeholder="$t('tools.nearby.passphrase')"
                                maxlength="63"
                            />
                            <button
                                type="button"
                                class="primary-chip py-1! px-3!"
                                :disabled="!joinSsid || joining"
                                @click="joinManual"
                            >
                                {{ joining ? $t("tools.nearby.joining") : $t("tools.nearby.join") }}
                            </button>
                        </div>
                    </details>
                </div>

                <!-- wifi direct card -->
                <div class="rounded-xl border border-sem-border bg-sem-surface p-4 sm:p-5 space-y-4">
                    <div class="flex items-center gap-3">
                        <div class="p-2 rounded-lg bg-violet-100 dark:bg-violet-900/30">
                            <MaterialDesignIcon
                                icon-name="wifi-tethering"
                                class="w-5 h-5 text-violet-600 dark:text-violet-400"
                            />
                        </div>
                        <div>
                            <h2 class="text-base font-bold text-sem-fg">{{ $t("tools.nearby.p2p_title") }}</h2>
                            <p class="text-sm text-sem-fg-muted">{{ $t("tools.nearby.p2p_description") }}</p>
                        </div>
                    </div>

                    <div v-if="!p2pActive">
                        <button
                            type="button"
                            class="primary-chip py-1.5! px-4!"
                            :disabled="startingP2p || !canUseP2p"
                            @click="startP2p"
                        >
                            <MaterialDesignIcon icon-name="wifi-tethering" class="w-4 h-4" />
                            {{ startingP2p ? $t("tools.nearby.starting") : $t("tools.nearby.start_group") }}
                        </button>
                    </div>

                    <div v-else class="space-y-4">
                        <div class="flex flex-col sm:flex-row gap-4">
                            <div v-if="p2pQrDataUrl" class="shrink-0 self-center sm:self-start">
                                <img
                                    :src="p2pQrDataUrl"
                                    :alt="$t('tools.nearby.qr_alt')"
                                    class="w-44 h-44 rounded-lg border border-sem-border bg-white p-2"
                                />
                            </div>
                            <div class="space-y-2 min-w-0 flex-1">
                                <div class="text-sm">
                                    <span class="text-sem-fg-muted">{{ $t("tools.nearby.ssid") }}:</span>
                                    <span class="font-mono font-medium text-sem-fg break-all">{{ p2pSsid }}</span>
                                    <button
                                        type="button"
                                        class="ml-1 text-sem-fg-muted hover:text-sem-fg align-middle"
                                        :title="$t('common.copy')"
                                        @click="copyValue(p2pSsid)"
                                    >
                                        <MaterialDesignIcon icon-name="content-copy" class="w-3.5 h-3.5" />
                                    </button>
                                </div>
                                <div class="text-sm">
                                    <span class="text-sem-fg-muted">{{ $t("tools.nearby.passphrase") }}:</span>
                                    <span class="font-mono font-medium text-sem-fg break-all">{{ p2pPassphrase }}</span>
                                    <button
                                        type="button"
                                        class="ml-1 text-sem-fg-muted hover:text-sem-fg align-middle"
                                        :title="$t('common.copy')"
                                        @click="copyValue(p2pPassphrase)"
                                    >
                                        <MaterialDesignIcon icon-name="content-copy" class="w-3.5 h-3.5" />
                                    </button>
                                </div>
                                <p class="text-xs text-sem-fg-muted">{{ $t("tools.nearby.qr_hint") }}</p>
                            </div>
                        </div>
                        <button
                            type="button"
                            class="secondary-chip py-1! px-3! text-red-500! hover:bg-red-50! dark:hover:bg-red-900/20!"
                            @click="stopP2p"
                        >
                            <MaterialDesignIcon icon-name="wifi-off" class="w-3.5 h-3.5" />
                            {{ $t("tools.nearby.stop_group") }}
                        </button>
                    </div>
                </div>

                <!-- wifi aware card -->
                <div class="rounded-xl border border-sem-border bg-sem-surface p-4 sm:p-5 space-y-4">
                    <div class="flex items-center gap-3">
                        <div class="p-2 rounded-lg bg-emerald-100 dark:bg-emerald-900/30">
                            <MaterialDesignIcon
                                icon-name="radar"
                                class="w-5 h-5 text-emerald-600 dark:text-emerald-400"
                            />
                        </div>
                        <div>
                            <h2 class="text-base font-bold text-sem-fg">{{ $t("tools.nearby.aware_title") }}</h2>
                            <p class="text-sm text-sem-fg-muted">{{ $t("tools.nearby.aware_description") }}</p>
                        </div>
                    </div>

                    <div v-if="!awareActive" class="space-y-3">
                        <div class="flex flex-wrap gap-3 text-sm text-sem-fg">
                            <label class="inline-flex items-center gap-2 cursor-pointer">
                                <input v-model="awareMode" type="radio" value="subscribe" class="accent-sem-accent" />
                                {{ $t("tools.nearby.aware_subscribe") }}
                            </label>
                            <label class="inline-flex items-center gap-2 cursor-pointer">
                                <input v-model="awareMode" type="radio" value="publish" class="accent-sem-accent" />
                                {{ $t("tools.nearby.aware_publish") }}
                            </label>
                        </div>
                        <button
                            type="button"
                            class="primary-chip py-1.5! px-4!"
                            :disabled="startingAware || !canUseAware"
                            @click="startAware"
                        >
                            <MaterialDesignIcon icon-name="radar" class="w-4 h-4" />
                            {{ startingAware ? $t("tools.nearby.starting") : $t("tools.nearby.aware_start") }}
                        </button>
                        <p class="text-xs text-sem-fg-muted">{{ $t("tools.nearby.aware_hint") }}</p>
                    </div>

                    <div v-else class="space-y-3">
                        <div class="flex flex-wrap items-center gap-2 text-sm text-sem-fg">
                            <span
                                class="inline-flex items-center gap-1.5 rounded-full bg-emerald-100 dark:bg-emerald-900/30 px-2.5 py-0.5 text-xs font-medium text-emerald-700 dark:text-emerald-300"
                            >
                                <MaterialDesignIcon icon-name="radar" class="w-3 h-3" />
                                {{ awareStatus.role }}
                            </span>
                            <span class="text-sem-fg-muted">
                                {{
                                    $t("tools.nearby.aware_peers", {
                                        peers: awareStatus.peers,
                                        links: awareStatus.links,
                                    })
                                }}
                            </span>
                        </div>
                        <button
                            type="button"
                            class="secondary-chip py-1! px-3! text-red-500! hover:bg-red-50! dark:hover:bg-red-900/20!"
                            @click="stopAware"
                        >
                            <MaterialDesignIcon icon-name="stop" class="w-3.5 h-3.5" />
                            {{ $t("tools.nearby.aware_stop") }}
                        </button>
                    </div>
                </div>

                <!-- nfc card -->
                <div class="rounded-xl border border-sem-border bg-sem-surface p-4 sm:p-5 space-y-4">
                    <div class="flex items-center gap-3">
                        <div class="p-2 rounded-lg bg-orange-100 dark:bg-orange-900/30">
                            <MaterialDesignIcon
                                icon-name="nfc-variant"
                                class="w-5 h-5 text-orange-600 dark:text-orange-400"
                            />
                        </div>
                        <div>
                            <h2 class="text-base font-bold text-sem-fg">{{ $t("tools.nearby.nfc_title") }}</h2>
                            <p class="text-sm text-sem-fg-muted">{{ $t("tools.nearby.nfc_description") }}</p>
                        </div>
                    </div>

                    <div class="space-y-3">
                        <div class="flex flex-wrap items-center gap-3">
                            <button
                                v-if="!nfcSharing"
                                type="button"
                                class="secondary-chip py-1! px-3!"
                                :disabled="!nfcSharePayload || !canUseNfc"
                                @click="startNfcShare"
                            >
                                <MaterialDesignIcon icon-name="nfc-variant" class="w-3.5 h-3.5" />
                                {{ $t("tools.nearby.nfc_share_credentials") }}
                            </button>
                            <button
                                v-else
                                type="button"
                                class="secondary-chip py-1! px-3! text-red-500! hover:bg-red-50! dark:hover:bg-red-900/20!"
                                @click="stopNfcShare"
                            >
                                <MaterialDesignIcon icon-name="nfc-variant-off" class="w-3.5 h-3.5" />
                                {{ $t("tools.nearby.nfc_share_stop") }}
                            </button>
                            <button
                                v-if="!nfcReading"
                                type="button"
                                class="secondary-chip py-1! px-3!"
                                :disabled="!canUseNfc"
                                @click="startNfcRead"
                            >
                                <MaterialDesignIcon icon-name="cellphone-nfc" class="w-3.5 h-3.5" />
                                {{ $t("tools.nearby.nfc_read_start") }}
                            </button>
                            <button
                                v-else
                                type="button"
                                class="secondary-chip py-1! px-3! text-red-500! hover:bg-red-50! dark:hover:bg-red-900/20!"
                                @click="stopNfcRead"
                            >
                                {{ $t("tools.nearby.nfc_read_stop") }}
                            </button>
                        </div>
                        <p v-if="!nfcSharePayload" class="text-xs text-sem-fg-muted">
                            {{ $t("tools.nearby.nfc_no_credentials") }}
                        </p>
                        <p v-else-if="nfcSharing" class="text-xs text-amber-600 dark:text-amber-400">
                            {{ $t("tools.nearby.nfc_sharing_note") }}
                        </p>
                        <p v-if="nfcReading" class="text-xs text-sem-fg-muted">
                            {{ $t("tools.nearby.nfc_reading") }}
                        </p>
                        <div
                            v-if="nfcLastPayload"
                            class="rounded-lg border border-sem-border bg-sem-canvas p-3 space-y-2"
                        >
                            <p class="text-xs font-mono text-sem-fg break-all">{{ nfcLastPayload }}</p>
                            <button
                                v-if="nfcPayloadJoinable"
                                type="button"
                                class="primary-chip py-1! px-3!"
                                @click="joinFromNfc"
                            >
                                {{ $t("tools.nearby.nfc_join_this") }}
                            </button>
                        </div>
                    </div>
                </div>

                <!-- satellite posture hint -->
                <div
                    v-if="capabilities?.satellite?.feature"
                    class="rounded-xl border border-sem-border bg-sem-surface p-4 text-sm text-sem-fg-muted flex items-start gap-3"
                >
                    <MaterialDesignIcon icon-name="satellite-variant" class="w-5 h-5 text-sem-fg-muted shrink-0" />
                    <p>{{ $t("tools.nearby.satellite_hint") }}</p>
                </div>

                <!-- autointerface hint -->
                <div
                    v-if="autoInterfaceHint"
                    class="rounded-xl border border-sem-border bg-sem-surface p-4 text-sm text-sem-fg-muted flex items-start gap-3"
                >
                    <MaterialDesignIcon icon-name="information-outline" class="w-5 h-5 text-sem-fg-muted shrink-0" />
                    <p>
                        {{ $t("tools.nearby.autointerface_hint") }}
                        <RouterLink to="/interfaces/add" class="text-sem-accent hover:underline">
                            {{ $t("tools.nearby.autointerface_link") }}
                        </RouterLink>
                    </p>
                </div>
            </div>
        </div>

        <!-- QR scanner dialog -->
        <div
            v-if="isScannerDialogOpen"
            class="fixed inset-0 z-220 flex items-center justify-center p-4 bg-black/70 backdrop-blur-xs"
            @click.self="closeScannerDialog"
        >
            <div class="w-full max-w-xl rounded-2xl bg-sem-surface shadow-2xl overflow-hidden">
                <div class="px-5 py-4 border-b border-sem-border flex items-center justify-between">
                    <h3 class="text-lg font-bold text-sem-fg">{{ $t("tools.nearby.scan_qr") }}</h3>
                    <button type="button" class="text-sem-fg-muted hover:text-sem-fg" @click="closeScannerDialog">
                        <MaterialDesignIcon icon-name="close" class="size-5" />
                    </button>
                </div>
                <div class="p-5 space-y-3">
                    <video
                        ref="scannerVideo"
                        class="w-full rounded-xl bg-black max-h-[60vh]"
                        autoplay
                        playsinline
                        muted
                    ></video>
                    <div class="text-sm text-sem-fg-muted">
                        {{ scannerError || $t("tools.nearby.scanner_hint") }}
                    </div>
                </div>
            </div>
        </div>

        <!-- join confirm dialog -->
        <div
            v-if="pendingJoin"
            class="fixed inset-0 z-230 flex items-center justify-center p-4 bg-black/70 backdrop-blur-xs"
            @click.self="pendingJoin = null"
        >
            <div class="w-full max-w-md rounded-2xl bg-sem-surface shadow-2xl overflow-hidden">
                <div class="px-5 py-4 border-b border-sem-border">
                    <h3 class="text-lg font-bold text-sem-fg">{{ $t("tools.nearby.confirm_join_title") }}</h3>
                </div>
                <div class="p-5 space-y-4">
                    <p class="text-sm text-sem-fg">
                        {{ $t("tools.nearby.confirm_join_body", { ssid: pendingJoin.ssid }) }}
                    </p>
                    <div class="flex justify-end gap-2">
                        <button type="button" class="secondary-chip py-1! px-3!" @click="pendingJoin = null">
                            {{ $t("common.cancel") }}
                        </button>
                        <button type="button" class="primary-chip py-1! px-3!" :disabled="joining" @click="confirmJoin">
                            {{ $t("tools.nearby.join") }}
                        </button>
                    </div>
                </div>
            </div>
        </div>
    </div>
</template>

<script>
import QRCode from "qrcode";
import MaterialDesignIcon from "../MaterialDesignIcon.vue";
import ToastUtils from "../../js/ToastUtils";
import ToolsPageHeader from "./ToolsPageHeader.vue";
import AndroidBridge from "../../js/rnode/AndroidBridge";
import { apiPath } from "../../js/constants.js";
import {
    attachStreamToVideo,
    decodeQrFromVideo,
    describeCameraError as describeQrCameraError,
    isCameraSupported,
    startCameraStream,
} from "../../js/qrScannerUtils";
import { buildWifiQrPayload, parseWifiQrPayload } from "../../js/locallinkUri";

export default {
    name: "NearbyPage",
    components: {
        MaterialDesignIcon,
        ToolsPageHeader,
    },
    data() {
        return {
            loading: false,
            capabilities: null,
            nearbyWifiGranted: true,
            requestingPermission: false,
            hotspotActive: false,
            hotspotSsid: null,
            hotspotPassphrase: null,
            startingHotspot: false,
            wifiQrDataUrl: null,
            joinSsid: "",
            joinPassphrase: "",
            joinStatus: "idle",
            joining: false,
            pendingJoin: null,
            isScannerDialogOpen: false,
            scannerError: null,
            scannerStream: null,
            scannerAnimationFrame: null,
            autoInterfaceHint: false,
            androidBridge: new AndroidBridge(),
            cameraSupported: isCameraSupported(),
            p2pActive: false,
            p2pSsid: null,
            p2pPassphrase: null,
            startingP2p: false,
            p2pQrDataUrl: null,
            awareMode: "subscribe",
            awareStatus: { role: "off", session: false, peers: 0, links: 0 },
            startingAware: false,
            nfcSharing: false,
            nfcReading: false,
            nfcLastPayload: null,
        };
    },
    computed: {
        capabilityBadges() {
            const caps = this.capabilities || {};
            const t = (key) => this.$t(`tools.nearby.cap_${key}`);
            return [
                { key: "hotspot", label: t("hotspot"), ok: Boolean(caps.hotspot) },
                { key: "join", label: t("join"), ok: Boolean(caps.wifi_join_specifier) },
                { key: "aware", label: t("aware"), ok: Boolean(caps.wifi_aware_available) },
                { key: "direct", label: t("direct"), ok: Boolean(caps.wifi_direct) },
                { key: "nfc", label: t("nfc"), ok: Boolean(caps.nfc) },
                { key: "satellite", label: t("satellite"), ok: Boolean(caps.satellite?.feature) },
            ];
        },
        satelliteEnabled() {
            return Boolean(this.capabilities?.satellite?.enabled);
        },
        canUseHotspot() {
            return Boolean(this.capabilities?.supported && this.capabilities?.hotspot);
        },
        canUseP2p() {
            return Boolean(this.capabilities?.supported && this.capabilities?.wifi_direct);
        },
        canUseAware() {
            return Boolean(this.capabilities?.supported && this.capabilities?.wifi_aware_available);
        },
        canUseNfc() {
            return Boolean(this.capabilities?.supported && this.capabilities?.nfc);
        },
        awareActive() {
            return this.awareStatus.role !== "off" || this.awareStatus.session;
        },
        nfcSharePayload() {
            if (this.hotspotActive && this.hotspotSsid && this.hotspotPassphrase) {
                return buildWifiQrPayload({
                    ssid: this.hotspotSsid,
                    passphrase: this.hotspotPassphrase,
                });
            }
            if (this.p2pActive && this.p2pSsid && this.p2pPassphrase) {
                return buildWifiQrPayload({
                    ssid: this.p2pSsid,
                    passphrase: this.p2pPassphrase,
                });
            }
            return null;
        },
        nfcPayloadJoinable() {
            return Boolean(this.nfcLastPayload && parseWifiQrPayload(this.nfcLastPayload));
        },
        joinConnected() {
            return Boolean(this.capabilities?.join_network_connected);
        },
    },
    async mounted() {
        this._permListener = (event) => {
            if (event?.detail?.group === "nearby_wifi") {
                this.nearbyWifiGranted = Boolean(event.detail.granted);
                this.loadCapabilities();
            }
        };
        window.addEventListener("meshchatx-android-permission", this._permListener);
        await this.refreshAll();
        await Promise.all([this.loadP2pStatus(), this.loadAwareStatus(), this.loadNfcStatus()]);
    },
    beforeUnmount() {
        this.stopScanner();
        this.stopJoinPolling();
        this.stopAwarePolling();
        this.stopNfcPolling();
        // NFC emits only while this screen is open.
        if (this.nfcSharing) {
            window.api.post(apiPath("/locallink/nfc/share"), { payload: null }).catch(() => {});
        }
        if (this.nfcReading) {
            window.api.post(apiPath("/locallink/nfc/read/stop"), {}).catch(() => {});
        }
        if (this._permListener) {
            window.removeEventListener("meshchatx-android-permission", this._permListener);
        }
    },
    methods: {
        async refreshAll() {
            this.loading = true;
            try {
                await Promise.all([this.loadCapabilities(), this.loadInterfaces()]);
            } finally {
                this.loading = false;
            }
        },
        async loadCapabilities() {
            try {
                const res = await window.api.get(apiPath("/locallink/capabilities"));
                this.capabilities = res.data || {};
                if (this.capabilities.supported) {
                    this.nearbyWifiGranted =
                        Boolean(this.capabilities.permission_nearby_wifi) ||
                        this.androidBridge.hasPermission(AndroidBridge.PERM_NEARBY_WIFI);
                }
                if (this.capabilities.hotspot_active && !this.hotspotActive) {
                    await this.loadHotspotStatus();
                }
            } catch {
                this.capabilities = { supported: false };
            }
        },
        async loadHotspotStatus() {
            try {
                const res = await window.api.get(apiPath("/locallink/hotspot/status"));
                this.hotspotActive = Boolean(res.data?.active);
                if (this.hotspotActive && !this.hotspotSsid) {
                    this.hotspotSsid = res.data?.ssid || null;
                }
            } catch {
                // status is best effort
            }
        },
        async loadInterfaces() {
            try {
                const res = await window.api.get(apiPath("/reticulum/interfaces"));
                const interfaces = res.data?.interfaces || {};
                const hasAuto = Object.values(interfaces).some(
                    (iface) => iface && iface.type === "AutoInterface" && iface.enabled
                );
                this.autoInterfaceHint = !hasAuto;
            } catch {
                this.autoInterfaceHint = false;
            }
        },
        async requestNearbyPermission() {
            this.requestingPermission = true;
            try {
                const result = await this.androidBridge.requestPermission(AndroidBridge.PERM_NEARBY_WIFI);
                if (result === "granted") {
                    this.nearbyWifiGranted = true;
                    await this.loadCapabilities();
                } else if (result === "settings") {
                    ToastUtils.warning(this.$t("tools.nearby.permission_settings"));
                } else if (result !== "requested") {
                    ToastUtils.warning(this.$t("tools.nearby.permission_failed"));
                }
            } finally {
                this.requestingPermission = false;
            }
        },
        async startHotspot() {
            this.startingHotspot = true;
            try {
                const res = await window.api.post(apiPath("/locallink/hotspot/start"), {});
                const data = res.data || {};
                if (!data.ok) {
                    ToastUtils.error(data.error || this.$t("tools.nearby.hotspot_failed"));
                    return;
                }
                this.hotspotActive = true;
                this.hotspotSsid = data.ssid;
                this.hotspotPassphrase = data.passphrase;
                await this.renderWifiQr();
                ToastUtils.success(this.$t("tools.nearby.hotspot_started"));
            } catch (e) {
                ToastUtils.error(e.response?.data?.error || this.$t("tools.nearby.hotspot_failed"));
            } finally {
                this.startingHotspot = false;
            }
        },
        async stopHotspot() {
            try {
                await window.api.post(apiPath("/locallink/hotspot/stop"), {});
                this.hotspotActive = false;
                this.hotspotSsid = null;
                this.hotspotPassphrase = null;
                this.wifiQrDataUrl = null;
                ToastUtils.info(this.$t("tools.nearby.hotspot_stopped"));
            } catch (e) {
                ToastUtils.error(e.response?.data?.error || this.$t("tools.nearby.hotspot_failed"));
            }
        },
        async rotateHotspot() {
            await this.stopHotspot();
            await this.startHotspot();
        },
        async renderWifiQr() {
            const payload = buildWifiQrPayload({
                ssid: this.hotspotSsid,
                passphrase: this.hotspotPassphrase,
            });
            this.wifiQrDataUrl = payload ? await QRCode.toDataURL(payload, { margin: 1, scale: 6 }) : null;
        },
        async copyValue(value) {
            if (!value) return;
            try {
                await navigator.clipboard.writeText(value);
                ToastUtils.success(this.$t("common.copied"));
            } catch {
                ToastUtils.error(this.$t("common.failed_to_copy"));
            }
        },
        async openScannerDialog() {
            this.isScannerDialogOpen = true;
            this.scannerError = null;
            await this.$nextTick();
            await this.startScanner();
        },
        async startScanner() {
            if (!this.cameraSupported) {
                this.scannerError = this.$t("tools.nearby.camera_not_supported");
                return;
            }
            try {
                const stream = await startCameraStream();
                if (!stream.getVideoTracks().length) {
                    this.scannerError = this.$t("tools.nearby.camera_not_found");
                    stream.getTracks().forEach((track) => track.stop());
                    return;
                }
                this.scannerStream = stream;
                const video = this.$refs.scannerVideo;
                if (!(await attachStreamToVideo(stream, video))) {
                    return;
                }
                this.detectQrLoop();
            } catch (e) {
                this.scannerError = describeQrCameraError(e, {
                    permissionDenied: this.$t("tools.nearby.camera_denied"),
                    notFound: this.$t("tools.nearby.camera_not_found"),
                    failed: this.$t("tools.nearby.camera_failed"),
                });
            }
        },
        detectQrLoop() {
            if (!this.isScannerDialogOpen) return;
            const video = this.$refs.scannerVideo;
            decodeQrFromVideo(video)
                .then((qr) => {
                    if (!this.isScannerDialogOpen) return;
                    if (qr) {
                        this.onQrScanned(qr);
                        return;
                    }
                    this.scannerAnimationFrame = requestAnimationFrame(() => this.detectQrLoop());
                })
                .catch(() => {
                    if (this.isScannerDialogOpen) {
                        this.scannerAnimationFrame = requestAnimationFrame(() => this.detectQrLoop());
                    }
                });
        },
        onQrScanned(raw) {
            const parsed = parseWifiQrPayload(raw);
            if (!parsed) {
                this.scannerError = this.$t("tools.nearby.qr_not_wifi");
                this.scannerAnimationFrame = requestAnimationFrame(() => this.detectQrLoop());
                return;
            }
            this.closeScannerDialog();
            this.pendingJoin = parsed;
        },
        stopScanner() {
            if (this.scannerAnimationFrame) {
                cancelAnimationFrame(this.scannerAnimationFrame);
                this.scannerAnimationFrame = null;
            }
            if (this.scannerStream) {
                this.scannerStream.getTracks().forEach((track) => track.stop());
                this.scannerStream = null;
            }
        },
        closeScannerDialog() {
            this.isScannerDialogOpen = false;
            this.stopScanner();
        },
        async confirmJoin() {
            if (!this.pendingJoin) return;
            const { ssid, passphrase } = this.pendingJoin;
            this.pendingJoin = null;
            await this.joinNetwork(ssid, passphrase);
        },
        async joinManual() {
            if (!this.joinSsid) return;
            await this.joinNetwork(this.joinSsid.trim(), this.joinPassphrase || null);
        },
        async joinNetwork(ssid, passphrase) {
            this.joining = true;
            try {
                const res = await window.api.post(apiPath("/locallink/wifi/join"), {
                    ssid,
                    passphrase,
                });
                const data = res.data || {};
                if (!data.ok && data.status !== "requested") {
                    ToastUtils.error(data.error || this.$t("tools.nearby.join_failed"));
                    return;
                }
                this.joinStatus = data.status || "requested";
                ToastUtils.info(this.$t("tools.nearby.join_requested"));
                this.startJoinPolling();
                await this.loadCapabilities();
            } catch (e) {
                ToastUtils.error(e.response?.data?.error || this.$t("tools.nearby.join_failed"));
            } finally {
                this.joining = false;
            }
        },
        startJoinPolling() {
            this.stopJoinPolling();
            let attempts = 0;
            this._joinPoll = setInterval(async () => {
                attempts += 1;
                await this.loadCapabilities();
                if (this.joinConnected || attempts >= 10 || this.capabilities?.join_status === "idle") {
                    this.stopJoinPolling();
                }
            }, 3000);
        },
        stopJoinPolling() {
            if (this._joinPoll) {
                clearInterval(this._joinPoll);
                this._joinPoll = null;
            }
        },
        async leaveNetwork() {
            try {
                await window.api.post(apiPath("/locallink/wifi/leave"), {});
                this.joinStatus = "idle";
                this.stopJoinPolling();
                await this.loadCapabilities();
                ToastUtils.info(this.$t("tools.nearby.left"));
            } catch (e) {
                ToastUtils.error(e.response?.data?.error || this.$t("tools.nearby.join_failed"));
            }
        },
        async loadP2pStatus() {
            try {
                const res = await window.api.get(apiPath("/locallink/p2p/status"));
                this.p2pActive = Boolean(res.data?.active);
                if (this.p2pActive && !this.p2pSsid) {
                    this.p2pSsid = res.data?.ssid || null;
                }
            } catch {
                this.p2pActive = false;
            }
        },
        async startP2p() {
            this.startingP2p = true;
            try {
                const res = await window.api.post(apiPath("/locallink/p2p/start"), {});
                const data = res.data || {};
                if (!data.ok) {
                    ToastUtils.error(data.error || this.$t("tools.nearby.group_failed"));
                    return;
                }
                this.p2pActive = true;
                this.p2pSsid = data.ssid;
                this.p2pPassphrase = data.passphrase;
                const payload = buildWifiQrPayload({
                    ssid: this.p2pSsid,
                    passphrase: this.p2pPassphrase,
                });
                this.p2pQrDataUrl = payload ? await QRCode.toDataURL(payload, { margin: 1, scale: 6 }) : null;
                ToastUtils.success(this.$t("tools.nearby.group_started"));
            } catch (e) {
                ToastUtils.error(e.response?.data?.error || this.$t("tools.nearby.group_failed"));
            } finally {
                this.startingP2p = false;
            }
        },
        async stopP2p() {
            try {
                await window.api.post(apiPath("/locallink/p2p/stop"), {});
                this.p2pActive = false;
                this.p2pSsid = null;
                this.p2pPassphrase = null;
                this.p2pQrDataUrl = null;
                ToastUtils.info(this.$t("tools.nearby.group_stopped"));
            } catch (e) {
                ToastUtils.error(e.response?.data?.error || this.$t("tools.nearby.group_failed"));
            }
        },
        async loadAwareStatus() {
            try {
                const res = await window.api.get(apiPath("/locallink/aware/status"));
                const data = res.data || {};
                this.awareStatus = {
                    role: data.role || "off",
                    session: Boolean(data.session),
                    peers: data.peers || 0,
                    links: data.links || 0,
                };
            } catch {
                this.awareStatus = { role: "off", session: false, peers: 0, links: 0 };
            }
        },
        async startAware() {
            this.startingAware = true;
            try {
                const res = await window.api.post(apiPath("/locallink/aware/start"), {
                    mode: this.awareMode,
                });
                const data = res.data || {};
                if (!data.ok) {
                    ToastUtils.error(data.error || this.$t("tools.nearby.aware_failed"));
                    return;
                }
                this.awareStatus.role = this.awareMode;
                this.awareStatus.session = true;
                ToastUtils.success(this.$t("tools.nearby.aware_started"));
                this.startAwarePolling();
            } catch (e) {
                ToastUtils.error(e.response?.data?.error || this.$t("tools.nearby.aware_failed"));
            } finally {
                this.startingAware = false;
            }
        },
        async stopAware() {
            try {
                await window.api.post(apiPath("/locallink/aware/stop"), {});
                this.awareStatus = { role: "off", session: false, peers: 0, links: 0 };
                this.stopAwarePolling();
                ToastUtils.info(this.$t("tools.nearby.aware_stopped"));
            } catch (e) {
                ToastUtils.error(e.response?.data?.error || this.$t("tools.nearby.aware_failed"));
            }
        },
        startAwarePolling() {
            this.stopAwarePolling();
            this._awarePoll = setInterval(() => this.loadAwareStatus(), 3000);
        },
        stopAwarePolling() {
            if (this._awarePoll) {
                clearInterval(this._awarePoll);
                this._awarePoll = null;
            }
        },
        async loadNfcStatus() {
            try {
                const res = await window.api.get(apiPath("/locallink/nfc/status"));
                const data = res.data || {};
                this.nfcSharing = Boolean(data.sharing);
                this.nfcReading = Boolean(data.reading);
                if (data.last_payload) {
                    this.nfcLastPayload = data.last_payload;
                }
            } catch {
                // status is best effort
            }
        },
        async startNfcShare() {
            try {
                const res = await window.api.post(apiPath("/locallink/nfc/share"), {
                    payload: this.nfcSharePayload,
                });
                const data = res.data || {};
                if (!data.ok) {
                    ToastUtils.error(data.error || this.$t("tools.nearby.nfc_failed"));
                    return;
                }
                this.nfcSharing = true;
                ToastUtils.info(this.$t("tools.nearby.nfc_sharing_note"));
            } catch (e) {
                ToastUtils.error(e.response?.data?.error || this.$t("tools.nearby.nfc_failed"));
            }
        },
        async stopNfcShare() {
            try {
                await window.api.post(apiPath("/locallink/nfc/share"), { payload: null });
                this.nfcSharing = false;
            } catch (e) {
                ToastUtils.error(e.response?.data?.error || this.$t("tools.nearby.nfc_failed"));
            }
        },
        async startNfcRead() {
            try {
                const res = await window.api.post(apiPath("/locallink/nfc/read/start"), {});
                const data = res.data || {};
                if (!data.ok) {
                    ToastUtils.error(data.error || this.$t("tools.nearby.nfc_failed"));
                    return;
                }
                this.nfcReading = true;
                this.nfcLastPayload = null;
                this.startNfcPolling();
            } catch (e) {
                ToastUtils.error(e.response?.data?.error || this.$t("tools.nearby.nfc_failed"));
            }
        },
        async stopNfcRead() {
            try {
                await window.api.post(apiPath("/locallink/nfc/read/stop"), {});
                this.nfcReading = false;
                this.stopNfcPolling();
            } catch (e) {
                ToastUtils.error(e.response?.data?.error || this.$t("tools.nearby.nfc_failed"));
            }
        },
        startNfcPolling() {
            this.stopNfcPolling();
            this._nfcPoll = setInterval(() => this.loadNfcStatus(), 1500);
        },
        stopNfcPolling() {
            if (this._nfcPoll) {
                clearInterval(this._nfcPoll);
                this._nfcPoll = null;
            }
        },
        joinFromNfc() {
            const parsed = parseWifiQrPayload(this.nfcLastPayload);
            if (parsed) {
                this.pendingJoin = parsed;
            }
        },
    },
};
</script>
