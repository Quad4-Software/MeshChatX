// @ts-check
// SPDX-License-Identifier: 0BSD

import { computed, getCurrentInstance, onMounted, onUnmounted, ref } from "vue";

import DialogUtils from "../DialogUtils.js";
import GlobalEmitter from "../GlobalEmitter.js";
import { EMITTER_EVENTS } from "../constants.js";
import {
    NOMAD_FAVOURITES_LAYOUT_KEY,
    clearLocalNomadFavouritesLayout,
    loadNomadFavouritesLayout,
    readLocalNomadFavouritesLayout,
    saveNomadFavouritesLayout,
} from "../nomadFavouritesLayoutStore.js";

/**
 * Favourites section-layout state for NomadNetworkSidebar: favourites tab
 * search term, section list/order/membership, persisted layout hydration
 * and debounced save, favourites drag state, and inline section rename
 * state.
 *
 * The layout itself (sections, order, membership) is module-level shared
 * state: every NomadNet browser tab mounts its own sidebar, and per-tab
 * copies raced each other's debounced saves, so a stale tab could
 * overwrite edits made in another tab. One shared copy means one save
 * path and every tab renders the same layout. A storage listener keeps
 * separate windows in sync through the localStorage cache.
 *
 * Per-instance state (search term, rename editing, drag state) stays
 * inside the composable so each sidebar keeps its own UI context.
 *
 * options.t mirrors the host $t for translated default section names and
 * prompts. options.getFavourites returns the host favourites prop so the
 * layout can reconcile membership against the live list.
 */

const defaultSectionId = ref("default");
const sections = ref([]);
const sectionOrder = ref([]);
const favouritesBySection = ref({});
const favouriteLayoutLoadGen = ref(0);

let layoutPersistTimer = null;
let mountedSidebarCount = 0;
let sharedLayoutHydrated = false;
let sharedLayoutImportedHandler = null;
let sharedIdentitySwitchedHandler = null;
let sharedStorageHandler = null;
let activeT = (key) => key;
const ensureCallbacks = new Set();

function runEnsureCallbacks() {
    for (const ensure of ensureCallbacks) {
        ensure();
    }
}

function buildDefaultSection() {
    return {
        id: defaultSectionId.value,
        name: activeT("nomadnet.favourites"),
        collapsed: false,
    };
}

function resetDefaultSections() {
    const defaultSection = buildDefaultSection();
    sections.value = [defaultSection];
    sectionOrder.value = [defaultSection.id];
    favouritesBySection.value = { [defaultSection.id]: [] };
}

function applyFavouriteLayout(layout) {
    if (!layout) {
        if (sections.value.length === 0) {
            resetDefaultSections();
        }
        return;
    }
    sections.value = layout.sections || [];
    sectionOrder.value =
        layout.sectionOrder || (layout.sections ? layout.sections.map((section) => section.id) : sectionOrder.value);
    favouritesBySection.value = layout.favouritesBySection || {};
    if (sections.value.length === 0) {
        resetDefaultSections();
    }
}

async function reloadFavouriteLayoutFromStore() {
    const gen = ++favouriteLayoutLoadGen.value;
    const layout = await loadNomadFavouritesLayout(window.api);
    if (gen !== favouriteLayoutLoadGen.value) {
        return;
    }
    applyFavouriteLayout(layout);
    runEnsureCallbacks();
}

function persistFavouriteLayout(options = {}) {
    // User-driven saves invalidate in-flight remote loads so they cannot clobber edits.
    // Reconciliation persists (fromEnsure) must not, or the first hydrate is discarded.
    if (!options.fromEnsure) {
        favouriteLayoutLoadGen.value += 1;
    }
    const layout = {
        sections: sections.value,
        sectionOrder: sectionOrder.value,
        favouritesBySection: favouritesBySection.value,
    };
    const flush = () => {
        layoutPersistTimer = null;
        if (typeof window === "undefined" || !window.api) {
            return undefined;
        }
        return saveNomadFavouritesLayout(window.api, layout);
    };
    if (options.immediate) {
        if (layoutPersistTimer) {
            clearTimeout(layoutPersistTimer);
            layoutPersistTimer = null;
        }
        return flush();
    }
    if (layoutPersistTimer) {
        clearTimeout(layoutPersistTimer);
    }
    layoutPersistTimer = setTimeout(() => {
        void flush();
    }, 250);
    return undefined;
}

