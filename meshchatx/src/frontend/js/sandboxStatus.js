// SPDX-License-Identifier: 0BSD

const FEATURES = {
    landlock: {
        active: "landlock_active",
        supported: "landlock_kernel_supported",
        disabledByEnv: "landlock_disabled_by_env",
        autoEnabled: "landlock_auto_enabled",
        title: "app.landlock_status",
        notes: {
            activeAuto: "app.landlock_auto_enabled",
            active: "app.landlock_active",
            unsupported: "app.landlock_kernel_unsupported",
            disabledEnv: "app.landlock_disabled_by_env",
            inactive: "app.landlock_inactive",
        },
    },
    appcontainer: {
        active: "appcontainer_active",
        supported: "appcontainer_supported",
        disabledByEnv: "appcontainer_disabled_by_env",
        autoEnabled: "appcontainer_auto_enabled",
        title: "app.appcontainer_status",
        notes: {
            activeAuto: "app.appcontainer_auto_enabled",
            active: "app.appcontainer_active",
            unsupported: "app.appcontainer_unsupported",
            disabledEnv: "app.appcontainer_disabled_by_env",
            inactive: "app.appcontainer_inactive",
        },
    },
    seccomp: {
        active: "seccomp_active",
        supported: "seccomp_kernel_supported",
        disabledByEnv: "seccomp_disabled_by_env",
        autoEnabled: "seccomp_auto_enabled",
        title: "app.seccomp_status",
        notes: {
            activeAuto: "app.seccomp_auto_enabled",
            active: "app.seccomp_active",
            unsupported: "app.seccomp_kernel_unsupported",
            disabledEnv: "app.seccomp_disabled_by_env",
            inactive: "app.seccomp_inactive",
        },
    },
};

export function resolveSandboxFeature(info, feature) {
    const spec = FEATURES[feature];
    const data = info || {};
    const active = !!data[spec.active];
    const unavailable = data[spec.supported] === false;
    const disabledByEnv = !!data[spec.disabledByEnv];
    const autoEnabled = !!data[spec.autoEnabled];

    let badge = "app.enabled";
    if (active) {
        badge = "app.enabled";
    } else if (unavailable) {
        badge = "about.sandbox_status_unavailable";
    } else {
        badge = "app.disabled";
    }

    let noteKey = spec.notes.inactive;
    if (active) {
        noteKey = autoEnabled ? spec.notes.activeAuto : spec.notes.active;
    } else if (unavailable) {
        noteKey = spec.notes.unsupported;
    } else if (disabledByEnv) {
        noteKey = spec.notes.disabledEnv;
    }

    return {
        id: feature,
        titleKey: spec.title,
        badgeKey: badge,
        noteKey,
        active,
        unavailable,
        warn: !active && !unavailable && disabledByEnv,
    };
}

export function listSandboxFeatures(info) {
    const data = info || {};
    const rows = [];
    if (data.landlock_requested !== undefined) {
        rows.push(resolveSandboxFeature(data, "landlock"));
    }
    if (data.appcontainer_requested !== undefined) {
        rows.push(resolveSandboxFeature(data, "appcontainer"));
    }
    if (data.seccomp_requested !== undefined) {
        rows.push(resolveSandboxFeature(data, "seccomp"));
    }
    return rows;
}

export function sandboxSummaryType(info) {
    const data = info || {};
    const landlock = !!data.landlock_active;
    const seccomp = !!data.seccomp_active;
    const appcontainer = !!data.appcontainer_active;

    if (landlock && seccomp) {
        return "about.sandbox_type_landlock_seccomp";
    }
    if (appcontainer && seccomp) {
        return "about.sandbox_type_appcontainer_seccomp";
    }
    if (landlock) {
        return "about.sandbox_type_landlock";
    }
    if (seccomp) {
        return "about.sandbox_type_seccomp";
    }
    if (appcontainer) {
        return "about.sandbox_type_appcontainer";
    }
    return "about.sandbox_type_none";
}

export function sandboxSummaryActive(info) {
    const data = info || {};
    return Boolean(data.landlock_active || data.seccomp_active || data.appcontainer_active || data.fs_sandbox_active);
}
