<!-- SPDX-License-Identifier: 0BSD AND MIT -->

<template>
    <RouterLink v-slot="{ href, navigate, isActive }" :to="to" custom>
        <a
            :href="href"
            type="button"
            :draggable="false"
            :aria-label="ariaLabel"
            :aria-current="isActive ? 'page' : null"
            :class="[
                collapsedActiveClass(navActive(isActive)),
                isCollapsed ? 'overflow-visible justify-center rounded-none' : 'overflow-hidden rounded-r-full mr-2',
            ]"
            class="sidebar-nav-link group focus-visible:outline-sem-focus"
            @click="handleNavigate($event, navigate)"
        >
            <span class="my-auto shrink-0 -translate-y-px">
                <slot name="icon"></slot>
            </span>
            <span v-if="!isCollapsed" class="my-auto flex w-full truncate transition-all duration-300">
                <slot name="text"></slot>
            </span>
        </a>
    </RouterLink>
</template>

<script setup lang="ts">
import { getCurrentInstance } from "vue";
import { useRoute } from "vue-router";
import { navRouteIsActive } from "../js/navRouteActive.js";

const props = withDefaults(
    defineProps<{
        ariaLabel?: string;
        to: Record<string, any>;
        isCollapsed?: boolean;
        editMode?: boolean;
    }>(),
    {
        ariaLabel: "",
        isCollapsed: false,
        editMode: false,
    }
);

const emit = defineEmits<{
    click: [];
}>();

const instance = getCurrentInstance();
const injectedRoute = useRoute();

// Resolve lazily: tests mock $route on the instance without installing vue-router.
function resolveRoute(): any {
    return (instance?.proxy as any)?.$route ?? injectedRoute;
}

function navActive(routerIsActive: boolean) {
    if (navRouteIsActive(props.to?.name, resolveRoute()?.name)) {
        return true;
    }
    return Boolean(routerIsActive);
}

defineExpose({ navActive, collapsedActiveClass, handleNavigate });

function collapsedActiveClass(isActive: boolean) {
    if (props.isCollapsed && isActive) {
        return [
            "text-sem-accent",
            "bg-sem-surface-muted",
            "shadow-[inset_2px_2px_5px_rgba(0,0,0,0.12),inset_-1px_-1px_2px_rgba(255,255,255,0.6)]",
            "dark:shadow-[inset_2px_2px_6px_rgba(0,0,0,0.72),inset_-1px_-1px_1px_rgba(255,255,255,0.07)]",
        ].join(" ");
    }
    if (isActive) {
        return "sidebar-nav-link--active";
    }
    return "sidebar-nav-link--hover";
}

function handleNavigate(event: Event, navigate: (e: Event) => void) {
    emit("click");
    if (props.editMode) {
        event.preventDefault();
        return;
    }
    navigate(event);
}
</script>
