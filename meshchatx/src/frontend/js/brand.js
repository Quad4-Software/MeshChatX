// SPDX-License-Identifier: 0BSD
// Brand constants for the frontend. Values come from repo-root brand.json
// injected by vite/vitest define as __BRAND__, with the upstream defaults as
// fallback so tests and partial builds still work.

const DEFAULT_BRAND = {
    name: "MeshChatX",
    product_name: "Reticulum MeshChatX",
    slug: "meshchatx",
    app_id: "com.meshchatx.app",
    repository: "Quad4-Software/MeshChatX",
    homepage: "https://meshchatx.com",
    issues_url: "https://github.com/Quad4-Software/MeshChatX/issues",
    container_image: "ghcr.io/quad4-software/meshchatx",
    docker_hub_image: "quad4io/meshchatx",
    flatpak_repo_base_url: "",
    copyright_holder: "MeshChatX contributors",
    security_contact: "f489752fbef161c64d65e385a4e9fc74",
};

const injected = typeof globalThis !== "undefined" && globalThis.__BRAND__ ? globalThis.__BRAND__ : {};

function derive(brand) {
    const out = { ...brand };
    if (!out.issues_url && out.repository) {
        out.issues_url = `https://github.com/${out.repository}/issues`;
    }
    if (!out.flatpak_repo_base_url && out.repository && out.repository.includes("/")) {
        const [owner, name] = out.repository.split("/");
        out.flatpak_repo_base_url = `https://${owner.toLowerCase()}.github.io/${name}/flatpak`;
    }
    if (!out.repo_url && out.repository) {
        out.repo_url = `https://github.com/${out.repository}`;
    }
    return out;
}

export const brand = derive({ ...DEFAULT_BRAND, ...injected });
