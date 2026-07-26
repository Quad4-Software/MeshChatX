/* SPDX-License-Identifier: 0BSD */
(function () {
    try {
        var theme = null;
        if (window.MeshChatXAndroid && typeof window.MeshChatXAndroid.getPreferredUiTheme === "function") {
            theme = window.MeshChatXAndroid.getPreferredUiTheme();
        }
        if (!theme) {
            try {
                theme = window.localStorage.getItem("meshchatx_ui_theme");
            } catch (e) {}
        }
        if (theme !== "light" && theme !== "dark") {
            theme = "dark";
        }
        if (theme === "dark") {
            document.documentElement.classList.add("dark");
            document.documentElement.dataset.bootTheme = "dark";
            document.documentElement.style.colorScheme = "dark";
        } else {
            document.documentElement.classList.remove("dark");
            document.documentElement.dataset.bootTheme = "light";
            document.documentElement.style.colorScheme = "light";
        }
    } catch (e) {}
})();
