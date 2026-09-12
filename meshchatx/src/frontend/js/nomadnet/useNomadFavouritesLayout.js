// @ts-check
// SPDX-License-Identifier: 0BSD

import { computed, getCurrentInstance, onMounted, onUnmounted, ref } from "vue";

import DialogUtils from "../DialogUtils.js";
import GlobalEmitter from "../GlobalEmitter.js";
import { EMITTER_EVENTS } from "../constants.js";
import {
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
 * options.t mirrors the host $t for translated default section names and
 * prompts. options.getFavourites returns the host favourites prop so the
 * layout can reconcile membership against the live list.
 */
export function useNomadFavouritesLayout(options = {}) {
    const { t = (key) => key, getFavourites = () => [] } = options;

    const favouritesSearchTerm = ref("");
    const defaultSectionId = ref("default");
    const sections = ref([]);
    const sectionOrder = ref([]);
    const favouritesBySection = ref({});
    const favouriteLayoutLoadGen = ref(0);
    const editingSectionId = ref(null);
    const editingSectionName = ref("");
    const draggingFavouriteHash = ref(null);
    const draggingFavouriteHashes = ref([]);
    const draggingFavouriteSectionId = ref(null);
    const dragOverSectionId = ref(null);
    const draggingSectionId = ref(null);
    const draggingSectionOverId = ref(null);

    let layoutPersistTimer = null;
    let onLayoutImported = null;
    let onIdentitySwitched = null;

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

    function applyFavouriteLayout(layout) {
        if (!layout) {
            if (sections.value.length === 0) {
                resetDefaultSections();
            }
            return;
        }
        sections.value = layout.sections || [];
        sectionOrder.value =
            layout.sectionOrder ||
            (layout.sections ? layout.sections.map((section) => section.id) : sectionOrder.value);
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
        ensureFavouriteLayout();
    }

    function loadFavouriteLayout() {
        void reloadFavouriteLayoutFromStore();
    }

    function matchesFavouriteSearch(favourite, searchTerm = favouritesSearchTerm.value.toLowerCase()) {
        const matchesDisplayName = favourite.display_name.toLowerCase().includes(searchTerm);
        const matchesCustomDisplayName = favourite.custom_display_name?.toLowerCase()?.includes(searchTerm) === true;
        const matchesDestinationHash = favourite.destination_hash.toLowerCase().includes(searchTerm);
        return matchesDisplayName || matchesCustomDisplayName || matchesDestinationHash;
    }

    function buildDefaultSection() {
        return {
            id: defaultSectionId.value,
            name: t("nomadnet.favourites"),
            collapsed: false,
        };
    }

    function resetDefaultSections() {
        const defaultSection = buildDefaultSection();
        sections.value = [defaultSection];
        sectionOrder.value = [defaultSection.id];
        favouritesBySection.value = { [defaultSection.id]: [] };
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
            // Paint immediately from local cache/defaults, then hydrate from the identity DB.
            applyFavouriteLayout(readLocalNomadFavouritesLayout());
            ensureFavouriteLayout();
            reloadFavouriteLayoutFromStore();
            onLayoutImported = () => {
                reloadFavouriteLayoutFromStore();
            };
            GlobalEmitter.on(EMITTER_EVENTS.NOMADNET_FAVOURITES_LAYOUT_IMPORTED, onLayoutImported);
            onIdentitySwitched = () => {
                clearLocalNomadFavouritesLayout();
                resetDefaultSections();
                reloadFavouriteLayoutFromStore();
            };
            GlobalEmitter.on(EMITTER_EVENTS.IDENTITY_SWITCHED, onIdentitySwitched);
        });
        onUnmounted(() => {
            if (layoutPersistTimer) {
                clearTimeout(layoutPersistTimer);
                layoutPersistTimer = null;
                persistFavouriteLayout({ immediate: true });
            }
            if (onLayoutImported) {
                GlobalEmitter.off(EMITTER_EVENTS.NOMADNET_FAVOURITES_LAYOUT_IMPORTED, onLayoutImported);
            }
            if (onIdentitySwitched) {
                GlobalEmitter.off(EMITTER_EVENTS.IDENTITY_SWITCHED, onIdentitySwitched);
            }
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
