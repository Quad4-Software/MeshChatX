<!-- SPDX-License-Identifier: 0BSD -->

<script lang="ts">
    import { onDestroy, onMount } from "svelte";
    import ElectronUtils from "../../js/ElectronUtils.js";
    import GlobalEmitter from "../../js/GlobalEmitter.js";
    import { getDeviceBatteryStatus, type DeviceBatteryStatus } from "../../js/deviceBattery.js";
    import { offWsEvent, onWsEvent } from "../../js/registries/wsEventRegistry.js";
    import {
        BATTERY_SAVER_CHANGED_EVENT,
        applyBackgroundPollInterval,
        loadBatterySaverPrefs,
    } from "../../js/settings/batterySaverPrefs.js";
    import AboutAutoBackupsSection from "./components/AboutAutoBackupsSection.svelte";
    import AboutDatabaseSection from "./components/AboutDatabaseSection.svelte";
    import AboutDependencySection from "./components/AboutDependencySection.svelte";
    import AboutEnvironmentSection from "./components/AboutEnvironmentSection.svelte";
    import AboutHeroSection from "./components/AboutHeroSection.svelte";
    import AboutSecuritySection from "./components/AboutSecuritySection.svelte";
    import AboutSessionsSection from "./components/AboutSessionsSection.svelte";
    import AboutSnapshotsSection from "./components/AboutSnapshotsSection.svelte";
    import AboutUsageSection from "./components/AboutUsageSection.svelte";
    import {
        acknowledgeIntegrity,
        fetchActiveSessions,
        fetchAppInfo,
        fetchDatabaseHealth,
        reloadRns,
        revealPath,
        runAutoRecover,
        runRecovery,
        shutdownApp,
        vacuumDatabase,
    } from "./lib/aboutApi.js";
    import {
        backupDatabase,
        createSnapshot,
        deleteBackup,
        deleteSnapshot,
        downloadBackupFile,
        downloadSnapshot,
        listAutoBackups,
        listSnapshots,
        restoreDatabaseFromFile,
        restoreFromSnapshot,
    } from "./lib/backupApi.js";
    import {
        ABOUT_HEALTH_POLL_INTERVAL_MS,
        ABOUT_INFO_POLL_INTERVAL_MS,
        AUTOBACKUPS_PAGE_LIMIT,
        SNAPSHOTS_PAGE_LIMIT,
    } from "./lib/constants.js";
    import type { ActiveSession, AppInfo, AutoBackupItem, DatabaseHealth, SnapshotItem } from "./lib/types.js";

    interface Props {
        routeQuery?: Record<string, unknown>;
        router?: unknown;
    }

    let { routeQuery: _routeQuery = {}, router: _router }: Props = $props();

    const isElectron = ElectronUtils.isElectron();

    let appInfo = $state<AppInfo | null>({ version: "unknown" });
    let activeSessions = $state<ActiveSession[]>([]);
    let activeSessionCount = $state(0);

    let databaseHealth = $state<DatabaseHealth | null>(null);
    let databaseActionInProgress = $state(false);
    let healthLoading = $state(false);

    let electronMemoryUsage = $state<unknown>(null);
    let batteryStatus = $state<DeviceBatteryStatus | null>(null);
    let batterySaverPrefs = $state(loadBatterySaverPrefs());

    let backupInProgress = $state(false);
    let restoreInProgress = $state(false);
    let reloadingRns = $state(false);
    let snapshotInProgress = $state(false);

    let snapshots = $state<SnapshotItem[]>([]);
    let snapshotsTotal = $state(0);
    let snapshotsOffset = $state(0);

    let autoBackups = $state<AutoBackupItem[]>([]);
    let autoBackupsTotal = $state(0);
    let autoBackupsOffset = $state(0);

    let electronVersion = $state<string | null>(null);
    let chromeVersion = $state<string | null>(null);
    let nodeVersion = $state<string | null>(null);

    let updateInterval: ReturnType<typeof setInterval> | null = null;
    let healthInterval: ReturnType<typeof setInterval> | null = null;
    let sessionsWsHandler: ((payload: unknown) => void) | null = null;
    let batterySaverPrefsHandler: ((prefs: unknown) => void) | null = null;

    function applyActiveSessionsPayload(payload: unknown): void {
        const data = payload as { sessions?: ActiveSession[]; count?: number } | undefined;
        const list = Array.isArray(data?.sessions) ? data.sessions : [];
        activeSessions = list;
        const count = Number(data?.count);
        activeSessionCount = Number.isFinite(count) ? count : list.length;
    }

    async function loadAppInfo(): Promise<void> {
        const info = await fetchAppInfo();
        if (info) {
            appInfo = {
                ...(appInfo || {}),
                ...info,
            };
        }
        if (isElectron && typeof window !== "undefined" && (window as any).electron) {
            try {
                electronMemoryUsage = await ElectronUtils.getMemoryUsage();
                electronVersion = (window as any).electron.electronVersion?.() || null;
                chromeVersion = (window as any).electron.chromeVersion?.() || null;
                nodeVersion = (window as any).electron.nodeVersion?.() || null;
            } catch {
                // Electron runtime probes optional
            }
        }
        try {
            batteryStatus = await getDeviceBatteryStatus();
        } catch {
            batteryStatus = null;
        }
    }

    async function loadSessions(): Promise<void> {
        const res = await fetchActiveSessions();
        activeSessions = res.sessions;
        activeSessionCount = res.count;
    }

    async function loadDatabaseHealth(): Promise<void> {
        healthLoading = true;
        try {
            const health = await fetchDatabaseHealth();
            databaseHealth = health;
        } catch {
            // Error logged by fetchDatabaseHealth
        } finally {
            healthLoading = false;
        }
    }

    async function loadSnapshots(): Promise<void> {
        const res = await listSnapshots(snapshotsOffset, SNAPSHOTS_PAGE_LIMIT);
        snapshots = res.snapshots;
        snapshotsTotal = res.total;
    }

    async function loadAutoBackups(): Promise<void> {
        const res = await listAutoBackups(autoBackupsOffset, AUTOBACKUPS_PAGE_LIMIT);
        autoBackups = res.backups;
        autoBackupsTotal = res.total;
    }

    function scrollToDatabaseBackupsIfNeeded(): void {
        if (typeof window === "undefined") return;
        const hash = window.location.hash || "";
        if (!hash.includes("about-database-backups")) return;
        const el = document.getElementById("about-database-backups");
        if (el) {
            el.scrollIntoView({ behavior: "smooth", block: "start" });
        }
    }

    function restartAboutPollIntervals(): void {
        if (updateInterval) clearInterval(updateInterval);
        if (healthInterval) clearInterval(healthInterval);
        const prefs = batterySaverPrefs || loadBatterySaverPrefs();
        updateInterval = setInterval(
            () => {
                void loadAppInfo();
                void loadSessions();
            },
            applyBackgroundPollInterval(ABOUT_INFO_POLL_INTERVAL_MS, prefs)
        );

        healthInterval = setInterval(
            () => {
                void loadDatabaseHealth();
            },
            applyBackgroundPollInterval(ABOUT_HEALTH_POLL_INTERVAL_MS, prefs)
        );
    }

    function onIdentitySwitched(): void {
        void loadAppInfo();
        void loadSessions();
        void loadDatabaseHealth();
        snapshotsOffset = 0;
        autoBackupsOffset = 0;
        void loadSnapshots();
        void loadAutoBackups();
    }

    function onWebsocketReconnected(): void {
        void loadAppInfo();
        void loadSessions();
    }

    async function handleAcknowledgeIntegrity(): Promise<void> {
        const ok = await acknowledgeIntegrity();
        if (ok) {
            await loadAppInfo();
        }
    }

    async function handleReloadRns(): Promise<void> {
        if (reloadingRns) return;
        reloadingRns = true;
        try {
            await reloadRns();
            await loadAppInfo();
        } finally {
            reloadingRns = false;
        }
    }

    function handleRelaunch(): void {
        ElectronUtils.relaunch();
    }

    async function handleShutdown(): Promise<void> {
        await shutdownApp(isElectron);
    }

    async function handleVacuum(): Promise<void> {
        if (databaseActionInProgress) return;
        databaseActionInProgress = true;
        try {
            const res = await vacuumDatabase();
            if (res.health) databaseHealth = res.health;
        } finally {
            databaseActionInProgress = false;
        }
    }

    async function handleAutoRecover(): Promise<void> {
        if (databaseActionInProgress) return;
        databaseActionInProgress = true;
        try {
            const res = await runAutoRecover();
            if (res.health) databaseHealth = res.health;
        } finally {
            databaseActionInProgress = false;
        }
    }

    async function handleRecovery(): Promise<void> {
        if (databaseActionInProgress) return;
        databaseActionInProgress = true;
        try {
            const res = await runRecovery();
            if (res.health) databaseHealth = res.health;
        } finally {
            databaseActionInProgress = false;
        }
    }

    async function handleBackupDatabase(): Promise<void> {
        if (backupInProgress) return;
        backupInProgress = true;
        try {
            await backupDatabase();
            await loadDatabaseHealth();
        } finally {
            backupInProgress = false;
        }
    }

    async function handleRestoreFile(file: File): Promise<void> {
        if (restoreInProgress) return;
        restoreInProgress = true;
        try {
            const res = await restoreDatabaseFromFile(file, isElectron);
            if (res.health) databaseHealth = res.health;
            await loadDatabaseHealth();
        } finally {
            restoreInProgress = false;
        }
    }

    async function handleCreateSnapshot(name: string): Promise<void> {
        if (snapshotInProgress) return;
        snapshotInProgress = true;
        try {
            const res = await createSnapshot(name);
            if (res.success) {
                await loadSnapshots();
            }
        } finally {
            snapshotInProgress = false;
        }
    }

    async function handleRestoreSnapshot(path: string): Promise<void> {
        if (restoreInProgress) return;
        restoreInProgress = true;
        try {
            await restoreFromSnapshot(path, isElectron);
        } finally {
            restoreInProgress = false;
        }
    }

    async function handleDeleteSnapshot(name: string): Promise<void> {
        const ok = await deleteSnapshot(name);
        if (ok) {
            await loadSnapshots();
        }
    }

    async function handleDeleteBackup(name: string): Promise<void> {
        const ok = await deleteBackup(name);
        if (ok) {
            await loadAutoBackups();
        }
    }

    async function handleSnapshotsPrev(): Promise<void> {
        if (snapshotsOffset > 0) {
            snapshotsOffset = Math.max(0, snapshotsOffset - SNAPSHOTS_PAGE_LIMIT);
            await loadSnapshots();
        }
    }

    async function handleSnapshotsNext(): Promise<void> {
        if (snapshotsOffset + SNAPSHOTS_PAGE_LIMIT < snapshotsTotal) {
            snapshotsOffset += SNAPSHOTS_PAGE_LIMIT;
            await loadSnapshots();
        }
    }

    async function handleBackupsPrev(): Promise<void> {
        if (autoBackupsOffset > 0) {
            autoBackupsOffset = Math.max(0, autoBackupsOffset - AUTOBACKUPS_PAGE_LIMIT);
            await loadAutoBackups();
        }
    }

    async function handleBackupsNext(): Promise<void> {
        if (autoBackupsOffset + AUTOBACKUPS_PAGE_LIMIT < autoBackupsTotal) {
            autoBackupsOffset += AUTOBACKUPS_PAGE_LIMIT;
            await loadAutoBackups();
        }
    }

    onMount(() => {
        void loadAppInfo();
        void loadSessions();
        void loadDatabaseHealth();
        void loadSnapshots();
        void loadAutoBackups();

        batterySaverPrefsHandler = (prefs: unknown) => {
            batterySaverPrefs = (prefs as any) || loadBatterySaverPrefs();
            restartAboutPollIntervals();
        };
        GlobalEmitter.on(BATTERY_SAVER_CHANGED_EVENT, batterySaverPrefsHandler);
        GlobalEmitter.on("identity-switched", onIdentitySwitched);
        GlobalEmitter.on("websocket-reconnected", onWebsocketReconnected);

        sessionsWsHandler = (payload: unknown) => {
            applyActiveSessionsPayload(payload);
        };
        onWsEvent("app.sessions.updated", sessionsWsHandler);

        restartAboutPollIntervals();

        setTimeout(() => {
            scrollToDatabaseBackupsIfNeeded();
        }, 50);
    });

    onDestroy(() => {
        if (updateInterval) clearInterval(updateInterval);
        if (healthInterval) clearInterval(healthInterval);
        if (batterySaverPrefsHandler) {
            GlobalEmitter.off(BATTERY_SAVER_CHANGED_EVENT, batterySaverPrefsHandler);
        }
        GlobalEmitter.off("identity-switched", onIdentitySwitched);
        GlobalEmitter.off("websocket-reconnected", onWebsocketReconnected);
        if (sessionsWsHandler) {
            offWsEvent("app.sessions.updated", sessionsWsHandler);
            sessionsWsHandler = null;
        }
    });
