// SPDX-License-Identifier: 0BSD

import DownloadUtils from "../../../js/DownloadUtils.js";
import type { BotRecord, BotTemplate, LxmfConfigPatch } from "./types.js";

type WindowApi = {
    get: (
        url: string,
        config?: { params?: Record<string, unknown>; responseType?: string }
    ) => Promise<{ data?: unknown }>;
    post: (url: string, body?: unknown, config?: { responseType?: string }) => Promise<{ data?: unknown }>;
    patch: (url: string, body?: unknown) => Promise<{ data?: unknown }>;
};

function getApi(): WindowApi {
    const api = (window as unknown as { api?: WindowApi }).api;
    if (!api) {
        throw new Error("window.api is not available");
    }
    return api;
}

export async function fetchBotsStatus(): Promise<{ bots: BotRecord[]; templates: BotTemplate[] }> {
    const res = await getApi().get("/api/v1/bots/status");
    const data = (res.data || {}) as {
        status?: { bots?: BotRecord[] };
        templates?: BotTemplate[];
    };
    return {
        bots: data.status?.bots || [],
        templates: data.templates || [],
    };
}

export async function startBotApi(payload: {
    template_id?: string;
    name?: string;
    bot_id?: string;
    lxmf_config?: LxmfConfigPatch;
}): Promise<void> {
    await getApi().post("/api/v1/bots/start", payload);
}

export async function stopBotApi(botId: string): Promise<void> {
    await getApi().post("/api/v1/bots/stop", { bot_id: botId });
}

export async function restartBotApi(botId: string): Promise<void> {
    await getApi().post("/api/v1/bots/restart", { bot_id: botId });
}

export async function deleteBotApi(botId: string): Promise<void> {
    await getApi().post("/api/v1/bots/delete", { bot_id: botId });
}

export async function exportBotIdentityApi(botId: string): Promise<void> {
    const response = await getApi().post("/api/v1/bots/export", { bot_id: botId }, { responseType: "arraybuffer" });
    await DownloadUtils.downloadFromApiResponse(response, `bot_${botId}_identity`);
}

export async function updateBotNameApi(botId: string, name: string): Promise<void> {
    await getApi().patch("/api/v1/bots/update", {
        bot_id: botId,
        name,
    });
}

export async function forceAnnounceBotApi(botId: string): Promise<void> {
    await getApi().post("/api/v1/bots/announce", { bot_id: botId });
}

export async function fetchBotProcessLogApi(botId: string): Promise<{ log: string; truncated: boolean }> {
    const res = await getApi().get("/api/v1/bots/subprocess-log", {
        params: { bot_id: botId },
    });
    const data = (res.data || {}) as { log?: unknown; truncated?: boolean };
    return {
        log: data.log === null || data.log === undefined ? "" : String(data.log),
        truncated: Boolean(data.truncated),
    };
}

export async function patchBotLxmfConfigApi(botId: string, lxmf_config: LxmfConfigPatch): Promise<void> {
    await getApi().patch("/api/v1/bots/lxmf-config", {
        bot_id: botId,
        lxmf_config,
    });
}

export {
    startBotApi as startBot,
    stopBotApi as stopBot,
    restartBotApi as restartBot,
    deleteBotApi as deleteBot,
    exportBotIdentityApi as exportBotIdentity,
    updateBotNameApi as updateBotName,
    forceAnnounceBotApi as forceBotAnnounce,
    fetchBotProcessLogApi as fetchBotProcessLog,
    patchBotLxmfConfigApi as patchBotLxmfConfig,
};