function registerSharedListeners() {
    if (!sharedLayoutImportedHandler) {
        sharedLayoutImportedHandler = () => {
            void reloadFavouriteLayoutFromStore();
        };
        GlobalEmitter.on(EMITTER_EVENTS.NOMADNET_FAVOURITES_LAYOUT_IMPORTED, sharedLayoutImportedHandler);
    }
    if (!sharedIdentitySwitchedHandler) {
        sharedIdentitySwitchedHandler = () => {
            clearLocalNomadFavouritesLayout();
            resetDefaultSections();
            void reloadFavouriteLayoutFromStore();
        };
        GlobalEmitter.on(EMITTER_EVENTS.IDENTITY_SWITCHED, sharedIdentitySwitchedHandler);
    }
    // Another window wrote the cached layout. Adopt it unless this window has
    // pending unsaved edits, which win within the debounce window.
    if (!sharedStorageHandler && typeof window !== "undefined") {
        sharedStorageHandler = (event) => {
            if (event.key !== NOMAD_FAVOURITES_LAYOUT_KEY || layoutPersistTimer) {
                return;
            }
            applyFavouriteLayout(readLocalNomadFavouritesLayout());
            runEnsureCallbacks();
        };
        window.addEventListener("storage", sharedStorageHandler);
    }
}

function unregisterSharedListeners() {
    if (sharedLayoutImportedHandler) {
        GlobalEmitter.off(EMITTER_EVENTS.NOMADNET_FAVOURITES_LAYOUT_IMPORTED, sharedLayoutImportedHandler);
        sharedLayoutImportedHandler = null;
    }
    if (sharedIdentitySwitchedHandler) {
        GlobalEmitter.off(EMITTER_EVENTS.IDENTITY_SWITCHED, sharedIdentitySwitchedHandler);
        sharedIdentitySwitchedHandler = null;
    }
    if (sharedStorageHandler && typeof window !== "undefined") {
        window.removeEventListener("storage", sharedStorageHandler);
        sharedStorageHandler = null;
    }
}

/** Test helper: reset shared layout state between cases. */
export function _resetNomadFavouritesLayoutSharedStateForTests() {
    sections.value = [];
    sectionOrder.value = [];
    favouritesBySection.value = {};
    favouriteLayoutLoadGen.value = 0;
    defaultSectionId.value = "default";
    if (layoutPersistTimer) {
        clearTimeout(layoutPersistTimer);
        layoutPersistTimer = null;
    }
    mountedSidebarCount = 0;
    sharedLayoutHydrated = false;
    ensureCallbacks.clear();
    unregisterSharedListeners();
    activeT = (key) => key;
}

