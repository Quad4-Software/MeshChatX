<!-- SPDX-License-Identifier: 0BSD -->

<script lang="ts">
    import { onMount, tick, untrack } from "svelte";
    import GlobalState from "../../../js/GlobalState.js";
    import GlobalEmitter from "../../../js/GlobalEmitter.js";
    import { t } from "../../../js/i18n.js";
    import {
        DEFAULT_SECTION_ID,
        buildDefaultSection,
        matchesFavouriteSearch,
        ensureFavouriteLayout,
        moveFavouritesToSection,
    } from "../lib/nomadSidebarFavourites.js";
    import { loadNomadFavouritesLayout, saveNomadFavouritesLayout } from "../../../js/nomadFavouritesLayoutStore.js";
    import {
        parseStoredLayout,
        promptCreateSection,
        removeSectionFromLayout,
        exportSectionFavourites,
        exportSelectedFavourites,
    } from "../lib/nomadFavouritesLayoutManager.js";
    import {
        calculateContextMenuCoords,
        createInitialFavContextMenu,
        createInitialSecContextMenu,
    } from "../lib/nomadSidebarContextMenu.js";
    import NomadSidebarFavouritesContextMenu from "./NomadSidebarFavouritesContextMenu.svelte";
    import NomadFavouritesBulkToolbar from "./NomadFavouritesBulkToolbar.svelte";
    import NomadFavouritesSearchHeader from "./NomadFavouritesSearchHeader.svelte";
    import NomadSectionContainer from "./NomadSectionContainer.svelte";
    import type { NomadFavourite, NomadNode, NomadSection } from "../lib/types.js";

    interface Props {
        favourites: NomadFavourite[];
        nodes: Record<string, NomadNode>;
        selectedDestinationHash?: string;
        onfavouriteclick?: (fav: NomadFavourite) => void;
        onrenamefavourite?: (fav: NomadFavourite) => void;
        onremovefavourite?: (fav: NomadFavourite) => void;
        ontoggleidentifyonconnect?: (hash: string) => void;
        onbulkremovefavourites?: (hashes: string[]) => void;
        onbanishfavourite?: (fav: NomadFavourite) => void;
        onunblockfavourite?: (hash: string) => void;
    }

    let {
        favourites = [],
        nodes = {},
        selectedDestinationHash = "",
        onfavouriteclick,
        onrenamefavourite,
        onremovefavourite,
        ontoggleidentifyonconnect,
        onbulkremovefavourites,
        onbanishfavourite,
        onunblockfavourite,
    }: Props = $props();

    let searchTerm = $state("");
    let selectionMode = $state(false);
    let selectedHashes = $state<string[]>([]);
    let sections = $state<NomadSection[]>([buildDefaultSection("Favourites")]);
    let sectionOrder = $state<string[]>([DEFAULT_SECTION_ID]);
    let favouritesBySection = $state<Record<string, string[]>>({ [DEFAULT_SECTION_ID]: [] });

    let editingSectionId = $state<string | null>(null);
    let editingSectionName = $state("");
    let draggingFavouriteHashes = $state<string[]>([]);

    let favContextMenu = $state(createInitialFavContextMenu());
    let secContextMenu = $state(createInitialSecContextMenu());
    let favMenuLeft = $state(0);
    let favMenuTop = $state(0);
    let secMenuLeft = $state(0);
    let secMenuTop = $state(0);

    let persistTimer: ReturnType<typeof setTimeout> | null = null;
    let loadGen = 0;

    const orderedSections = $derived.by(() => {
        const map: Record<string, NomadSection> = {};
        sections.forEach((s) => {
            map[s.id] = s;
        });
        const ids = sectionOrder.length > 0 ? sectionOrder : sections.map((s) => s.id);
        return ids.map((id) => map[id]).filter(Boolean);
    });

    const sectionsWithFavourites = $derived.by(() => {
        const s = searchTerm.toLowerCase();
        return orderedSections.map((sec) => {
            const hashes = favouritesBySection[sec.id] || [];
            const favs = hashes
                .map((h) => favourites.find((f) => f.destination_hash === h))
                .filter((f): f is NomadFavourite => Boolean(f))
                .filter((f) => matchesFavouriteSearch(f, s));
            return { ...sec, favourites: favs };
        });
    });

    const searchNoResults = $derived(
        favourites.length > 0 &&
            searchTerm.trim() !== "" &&
            !sectionsWithFavourites.some((sec) => (sec.favourites?.length || 0) > 0)
    );

    const flatVisibleHashes = $derived.by(() => {
        const out: string[] = [];
        sectionsWithFavourites.forEach((sec) => {
            sec.favourites?.forEach((fav) => out.push(fav.destination_hash));
        });
        return out;
    });

    const allVisibleSelected = $derived(
        flatVisibleHashes.length > 0 && flatVisibleHashes.every((h) => selectedHashes.includes(h))
    );

    function isBlocked(hash: string): boolean {
        const blocked = (GlobalState.blockedDestinations || []) as Array<{ destination_hash?: string }>;
        return blocked.some((b) => b.destination_hash === hash);
    }

    function persistLayout(immediate = false) {
        if (persistTimer) {
            clearTimeout(persistTimer);
            persistTimer = null;
        }
        const layout = { sections, sectionOrder, favouritesBySection };
        const flush = () => {
            if (typeof window !== "undefined" && (window as any).api) {
                saveNomadFavouritesLayout((window as any).api, layout);
            }
        };
        if (immediate) {
            flush();
            return;
        }
        persistTimer = setTimeout(flush, 250);
    }

    function reconcileLayout() {
        const result = ensureFavouriteLayout(
            favourites,
            sections,
            sectionOrder,
            favouritesBySection,
            t("nomadnet.favourites")
        );
        sections = result.sections;
        sectionOrder = result.sectionOrder;
        favouritesBySection = result.favouritesBySection;
        if (result.changed) persistLayout();
    }

    $effect(() => {
        const _ = favourites;
        untrack(() => {
            reconcileLayout();
        });
    });

    async function reloadFromStore() {
        const gen = ++loadGen;
        if (typeof window !== "undefined" && (window as any).api) {
            const raw = await loadNomadFavouritesLayout((window as any).api);
            const parsed = parseStoredLayout(raw);
            if (gen === loadGen && parsed) {
                sections = parsed.sections;
                sectionOrder = parsed.sectionOrder;
                favouritesBySection = parsed.favouritesBySection;
                reconcileLayout();
            }
        }
    }

    function toggleSelectAll() {
        selectedHashes = allVisibleSelected
            ? selectedHashes.filter((h) => !flatVisibleHashes.includes(h))
            : [...new Set([...selectedHashes, ...flatVisibleHashes])];
    }

    function toggleSelect(hash: string) {
        selectedHashes = selectedHashes.includes(hash)
            ? selectedHashes.filter((h) => h !== hash)
            : [...selectedHashes, hash];
    }

    function moveSelectedToSection(targetSectionId: string) {
        if (selectedHashes.length === 0) return;
        favouritesBySection = moveFavouritesToSection(favouritesBySection, selectedHashes, targetSectionId);
        persistLayout();
        selectionMode = false;
        selectedHashes = [];
    }

    function bulkRemoveFavourites() {
        if (selectedHashes.length === 0) return;
        onbulkremovefavourites?.(selectedHashes);
        selectionMode = false;
        selectedHashes = [];
    }

    function bulkExportFavourites() {
        exportSelectedFavourites(selectedHashes, favourites);
    }

    async function promptAddSection() {
        const next = await promptCreateSection({ sections, sectionOrder, favouritesBySection });
        if (next) {
            sections = next.sections;
            sectionOrder = next.sectionOrder;
            favouritesBySection = next.favouritesBySection;
            persistLayout(true);
        }
    }

    function toggleSectionCollapse(secId: string) {
        sections = sections.map((s) => (s.id === secId ? { ...s, collapsed: !s.collapsed } : s));
        persistLayout();
    }

    function startEditingSection(sec: NomadSection) {
        editingSectionId = sec.id;
        editingSectionName = sec.name;
    }

    function saveSectionName() {
        if (!editingSectionId) return;
        const trimmed = editingSectionName.trim();
        if (trimmed) {
            sections = sections.map((s) => (s.id === editingSectionId ? { ...s, name: trimmed } : s));
            persistLayout();
        }
        editingSectionId = null;
    }

    function openFavMenu(e: MouseEvent, fav: NomadFavourite, sectionId: string) {
        favContextMenu = {
            show: true,
            justOpened: true,
            x: e.clientX,
            y: e.clientY,
            targetHash: fav.destination_hash,
            targetSectionId: sectionId,
        };
        secContextMenu.show = false;
        tick().then(() => {
            const coords = calculateContextMenuCoords(e.clientX, e.clientY, 180, 240);
            favMenuLeft = coords.left;
            favMenuTop = coords.top;
        });
        setTimeout(() => {
            favContextMenu.justOpened = false;
        }, 50);
    }

    function openSecMenu(e: MouseEvent, sec: NomadSection) {
        secContextMenu = { show: true, x: e.clientX, y: e.clientY, sectionId: sec.id };
        favContextMenu.show = false;
        tick().then(() => {
            const coords = calculateContextMenuCoords(e.clientX, e.clientY, 180, 160);
            secMenuLeft = coords.left;
            secMenuTop = coords.top;
        });
    }

    function closeAllMenus() {
        favContextMenu.show = false;
        secContextMenu.show = false;
    }

    function removeSection(secId: string) {
        const next = removeSectionFromLayout({ sections, sectionOrder, favouritesBySection }, secId);
        sections = next.sections;
        sectionOrder = next.sectionOrder;
        favouritesBySection = next.favouritesBySection;
        persistLayout(true);
    }

    onMount(() => {
        void reloadFromStore();
        const onLayoutImported = () => {
            void reloadFromStore();
        };
        GlobalEmitter.on("nomadnet-favourites-layout-imported", onLayoutImported);
        return () => {
            GlobalEmitter.off("nomadnet-favourites-layout-imported", onLayoutImported);
        };
    });
