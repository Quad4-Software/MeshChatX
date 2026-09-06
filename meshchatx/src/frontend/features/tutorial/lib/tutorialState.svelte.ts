// SPDX-License-Identifier: 0BSD

/**
 * Tutorial wizard state and side effects.
 *
 * One instance backs either the /tutorial page or the shell modal, selected by
 * the variant the host passes in. Identity setup keeps the two-phase contract
 * from the identity-restore skill: import on Continue, activate on Finish.
 */

import AndroidStorageBridge from "../../../js/AndroidStorageBridge.js";
import DialogUtils from "../../../js/DialogUtils.js";
import GlobalEmitter from "../../../js/GlobalEmitter.js";
import GlobalState from "../../../js/GlobalState.js";
import ToastUtils from "../../../js/ToastUtils.js";
import { t } from "../../../js/i18n.js";
import { getCurrentUiLocale, normalizeUiLocaleCode, setLocale } from "../../../js/localeLoader.js";
import { bundledReticulumDocsUrl } from "../../../js/reticulumDocsEntryUrl.js";
import { navigate } from "../../../shell/hashRouter.js";

export type TutorialVariant = "page" | "modal";
export type IdentityMode = "new" | "import";
export type ConnectionMode = "recommended" | "discovery" | "local" | "manual" | null;

export interface CommunityInterface {
    name: string;
    type?: string;
    description?: string;
    target_host?: string;
    target_port?: number | string | null;
    online?: boolean;
}

export interface DiscoveredInterface {
    name: string;
    type?: string;
    status?: string;
    reachable_on?: string;
    port?: number | string | null;
    discovery_hash?: string;
    latitude?: number | null;
    longitude?: number | null;
    last_heard?: number;
}

export interface MigrationOffer {
    show_choice?: boolean;
    [key: string]: unknown;
}

export interface AndroidStorageStatus {
    needs_setup_choice?: boolean;
    active_mode?: string;
    [key: string]: unknown;
}

interface BootstrapEntry {
    key: string;
    kind: "community" | "discovered";
    iface: CommunityInterface & DiscoveredInterface;
    dedupe: string;
}

interface PickRandomOptions {
    silent?: boolean;
    auto?: boolean;
    count?: number;
}

const DISCOVERY_POLL_MS = 5000;
const MAX_IDENTITY_KEY_BYTES = 65536;

/** Read the message of a rejected window.api call, falling back to a locale key. */
function apiErrorMessage(error: unknown, fallbackKey: string): string {
    const response = (error as { response?: { data?: { message?: string; error?: string } } })?.response;
    return response?.data?.message || response?.data?.error || t(fallbackKey);
}

export class TutorialState {
    readonly variant: TutorialVariant;
    readonly totalSteps = 8;
    readonly defaultUsername = "Anonymous Peer";

    visible = $state(false);
    currentStep = $state(1);
    theme = $state<string>(String((GlobalState.config as Record<string, unknown>)?.theme ?? "light"));
    localeVersion = $state(0);
    windowWidth = $state(typeof window !== "undefined" ? window.innerWidth : 1024);

    identityMode = $state<IdentityMode>("new");
    identityName = $state("");
    identityImportBase32 = $state("");
    identityImportFile = $state<File | null>(null);
    identityImportInProgress = $state(false);
    identityImportError = $state("");
    identityImportedHash = $state<string | null>(null);
    originalIdentityHash = $state<string | null>(null);

    communityInterfaces = $state<CommunityInterface[]>([]);
    discoveredInterfaces = $state<DiscoveredInterface[]>([]);
    loadingInterfaces = $state(false);
    loadingDiscovered = $state(false);

    finishingTutorial = $state(false);
    interfaceAddedViaTutorial = $state(false);
    connectionMode = $state<ConnectionMode>(null);
    selectedBootstrapKeys = $state<string[]>([]);
    addedBootstrapKeys = $state<string[]>([]);
    addingBootstraps = $state(false);
    addingLocal = $state(false);
    reloadingReticulum = $state(false);
    savingDiscovery = $state(false);
    savingPropagation = $state(false);
    markingSeen = $state(false);
    defaultBootstrapOnly = $state(false);
    bootstrapListSearch = $state("");
    bootstrapDiscoveredSectionOpen = $state(true);
    bootstrapCommunitySectionOpen = $state(true);
    bootstrapAutoPickDone = $state(false);
    pickingRandomBootstraps = $state(false);
    addingRecommended = $state(false);

    migrationOffer = $state<MigrationOffer | null>(null);
    migrationBusy = $state(false);
    androidStorageSetup = $state<AndroidStorageStatus | null>(null);
    androidStorageSetupChoice = $state("external");
    androidStorageBusy = $state(false);

    private discoveryInterval: ReturnType<typeof setInterval> | null = null;
    private androidStorageBridge: AndroidStorageBridge | null = null;

    constructor(variant: TutorialVariant) {
        this.variant = variant;
    }

    get isPage(): boolean {
        return this.variant === "page";
    }

    get dialogFullscreen(): boolean {
        return this.windowWidth < 768;
    }

