const { test, expect } = require("@playwright/test");

const E2E_BACKEND_PORT = process.env.E2E_BACKEND_PORT || "18079";
const E2E_BACKEND_ORIGIN = `http://127.0.0.1:${E2E_BACKEND_PORT}`;

test.describe("MeshChatX E2E (Vite + Python backend)", () => {
    test("backend /api/v1/status is OK (via Vite proxy)", async ({ request }) => {
        const res = await request.get("/api/v1/status");
        expect(res.ok()).toBeTruthy();
        const body = await res.json();
        expect(body.status).toBe("ok");
    });

    test("backend /api/v1/self-test returns success for all checks", async ({ request }) => {
        const res = await request.get("/api/v1/self-test");
        expect(res.ok()).toBeTruthy();
        const body = await res.json();
        const keys = [
            "stack_up",
            "config_good",
            "db_good",
            "read_write_good",
            "identity_good",
            "imports_good",
            "storage_lock_good",
            "temp_fs_good",
            "public_assets_good",
            "lxmf_router_good",
            "subprocess_good",
            "run_module_good",
            "sqlite_roundtrip",
            "identity_roundtrip",
            "loopback_tcp",
            "unicode_path_good",
            "rnode_support_good",
            "bot_launcher_good",
            "http_status_good",
            "http_app_info_good",
            "http_config_good",
            "http_db_health_good",
            "http_auth_csrf_good",
            "http_bots_status_good",
            "http_security_good",
            "http_interfaces_good",
            "http_reticulum_instance_good",
            "http_identities_good",
            "http_favourites_good",
            "http_telephone_good",
            "http_plugins_good",
            "http_plugins_trust_good",
            "http_sideband_plugins_good",
            "http_sideband_config_good",
            "http_rrc_hubs_good",
            "http_rrc_servers_good",
            "plugins_runtime_good",
            "websocket_good",
            "websocket_rns_link_good",
            "bots_lifecycle",
        ];
        for (const key of keys) {
            expect(body[key], key).toBeDefined();
            expect(body[key].status, `${key}: ${body[key].reason || "(no reason)"}`).toBe("ok");
        }
    });

    test("backend /api/v1/app/info returns version JSON (direct backend)", async ({ request }) => {
        const res = await request.get(`${E2E_BACKEND_ORIGIN}/api/v1/app/info`);
        expect(res.ok()).toBeTruthy();
        const body = await res.json();
        expect(body.app_info).toBeDefined();
        expect(String(body.app_info.version).length).toBeGreaterThan(0);
    });

    test("document title, shell, and app name in header", async ({ page }) => {
        await page.goto("/");
        await expect(page).toHaveTitle(/Reticulum MeshChatX/);
        await expect(page.getByText("Reticulum MeshChatX", { exact: true }).first()).toBeVisible({
            timeout: 30000,
        });
        const root = page.locator("#app");
        await expect(root).toBeVisible();
        await expect(root.locator("div").first()).toBeVisible({ timeout: 30000 });
    });

    test("about page shows MeshChatX and version", async ({ page }) => {
        await page.goto("/#/about");
        await expect(page).toHaveURL(/#\/about/);
        await expect(page.getByText("MeshChatX", { exact: true }).first()).toBeVisible({ timeout: 30000 });
        await expect(page.locator("#app")).toBeVisible();
    });

    test("settings route loads profile section", async ({ page }) => {
        await page.goto("/#/settings");
        await expect(page).toHaveURL(/#\/settings/);
        await expect(page.getByText("Profile", { exact: true }).first()).toBeVisible({ timeout: 30000 });
    });

    test("messages route is reachable", async ({ page }) => {
        await page.goto("/#/messages");
        await expect(page).toHaveURL(/#\/messages/);
        await expect(page.locator("#app")).toBeVisible();
    });

    test("debug logs route shows Logs and Access attempts tabs", async ({ page }) => {
        await page.goto("/#/debug/logs");
        await expect(page).toHaveURL(/#\/debug\/logs/);
        await expect(page.getByRole("button", { name: "Logs", exact: true })).toBeVisible({ timeout: 30000 });
        await expect(page.getByRole("button", { name: "Access attempts", exact: true })).toBeVisible({
            timeout: 30000,
        });
    });
});
