<!-- SPDX-License-Identifier: 0BSD AND MIT -->

<template>
    <div :class="sidebarRootClass">
        <div
            v-if="effectiveCollapsed"
            class="flex flex-col h-full min-h-0 bg-white dark:bg-zinc-950 border-r border-gray-200 dark:border-zinc-800"
        >
            <div
                class="hidden sm:flex h-10 shrink-0 items-center justify-end border-b border-gray-200 dark:border-zinc-800 px-2"
            >
                <button
                    type="button"
                    class="p-1.5 rounded-lg text-gray-500 hover:bg-gray-100 dark:text-zinc-400 dark:hover:bg-zinc-800 transition-colors"
                    @click="$emit('toggle-collapse')"
                >
                    <MaterialDesignIcon icon-name="chevron-right" class="size-5" />
                </button>
            </div>
            <div class="flex flex-col items-center gap-1 py-2 px-1 border-b border-gray-200 dark:border-zinc-800">
                <button
                    type="button"
                    class="p-2 rounded-xl transition-colors"
                    :class="
                        tab === 'favourites'
                            ? 'bg-blue-600 text-white dark:bg-blue-500'
                            : 'text-gray-500 hover:bg-gray-100 dark:text-zinc-400 dark:hover:bg-zinc-800'
                    "
                    @click="tab = 'favourites'"
                >
                    <MaterialDesignIcon icon-name="star" class="size-6" />
                </button>
                <button
                    type="button"
                    class="p-2 rounded-xl transition-colors"
                    :class="
                        tab === 'announces'
                            ? 'bg-blue-600 text-white dark:bg-blue-500'
                            : 'text-gray-500 hover:bg-gray-100 dark:text-zinc-400 dark:hover:bg-zinc-800'
                    "
                    @click="tab = 'announces'"
                >
                    <MaterialDesignIcon icon-name="satellite-uplink" class="size-6" />
                </button>
            </div>
            <div
                v-if="tab === 'favourites'"
                class="flex-1 min-h-0 w-full overflow-y-auto overflow-x-hidden flex flex-col items-center gap-1 py-1 px-0.5"
            >
                <button
                    v-for="fav in collapsedFavouritePreview"
                    :key="fav.destination_hash"
                    type="button"
                    class="shrink-0 p-1 rounded-xl transition-colors focus:outline-hidden focus-visible:ring-2 focus-visible:ring-blue-500"
                    :class="
                        fav.destination_hash === selectedDestinationHash
                            ? 'ring-2 ring-blue-500 ring-offset-1 ring-offset-white dark:ring-offset-zinc-950'
                            : 'hover:bg-white/10'
                    "
                    :title="fav.display_name"
                    @click="onFavouriteClick(fav)"
                >
                    <MaterialDesignIcon icon-name="server-network" class="size-6 text-gray-600 dark:text-gray-300" />
                </button>
            </div>
            <div
                v-else-if="tab === 'announces'"
                class="flex-1 min-h-0 w-full overflow-y-auto overflow-x-hidden flex flex-col items-center gap-1 py-1 px-0.5"
            >
                <button
                    v-for="node in collapsedAnnounceNodesPreview"
                    :key="node.destination_hash"
                    type="button"
                    class="shrink-0 p-1 rounded-xl transition-colors focus:outline-hidden focus-visible:ring-2 focus-visible:ring-blue-500"
                    :class="
                        node.destination_hash === selectedDestinationHash
                            ? 'ring-2 ring-blue-500 ring-offset-1 ring-offset-white dark:ring-offset-zinc-950'
                            : 'hover:bg-white/10'
                    "
                    :title="node.custom_display_name || node.display_name"
                    @click="onNodeClick(node)"
                >
                    <MaterialDesignIcon icon-name="satellite-uplink" class="size-6 text-gray-600 dark:text-gray-300" />
                </button>
            </div>
        </div>
        <template v-else>
            <div
                class="-mb-px flex h-10 min-w-0 items-stretch border-b border-gray-200 dark:border-zinc-800 bg-white dark:bg-zinc-950"
            >
                <div class="flex min-w-0 flex-1">
                    <button
                        type="button"
                        class="sidebar-tab"
                        :class="{ 'sidebar-tab--active': tab === 'favourites' }"
                        @click="tab = 'favourites'"
                    >
                        {{ $t("nomadnet.favourites") }}
                    </button>
                    <button
                        type="button"
                        class="sidebar-tab"
                        :class="{ 'sidebar-tab--active': tab === 'announces' }"
                        @click="tab = 'announces'"
                    >
                        {{ $t("nomadnet.announces") }}
                    </button>
                </div>
                <button
                    type="button"
                    class="hidden sm:flex shrink-0 items-center border-b-2 border-transparent px-1.5 text-gray-500 hover:bg-gray-100 dark:text-zinc-400 dark:hover:bg-zinc-800 transition-colors"
                    @click="$emit('toggle-collapse')"
                >
                    <MaterialDesignIcon icon-name="chevron-left" class="size-5" />
                </button>
            </div>

            <div v-if="tab === 'favourites'" class="flex-1 flex flex-col min-h-0">
                <div class="p-3 border-b border-gray-200 dark:border-zinc-800 space-y-2">
                    <input
                        v-model="favouritesSearchTerm"
                        type="text"
                        :placeholder="$t('nomadnet.search_favourites_placeholder', { count: favourites.length })"
                        class="input-field w-full rounded-none"
                    />
                    <div
                        v-if="favouritesSelectionMode"
                        class="flex flex-col gap-2 px-2 py-2 bg-blue-50 dark:bg-blue-900/10 rounded-lg"
                    >
                        <div class="flex items-center gap-2 min-w-0 w-full">
                            <div class="flex items-center gap-2 min-w-0 flex-1 overflow-hidden">
                                <input
                                    type="checkbox"
                                    :checked="allVisibleFavouritesSelected"
                                    class="rounded-sm border-gray-300 text-blue-600 focus:ring-blue-500 shrink-0"
                                    @change="toggleSelectAllVisibleFavourites"
                                />
                                <span
                                    class="text-xs font-semibold text-blue-700 dark:text-blue-400 truncate leading-none"
                                >
                                    {{ $t("nomadnet.bulk_selected_count", { count: selectedFavouriteHashes.length }) }}
                                </span>
                            </div>
                            <div class="flex items-center gap-2 shrink-0">
                                <div class="relative inline-flex items-center">
                                    <button
                                        type="button"
                                        class="inline-flex items-center whitespace-nowrap rounded px-0 py-0.5 text-xs font-bold leading-none text-blue-600 dark:text-blue-400 hover:underline disabled:pointer-events-none disabled:opacity-40"
                                        :disabled="selectedFavouriteHashes.length === 0"
                                        @click="favouriteBulkMoveMenuOpen = !favouriteBulkMoveMenuOpen"
                                    >
                                        {{ $t("nomadnet.bulk_move_to_section") }}
                                    </button>
                                    <div
                                        v-if="favouriteBulkMoveMenuOpen"
                                        v-click-outside="{ handler: closeFavouriteBulkMoveMenu, capture: true }"
                                        class="absolute right-0 top-full mt-1 z-60 min-w-[10rem] max-h-56 overflow-y-auto bg-white dark:bg-zinc-800 rounded-xl shadow-xl border border-gray-200 dark:border-zinc-700 py-1"
                                    >
                                        <button
                                            v-for="section in orderedSections"
                                            :key="'bulk-move-' + section.id"
                                            type="button"
                                            class="w-full text-left px-3 py-2 text-sm text-gray-700 dark:text-zinc-300 hover:bg-gray-100 dark:hover:bg-zinc-700"
                                            @click="bulkMoveSelectedFavouritesToSection(section.id)"
                                        >
                                            {{ section.name }}
                                        </button>
                                    </div>
                                </div>
                                <button
                                    type="button"
                                    class="inline-flex items-center whitespace-nowrap rounded px-0 py-0.5 text-xs font-bold leading-none text-red-600 dark:text-red-400 hover:underline disabled:pointer-events-none disabled:opacity-40"
                                    :disabled="selectedFavouriteHashes.length === 0"
                                    @click="bulkRemoveSelectedFavourites"
                                >
                                    {{ $t("nomadnet.bulk_remove") }}
                                </button>
                            </div>
                        </div>
                    </div>
                </div>
                <div
                    class="flex items-center justify-between px-3 pt-2 text-[11px] uppercase tracking-wide text-gray-500 dark:text-gray-400"
                >
                    <div class="flex items-center gap-1 min-w-0">
                        <button
                            type="button"
                            class="shrink-0 inline-flex items-center justify-center p-0.5 rounded-sm text-gray-400 hover:text-blue-500 dark:hover:text-blue-400 transition-colors leading-none"
                            :title="$t('nomadnet.sidebar_selection_mode')"
                            :class="{ 'text-blue-500 dark:text-blue-400': favouritesSelectionMode }"
                            @click.stop="toggleFavouritesSelectionMode"
                        >
                            <span class="block size-[14px]">
                                <MaterialDesignIcon icon-name="checkbox-multiple-marked-outline" />
                            </span>
                        </button>
                        <span class="font-semibold truncate">Sections</span>
                    </div>
                    <button
                        type="button"
                        class="inline-flex items-center gap-1 text-xs font-semibold text-blue-600 dark:text-blue-400 hover:text-blue-700 dark:hover:text-blue-300"
                        @click="createSection"
                    >
                        <MaterialDesignIcon icon-name="plus" class="size-4" />
                        <span>Add Section</span>
                    </button>
                </div>
                <div class="flex-1 overflow-y-auto px-2 pb-4">
                    <div v-if="favouritesSearchNoResults" class="empty-state empty-state--panel">
                        <MaterialDesignIcon icon-name="star-outline" class="w-8 h-8" />
                        <div class="font-semibold">{{ $t("nomadnet.favourites_search_no_results") }}</div>
                        <div class="text-sm text-gray-500 dark:text-gray-400">
                            {{ $t("nomadnet.favourites_search_try_other") }}
                        </div>
                    </div>
                    <div v-else class="space-y-3 pt-2">
                        <div
                            v-if="favourites.length === 0"
                            class="empty-state empty-state--compact border border-dashed border-gray-200 dark:border-zinc-800 rounded-xl py-4 mb-1"
                        >
                            <MaterialDesignIcon icon-name="star-outline" class="w-8 h-8" />
                            <div class="font-semibold">{{ $t("nomadnet.no_favourites") }}</div>
                            <div class="text-sm text-gray-500 dark:text-gray-400">
                                {{ $t("nomadnet.add_nodes_from_announces") }}
                            </div>
                        </div>
                        <div
                            v-for="section in sectionsWithFavourites"
                            :key="section.id"
                            class="rounded-xl"
                            :class="[
                                dragOverSectionId === section.id
                                    ? 'ring-1 ring-blue-400 dark:ring-blue-600 bg-blue-50/40 dark:bg-blue-900/10'
                                    : '',
                                draggingSectionOverId === section.id
                                    ? 'ring-1 ring-blue-300 dark:ring-blue-700 bg-blue-50/30 dark:bg-blue-900/5'
                                    : '',
                            ]"
                            @dragover.prevent="onSectionDragOver(section.id)"
                            @dragleave="onSectionDragLeave"
                            @drop.prevent="onDropOnSection(section.id)"
                        >
                            <div
                                class="flex items-center justify-between px-2 py-1 cursor-pointer select-none"
                                draggable="true"
                                @click="toggleSectionCollapse(section.id)"
                                @contextmenu.prevent="openSectionContextMenu($event, section)"
                                @dragstart="onSectionDragStart(section.id)"
                                @dragover.prevent="onSectionReorderDragOver(section.id)"
                                @drop.prevent="onSectionDrop(section.id)"
                                @dragend="onSectionDragEnd"
                            >
                                <div class="flex items-center gap-2 flex-1 min-w-0">
                                    <MaterialDesignIcon
                                        :icon-name="section.collapsed ? 'chevron-right' : 'chevron-down'"
                                        class="size-4 text-gray-400 shrink-0"
                                    />
                                    <template v-if="editingSectionId === section.id">
                                        <input
                                            :ref="`sectionInput-${section.id}`"
                                            v-model="editingSectionName"
                                            type="text"
                                            class="flex-1 bg-transparent border-b border-blue-500 text-xs font-semibold uppercase tracking-wide text-gray-900 dark:text-white focus:outline-hidden min-w-0"
                                            @click.stop
                                            @keydown.enter="saveSectionName"
                                            @keydown.esc="cancelEditingSection"
                                            @blur="saveSectionName"
                                        />
                                        <button
                                            type="button"
                                            class="p-1 text-green-500 hover:text-green-600 shrink-0"
                                            @click.stop="saveSectionName"
                                        >
                                            <MaterialDesignIcon icon-name="check" class="size-4" />
                                        </button>
                                    </template>
                                    <span
                                        v-else
                                        class="text-xs font-semibold uppercase tracking-wide text-gray-600 dark:text-gray-300 truncate"
                                        @click.stop="startEditingSection(section)"
                                    >
                                        {{ section.name }}
                                    </span>
                                    <span
                                        v-if="section.collapsed"
                                        class="text-[10px] font-semibold text-gray-500 dark:text-gray-400 bg-gray-100 dark:bg-zinc-800 px-2 py-0.5 rounded-full shrink-0"
                                    >
                                        {{ section.favourites.length }}
                                    </span>
                                </div>
                            </div>
                            <div class="h-px bg-gray-200 dark:bg-zinc-800 mx-1"></div>
                            <div v-if="!section.collapsed" class="space-y-2 pt-2 pb-1 px-1">
                                <div
                                    v-for="favourite of section.favourites"
                                    :key="favourite.destination_hash"
                                    class="favourite-card relative"
                                    :class="[
                                        favourite.destination_hash === selectedDestinationHash
                                            ? 'favourite-card--active'
                                            : '',
                                        isFavouriteRowDragging(favourite.destination_hash)
                                            ? 'favourite-card--dragging'
                                            : '',
                                        favouritesSelectionMode &&
                                        selectedFavouriteHashes.includes(favourite.destination_hash)
                                            ? 'ring-1 ring-blue-400/60 dark:ring-blue-500/50'
                                            : '',
                                    ]"
                                    draggable="true"
                                    @click="onFavouriteRowActivate(favourite)"
                                    @contextmenu.prevent="openFavouriteContextMenu($event, favourite, section.id)"
                                    @dragstart="onFavouriteDragStart($event, favourite, section.id)"
                                    @dragover.prevent="onFavouriteDragOver($event)"
                                    @drop.prevent="onFavouriteDrop($event, section.id, favourite)"
                                    @dragend="onFavouriteDragEnd"
                                >
                                    <div
                                        v-if="favouritesSelectionMode"
                                        class="my-auto mr-1 px-0.5 shrink-0"
                                        @click.stop
                                    >
                                        <input
                                            type="checkbox"
                                            :checked="selectedFavouriteHashes.includes(favourite.destination_hash)"
                                            class="rounded-sm border-gray-300 text-blue-600 focus:ring-blue-500"
                                            @change="toggleSelectFavourite(favourite.destination_hash)"
                                        />
                                    </div>
                                    <div
                                        v-if="
                                            GlobalState.config.banished_effect_enabled &&
                                            isBlocked(favourite.destination_hash)
                                        "
                                        class="banished-overlay"
                                        :style="{ background: GlobalState.config.banished_color + '33' }"
                                    >
                                        <span
                                            class="banished-text text-[10px]! opacity-100! tracking-widest! border! px-1! py-0.5! text-white! shadow-lg!"
                                            :style="{ 'background-color': GlobalState.config.banished_color }"
                                            >{{ GlobalState.config.banished_text }}</span
                                        >
                                    </div>

                                    <div class="favourite-card__icon shrink-0">
                                        <MaterialDesignIcon icon-name="server-network" class="w-5 h-5" />
                                    </div>
                                    <div class="min-w-0 flex-1">
                                        <div
                                            class="text-sm font-semibold text-gray-900 dark:text-white truncate"
                                            :title="favourite.display_name"
                                        >
                                            {{ favourite.display_name }}
                                        </div>
                                        <div
                                            class="text-xs text-gray-500 dark:text-gray-400 hover:text-blue-500 dark:hover:text-blue-400 cursor-pointer inline-flex items-center"
                                            :title="$t('common.copy_to_clipboard')"
                                            @click.stop="copyToClipboard(favourite.destination_hash, 'Address')"
                                        >
                                            {{ formatDestinationHash(favourite.destination_hash) }}
                                        </div>
                                    </div>
                                    <IconButton
                                        class="shrink-0 text-gray-500 dark:text-gray-300"
                                        @click.stop="openFavouriteContextMenu($event, favourite, section.id)"
                                    >
                                        <MaterialDesignIcon icon-name="dots-vertical" class="w-5 h-5" />
                                    </IconButton>
                                </div>
                                <div
                                    v-if="section.favourites.length === 0"
                                    class="text-xs text-gray-500 dark:text-gray-400 px-3 pb-2 italic"
                                >
                                    {{ $t("nomadnet.no_favourites_in_section") }}
                                </div>
                            </div>
                        </div>
                    </div>
                </div>

                <!-- Favourite Context Menu (Teleport to body to avoid overflow clipping) -->
                <Teleport to="body">
                    <ContextMenuPanel
                        v-click-outside="{
                            handler: () => {
                                if (!favouriteContextMenu.justOpened) closeContextMenus();
                            },
                            capture: true,
                        }"
                        :show="favouriteContextMenu.show"
                        :x="favouriteContextMenu.x"
                        :y="favouriteContextMenu.y"
                        panel-class="z-200 min-w-56"
                    >
                        <ContextMenuItem @click="renameFavouriteFromContext">
                            <MaterialDesignIcon icon-name="pencil" class="size-4 text-gray-400" />
                            {{ $t("nomadnet.rename") }}
                        </ContextMenuItem>
                        <ContextMenuItem
                            v-if="!isBlocked(favouriteContextMenu.targetHash)"
                            item-class="text-red-600 dark:text-red-400"
                            @click="banishFavouriteFromContext"
                        >
                            <MaterialDesignIcon icon-name="gavel" class="size-4 text-red-400" />
                            {{ $t("nomadnet.block_node") }}
                        </ContextMenuItem>
                        <ContextMenuItem
                            v-else
                            item-class="text-emerald-600 dark:text-emerald-400"
                            @click="unblockFavouriteFromContext"
                        >
                            <MaterialDesignIcon icon-name="check-circle" class="size-4 text-emerald-500" />
                            {{ $t("nomadnet.lift_banishment") }}
                        </ContextMenuItem>
                        <ContextMenuItem
                            item-class="text-red-600 dark:text-red-400"
                            @click="removeFavouriteFromContext"
                        >
                            <MaterialDesignIcon icon-name="trash-can" class="size-4 text-red-400" />
                            {{ $t("nomadnet.remove") }}
                        </ContextMenuItem>
                        <ContextMenuDivider />
                        <ContextMenuSectionLabel>Move to Section</ContextMenuSectionLabel>
                        <div class="max-h-56 overflow-y-auto custom-scrollbar">
                            <ContextMenuItem
                                v-for="section in sectionsWithFavourites"
                                :key="section.id + '-move'"
                                @click="moveContextFavouriteToSection(section.id)"
                            >
                                <MaterialDesignIcon icon-name="folder" class="size-4 opacity-70" />
                                <span class="truncate">{{ section.name }}</span>
                            </ContextMenuItem>
                        </div>
                    </ContextMenuPanel>
                </Teleport>

                <!-- Section Context Menu (Teleport to body) -->
                <Teleport to="body">
                    <ContextMenuPanel
                        v-click-outside="{ handler: closeContextMenus, capture: true }"
                        :show="sectionContextMenu.show"
                        :x="sectionContextMenu.x"
                        :y="sectionContextMenu.y"
                        panel-class="z-200"
                    >
                        <ContextMenuItem @click="renameSectionFromContext">
                            <MaterialDesignIcon icon-name="pencil" class="size-4 text-gray-400" />
                            Rename Section
                        </ContextMenuItem>
                        <ContextMenuItem @click="exportSectionFavouritesFromContext">
                            <MaterialDesignIcon icon-name="file-export" class="size-4 text-gray-400" />
                            {{ $t("nomadnet.export_section_favourites") }}
                        </ContextMenuItem>
                        <ContextMenuItem
                            :item-class="
                                'text-red-600 dark:text-red-400' +
                                (sectionContextMenu.sectionId === defaultSectionId
                                    ? ' opacity-50 cursor-not-allowed'
                                    : '')
                            "
                            :disabled="sectionContextMenu.sectionId === defaultSectionId"
                            @click="removeSectionFromContext"
                        >
                            <MaterialDesignIcon icon-name="delete" class="size-4 text-red-400" />
                            Delete Section
                        </ContextMenuItem>
                    </ContextMenuPanel>
                </Teleport>
            </div>

            <div v-else class="flex-1 flex flex-col min-h-0">
                <div class="p-3 border-b border-gray-200 dark:border-zinc-800 space-y-2">
                    <div class="flex gap-1.5 items-center">
                        <input
                            :value="nodesSearchTerm"
                            type="text"
                            :placeholder="$t('nomadnet.search_placeholder_announces', { count: totalNodesCount })"
                            class="input-field flex-1 min-w-0 rounded-none"
                            @input="onNodesSearchInput"
                        />
                        <button
                            type="button"
                            class="shrink-0 self-center inline-flex items-center justify-center p-0.5 rounded-sm text-gray-400 hover:text-blue-500 dark:hover:text-blue-400 transition-colors leading-none"
                            :title="$t('nomadnet.sidebar_selection_mode')"
                            :class="{ 'text-blue-500 dark:text-blue-400': announcesSelectionMode }"
                            @click="toggleAnnouncesSelectionMode"
                        >
                            <span class="block size-[14px]">
                                <MaterialDesignIcon icon-name="checkbox-multiple-marked-outline" />
                            </span>
                        </button>
                    </div>
                    <div
                        v-if="announcesSelectionMode"
                        class="flex flex-col gap-2 px-2 py-2 bg-blue-50 dark:bg-blue-900/10 rounded-lg"
                    >
                        <div class="flex items-center gap-2 min-w-0 w-full">
                            <div class="flex items-center gap-2 min-w-0 flex-1 overflow-hidden">
                                <input
                                    type="checkbox"
                                    :checked="allVisibleAnnouncesSelected"
                                    class="rounded-sm border-gray-300 text-blue-600 focus:ring-blue-500 shrink-0"
                                    @change="toggleSelectAllVisibleAnnounces"
                                />
                                <span
                                    class="text-xs font-semibold text-blue-700 dark:text-blue-400 truncate leading-none"
                                >
                                    {{ $t("nomadnet.bulk_selected_count", { count: selectedAnnounceHashes.length }) }}
                                </span>
                            </div>
                            <div class="flex items-center gap-2 shrink-0">
                                <button
                                    type="button"
                                    class="inline-flex items-center whitespace-nowrap rounded px-0 py-0.5 text-xs font-bold leading-none text-yellow-600 dark:text-yellow-400 hover:underline disabled:pointer-events-none disabled:opacity-40"
                                    :disabled="selectedAnnounceHashes.length === 0"
                                    @click="bulkAddSelectedAnnouncesToFavourites"
                                >
                                    {{ $t("nomadnet.bulk_add_to_favourites") }}
                                </button>
                                <button
                                    type="button"
                                    class="inline-flex items-center whitespace-nowrap rounded px-0 py-0.5 text-xs font-bold leading-none text-red-600 dark:text-red-400 hover:underline disabled:pointer-events-none disabled:opacity-40"
                                    :disabled="selectedAnnounceHashes.length === 0"
                                    @click="bulkBanishSelectedAnnounces"
                                >
                                    {{ $t("nomadnet.bulk_block_nodes") }}
                                </button>
                            </div>
                        </div>
                    </div>
                </div>
                <div class="flex-1 overflow-y-auto px-2 pb-4" @scroll="onNodesScroll">
                    <div v-if="searchedNodes.length > 0" class="space-y-2 pt-2">
                        <div
                            v-for="node of searchedNodes"
                            :key="node.destination_hash"
                            class="announce-card relative"
                            :class="[
                                node.destination_hash === selectedDestinationHash ? 'announce-card--active' : '',
                                announcesSelectionMode && selectedAnnounceHashes.includes(node.destination_hash)
                                    ? 'ring-1 ring-blue-400/60 dark:ring-blue-500/50'
                                    : '',
                            ]"
                            @contextmenu.prevent="openAnnounceContextMenu($event, node)"
                        >
                            <!-- banished overlay -->
                            <div
                                v-if="GlobalState.config.banished_effect_enabled && isBlocked(node.identity_hash)"
                                class="banished-overlay"
                                :style="{ background: GlobalState.config.banished_color + '33' }"
                            >
                                <span
                                    class="banished-text text-[10px]! opacity-100! tracking-widest! border! px-1! py-0.5! text-white! shadow-lg!"
                                    :style="{ 'background-color': GlobalState.config.banished_color }"
                                    >{{ GlobalState.config.banished_text }}</span
                                >
                            </div>

                            <div
                                class="flex items-center gap-3 flex-1 min-w-0 cursor-pointer"
                                @click="onAnnounceRowActivate(node)"
                            >
                                <div v-if="announcesSelectionMode" class="my-auto shrink-0 px-0.5" @click.stop>
                                    <input
                                        type="checkbox"
                                        :checked="selectedAnnounceHashes.includes(node.destination_hash)"
                                        class="rounded-sm border-gray-300 text-blue-600 focus:ring-blue-500"
                                        @change="toggleSelectAnnounce(node.destination_hash)"
                                    />
                                </div>
                                <div class="announce-card__icon shrink-0">
                                    <MaterialDesignIcon icon-name="satellite-uplink" class="w-5 h-5" />
                                </div>
                                <div class="min-w-0 flex-1">
                                    <div
                                        class="text-sm font-semibold text-gray-900 dark:text-white truncate"
                                        :title="node.custom_display_name || node.display_name"
                                    >
                                        {{ node.custom_display_name || node.display_name }}
                                    </div>
                                    <div class="text-xs text-gray-500 dark:text-gray-400 flex flex-col gap-0.5">
                                        <span class="truncate">{{
                                            $t("nomadnet.announced_time_ago", {
                                                time: formatTimeAgoForI18n(node.updated_at),
                                            })
                                        }}</span>
                                        <span
                                            class="cursor-pointer hover:text-blue-500 dark:hover:text-blue-400 inline-flex items-center"
                                            :title="$t('common.copy_to_clipboard')"
                                            @click.stop="copyToClipboard(node.destination_hash, 'Address')"
                                        >
                                            {{ formatDestinationHash(node.destination_hash) }}
                                        </span>
                                    </div>
                                </div>
                            </div>
                            <div class="shrink-0">
                                <DropDownMenu>
                                    <template #button>
                                        <IconButton>
                                            <MaterialDesignIcon icon-name="dots-vertical" class="w-5 h-5" />
                                        </IconButton>
                                    </template>
                                    <template #items>
                                        <DropDownMenuItem
                                            v-if="!isBlocked(node.identity_hash)"
                                            @click.stop="onBlockNode(node)"
                                        >
                                            <MaterialDesignIcon icon-name="gavel" class="w-5 h-5 text-red-500" />
                                            <span class="text-red-500">{{ $t("nomadnet.block_node") }}</span>
                                        </DropDownMenuItem>
                                        <DropDownMenuItem v-else @click.stop="onUnblockNode(node.identity_hash)">
                                            <MaterialDesignIcon
                                                icon-name="check-circle"
                                                class="w-5 h-5 text-green-500"
                                            />
                                            <span class="text-green-500">{{ $t("nomadnet.lift_banishment") }}</span>
                                        </DropDownMenuItem>
                                    </template>
                                </DropDownMenu>
                            </div>
                        </div>

                        <!-- loading more spinner -->
                        <div v-if="isLoadingMoreNodes" class="p-4 text-center">
                            <MaterialDesignIcon icon-name="loading" class="size-6 animate-spin text-gray-400" />
                        </div>
                    </div>
                    <div v-else class="empty-state empty-state--panel">
                        <MaterialDesignIcon icon-name="radar" class="w-8 h-8" />
                        <div class="font-semibold">{{ $t("nomadnet.no_announces_yet") }}</div>
                        <div class="text-sm text-gray-500 dark:text-gray-400">
                            {{ $t("nomadnet.listening_for_peers") }}
                        </div>
                    </div>
                </div>

                <!-- Announce Context Menu (right-click, Teleport to body) -->
                <Teleport to="body">
                    <ContextMenuPanel
                        v-click-outside="{
                            handler: () => {
                                if (!announceContextMenu.justOpened) closeContextMenus();
                            },
                            capture: true,
                        }"
                        :show="announceContextMenu.show"
                        :x="announceContextMenu.x"
                        :y="announceContextMenu.y"
                        panel-class="z-200"
                    >
                        <ContextMenuItem
                            v-if="!isFavourite(announceContextMenu.node?.destination_hash)"
                            @click="addFavouriteFromContext"
                        >
                            <MaterialDesignIcon icon-name="star-outline" class="size-4 text-yellow-500" />
                            {{ $t("nomadnet.add_favourite") }}
                        </ContextMenuItem>
                        <ContextMenuItem
                            v-if="!isBlocked(announceContextMenu.node?.identity_hash)"
                            item-class="text-red-600 dark:text-red-400"
                            @click="blockAnnounceFromContext"
                        >
                            <MaterialDesignIcon icon-name="gavel" class="size-4 text-red-400" />
                            {{ $t("nomadnet.block_node") }}
                        </ContextMenuItem>
                        <ContextMenuItem
                            v-else
                            item-class="text-emerald-600 dark:text-emerald-400"
                            @click="unblockAnnounceFromContext"
                        >
                            <MaterialDesignIcon icon-name="check-circle" class="size-4 text-emerald-500" />
                            {{ $t("nomadnet.lift_banishment") }}
                        </ContextMenuItem>
                    </ContextMenuPanel>
                </Teleport>
            </div>
        </template>
    </div>