    get sortedDiscoveredInterfaces(): DiscoveredInterface[] {
        return [...this.discoveredInterfaces].sort((a, b) => (b.last_heard || 0) - (a.last_heard || 0));
    }

    get hasAnyBootstrapsToShow(): boolean {
        return this.communityInterfaces.length > 0 || this.sortedDiscoveredInterfaces.length > 0;
    }

    get filteredDiscoveredForBootstrap(): DiscoveredInterface[] {
        const list = this.sortedDiscoveredInterfaces;
        const q = (this.bootstrapListSearch || "").trim().toLowerCase();
        if (!q) {
            return list;
        }
        return list.filter((iface) => {
            const parts = [
                iface.name,
                iface.type,
                iface.reachable_on,
                String(iface.port ?? ""),
                iface.status,
                iface.discovery_hash,
            ].filter(Boolean);
            return parts.join(" ").toLowerCase().includes(q);
        });
    }

    get filteredCommunityForBootstrap(): CommunityInterface[] {
        const list = this.communityInterfaces;
        const q = (this.bootstrapListSearch || "").trim().toLowerCase();
        if (!q) {
            return list;
        }
        return list.filter((iface) => {
            const parts = [iface.name, iface.target_host, String(iface.target_port ?? ""), iface.type].filter(Boolean);
            return parts.join(" ").toLowerCase().includes(q);
        });
    }

    get selectedBootstrapCount(): number {
        return this.selectedBootstrapKeys.length;
    }

    get bootstrapSelectedLabels(): string[] {
        return this.selectedBootstrapKeys.map((key) => this.bootstrapDisplayLabelForKey(key)).filter(Boolean);
    }

    get reticulumBundledDocsUrl(): string {
        void this.localeVersion;
        return bundledReticulumDocsUrl(getCurrentUiLocale() || "en");
    }

    get hasIdentityImportInput(): boolean {
        return Boolean(this.identityImportFile || this.normalizeBase32(this.identityImportBase32));
    }

    get showFooterContinue(): boolean {
        if (this.currentStep === 3 || this.currentStep === 4) {
            return false;
        }
        return this.currentStep < this.totalSteps;
    }

    get connectionSetupBusy(): boolean {
        return this.addingRecommended || this.savingDiscovery || this.addingLocal || this.reloadingReticulum;
    }

    get bootstrapPickBusy(): boolean {
        return this.pickingRandomBootstraps || this.loadingInterfaces || this.loadingDiscovered;
    }

    get bootstrapActionBusy(): boolean {
        return this.pickingRandomBootstraps || this.addingBootstraps || this.reloadingReticulum;
    }

    get tutorialNavBusy(): boolean {
        return (
            this.connectionSetupBusy ||
            this.bootstrapActionBusy ||
            this.savingPropagation ||
            this.finishingTutorial ||
            this.identityImportInProgress
        );
    }

    /** Translate through the kernel adapter, re-reading when the locale flips. */
    t(key: string, values?: Record<string, unknown>): string {
        void this.localeVersion;
        return t(key, values);
    }

    onWindowResize(): void {
        if (typeof window !== "undefined") {
            this.windowWidth = window.innerWidth;
        }
    }

    /** Page hosts start loading immediately. Modal hosts wait for show(). */
    mountPage(): void {
        void this.loadIdentitySetupDefaults();
        void this.loadDiscoveryBootstrapDefaults();
        void this.loadCommunityInterfaces();
        void this.loadDiscoveredInterfaces();
        void this.refreshMigrationOffer();
        this.refreshAndroidStorageSetup();
        this.startDiscoveryPolling();
    }

    destroy(): void {
        this.stopDiscoveryPolling();
    }

    private startDiscoveryPolling(): void {
        this.stopDiscoveryPolling();
        this.discoveryInterval = setInterval(() => {
            void this.loadDiscoveredInterfaces();
        }, DISCOVERY_POLL_MS);
    }

    private stopDiscoveryPolling(): void {
        if (this.discoveryInterval) {
            clearInterval(this.discoveryInterval);
            this.discoveryInterval = null;
        }
    }

    private setStep(step: number): void {
        this.currentStep = step;
        if (step === 4) {
            void this.maybeAutoPickBootstrapTcp();
        }
    }

    resetIdentitySetupState(): void {
        this.identityMode = "new";
        this.identityName = "";
        this.identityImportBase32 = "";
        this.identityImportFile = null;
        this.identityImportError = "";
        this.identityImportInProgress = false;
        this.identityImportedHash = null;
        this.originalIdentityHash = null;
        this.finishingTutorial = false;
    }

    setIdentityMode(mode: IdentityMode): void {
        this.identityMode = mode;
        this.identityImportError = "";
        if (mode === "new") {
            this.identityImportFile = null;
            this.identityImportBase32 = "";
            this.identityImportedHash = null;
        }
    }

    normalizeBase32(value: unknown): string {
        return String(value || "").replace(/\s+/g, "");
    }

    onIdentityImportBase32Input(): void {
        this.identityImportedHash = null;
        this.identityImportError = "";
    }