export function useNomadFavouritesLayout(options = {}) {
    const { t = (key) => key, getFavourites = () => [] } = options;

    const favouritesSearchTerm = ref("");
    const editingSectionId = ref(null);
    const editingSectionName = ref("");
    const draggingFavouriteHash = ref(null);
    const draggingFavouriteHashes = ref([]);
    const draggingFavouriteSectionId = ref(null);
    const dragOverSectionId = ref(null);
    const draggingSectionId = ref(null);
    const draggingSectionOverId = ref(null);

    const orderedSections = computed(() => {
        const map = {};
        sections.value.forEach((section) => {
            map[section.id] = section;
        });
        const ids = sectionOrder.value.length > 0 ? sectionOrder.value : sections.value.map((section) => section.id);
        return ids.map((id) => map[id]).filter((section) => section);
    });

    const sectionsWithFavourites = computed(() => {
        const search = favouritesSearchTerm.value.toLowerCase();
        const favourites = getFavourites();
        return orderedSections.value.map((section) => {
            const hashes = favouritesBySection.value[section.id] || [];
            const sectionFavourites = hashes
                .map((hash) => favourites.find((fav) => fav.destination_hash === hash))
                .filter((fav) => fav)
                .filter((fav) => matchesFavouriteSearch(fav, search));
            return { ...section, favourites: sectionFavourites };
        });
    });

    const favouritesSearchNoResults = computed(() => {
        if (getFavourites().length === 0) {
            return false;
        }
        if (favouritesSearchTerm.value.trim() === "") {
            return false;
        }
        return !sectionsWithFavourites.value.some((section) => section.favourites.length > 0);
    });

    const collapsedFavouritePreview = computed(() => {
        const out = [];
        const max = 5;
        const favourites = getFavourites();
        for (const section of orderedSections.value) {
            const hashes = favouritesBySection.value[section.id] || [];
            for (const hash of hashes) {
                const fav = favourites.find((f) => f.destination_hash === hash);
                if (!fav) {
                    continue;
                }
                if (out.length >= max) {
                    return out;
                }
                out.push(fav);
            }
        }
        return out;
    });

    const flatVisibleFavouriteDestinationHashes = computed(() => {
        const out = [];
        for (const section of sectionsWithFavourites.value) {
            for (const fav of section.favourites) {
                out.push(fav.destination_hash);
            }
        }
        return out;
    });

    function loadFavouriteLayout() {
        void reloadFavouriteLayoutFromStore();
    }

    function matchesFavouriteSearch(favourite, searchTerm = favouritesSearchTerm.value.toLowerCase()) {
        const matchesDisplayName = favourite.display_name.toLowerCase().includes(searchTerm);
        const matchesCustomDisplayName = favourite.custom_display_name?.toLowerCase()?.includes(searchTerm) === true;
        const matchesDestinationHash = favourite.destination_hash.toLowerCase().includes(searchTerm);
        return matchesDisplayName || matchesCustomDisplayName || matchesDestinationHash;
    }

    function ensureFavouriteLayout() {
        const favourites = getFavourites();
        if (!Array.isArray(favourites) || favourites.length === 0) {
            return;
        }
        if (sections.value.length === 0) {
            resetDefaultSections();
        }
        const hashes = favourites.map((fav) => fav.destination_hash);
        const sectionIds = new Set();
        const sanitizedSections = [];
        sections.value.forEach((section) => {
            if (!section || !section.id || sectionIds.has(section.id)) {
                return;
            }
            sectionIds.add(section.id);
            sanitizedSections.push({
                id: section.id,
                name: section.name || t("nomadnet.favourites"),
                collapsed: section.collapsed === true ? true : false,
            });
        });
        if (!sectionIds.has(defaultSectionId.value)) {
            const defaultSection = buildDefaultSection();
            sanitizedSections.unshift(defaultSection);
            sectionIds.add(defaultSection.id);
        }
        const existingOrder = Array.isArray(sectionOrder.value) ? sectionOrder.value : [];
        const filteredOrder = existingOrder.filter((id) => sectionIds.has(id));
        const remaining = sanitizedSections.map((section) => section.id).filter((id) => !filteredOrder.includes(id));
        const nextSectionOrder = [...filteredOrder, ...remaining];

        const nextFavouritesBySection = {};
        sanitizedSections.forEach((section) => {
            const existing = favouritesBySection.value[section.id] || [];
            nextFavouritesBySection[section.id] = existing.filter((hash) => hashes.includes(hash));
        });
        const assigned = new Set(Object.values(nextFavouritesBySection).flat());
        hashes.forEach((hash) => {
            if (!assigned.has(hash)) {
                nextFavouritesBySection[defaultSectionId.value].push(hash);
                assigned.add(hash);
            }
        });

        const sectionsChanged = JSON.stringify(sections.value) !== JSON.stringify(sanitizedSections);
        const orderChanged = JSON.stringify(sectionOrder.value) !== JSON.stringify(nextSectionOrder);
        const favouritesChanged = JSON.stringify(favouritesBySection.value) !== JSON.stringify(nextFavouritesBySection);
        sections.value = sanitizedSections;
        sectionOrder.value = nextSectionOrder;
        favouritesBySection.value = nextFavouritesBySection;
        if (sectionsChanged || orderChanged || favouritesChanged) {
            persistFavouriteLayout({ fromEnsure: true });
        }
    }

    function moveFavouriteToSection(hash, targetSectionId, beforeHash = null) {
        moveFavouritesToSection([hash], targetSectionId, beforeHash);
    }

    function moveFavouritesToSection(hashes, targetSectionId, beforeHash = null) {
        const unique = [...new Set((hashes || []).filter(Boolean))];
        if (!unique.length || !targetSectionId) {
            return;
        }
        const updated = {};
        Object.keys(favouritesBySection.value).forEach((sectionKey) => {
            updated[sectionKey] = [...(favouritesBySection.value[sectionKey] || [])].filter(
                (value) => !unique.includes(value)
            );
        });

        if (!updated[targetSectionId]) {
            updated[targetSectionId] = [];
        }

        let targetList = [...updated[targetSectionId]];

        if (beforeHash && !unique.includes(beforeHash)) {
            const insertIndex = targetList.indexOf(beforeHash);
            if (insertIndex === -1) {
                targetList.push(...unique);
            } else {
                targetList.splice(insertIndex, 0, ...unique);
            }
        } else {
            targetList.push(...unique);
        }

        updated[targetSectionId] = targetList;
        favouritesBySection.value = updated;
        persistFavouriteLayout();
        draggingFavouriteHash.value = null;
        draggingFavouriteHashes.value = [];
        draggingFavouriteSectionId.value = null;
        dragOverSectionId.value = null;
    }

    function isFavouriteRowDragging(destinationHash) {
        return draggingFavouriteHashes.value.includes(destinationHash);
    }

    function toggleSectionCollapse(sectionId) {
        const idx = sections.value.findIndex((section) => section.id === sectionId);
        if (idx === -1) {
            return;
        }
        const updated = [...sections.value];
        const section = { ...updated[idx] };
        section.collapsed = !section.collapsed;
        updated[idx] = section;
        sections.value = updated;
        persistFavouriteLayout();
    }

    async function createSection() {
        const name = await DialogUtils.prompt(t("nomadnet.enter_section_name"), t("nomadnet.new_section"));
        if (!name) {
            return;
        }
        const section = {
            id: `section-${Date.now()}`,
            name,
            collapsed: false,
        };
        sections.value = [...sections.value, section];
        sectionOrder.value = [...sectionOrder.value, section.id];
        favouritesBySection.value = { ...favouritesBySection.value, [section.id]: [] };
        persistFavouriteLayout();
    }

    function saveSectionName() {
        if (!editingSectionId.value) return;
        const sectionId = editingSectionId.value;
        const name = editingSectionName.value.trim();
        if (name) {
            sections.value = sections.value.map((sec) => (sec.id === sectionId ? { ...sec, name } : sec));
            persistFavouriteLayout();
        }
        cancelEditingSection();
    }

    function cancelEditingSection() {
        editingSectionId.value = null;
        editingSectionName.value = "";
    }

    if (getCurrentInstance()) {
        onMounted(() => {
            activeT = t;
            mountedSidebarCount += 1;
            if (!sharedLayoutHydrated) {
                // Paint immediately from local cache/defaults, then hydrate from the identity DB.
                sharedLayoutHydrated = true;
                applyFavouriteLayout(readLocalNomadFavouritesLayout());
                void reloadFavouriteLayoutFromStore();
            }
            ensureFavouriteLayout();
            ensureCallbacks.add(ensureFavouriteLayout);
            registerSharedListeners();
        });
        onUnmounted(() => {
            ensureCallbacks.delete(ensureFavouriteLayout);
            mountedSidebarCount -= 1;
            if (mountedSidebarCount > 0) {
                return;
            }
            mountedSidebarCount = 0;
            sharedLayoutHydrated = false;
            if (layoutPersistTimer) {
                clearTimeout(layoutPersistTimer);
                layoutPersistTimer = null;
                persistFavouriteLayout({ immediate: true });
            }
            unregisterSharedListeners();
        });
    }

    return {
        favouritesSearchTerm,
        defaultSectionId,
        sections,
        sectionOrder,
        favouritesBySection,
        favouriteLayoutLoadGen,
        editingSectionId,
        editingSectionName,
        draggingFavouriteHash,
        draggingFavouriteHashes,
        draggingFavouriteSectionId,
        dragOverSectionId,
        draggingSectionId,
        draggingSectionOverId,
        orderedSections,
        sectionsWithFavourites,
        favouritesSearchNoResults,
        collapsedFavouritePreview,
        flatVisibleFavouriteDestinationHashes,
        applyFavouriteLayout,
        reloadFavouriteLayoutFromStore,
        loadFavouriteLayout,
        matchesFavouriteSearch,
        buildDefaultSection,
        resetDefaultSections,
        persistFavouriteLayout,
        ensureFavouriteLayout,
        moveFavouriteToSection,
        moveFavouritesToSection,
        isFavouriteRowDragging,
        toggleSectionCollapse,
        createSection,
        saveSectionName,
        cancelEditingSection,
    };
}