</script>

<div class="flex flex-col flex-1 overflow-hidden min-w-0 bg-sem-canvas">
    <div
        class="flex-1 overflow-y-auto overflow-x-hidden w-full min-w-0 px-3 sm:px-5 md:px-5 lg:px-8 py-4 sm:py-6 text-sem-fg"
    >
        <div class="space-y-0 w-full max-w-4xl mx-auto pb-16 sm:pb-24 min-w-0">
            <!-- Hero section -->
            <AboutHeroSection
                {appInfo}
                {isElectron}
                {reloadingRns}
                onreloadrns={handleReloadRns}
                onrelaunch={handleRelaunch}
                onshutdown={handleShutdown}
            />

            <div class="space-y-6">
                <!-- Security & Integrity -->
                <AboutSecuritySection {appInfo} onacknowledge={handleAcknowledgeIntegrity} />

                <!-- Active Sessions -->
                <AboutSessionsSection {activeSessions} {activeSessionCount} />

                <!-- Environment Paths -->
                <AboutEnvironmentSection
                    {appInfo}
                    {isElectron}
                    onshowreticulumconfig={() => revealPath(appInfo?.reticulum_config_path)}
                    onshowdatabase={() => revealPath(appInfo?.database_path)}
                />

                <!-- Usage Insights -->
                <AboutUsageSection {appInfo} {batterySaverPrefs} {batteryStatus} {electronMemoryUsage} />

                <!-- Dependency Chain -->
                <AboutDependencySection {appInfo} {electronVersion} {chromeVersion} {nodeVersion} />

                <!-- Database Health & Maintenance -->
                <AboutDatabaseSection
                    {databaseHealth}
                    {databaseActionInProgress}
                    {healthLoading}
                    {backupInProgress}
                    {restoreInProgress}
                    onrefreshhealth={() => loadDatabaseHealth()}
                    onvacuum={handleVacuum}
                    onautorecover={handleAutoRecover}
                    onrecovery={handleRecovery}
                    onbackup={handleBackupDatabase}
                    onrestorefile={handleRestoreFile}
                >
                    <!-- Snapshots Subsection -->
                    <AboutSnapshotsSection
                        {snapshots}
                        {snapshotsTotal}
                        {snapshotsOffset}
                        snapshotsLimit={SNAPSHOTS_PAGE_LIMIT}
                        {snapshotInProgress}
                        oncreatesnapshot={handleCreateSnapshot}
                        ondownloadsnapshot={downloadSnapshot}
                        onrestoresnapshot={handleRestoreSnapshot}
                        ondeletesnapshot={handleDeleteSnapshot}
                        onprev={handleSnapshotsPrev}
                        onnext={handleSnapshotsNext}
                    />

                    <!-- Auto Backups Subsection -->
                    <AboutAutoBackupsSection
                        {autoBackups}
                        {autoBackupsTotal}
                        {autoBackupsOffset}
                        autoBackupsLimit={AUTOBACKUPS_PAGE_LIMIT}
                        ondownloadbackup={downloadBackupFile}
                        onrestorebackup={handleRestoreSnapshot}
                        ondeletebackup={handleDeleteBackup}
                        onprev={handleBackupsPrev}
                        onnext={handleBackupsNext}
                    />
                </AboutDatabaseSection>
            </div>
        </div>
    </div>
</div>