    async loadIdentitySetupDefaults(): Promise<void> {
        try {
            const [identitiesRes, configRes] = await Promise.all([
                window.api.get("/api/v1/identities"),
                window.api.get("/api/v1/config"),
            ]);
            const identities = identitiesRes.data?.identities ?? [];
            const currentIdentity = identities.find((item: { is_current?: boolean }) => item.is_current);
            this.originalIdentityHash = currentIdentity?.hash || null;
            this.identityName = configRes.data?.config?.display_name || this.defaultUsername;
        } catch (e) {
            console.error("Failed to load identity setup defaults:", e);
            this.identityName = this.defaultUsername;
        }
    }

    /**
     * Accept an identity key file. Empty and oversized payloads are rejected
     * here as well as on the server.
     */
    onIdentityImportFileChange(event: Event): void {
        const input = event.target as HTMLInputElement | null;
        const file = input?.files?.[0] || null;
        this.identityImportedHash = null;
        this.identityImportError = "";
        if (file && file.size === 0) {
            this.identityImportFile = null;
            this.identityImportError = t("tutorial.identity_import_empty_file");
        } else if (file && file.size > MAX_IDENTITY_KEY_BYTES) {
            this.identityImportFile = null;
            this.identityImportError = t("tutorial.identity_import_file_too_large");
        } else {
            this.identityImportFile = file;
        }
        if (input) {
            input.value = "";
        }
    }

    private async importIdentityFromFile(file: File, displayName: string): Promise<string | null> {
        const formData = new FormData();
        formData.append("file", file);
        if (displayName) {
            formData.append("display_name", displayName);
        }
        const response = await window.api.post("/api/v1/identity/restore", formData, {
            headers: { "Content-Type": "multipart/form-data" },
        });
        return response.data?.identity?.hash || null;
    }

    private async importIdentityFromBase32(base32: string, displayName: string): Promise<string | null> {
        const payload: Record<string, string> = { base32: this.normalizeBase32(base32) };
        if (displayName) {
            payload.display_name = displayName;
        }
        const response = await window.api.post("/api/v1/identity/restore", payload);
        return response.data?.identity?.hash || null;
    }

    /**
     * Step 2 Continue. Creating a new identity only renames the current one.
     * Importing restores the key now and defers activation to Finish.
     */
    async handleIdentityContinue(): Promise<void> {
        if (this.identityImportInProgress) {
            return;
        }
        const trimmedName = this.identityName.trim() || this.defaultUsername;
        this.identityImportError = "";
        if (this.identityMode === "new") {
            try {
                await window.api.patch("/api/v1/config", { display_name: trimmedName });
                (GlobalState.config as Record<string, unknown>).display_name = trimmedName;
                this.identityImportedHash = null;
                this.setStep(3);
            } catch (e) {
                this.identityImportError = apiErrorMessage(e, "tutorial.identity_name_update_failed");
            }
            return;
        }
        if (!this.hasIdentityImportInput) {
            this.identityImportError = t("tutorial.identity_import_required");
            return;
        }
        this.identityImportInProgress = true;
        try {
            let importedHash: string | null = null;
            if (this.identityImportFile) {
                importedHash = await this.importIdentityFromFile(this.identityImportFile, trimmedName);
                this.identityImportFile = null;
            } else {
                importedHash = await this.importIdentityFromBase32(this.identityImportBase32, trimmedName);
                this.identityImportBase32 = "";
            }
            if (!importedHash) {
                throw new Error("Missing imported identity hash");
            }
            this.identityImportedHash = importedHash;
            this.setStep(3);
        } catch (e) {
            this.identityImportError = apiErrorMessage(e, "tutorial.identity_import_failed");
        } finally {
            this.identityImportInProgress = false;
        }
    }

    async toggleTheme(): Promise<void> {
        const newTheme = this.theme === "dark" ? "light" : "dark";
        try {
            await window.api.patch("/api/v1/config", { theme: newTheme });
            (GlobalState.config as Record<string, unknown>).theme = newTheme;
            this.theme = newTheme;
        } catch (e) {
            console.error("Failed to update theme:", e);
        }
    }

    async onLanguageChange(langCode: string): Promise<void> {
        const code = normalizeUiLocaleCode(langCode);
        try {
            await setLocale(null, code);
            this.localeVersion += 1;
            await window.api.patch("/api/v1/config", { language: code });
            (GlobalState.config as Record<string, unknown>).language = code;
        } catch (e) {
            console.error("Failed to update language:", e);
        }
    }

    /** Modal entry point. Resets the wizard and refills every list. */
    async show(): Promise<void> {
        this.visible = true;
        this.currentStep = 1;
        this.resetIdentitySetupState();
        this.interfaceAddedViaTutorial = false;
        this.connectionMode = null;
        this.selectedBootstrapKeys = [];
        this.addedBootstrapKeys = [];
        this.bootstrapListSearch = "";
        this.bootstrapDiscoveredSectionOpen = true;
        this.bootstrapCommunitySectionOpen = true;
        this.bootstrapAutoPickDone = false;
        await this.refreshMigrationOffer();
        this.refreshAndroidStorageSetup();
        await this.loadIdentitySetupDefaults();
        await this.loadDiscoveryBootstrapDefaults();
        await this.loadCommunityInterfaces();
        await this.loadDiscoveredInterfaces();
        this.startDiscoveryPolling();
    }

