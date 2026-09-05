// SPDX-License-Identifier: 0BSD

import { mount, unmount } from "svelte";

type VueHostVm = {
    $refs: Record<string, Element | undefined>;
    [key: string]: unknown;
};

type BuildPropsFn = (vm: VueHostVm) => Record<string, unknown>;

type ThinSvelteHostOptions = {
    component: Parameters<typeof mount>[0];
    buildProps: BuildPropsFn;
    refKey?: string;
    stateKey?: string;
    extraWatch?: Record<string, unknown>;
};

export function serializeSvelteProps(props: Record<string, unknown>): string {
    return JSON.stringify(props, (_key, value) => {
        if (typeof value === "function") {
            return undefined;
        }
        return value;
    });
}

export function teardownSvelteHost(vm: VueHostVm, stateKey = "_svelte"): void {
    const inst = vm[stateKey];
    if (inst) {
        try {
            unmount(inst as Parameters<typeof unmount>[0]);
        } catch {
            /* already gone */
        }
        vm[stateKey] = null;
    }
}

export function createThinSvelteHostMethods(options: ThinSvelteHostOptions) {
    const { component, buildProps, refKey = "root", stateKey = "_svelte" } = options;

    const methods = {
        _teardownSvelte(this: VueHostVm) {
            teardownSvelteHost(this, stateKey);
            this._sveltePropsSnapshot = null;
        },
        _ensureSvelteMounted(this: VueHostVm) {
            methods._syncSvelteProps.call(this, true);
        },
        _syncSvelteProps(this: VueHostVm, force = false) {
            if (this._svelteMounting) {
                return;
            }
            const root = this.$refs[refKey];
            if (!root) {
                return;
            }

            const props = buildProps(this);
            const snapshot = serializeSvelteProps(props);
            if (!force && this._svelte && this._sveltePropsSnapshot === snapshot) {
                return;
            }

            this._svelteMounting = true;
            try {
                teardownSvelteHost(this, stateKey);
                this[stateKey] = mount(component, {
                    target: root,
                    props,
                });
                this._sveltePropsSnapshot = snapshot;
            } finally {
                this._svelteMounting = false;
            }
        },
    };
    return methods;
}

export function createThinSvelteHost(options: ThinSvelteHostOptions) {
    const methods = createThinSvelteHostMethods(options);

    return {
        mounted(this: VueHostVm) {
            methods._ensureSvelteMounted.call(this);
        },
        beforeUnmount(this: VueHostVm) {
            methods._teardownSvelte.call(this);
        },
        watch: {
            $props: {
                deep: true,
                handler(this: VueHostVm) {
                    methods._syncSvelteProps.call(this);
                },
            },
            ...(options.extraWatch || {}),
        },
        methods,
    };
}
