/* SPDX-License-Identifier: 0BSD */
(function () {
    try {
        var preference = null;
        if (window.MeshChatXAndroid && typeof window.MeshChatXAndroid.getPreferredUiTheme === "function") {
            preference = window.MeshChatXAndroid.getPreferredUiTheme();
        }
        if (!preference) {
            try {
                preference = window.localStorage.getItem("meshchatx_ui_theme");
            } catch (e) {}
        }
        var effective;
        if (preference === "light" || preference === "dark") {
            // Explicit choices are preserved verbatim.
            effective = preference;
        } else {
            // "system", unset, or unrecognized values follow the OS scheme.
            // When the platform cannot report one, stay dark.
            var media =
                window.matchMedia && window.matchMedia("(prefers-color-scheme: dark)");
            effective = !media || media.matches ? "dark" : "light";
        }
        if (effective === "dark") {
            document.documentElement.classList.add("dark");
            document.documentElement.dataset.bootTheme = "dark";
            document.documentElement.style.colorScheme = "dark";
        } else {
            document.documentElement.classList.remove("dark");
            document.documentElement.dataset.bootTheme = "light";
            document.documentElement.style.colorScheme = "light";
        }
        document.documentElement.dataset.themePreference =
            preference === "light" || preference === "dark" || preference === "system"
                ? preference
                : "system";
    } catch (e) {}
})();