    isOpen(): boolean {
        return this.visible;
    }

    hide(): void {
        this.setHidden();
    }

    /**
     * Closing without finishing still marks the tutorial seen, and warns when
     * an imported identity was never activated.
     */
    private setHidden(): void {
        if (!this.visible) {
            return;
        }
        this.visible = false;
        if (this.identityImportedHash && this.identityImportedHash !== this.originalIdentityHash) {
            ToastUtils.warning(t("tutorial.identity_import_pending_kept"));
        }
        void this.markSeen();
    }

    async loadCommunityInterfaces(): Promise<void> {
        this.loadingInterfaces = true;
        try {
            const response = await window.api.get("/api/v1/community-interfaces");
            this.communityInterfaces = response.data.interfaces;
        } catch (e) {
            console.error("Failed to load community interfaces:", e);
        } finally {
            this.loadingInterfaces = false;
        }
        void this.maybeAutoPickBootstrapTcp();
    }

    async loadDiscoveredInterfaces(): Promise<void> {
        this.loadingDiscovered = true;
        try {
            const response = await window.api.get("/api/v1/reticulum/discovered-interfaces");
            this.discoveredInterfaces = response.data?.interfaces ?? [];
        } catch (e) {
            console.error("Failed to load discovered interfaces:", e);
        } finally {
            this.loadingDiscovered = false;
        }
        void this.maybeAutoPickBootstrapTcp();
    }

    async refreshMigrationOffer(): Promise<void> {
        this.migrationOffer = null;
        try {
            const response = await window.api.get("/api/v1/app/info");
            const offer = response.data?.app_info?.migration;
            if (offer && offer.show_choice) {
                this.migrationOffer = offer;
            }
        } catch (e) {
            console.error("Failed to load migration status:", e);
        }
    }

    private ensureAndroidStorageBridge(): AndroidStorageBridge {
        if (!this.androidStorageBridge) {
            this.androidStorageBridge = new AndroidStorageBridge();
        }
        return this.androidStorageBridge;
    }

    refreshAndroidStorageSetup(): void {
        this.androidStorageSetup = null;
        const bridge = this.ensureAndroidStorageBridge();
        if (!bridge.isAndroidHost()) {
            return;
        }
        const status = bridge.getStatus();
        if (status?.needs_setup_choice) {
            this.androidStorageSetup = status;
            this.androidStorageSetupChoice = status.active_mode === "internal" ? "internal" : "external";
        }
    }

    async applyAndroidStorageSetup(): Promise<void> {
        if (this.androidStorageBusy || !this.androidStorageSetup) {
            return;
        }
        const bridge = this.ensureAndroidStorageBridge();
        const mode = this.androidStorageSetupChoice || "external";
        this.androidStorageBusy = true;
        try {
            const result = bridge.applySetupChoice(mode, this.androidStorageSetup);
            if (result.restarted) {
                ToastUtils.success(t("android_storage.restart_to_apply"));
            } else {
                this.androidStorageSetup = null;
            }
        } catch (e) {
            ToastUtils.error(t("android_storage.failed"));
            console.error(e);
        } finally {
            this.androidStorageBusy = false;
        }
    }

    async migrationMigrate(): Promise<void> {
        await this.runStorageMigration("migrate");
    }

    async migrationFresh(): Promise<void> {
        await this.runStorageMigration("fresh");
    }

    private async runStorageMigration(action: "migrate" | "fresh"): Promise<void> {
        if (this.migrationBusy || !this.migrationOffer) {
            return;
        }
        this.migrationBusy = true;
        try {
            await window.api.post("/api/v1/setup/storage-migration", { action });
            ToastUtils.success(t("tutorial.migration_done_restart"));
            if (window.electron && typeof window.electron.relaunch === "function") {
                await window.electron.relaunch();
            }
        } catch (e) {
            ToastUtils.error(apiErrorMessage(e, "tutorial.migration_failed"));
            console.error(e);
        } finally {
            this.migrationBusy = false;
        }
    }

    async reloadReticulum(): Promise<boolean> {
        this.reloadingReticulum = true;
        try {
            await window.api.post("/api/v1/reticulum/reload");
            GlobalState.hasPendingInterfaceChanges = false;
            if (GlobalState.modifiedInterfaceNames && GlobalState.modifiedInterfaceNames.clear) {
                GlobalState.modifiedInterfaceNames.clear();
            }
            return true;
        } catch (e) {
            console.error("Failed to reload Reticulum:", e);
            ToastUtils.error(t("tutorial.failed_reload_rns"));
            return false;
        } finally {
            this.reloadingReticulum = false;
        }
    }