</template>

<script>
import Utils from "../../js/Utils";
import MaterialDesignIcon from "../MaterialDesignIcon.vue";
import ContextMenuDivider from "../contextmenu/ContextMenuDivider.vue";
import ContextMenuItem from "../contextmenu/ContextMenuItem.vue";
import ContextMenuPanel from "../contextmenu/ContextMenuPanel.vue";
import ContextMenuSectionLabel from "../contextmenu/ContextMenuSectionLabel.vue";
import DropDownMenu from "../DropDownMenu.vue";
import IconButton from "../IconButton.vue";
import DropDownMenuItem from "../DropDownMenuItem.vue";
import DialogUtils from "../../js/DialogUtils";
import GlobalState from "../../js/GlobalState";
import GlobalEmitter from "../../js/GlobalEmitter";
import ToastUtils from "../../js/ToastUtils";
import DownloadUtils from "../../js/DownloadUtils";

export default {
    name: "NomadNetworkSidebar",
    components: {
        ContextMenuDivider,
        ContextMenuItem,
        ContextMenuPanel,
        ContextMenuSectionLabel,
        DropDownMenuItem,
        IconButton,
        DropDownMenu,
        MaterialDesignIcon,
    },
    props: {
        nodes: {
            type: Object,
            required: true,
        },
        favourites: {
            type: Array,
            required: true,
        },
        selectedDestinationHash: {
            type: String,
            required: true,
        },
        nodesSearchTerm: {
            type: String,
            default: "",
        },
        totalNodesCount: {
            type: Number,
            default: 0,
        },
        isLoadingMoreNodes: {
            type: Boolean,
            default: false,
        },
        hasMoreNodes: {
            type: Boolean,
            default: false,
        },
        collapsed: {
            type: Boolean,
            default: false,
        },
    },
    emits: [
        "node-click",
        "rename-favourite",
        "remove-favourite",
        "add-favourite",
        "nodes-search-changed",
        "load-more-nodes",
        "toggle-collapse",
        "bulk-remove-favourites",
        "bulk-add-favourites",
    ],
    data() {
        return {
            GlobalState,
            tab: "favourites",
            favouritesSearchTerm: "",
            favouritesSelectionMode: false,
            announcesSelectionMode: false,
            selectedFavouriteHashes: [],
            selectedAnnounceHashes: [],
            favouriteBulkMoveMenuOpen: false,
            defaultSectionId: "default",
            sections: [],
            sectionOrder: [],
            favouritesBySection: {},
            draggingFavouriteHash: null,
            draggingFavouriteHashes: [],
            draggingFavouriteSectionId: null,
            dragOverSectionId: null,
            draggingSectionId: null,
            draggingSectionOverId: null,
            favouriteContextMenu: {
                show: false,
                x: 0,
                y: 0,
                targetHash: null,
                targetSectionId: null,
                justOpened: false,
            },
            sectionContextMenu: {
                show: false,
                x: 0,
                y: 0,
                sectionId: null,
            },
            announceContextMenu: {
                show: false,
                x: 0,
                y: 0,
                node: null,
                justOpened: false,
            },
            smUp: typeof window !== "undefined" ? window.innerWidth >= 640 : true,
            editingSectionId: null,
            editingSectionName: "",
        };
    },
    computed: {
        effectiveCollapsed() {
            return this.collapsed && this.smUp;
        },
        sidebarRootClass() {
            if (this.effectiveCollapsed) {
                return "flex flex-col w-16 min-w-16 max-w-16 h-full min-h-0 bg-white dark:bg-zinc-950 border-r border-gray-200 dark:border-zinc-800";
            }
            return "flex flex-col w-full sm:w-80 sm:min-w-80 md:max-lg:w-64 md:max-lg:min-w-64 lg:w-80 lg:min-w-80 min-h-0 bg-white dark:bg-zinc-950 border-r border-gray-200 dark:border-zinc-800";
        },
        blockedDestinations() {
            return GlobalState.blockedDestinations;
        },
        nodesCount() {
            return Object.keys(this.nodes).length;
        },
        nodesOrderedByLatestAnnounce() {
            const nodes = Object.values(this.nodes);
            return nodes.sort(function (nodeA, nodeB) {
                // order by updated_at desc
                const nodeAUpdatedAt = new Date(nodeA.updated_at).getTime();
                const nodeBUpdatedAt = new Date(nodeB.updated_at).getTime();
                return nodeBUpdatedAt - nodeAUpdatedAt;
            });
        },
        searchedNodes() {
            return this.nodesOrderedByLatestAnnounce.filter((node) => {
                const search = this.nodesSearchTerm.toLowerCase();
                const label = (node.custom_display_name || node.display_name || "").toLowerCase();
                const matchesDisplayName = label.includes(search);
                const matchesDestinationHash = node.destination_hash.toLowerCase().includes(search);
                return matchesDisplayName || matchesDestinationHash;
            });
        },
        orderedSections() {
            const map = {};
            this.sections.forEach((section) => {
                map[section.id] = section;
            });
            const ids = this.sectionOrder.length > 0 ? this.sectionOrder : this.sections.map((section) => section.id);
            return ids.map((id) => map[id]).filter((section) => section);
        },
        sectionsWithFavourites() {
            const search = this.favouritesSearchTerm.toLowerCase();
            return this.orderedSections.map((section) => {
                const hashes = this.favouritesBySection[section.id] || [];
                const favourites = hashes
                    .map((hash) => this.favourites.find((fav) => fav.destination_hash === hash))
                    .filter((fav) => fav)
                    .filter((fav) => this.matchesFavouriteSearch(fav, search));
                return { ...section, favourites };
            });
        },
        favouritesSearchNoResults() {
            if (this.favourites.length === 0) {
                return false;
            }
            if (this.favouritesSearchTerm.trim() === "") {
                return false;
            }
            return !this.sectionsWithFavourites.some((section) => section.favourites.length > 0);
        },
        collapsedFavouritePreview() {
            const out = [];
            const max = 5;
            for (const section of this.orderedSections) {
                const hashes = this.favouritesBySection[section.id] || [];
                for (const hash of hashes) {
                    const fav = this.favourites.find((f) => f.destination_hash === hash);
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
        },
        collapsedAnnounceNodesPreview() {
            return this.nodesOrderedByLatestAnnounce.slice(0, 5);
        },
        flatVisibleFavouriteDestinationHashes() {
            const out = [];
            for (const section of this.sectionsWithFavourites) {
                for (const fav of section.favourites) {
                    out.push(fav.destination_hash);
                }
            }
            return out;
        },
        flatVisibleAnnounceDestinationHashes() {
            return this.searchedNodes.map((n) => n.destination_hash);
        },
        allVisibleFavouritesSelected() {
            const ids = this.flatVisibleFavouriteDestinationHashes;
            return ids.length > 0 && ids.every((id) => this.selectedFavouriteHashes.includes(id));
        },
        allVisibleAnnouncesSelected() {
            const ids = this.flatVisibleAnnounceDestinationHashes;
            return ids.length > 0 && ids.every((id) => this.selectedAnnounceHashes.includes(id));
        },
    },
    watch: {
        favourites: {
            handler() {
                this.ensureFavouriteLayout();
            },
            deep: true,
        },
        tab() {
            this.exitFavouritesSelectionMode();
            this.exitAnnouncesSelectionMode();
            this.favouriteBulkMoveMenuOpen = false;
        },
    },
    mounted() {
        this.loadFavouriteLayout();
        this.ensureFavouriteLayout();
        this._smUpMql = window.matchMedia("(min-width: 640px)");
        this._smUpResize = () => {
            this.smUp = this._smUpMql.matches;
        };
        this._smUpResize();
        this._smUpMql.addEventListener("change", this._smUpResize);
        this._onNomadnetFavouritesLayoutImported = () => {
            this.loadFavouriteLayout();
        };
        GlobalEmitter.on("nomadnet-favourites-layout-imported", this._onNomadnetFavouritesLayoutImported);
    },
    unmounted() {
        if (this._smUpMql && this._smUpResize) {
            this._smUpMql.removeEventListener("change", this._smUpResize);
        }
        if (this._onNomadnetFavouritesLayoutImported) {
            GlobalEmitter.off("nomadnet-favourites-layout-imported", this._onNomadnetFavouritesLayoutImported);
        }
    },
    methods: {
        toggleFavouritesSelectionMode() {
            this.favouritesSelectionMode = !this.favouritesSelectionMode;
            if (!this.favouritesSelectionMode) {
                this.selectedFavouriteHashes = [];
            }
            this.favouriteBulkMoveMenuOpen = false;
        },
        toggleAnnouncesSelectionMode() {
            this.announcesSelectionMode = !this.announcesSelectionMode;
            if (!this.announcesSelectionMode) {
                this.selectedAnnounceHashes = [];
            }
        },
        exitFavouritesSelectionMode() {
            this.favouritesSelectionMode = false;
            this.selectedFavouriteHashes = [];
            this.favouriteBulkMoveMenuOpen = false;
        },
        exitAnnouncesSelectionMode() {
            this.announcesSelectionMode = false;
            this.selectedAnnounceHashes = [];
        },
        toggleSelectFavourite(hash) {
            const i = this.selectedFavouriteHashes.indexOf(hash);
            if (i >= 0) {
                this.selectedFavouriteHashes.splice(i, 1);
            } else {
                this.selectedFavouriteHashes.push(hash);
            }
        },
        toggleSelectAnnounce(hash) {
            const i = this.selectedAnnounceHashes.indexOf(hash);
            if (i >= 0) {
                this.selectedAnnounceHashes.splice(i, 1);
            } else {
                this.selectedAnnounceHashes.push(hash);
            }
        },
        toggleSelectAllVisibleFavourites() {
            const ids = this.flatVisibleFavouriteDestinationHashes;
            if (ids.length === 0) {
                return;
            }
            if (ids.every((id) => this.selectedFavouriteHashes.includes(id))) {
                this.selectedFavouriteHashes = this.selectedFavouriteHashes.filter((h) => !ids.includes(h));
            } else {
                this.selectedFavouriteHashes = [...new Set([...this.selectedFavouriteHashes, ...ids])];
            }
        },
        toggleSelectAllVisibleAnnounces() {
            const ids = this.flatVisibleAnnounceDestinationHashes;
            if (ids.length === 0) {
                return;
            }
            if (ids.every((id) => this.selectedAnnounceHashes.includes(id))) {
                this.selectedAnnounceHashes = this.selectedAnnounceHashes.filter((h) => !ids.includes(h));
            } else {
                this.selectedAnnounceHashes = [...new Set([...this.selectedAnnounceHashes, ...ids])];
            }
        },
        onFavouriteRowActivate(favourite) {
            if (this.isBlocked(favourite.destination_hash)) {
                return;
            }
            if (this.favouritesSelectionMode) {
                this.toggleSelectFavourite(favourite.destination_hash);
                return;
            }
            this.onFavouriteClick(favourite);
        },
        onAnnounceRowActivate(node) {
            if (this.isBlocked(node.identity_hash || node.destination_hash)) {
                return;
            }
            if (this.announcesSelectionMode) {
                this.toggleSelectAnnounce(node.destination_hash);
                return;
            }
            this.onNodeClick(node);
        },
        isFavouriteRowDragging(destinationHash) {
            return this.draggingFavouriteHashes.includes(destinationHash);
        },
        closeFavouriteBulkMoveMenu() {
            this.favouriteBulkMoveMenuOpen = false;
        },
        bulkMoveSelectedFavouritesToSection(sectionId) {
            if (!sectionId || this.selectedFavouriteHashes.length === 0) {
                this.closeFavouriteBulkMoveMenu();
                return;
            }
            this.moveFavouritesToSection([...this.selectedFavouriteHashes], sectionId);
            this.closeFavouriteBulkMoveMenu();
            this.exitFavouritesSelectionMode();
        },
        async bulkRemoveSelectedFavourites() {
            const hashes = [...this.selectedFavouriteHashes];
            if (hashes.length === 0) {
                return;
            }
            if (
                !(await DialogUtils.confirm(
                    this.$t("nomadnet.bulk_remove_favourites_confirm", { count: hashes.length })
                ))
            ) {
                return;
            }
            this.$emit("bulk-remove-favourites", hashes);
            this.exitFavouritesSelectionMode();
        },
        async bulkBanishSelectedAnnounces() {
            const nodes = this.selectedAnnounceHashes
                .map((h) => this.nodes[h])
                .filter((n) => n && !this.isBlocked(n.identity_hash) && !this.isBlocked(n.destination_hash));
            if (nodes.length === 0) {
                return;
            }
            if (!(await DialogUtils.confirm(this.$t("nomadnet.bulk_block_confirm", { count: nodes.length })))) {
                return;
            }
            try {
                for (const node of nodes) {
                    await window.api.post("/api/v1/blocked-destinations", {
                        destination_hash: node.identity_hash,
                    });
                }
                GlobalEmitter.emit("block-status-changed");
                ToastUtils.success(this.$t("nomadnet.bulk_block_done", { count: nodes.length }));
            } catch (e) {
                DialogUtils.alert(this.$t("nomadnet.failed_to_block_node"));
                console.error(e);
            }
            this.exitAnnouncesSelectionMode();
        },
        bulkAddSelectedAnnouncesToFavourites() {
            const nodes = this.selectedAnnounceHashes
                .map((h) => this.nodes[h])
                .filter((n) => n && !this.isFavourite(n.destination_hash));
            if (nodes.length === 0) {
                ToastUtils.info(this.$t("nomadnet.bulk_nothing_to_add_favourites"));
                return;
            }
            this.$emit("bulk-add-favourites", nodes);
            this.exitAnnouncesSelectionMode();
        },
        startEditingSection(section) {
            this.editingSectionId = section.id;
            this.editingSectionName = section.name;
            this.$nextTick(() => {
                const el = this.$refs[`sectionInput-${section.id}`];
                if (el && el[0]) el[0].focus();
            });
        },
        saveSectionName() {
            if (!this.editingSectionId) return;
            const sectionId = this.editingSectionId;
            const name = this.editingSectionName.trim();
            if (name) {
                this.sections = this.sections.map((sec) => (sec.id === sectionId ? { ...sec, name } : sec));
                this.persistFavouriteLayout();
            }
            this.cancelEditingSection();
        },
        cancelEditingSection() {
            this.editingSectionId = null;
            this.editingSectionName = "";
        },
        matchesFavouriteSearch(favourite, searchTerm = this.favouritesSearchTerm.toLowerCase()) {
            const matchesDisplayName = favourite.display_name.toLowerCase().includes(searchTerm);
            const matchesCustomDisplayName =
                favourite.custom_display_name?.toLowerCase()?.includes(searchTerm) === true;
            const matchesDestinationHash = favourite.destination_hash.toLowerCase().includes(searchTerm);
            return matchesDisplayName || matchesCustomDisplayName || matchesDestinationHash;
        },
        buildDefaultSection() {
            return {
                id: this.defaultSectionId,
                name: this.$t("nomadnet.favourites"),
                collapsed: false,
            };
        },
        resetDefaultSections() {
            const defaultSection = this.buildDefaultSection();
            this.sections = [defaultSection];
            this.sectionOrder = [defaultSection.id];
            this.favouritesBySection = { [defaultSection.id]: [] };
        },
        loadFavouriteLayout() {
            try {
                const stored = localStorage.getItem("meshchat.nomadnet.favourites.layout");
                if (stored) {
                    const parsed = JSON.parse(stored);
                    this.sections = parsed.sections || [];
                    this.sectionOrder =
                        parsed.sectionOrder ||
                        (parsed.sections ? parsed.sections.map((section) => section.id) : this.sectionOrder);
                    this.favouritesBySection = parsed.favouritesBySection || {};
                    return;
                }
                const legacyOrder = localStorage.getItem("meshchat.nomadnet.favourites");
                if (legacyOrder) {
                    const parsedOrder = JSON.parse(legacyOrder);
                    const defaultSection = this.buildDefaultSection();
                    this.sections = [defaultSection];
                    this.sectionOrder = [defaultSection.id];
                    this.favouritesBySection = { [defaultSection.id]: parsedOrder };
                }
            } catch (e) {
                console.log(e);
            }
            if (this.sections.length === 0) {
                this.resetDefaultSections();
            }
        },
        persistFavouriteLayout() {
            try {
                localStorage.setItem(
                    "meshchat.nomadnet.favourites.layout",
                    JSON.stringify({
                        sections: this.sections,
                        sectionOrder: this.sectionOrder,
                        favouritesBySection: this.favouritesBySection,
                    })
                );
            } catch (e) {
                console.log(e);
            }
        },
        ensureFavouriteLayout() {
            if (this.sections.length === 0) {
                this.resetDefaultSections();
            }
            const hashes = this.favourites.map((fav) => fav.destination_hash);
            const sectionIds = new Set();
            const sanitizedSections = [];
            this.sections.forEach((section) => {
                if (!section || !section.id || sectionIds.has(section.id)) {
                    return;
                }
                sectionIds.add(section.id);
                sanitizedSections.push({
                    id: section.id,
                    name: section.name || this.$t("nomadnet.favourites"),
                    collapsed: section.collapsed === true ? true : false,
                });
            });
            if (!sectionIds.has(this.defaultSectionId)) {
                const defaultSection = this.buildDefaultSection();
                sanitizedSections.unshift(defaultSection);
                sectionIds.add(defaultSection.id);
            }
            this.sections = sanitizedSections;
            const existingOrder = Array.isArray(this.sectionOrder) ? this.sectionOrder : [];
            const filteredOrder = existingOrder.filter((id) => sectionIds.has(id));
            const remaining = sanitizedSections
                .map((section) => section.id)
                .filter((id) => !filteredOrder.includes(id));
            this.sectionOrder = [...filteredOrder, ...remaining];

            const nextFavouritesBySection = {};
            sanitizedSections.forEach((section) => {
                const existing = this.favouritesBySection[section.id] || [];
                nextFavouritesBySection[section.id] = existing.filter((hash) => hashes.includes(hash));
            });
            const assigned = new Set(Object.values(nextFavouritesBySection).flat());
            hashes.forEach((hash) => {
                if (!assigned.has(hash)) {
                    nextFavouritesBySection[this.defaultSectionId].push(hash);
                    assigned.add(hash);
                }
            });
            this.favouritesBySection = nextFavouritesBySection;
            this.persistFavouriteLayout();
        },
        isBlocked(identityHash) {
            return this.blockedDestinations.some((b) => b.destination_hash === identityHash);
        },
        isFavourite(destinationHash) {
            return this.favourites.some((f) => f.destination_hash === destinationHash);
        },
        addFavouriteFromContext() {
            const node = this.announceContextMenu.node;
            if (!node) {
                this.closeContextMenus();
                return;
            }
            this.closeContextMenus();
            this.$emit("add-favourite", node);
        },
        async blockAnnounceFromContext() {
            const node = this.announceContextMenu.node;
            if (!node) {
                this.closeContextMenus();
                return;
            }
            this.closeContextMenus();
            await this.onBlockNode(node);
        },
        async unblockAnnounceFromContext() {
            const node = this.announceContextMenu.node;
            if (!node) {
                this.closeContextMenus();
                return;
            }
            this.closeContextMenus();
            await this.onUnblockNode(node.identity_hash);
        },
        async onBlockNode(node) {
            if (!(await DialogUtils.confirm(this.$t("nomadnet.block_node_confirm", { name: node.display_name })))) {
                return;
            }

            try {
                await window.api.post("/api/v1/blocked-destinations", {
                    destination_hash: node.identity_hash,
                });
                GlobalEmitter.emit("block-status-changed");
                DialogUtils.alert(this.$t("nomadnet.node_blocked_successfully"));
            } catch (e) {
                DialogUtils.alert(this.$t("nomadnet.failed_to_block_node"));
                console.log(e);
            }
        },
        async onUnblockNode(identityHash) {
            try {
                await window.api.delete(`/api/v1/blocked-destinations/${identityHash}`);
                GlobalEmitter.emit("block-status-changed");
                DialogUtils.alert(this.$t("nomadnet.banishment_lifted"));
            } catch (e) {
                DialogUtils.alert(this.$t("nomadnet.failed_lift_banishment"));
                console.log(e);
            }
        },
        onNodeClick(node) {
            if (this.isBlocked(node.identity_hash || node.destination_hash)) {
                return;
            }
            this.$emit("node-click", node);
        },
        onFavouriteClick(favourite) {
            if (this.isBlocked(favourite.destination_hash)) {
                return;
            }
            this.onNodeClick(favourite);
        },
        onRenameFavourite(favourite) {
            this.$emit("rename-favourite", favourite);
        },
        onRemoveFavourite(favourite) {
            this.$emit("remove-favourite", favourite);
        },
        onFavouriteDragStart(event, favourite, sectionId) {
            let hashes;
            if (
                this.favouritesSelectionMode &&
                this.selectedFavouriteHashes.includes(favourite.destination_hash) &&
                this.selectedFavouriteHashes.length > 1
            ) {
                hashes = [...this.selectedFavouriteHashes];
            } else {
                hashes = [favourite.destination_hash];
            }
            try {
                if (event?.dataTransfer) {
                    event.dataTransfer.effectAllowed = "move";
                    event.dataTransfer.setData("text/plain", favourite.destination_hash);
                    if (hashes.length > 1) {
                        event.dataTransfer.setData("application/x-meshchat-nomad-favs", JSON.stringify(hashes));
                    }
                }
            } catch {
                // ignore for browsers that prevent setting drag meta
            }
            this.draggingFavouriteHashes = hashes;
            this.draggingFavouriteHash = favourite.destination_hash;
            this.draggingFavouriteSectionId = sectionId;
        },
        onFavouriteDragOver(event) {
            if (event?.dataTransfer) {
                event.dataTransfer.dropEffect = "move";
            }
        },
        onFavouriteDrop(event, targetSectionId, targetFavourite) {
            const hashes =
                this.draggingFavouriteHashes.length > 0
                    ? [...this.draggingFavouriteHashes]
                    : this.draggingFavouriteHash
                      ? [this.draggingFavouriteHash]
                      : [];
            if (!hashes.length) {
                return;
            }
            if (hashes.includes(targetFavourite.destination_hash)) {
                return;
            }
            this.moveFavouritesToSection(hashes, targetSectionId, targetFavourite.destination_hash);
        },
        onFavouriteDragEnd() {
            this.draggingFavouriteHash = null;
            this.draggingFavouriteHashes = [];
            this.draggingFavouriteSectionId = null;
            this.dragOverSectionId = null;
        },
        onSectionDragOver(sectionId) {
            this.dragOverSectionId = sectionId;
        },
        onSectionDragLeave() {
            this.dragOverSectionId = null;
        },
        onDropOnSection(sectionId) {
            const hashes =
                this.draggingFavouriteHashes.length > 0
                    ? [...this.draggingFavouriteHashes]
                    : this.draggingFavouriteHash
                      ? [this.draggingFavouriteHash]
                      : [];
            if (!hashes.length) {
                return;
            }
            this.moveFavouritesToSection(hashes, sectionId);
        },
        onSectionDragStart(sectionId) {
            this.draggingSectionId = sectionId;
        },
        onSectionReorderDragOver(sectionId) {
            if (!this.draggingSectionId || this.draggingSectionId === sectionId) {
                return;
            }
            this.draggingSectionOverId = sectionId;
        },
        onSectionDrop(targetSectionId) {
            if (!this.draggingSectionId || this.draggingSectionId === targetSectionId) {
                this.onSectionDragEnd();
                return;
            }
            const currentOrder = [...this.sectionOrder];
            const fromIndex = currentOrder.indexOf(this.draggingSectionId);
            const toIndex = currentOrder.indexOf(targetSectionId);
            if (fromIndex === -1 || toIndex === -1) {
                this.onSectionDragEnd();
                return;
            }
            currentOrder.splice(fromIndex, 1);
            currentOrder.splice(toIndex, 0, this.draggingSectionId);
            this.sectionOrder = currentOrder;
            this.persistFavouriteLayout();
            this.onSectionDragEnd();
        },
        onSectionDragEnd() {
            this.draggingSectionId = null;
            this.draggingSectionOverId = null;
        },
        moveFavouriteToSection(hash, targetSectionId, beforeHash = null) {
            this.moveFavouritesToSection([hash], targetSectionId, beforeHash);
        },
        moveFavouritesToSection(hashes, targetSectionId, beforeHash = null) {
            const unique = [...new Set((hashes || []).filter(Boolean))];
            if (!unique.length || !targetSectionId) {
                return;
            }
            const updated = {};
            Object.keys(this.favouritesBySection).forEach((sectionKey) => {
                updated[sectionKey] = [...(this.favouritesBySection[sectionKey] || [])].filter(
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
            this.favouritesBySection = updated;
            this.persistFavouriteLayout();
            this.draggingFavouriteHash = null;
            this.draggingFavouriteHashes = [];
            this.draggingFavouriteSectionId = null;
            this.dragOverSectionId = null;
        },
        openFavouriteContextMenu(event, favourite, sectionId) {
            this.favouriteContextMenu = {
                show: true,
                justOpened: true,
                x: event.clientX,
                y: event.clientY,
                targetHash: favourite.destination_hash,
                targetSectionId: sectionId,
            };
            this.sectionContextMenu.show = false;
            setTimeout(() => {
                this.favouriteContextMenu.justOpened = false;
            }, 50);
        },
        openSectionContextMenu(event, section) {
            this.sectionContextMenu = {
                show: true,
                x: event.pageX || event.clientX,
                y: event.pageY || event.clientY,
                sectionId: section.id,
            };
            this.favouriteContextMenu.show = false;
        },
        async exportSectionFavouritesFromContext() {
            const sid = this.sectionContextMenu.sectionId;
            if (!sid) {
                this.closeContextMenus();
                return;
            }
            const section = this.sections.find((s) => s.id === sid);
            this.closeContextMenus();
            if (!section) {
                return;
            }
            const hashes = this.favouritesBySection[sid] || [];
            const payload = {
                format: "meshchatx/nomadnet_favourites_section/v1",
                exported_at: new Date().toISOString(),
                section: {
                    id: section.id,
                    name: section.name,
                    collapsed: section.collapsed === true,
                },
                destination_hashes: hashes.filter((h) => typeof h === "string"),
            };
            const slug = (section.name || "section")
                .replace(/[^a-z0-9]+/gi, "_")
                .replace(/^_|_$/g, "")
                .slice(0, 48);
            const namePart = slug || "section";
            const blob = new Blob([JSON.stringify(payload, null, 2)], { type: "application/json" });
            try {
                await DownloadUtils.downloadFile(`nomadnet_favourites_section_${namePart}.json`, blob);
                ToastUtils.success(this.$t("nomadnet.section_favourites_exported"));
            } catch {
                ToastUtils.error(this.$t("nomadnet.section_favourites_export_failed"));
            }
        },
        closeContextMenus() {
            this.favouriteContextMenu.show = false;
            this.sectionContextMenu.show = false;
            this.announceContextMenu.show = false;
            this.favouriteBulkMoveMenuOpen = false;
        },
        openAnnounceContextMenu(event, node) {
            this.announceContextMenu = {
                show: true,
                justOpened: true,
                x: event.clientX,
                y: event.clientY,
                node,
            };
            this.favouriteContextMenu.show = false;
            this.sectionContextMenu.show = false;
            setTimeout(() => {
                this.announceContextMenu.justOpened = false;
            }, 50);
        },
        getFavouriteByHash(hash) {
            return this.favourites.find((fav) => fav.destination_hash === hash);
        },
        renameFavouriteFromContext() {
            const favourite = this.getFavouriteByHash(this.favouriteContextMenu.targetHash);
            if (!favourite) {
                this.closeContextMenus();
                return;
            }
            this.closeContextMenus();
            this.onRenameFavourite(favourite);
        },
        removeFavouriteFromContext() {
            const favourite = this.getFavouriteByHash(this.favouriteContextMenu.targetHash);
            if (!favourite) {
                this.closeContextMenus();
                return;
            }
            this.closeContextMenus();
            this.onRemoveFavourite(favourite);
        },
        async banishFavouriteFromContext() {
            const favourite = this.getFavouriteByHash(this.favouriteContextMenu.targetHash);
            if (!favourite) {
                this.closeContextMenus();
                return;
            }
            this.closeContextMenus();
            if (
                !(await DialogUtils.confirm(
                    this.$t("nomadnet.block_node_confirm", {
                        name: favourite.display_name || favourite.custom_display_name,
                    })
                ))
            ) {
                return;
            }
            try {
                await window.api.post("/api/v1/blocked-destinations", {
                    destination_hash: favourite.destination_hash,
                });
                GlobalEmitter.emit("block-status-changed");
                DialogUtils.alert(this.$t("nomadnet.node_blocked_successfully"));
            } catch (e) {
                DialogUtils.alert(this.$t("nomadnet.failed_to_block_node"));
                console.error(e);
            }
        },
        async unblockFavouriteFromContext() {
            const hash = this.favouriteContextMenu.targetHash;
            if (!hash) {
                this.closeContextMenus();
                return;
            }
            this.closeContextMenus();
            try {
                await window.api.delete(`/api/v1/blocked-destinations/${hash}`);
                GlobalEmitter.emit("block-status-changed");
                DialogUtils.alert(this.$t("nomadnet.banishment_lifted"));
            } catch (e) {
                DialogUtils.alert(this.$t("nomadnet.failed_lift_banishment"));
                console.error(e);
            }
        },
        moveContextFavouriteToSection(sectionId) {
            if (!this.favouriteContextMenu.targetHash) {
                return;
            }
            this.moveFavouriteToSection(this.favouriteContextMenu.targetHash, sectionId);
            this.closeContextMenus();
        },
        toggleSectionCollapse(sectionId) {
            const idx = this.sections.findIndex((section) => section.id === sectionId);
            if (idx === -1) {
                return;
            }
            const updated = [...this.sections];
            const section = { ...updated[idx] };
            section.collapsed = !section.collapsed;
            updated[idx] = section;
            this.sections = updated;
            this.persistFavouriteLayout();
        },
        async createSection() {
            const name = await DialogUtils.prompt(
                this.$t("nomadnet.enter_section_name"),
                this.$t("nomadnet.new_section")
            );
            if (!name) {
                return;
            }
            const section = {
                id: `section-${Date.now()}`,
                name,
                collapsed: false,
            };
            this.sections = [...this.sections, section];
            this.sectionOrder = [...this.sectionOrder, section.id];
            this.favouritesBySection = { ...this.favouritesBySection, [section.id]: [] };
            this.persistFavouriteLayout();
        },
        async renameSectionFromContext() {
            const section = this.sections.find((sec) => sec.id === this.sectionContextMenu.sectionId);
            if (!section) {
                this.closeContextMenus();
                return;
            }
            const name = await DialogUtils.prompt(this.$t("nomadnet.rename_section"), section.name);
            if (!name || name === section.name) {
                this.closeContextMenus();
                return;
            }
            this.sections = this.sections.map((sec) => (sec.id === section.id ? { ...sec, name } : sec));
            this.persistFavouriteLayout();
            this.closeContextMenus();
        },
        async removeSectionFromContext() {
            const sectionId = this.sectionContextMenu.sectionId;
            if (!sectionId || sectionId === this.defaultSectionId) {
                this.closeContextMenus();
                return;
            }
            const confirmed = await DialogUtils.confirm(this.$t("nomadnet.delete_section_confirm"));
            if (!confirmed) {
                this.closeContextMenus();
                return;
            }
            const retainedSections = this.sections.filter((section) => section.id !== sectionId);
            const migrated = this.favouritesBySection[sectionId] || [];
            const nextMap = { ...this.favouritesBySection };
            delete nextMap[sectionId];
            nextMap[this.defaultSectionId] = [...(nextMap[this.defaultSectionId] || []), ...migrated];
            this.sections = retainedSections;
            this.sectionOrder = this.sectionOrder.filter((id) => id !== sectionId);
            this.favouritesBySection = nextMap;
            this.persistFavouriteLayout();
            this.closeContextMenus();
        },
        formatTimeAgo: function (datetimeString) {
            return Utils.formatTimeAgo(datetimeString);
        },
        formatTimeAgoForI18n: function (datetimeString) {
            return Utils.formatTimeAgoForI18n(datetimeString);
        },
        formatDestinationHash: function (destinationHash) {
            return Utils.formatDestinationHash(destinationHash);
        },
        copyToClipboard(text, label) {
            if (!text) return;
            navigator.clipboard.writeText(text);
            ToastUtils.success(`${label} copied to clipboard`);
        },
        onNodesSearchInput(event) {
            this.$emit("nodes-search-changed", event.target.value);
        },
        onNodesScroll(event) {
            const element = event.target;
            // if scrolled near bottom (within 200px)
            if (element.scrollHeight - element.scrollTop - element.clientHeight < 200) {
                if (this.hasMoreNodes && !this.isLoadingMoreNodes) {
                    this.$emit("load-more-nodes");
                }
            }
        },
    },
};
</script>

<style scoped>
@reference "../../style.css";
.sidebar-tab {
    @apply flex h-full w-1/2 items-center justify-center text-sm font-semibold text-gray-500 dark:text-gray-400 border-b-2 border-transparent transition;
}
.sidebar-tab--active {
    @apply text-blue-600 border-blue-500 dark:text-blue-300 dark:border-blue-400;
}
.favourite-card {
    @apply flex items-center gap-3 rounded-2xl border border-gray-200 dark:border-zinc-800 bg-white/90 dark:bg-zinc-900/70 px-3 py-2 cursor-pointer hover:border-blue-400 dark:hover:border-blue-500 hover:z-10;
}
.favourite-card--active {
    @apply border-blue-500 dark:border-blue-400 bg-blue-50/60 dark:bg-blue-900/30;
}
.favourite-card__icon,
.announce-card__icon {
    @apply w-10 h-10 rounded-xl bg-gray-100 dark:bg-zinc-800 flex items-center justify-center text-gray-500 dark:text-gray-300;
}
.favourite-card--dragging {
    @apply opacity-60 ring-2 ring-blue-300 dark:ring-blue-600;
}
.announce-card {
    @apply flex items-center gap-3 rounded-2xl border border-gray-200 dark:border-zinc-800 bg-white/90 dark:bg-zinc-900/70 px-3 py-2 hover:border-blue-400 dark:hover:border-blue-500 hover:z-10;
}
.announce-card--active {
    @apply border-blue-500 dark:border-blue-400 bg-blue-50/70 dark:bg-blue-900/30;
}
.empty-state {
    @apply flex flex-col items-center justify-center text-center gap-2 text-gray-500 dark:text-gray-400;
}
.empty-state--compact {
    @apply justify-center py-3;
}
.empty-state--panel {
    @apply min-h-[min(50vh,18rem)] py-10 sm:min-h-[min(45vh,20rem)];
}
</style>