</script>

<svelte:window
    onclick={() => {
        if (!favContextMenu.justOpened) closeAllMenus();
    }}
/>

<div class="flex-1 flex flex-col min-h-0">
    <div class="p-3 border-b border-sem-border space-y-2">
        <NomadFavouritesSearchHeader
            {searchTerm}
            favouritesCount={favourites.length}
            {selectionMode}
            onSearchChange={(t) => {
                searchTerm = t;
            }}
            onAddSection={promptAddSection}
            onToggleSelectionMode={() => {
                selectionMode = !selectionMode;
                if (!selectionMode) selectedHashes = [];
            }}
        />

        {#if selectionMode}
            <NomadFavouritesBulkToolbar
                selectedCount={selectedHashes.length}
                {allVisibleSelected}
                {orderedSections}
                onToggleSelectAll={toggleSelectAll}
                onMoveToSection={moveSelectedToSection}
                onBulkRemove={bulkRemoveFavourites}
                onBulkExport={bulkExportFavourites}
            />
        {/if}
    </div>

    <div class="flex-1 min-h-0 px-2 pb-4 overflow-y-auto space-y-3">
        {#if searchNoResults}
            <div class="text-center py-8 text-sm text-gray-400">
                {t("nomadnet.no_favourites_found")}
            </div>
        {:else}
            {#each sectionsWithFavourites as sec (sec.id)}
                {#if !searchTerm || (sec.favourites && sec.favourites.length > 0)}
                    <NomadSectionContainer
                        {sec}
                        {nodes}
                        {selectedDestinationHash}
                        {selectionMode}
                        {selectedHashes}
                        isBlockedFn={isBlocked}
                        {editingSectionId}
                        {editingSectionName}
                        {draggingFavouriteHashes}
                        onFavouriteClick={onfavouriteclick}
                        onToggleFavouriteSelect={toggleSelect}
                        onOpenFavMenu={openFavMenu}
                        onOpenSecMenu={openSecMenu}
                        onToggleSectionCollapse={toggleSectionCollapse}
                        onStartEditingSection={startEditingSection}
                        onSaveSectionName={saveSectionName}
                        onCancelEditingSection={() => {
                            editingSectionId = null;
                        }}
                        onSectionNameChange={(val) => {
                            editingSectionName = val;
                        }}
                        onFavouritesMoved={(targetId, hashes) => {
                            favouritesBySection = moveFavouritesToSection(favouritesBySection, hashes, targetId);
                            persistLayout();
                        }}
                    />
                {/if}
            {/each}
        {/if}
    </div>
</div>

<NomadSidebarFavouritesContextMenu
    {favContextMenu}
    {secContextMenu}
    {favMenuLeft}
    {favMenuTop}
    {secMenuLeft}
    {secMenuTop}
    {orderedSections}
    targetFavourite={favourites.find((f) => f.destination_hash === favContextMenu.targetHash)}
    isTargetBlocked={isBlocked(favContextMenu.targetHash)}
    onclose={closeAllMenus}
    onrename={onrenamefavourite}
    ontoggleidentify={ontoggleidentifyonconnect}
    onmovetosection={(hash, secId) => {
        favouritesBySection = moveFavouritesToSection(favouritesBySection, [hash], secId);
        persistLayout();
    }}
    onremove={onremovefavourite}
    onbanish={onbanishfavourite}
    onunblock={onunblockfavourite}
    onrenamesection={startEditingSection}
    onexportsection={(sec) => exportSectionFavourites(sec, favourites, favouritesBySection)}
    onremovesection={removeSection}
/>