    async useRecommendedMode(): Promise<void> {
        if (this.connectionSetupBusy) {
            return;
        }
        this.addingRecommended = true;
        try {
            await window.api.post("/api/v1/reticulum/interfaces/add", {
                name: "Local Network",
                type: "AutoInterface",
                enabled: true,
            });
            GlobalState.hasPendingInterfaceChanges = true;
            GlobalState.modifiedInterfaceNames.add("Local Network");

            await window.api.patch("/api/v1/reticulum/discovery", {
                discover_interfaces: true,
                autoconnect_discovered_interfaces: 3,
                default_bootstrap_only: false,
            });
            this.defaultBootstrapOnly = false;

            ToastUtils.success(t("tutorial.mode_recommended_added"));
            this.connectionMode = "recommended";
            this.setStep(4);
            this.bootstrapListSearch = "";
            this.bootstrapDiscoveredSectionOpen = true;
            this.bootstrapCommunitySectionOpen = true;
            this.bootstrapAutoPickDone = false;
            await this.loadCommunityInterfaces();
            await this.loadDiscoveredInterfaces();
            await this.pickRandomTcpBootstraps({ silent: true, auto: true, count: 3 });
            this.bootstrapAutoPickDone = true;
            this.interfaceAddedViaTutorial = true;
        } catch (e) {
            console.error("Failed to apply recommended connection mode:", e);
            ToastUtils.error(apiErrorMessage(e, "tutorial.failed_add_local"));
        } finally {
            this.addingRecommended = false;
        }
    }

    async useDiscoveryMode(): Promise<void> {
        if (this.connectionSetupBusy) {
            return;
        }
        this.savingDiscovery = true;
        try {
            await window.api.patch("/api/v1/reticulum/discovery", {
                discover_interfaces: true,
                autoconnect_discovered_interfaces: 3,
                default_bootstrap_only: false,
            });
            this.defaultBootstrapOnly = false;
            ToastUtils.success(t("tutorial.discovery_enabled"));
            this.connectionMode = "discovery";
            this.setStep(4);
            this.bootstrapListSearch = "";
            this.bootstrapDiscoveredSectionOpen = true;
            this.bootstrapCommunitySectionOpen = true;
            this.bootstrapAutoPickDone = false;
            await this.loadCommunityInterfaces();
            await this.loadDiscoveredInterfaces();
            await this.maybeAutoPickBootstrapTcp();
        } catch (e) {
            console.error("Failed to enable discovery:", e);
            ToastUtils.error(t("tutorial.failed_enable_discovery"));
        } finally {
            this.savingDiscovery = false;
        }
    }

    async useLocalMode(): Promise<void> {
        if (this.connectionSetupBusy) {
            return;
        }
        this.addingLocal = true;
        try {
            await window.api.post("/api/v1/reticulum/interfaces/add", {
                name: "Local Network",
                type: "AutoInterface",
                enabled: true,
            });
            this.interfaceAddedViaTutorial = true;
            GlobalState.hasPendingInterfaceChanges = true;
            GlobalState.modifiedInterfaceNames.add("Local Network");
            ToastUtils.success(t("tutorial.local_added"));
            const reloaded = await this.reloadReticulum();
            if (!reloaded) {
                return;
            }
            this.connectionMode = "local";
            this.setStep(5);
        } catch (e) {
            console.error("Failed to add AutoInterface:", e);
            ToastUtils.error(apiErrorMessage(e, "tutorial.failed_add_local"));
        } finally {
            this.addingLocal = false;
        }
    }

    useManualMode(): void {
        if (this.connectionSetupBusy) {
            return;
        }
        this.connectionMode = "manual";
        this.setStep(5);
    }

    isBootstrapSelected(key: string): boolean {
        return this.selectedBootstrapKeys.includes(key);
    }

    toggleBootstrap(key: string): void {
        if (this.bootstrapActionBusy) {
            return;
        }
        if (this.selectedBootstrapKeys.includes(key)) {
            this.selectedBootstrapKeys = this.selectedBootstrapKeys.filter((candidate) => candidate !== key);
        } else {
            this.selectedBootstrapKeys = [...this.selectedBootstrapKeys, key];
        }
    }

    bootstrapDisplayLabelForKey(key: string): string {
        if (!key) {
            return "";
        }
        if (key.startsWith("comm:")) {
            const name = key.slice(5);
            const iface = this.communityInterfaces.find((candidate) => candidate.name === name);
            return iface?.name || name;
        }
        if (key.startsWith("disc:")) {
            const suffix = key.slice(5);
            const iface = this.discoveredInterfaces.find(
                (candidate) => String(candidate.discovery_hash || candidate.name) === suffix
            );
            return iface?.name || suffix;
        }
        return key;
    }

    /**
     * Yggdrasil-only community entries are skipped by the random picker because
     * they need an overlay the fresh install has not joined yet.
     */
    private communityBootstrapExcludedFromRandom(iface: CommunityInterface): boolean {
        const hay = `${String(iface.name || "")} ${String(iface.description || "")}`.toLowerCase();
        const host = String(iface.target_host || "").trim();
        if (hay.includes("yggdrasil")) {
            return true;
        }
        if (/\bygg\b/.test(hay) || hay.includes("-ygg") || hay.includes(" ygg") || hay.includes("(ygg")) {
            return true;
        }
        if (/^(200|201|202|203):[0-9a-f:]+$/i.test(host)) {
            return true;
        }
        return false;
    }

    private pickEligibleCommunityTcpBootstrapForRandom(): BootstrapEntry[] {
        const out: BootstrapEntry[] = [];
        for (const iface of this.communityInterfaces) {
            const type = iface.type;
            if (type !== "TCPClientInterface" && type !== "BackboneInterface") {
                continue;
            }
            const host = String(iface.target_host || "").trim();
            const port = iface.target_port;
            if (!host || port === undefined || port === null || port === "") {
                continue;
            }
            if (this.communityBootstrapExcludedFromRandom(iface)) {
                continue;
            }
            out.push({
                key: `comm:${iface.name}`,
                kind: "community",
                iface: iface as CommunityInterface & DiscoveredInterface,
                dedupe: `${host.toLowerCase()}:${Number(port)}`,
            });
        }
        return out;
    }

    private dedupeBootstrapEntries(entries: BootstrapEntry[]): BootstrapEntry[] {
        const seen = new Set<string>();
        const deduped: BootstrapEntry[] = [];
        for (const entry of entries) {
            if (seen.has(entry.dedupe)) {
                continue;
            }
            seen.add(entry.dedupe);
            deduped.push(entry);
        }
        return deduped;
    }

    private shuffleArrayInPlace(arr: BootstrapEntry[]): void {
        for (let i = arr.length - 1; i > 0; i--) {
            const j = Math.floor(Math.random() * (i + 1));
            [arr[i], arr[j]] = [arr[j], arr[i]];
        }
    }

    async pickRandomTcpBootstraps(options: PickRandomOptions = {}): Promise<void> {
        const silent = options.silent === true;
        const auto = options.auto === true;
        if (this.pickingRandomBootstraps) {
            return;
        }
        this.pickingRandomBootstraps = true;
        // Yield once so the busy spinner can paint before selection work.
        await Promise.resolve();
        try {
            const entries = this.dedupeBootstrapEntries(this.pickEligibleCommunityTcpBootstrapForRandom());
            if (entries.length === 0) {
                if (!silent && !auto) {
                    ToastUtils.warning(t("tutorial.bootstrap_pick_random_none"));
                }
                return;
            }
            this.shuffleArrayInPlace(entries);
            const wanted = Number.isFinite(options.count) ? Number(options.count) : 3;
            const take = Math.min(Math.max(1, wanted), entries.length);
            this.selectedBootstrapKeys = entries.slice(0, take).map((entry) => entry.key);
            const labels = this.selectedBootstrapKeys.map((key) => this.bootstrapDisplayLabelForKey(key));
            if (!silent && !auto) {
                ToastUtils.success(t("tutorial.bootstrap_pick_random_done", { count: take, names: labels.join(", ") }));
            }
        } finally {
            this.pickingRandomBootstraps = false;
        }
    }

    async maybeAutoPickBootstrapTcp(): Promise<void> {
        if (this.bootstrapAutoPickDone) {
            return;
        }
        if (this.currentStep !== 4 || this.connectionMode !== "discovery") {
            return;
        }
        if (this.selectedBootstrapKeys.length > 0) {
            return;
        }
        if (this.pickingRandomBootstraps) {
            return;
        }
        const entries = this.dedupeBootstrapEntries(this.pickEligibleCommunityTcpBootstrapForRandom());
        if (entries.length === 0) {
            return;
        }
        await this.pickRandomTcpBootstraps({ silent: true, auto: true });
        if (this.selectedBootstrapKeys.length > 0) {
            this.bootstrapAutoPickDone = true;
        }
    }

    private buildBootstrapPayload(item: BootstrapEntry): Record<string, unknown> {
        const iface = item.iface;
        if (item.kind === "discovered") {
            const payload: Record<string, unknown> = {
                name: iface.name || `Discovered ${iface.discovery_hash || ""}`.trim(),
                type: iface.type === "BackboneInterface" ? "TCPClientInterface" : iface.type,
                enabled: true,
                bootstrap_only: this.defaultBootstrapOnly === true,
            };
            if (iface.reachable_on) {
                payload.target_host = iface.reachable_on;
            }
            if (iface.port) {
                payload.target_port = iface.port;
            }
            return payload;
        }
        return {
            name: iface.name,
            type: iface.type,
            target_host: iface.target_host,
            target_port: iface.target_port,
            enabled: true,
            bootstrap_only: this.defaultBootstrapOnly === true,
        };
    }

    private parseDiscoveryBool(value: unknown, defaultValue = false): boolean {
        if (value === undefined || value === null || value === "") {
            return defaultValue;
        }
        if (typeof value === "string") {
            return ["true", "yes", "1", "y", "on"].includes(value.toLowerCase());
        }
        return Boolean(value);
    }

    async loadDiscoveryBootstrapDefaults(): Promise<void> {
        try {
            const response = await window.api.get("/api/v1/reticulum/discovery");
            const discovery = response.data?.discovery ?? {};
            this.defaultBootstrapOnly = this.parseDiscoveryBool(discovery.default_bootstrap_only, false);
        } catch (e) {
            console.error(e);
            this.defaultBootstrapOnly = false;
        }
    }

    async persistDefaultBootstrapOnly(value: boolean): Promise<void> {
        try {
            await window.api.patch("/api/v1/reticulum/discovery", { default_bootstrap_only: value === true });
            this.defaultBootstrapOnly = value === true;
        } catch (e) {
            console.error("Failed to save default_bootstrap_only:", e);
            ToastUtils.error(t("tutorial.failed_save_bootstrap_only"));
            this.defaultBootstrapOnly = !value;
        }
    }

    async confirmBootstraps(): Promise<void> {
        if (this.bootstrapActionBusy) {
            return;
        }
        if (this.selectedBootstrapKeys.length === 0) {
            ToastUtils.warning(t("tutorial.bootstrap_pick_at_least_one"));
            return;
        }
        this.addingBootstraps = true;
        const items: BootstrapEntry[] = [];
        for (const key of this.selectedBootstrapKeys) {
            if (this.addedBootstrapKeys.includes(key)) {
                continue;
            }
            if (key.startsWith("comm:")) {
                const iface = this.communityInterfaces.find((candidate) => `comm:${candidate.name}` === key);
                if (iface) {
                    items.push({
                        key,
                        kind: "community",
                        iface: iface as CommunityInterface & DiscoveredInterface,
                        dedupe: key,
                    });
                }
            } else if (key.startsWith("disc:")) {
                const iface = this.discoveredInterfaces.find(
                    (candidate) => `disc:${candidate.discovery_hash || candidate.name}` === key
                );
                if (iface) {
                    items.push({
                        key,
                        kind: "discovered",
                        iface: iface as CommunityInterface & DiscoveredInterface,
                        dedupe: key,
                    });
                }
            }
        }
        let added = 0;
        for (const item of items) {
            try {
                const payload = this.buildBootstrapPayload(item);
                if (!payload.target_host) {
                    continue;
                }
                await window.api.post("/api/v1/reticulum/interfaces/add", payload);
                this.addedBootstrapKeys = [...this.addedBootstrapKeys, item.key];
                GlobalState.hasPendingInterfaceChanges = true;
                GlobalState.modifiedInterfaceNames.add(String(payload.name));
                added += 1;
            } catch (e) {
                console.error("Failed to add bootstrap interface:", e);
                ToastUtils.error(apiErrorMessage(e, "tutorial.failed_add_bootstrap"));
            }
        }
        if (added === 0) {
            ToastUtils.warning(t("tutorial.failed_add_bootstrap_none"));
            this.addingBootstraps = false;
            return;
        }
        this.interfaceAddedViaTutorial = true;
        ToastUtils.success(t("tutorial.bootstrap_added", { count: added }));
        const reloaded = await this.reloadReticulum();
        this.addingBootstraps = false;
        if (reloaded) {
            this.setStep(5);
        }
    }

    skipBootstraps(): void {
        if (this.bootstrapActionBusy) {
            return;
        }
        this.setStep(5);
    }

    async enableAutoPropagation(): Promise<void> {
        this.savingPropagation = true;
        try {
            await window.api.patch("/api/v1/config", {
                lxmf_preferred_propagation_node_auto_select: true,
            });
            if (GlobalState.config) {
                (GlobalState.config as Record<string, unknown>).lxmf_preferred_propagation_node_auto_select = true;
            }
            ToastUtils.success(t("tutorial.auto_propagation_enabled"));
            this.nextStep();
        } catch (e) {
            console.error("Failed to enable auto-propagation:", e);
            ToastUtils.error(apiErrorMessage(e, "tutorial.failed_enable_propagation"));
        } finally {
            this.savingPropagation = false;
        }
    }

    getDiscoveryIcon(iface: DiscoveredInterface): string {
        switch (iface.type) {
            case "AutoInterface":
                return "home-automation";
            case "RNodeInterface":
                return iface.port && iface.port.toString().startsWith("tcp://") ? "lan-connect" : "radio-tower";
            case "RNodeMultiInterface":
                return "access-point-network";
            case "TCPClientInterface":
            case "BackboneInterface":
                return "lan-connect";
            case "TCPServerInterface":
                return "lan";
            case "UDPInterface":
                return "wan";
            case "SerialInterface":
                return "usb-port";
            case "KISSInterface":
            case "AX25KISSInterface":
                return "antenna";
            case "I2PInterface":
                return "eye";
            case "PipeInterface":
                return "pipe";
            default:
                return "server-network";
        }
    }

    /** Leave the tutorial for another page, resolving a pending import first. */
    gotoRoute(routeName: string): void {
        void this.closeWithPendingImportGuard().then((closed) => {
            if (!closed) {
                return;
            }
            void navigate({ name: routeName });
        });
    }

    async closeWithPendingImportGuard(): Promise<boolean> {
        if (this.identityImportedHash && this.identityImportedHash !== this.originalIdentityHash) {
            const activate = await DialogUtils.confirm(t("tutorial.identity_import_pending_activate"));
            if (activate) {
                const activated = await this.activateImportedIdentity();
                if (!activated) {
                    return false;
                }
            } else {
                ToastUtils.warning(t("tutorial.identity_import_pending_kept"));
            }
        }
        if (!this.isPage) {
            this.visible = false;
        }
        return true;
    }

    async handlePrimaryAction(): Promise<void> {
        if (this.currentStep === 2) {
            await this.handleIdentityContinue();
            return;
        }
        this.nextStep();
    }

    nextStep(): void {
        if (this.currentStep >= this.totalSteps) {
            return;
        }
        if (this.currentStep === 3) {
            if (!this.connectionMode) {
                ToastUtils.warning(t("tutorial.connect_mode_required"));
                return;
            }
            if (this.connectionMode !== "discovery" && this.connectionMode !== "recommended") {
                this.setStep(5);
                return;
            }
        }
        if (this.currentStep === 4) {
            ToastUtils.warning(t("tutorial.bootstrap_pick_at_least_one"));
            return;
        }
        let next = this.currentStep + 1;
        if (next === 6 || next === 7) {
            next = 8;
        }
        if (next === 4) {
            this.bootstrapListSearch = "";
            this.bootstrapDiscoveredSectionOpen = true;
            this.bootstrapCommunitySectionOpen = true;
        }
        this.setStep(next);
    }

    previousStep(): void {
        if (this.tutorialNavBusy) {
            return;
        }
        if (this.currentStep <= 1) {
            return;
        }
        if (this.currentStep === 8) {
            this.setStep(5);
            return;
        }
        if (this.currentStep === 5 && this.connectionMode !== "discovery" && this.connectionMode !== "recommended") {
            this.setStep(3);
            return;
        }
        this.setStep(this.currentStep - 1);
    }

    async skipTutorial(): Promise<void> {
        if (this.tutorialNavBusy) {
            return;
        }
        if (!(await DialogUtils.confirm(t("tutorial.skip_confirm")))) {
            return;
        }
        if (this.identityImportedHash && this.identityImportedHash !== this.originalIdentityHash) {
            const activate = await DialogUtils.confirm(t("tutorial.identity_import_pending_activate"));
            if (activate) {
                const activated = await this.activateImportedIdentity();
                if (!activated) {
                    return;
                }
            } else {
                ToastUtils.warning(t("tutorial.identity_import_pending_kept"));
            }
        }
        this.setHidden();
        void this.markSeen();
    }

    async markSeen(): Promise<void> {
        if (this.markingSeen) {
            return;
        }
        this.markingSeen = true;
        try {
            await window.api.post("/api/v1/app/tutorial/seen");
        } catch (e) {
            console.error("Failed to mark tutorial as seen:", e);
        } finally {
            this.markingSeen = false;
        }
    }

    /**
     * Switch to the identity restored in step 2 and drop the throwaway default.
     * A failed delete is reported separately from a failed switch.
     */
    async activateImportedIdentity(): Promise<boolean> {
        if (!this.identityImportedHash) {
            return true;
        }
        if (this.identityImportedHash === this.originalIdentityHash) {
            return true;
        }
        try {
            GlobalEmitter.emit("identity-switching-start");
            const response = await window.api.post("/api/v1/identities/switch", {
                identity_hash: this.identityImportedHash,
            });
            if (this.originalIdentityHash) {
                try {
                    await window.api.delete(`/api/v1/identities/${this.originalIdentityHash}`);
                } catch (deleteError) {
                    console.error("Failed to delete default identity after import:", deleteError);
                    ToastUtils.warning(t("tutorial.identity_default_delete_failed"));
                }
            }
            if (response?.data?.hotswapped) {
                GlobalEmitter.emit("identity-switched-apply", {
                    identity_hash: response.data.identity_hash ?? this.identityImportedHash,
                    display_name: response.data.display_name ?? "",
                    requires_reauth: Boolean(response.data.requires_reauth),
                });
            } else if (response?.data?.hotswapped === false) {
                ToastUtils.info(t("identities.switch_scheduled"));
                GlobalEmitter.emit("identity-switching-abort");
                setTimeout(() => {
                    window.location.reload();
                }, 1500);
            }
            this.identityImportedHash = null;
            return true;
        } catch (e) {
            ToastUtils.error(apiErrorMessage(e, "tutorial.identity_switch_failed"));
            GlobalEmitter.emit("identity-switching-abort");
            return false;
        }
    }

    async finishTutorial(): Promise<void> {
        if (this.finishingTutorial || this.tutorialNavBusy) {
            return;
        }
        this.finishingTutorial = true;
        try {
            if (GlobalState.hasPendingInterfaceChanges) {
                const reloaded = await this.reloadReticulum();
                if (!reloaded) {
                    return;
                }
            }
            if (this.identityImportedHash && this.identityImportedHash !== this.originalIdentityHash) {
                const activated = await this.activateImportedIdentity();
                if (!activated) {
                    return;
                }
            }
            await this.markSeen();
            this.visible = false;
            GlobalEmitter.emit("tutorial-finished");
            if (this.interfaceAddedViaTutorial) {
                ToastUtils.success(t("tutorial.ready_finished"));
            }
        } finally {
            this.finishingTutorial = false;
        }
    }
}
