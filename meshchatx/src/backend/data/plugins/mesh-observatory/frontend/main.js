const MAX_ANNOUNCES = 80;

/**
 * @param {{ t: (key: string) => string }} api
 * @param {string} key
 * @param {Record<string, string | number>} [params]
 */
function formatLabel(api, key, params = {}) {
    let text = api.t(key);
    for (const [name, value] of Object.entries(params)) {
        text = text.replace(`{${name}}`, String(value));
    }
    return text;
}

function shortHash(hash) {
    if (!hash || hash.length < 12) {
        return hash || "—";
    }
    return `${hash.slice(0, 10)}…${hash.slice(-6)}`;
}

function shortInterface(name) {
    if (!name || typeof name !== "string") {
        return "—";
    }
    const match = name.match(/\[([^\]]+)\]/);
    if (match) {
        return match[1];
    }
    if (name.length > 36) {
        return `${name.slice(0, 18)}…${name.slice(-10)}`;
    }
    return name;
}

function hopLabel(api, hops) {
    if (hops == null) {
        return formatLabel(api, "hops_unknown");
    }
    if (hops === 1) {
        return formatLabel(api, "hops_one");
    }
    return formatLabel(api, "hops_many", { count: hops });
}

function stateNode(api, state) {
    let label = formatLabel(api, "state_unknown");
    let variant = "muted";
    if (state === 1) {
        label = formatLabel(api, "state_responsive");
        variant = "success";
    } else if (state === 2) {
        label = formatLabel(api, "state_unresponsive");
        variant = "danger";
    }
    return { type: "badge", label, variant };
}

/**
 * @param {{ t: (key: string) => string, invoke: Function, setUi: Function, onAction: Function, onEvent: Function, onRefresh: Function, getInputValue: Function }} api
 */
export async function activate(api) {
    /** @type {Array<Record<string, string>>} */
    let announces = [];
    /** @type {{ paths: Array<Record<string, unknown>>, total: number, responsive: number, unresponsive: number }} */
    let pathData = { paths: [], total: 0, responsive: 0, unresponsive: 0 };

    async function refreshPaths() {
        const search = (api.getInputValue("path-search") || "").trim();
        pathData = await api.invoke("readPaths", {
            search: search || undefined,
            limit: 150,
        });
    }

    function render() {
        const announceFilter = (api.getInputValue("announce-filter") || "").trim().toLowerCase();
        const filteredAnnounces = announces.filter((entry) => {
            if (!announceFilter) {
                return true;
            }
            const haystack =
                `${entry.aspect || ""} ${entry.destination_hash || ""} ${entry.app_data || ""}`.toLowerCase();
            return haystack.includes(announceFilter);
        });

        api.setUi({
            type: "column",
            children: [
                {
                    type: "text",
                    variant: "title",
                    value: formatLabel(api, "title"),
                },
                {
                    type: "text",
                    variant: "body",
                    value: formatLabel(api, "description"),
                },
                {
                    type: "actions",
                    items: [
                        {
                            type: "button",
                            id: "refresh",
                            label: formatLabel(api, "refresh"),
                        },
                    ],
                },
                {
                    type: "section",
                    title: formatLabel(api, "announces_section"),
                    description: formatLabel(api, "announce_stats", {
                        shown: Math.min(filteredAnnounces.length, 40),
                        total: announces.length,
                    }),
                    children: [
                        {
                            type: "input",
                            id: "announce-filter",
                            label: formatLabel(api, "filter"),
                            placeholder: formatLabel(api, "filter_placeholder"),
                        },
                        {
                            type: "actions",
                            items: [
                                {
                                    type: "button",
                                    id: "clear-announces",
                                    variant: "secondary",
                                    label: formatLabel(api, "clear_feed"),
                                },
                            ],
                        },
                        {
                            type: "list",
                            variant: "cards",
                            emptyText: formatLabel(api, "no_announces"),
                            items: filteredAnnounces.slice(0, 40).map((entry) => ({
                                type: "row",
                                variant: "announce-card",
                                children: [
                                    { type: "text", variant: "mono", value: entry.receivedAt || "—" },
                                    { type: "text", variant: "stat", value: entry.aspect || "—" },
                                    { type: "text", variant: "mono", value: shortHash(entry.destination_hash) },
                                    {
                                        type: "text",
                                        variant: "caption",
                                        value: (entry.app_data || "").slice(0, 72) || "—",
                                    },
                                ],
                            })),
                        },
                    ],
                },
                {
                    type: "section",
                    title: formatLabel(api, "paths_section"),
                    description: formatLabel(api, "path_stats", {
                        total: pathData.total || 0,
                        responsive: pathData.responsive || 0,
                        unresponsive: pathData.unresponsive || 0,
                    }),
                    children: [
                        {
                            type: "input",
                            id: "path-search",
                            label: formatLabel(api, "path_search"),
                            placeholder: formatLabel(api, "path_search_placeholder"),
                        },
                        {
                            type: "list",
                            variant: "cards",
                            emptyText: formatLabel(api, "no_paths"),
                            items: (pathData.paths || []).map((entry) => ({
                                type: "row",
                                variant: "card",
                                children: [
                                    {
                                        type: "text",
                                        variant: "mono",
                                        value: shortHash(entry.destination_hash),
                                    },
                                    { type: "text", variant: "stat", value: hopLabel(api, entry.hops) },
                                    {
                                        type: "text",
                                        variant: "caption",
                                        value: shortInterface(entry.interface),
                                    },
                                    stateNode(api, entry.state),
                                ],
                            })),
                        },
                    ],
                },
            ],
        });
    }

    async function refresh() {
        await refreshPaths();
        render();
    }

    api.onAction(async (actionId) => {
        if (actionId === "refresh") {
            await refresh();
        } else if (actionId === "clear-announces") {
            announces = [];
            render();
        }
    });

    api.onEvent("announce.received", async (payload) => {
        announces.unshift({
            aspect: payload?.aspect || "",
            destination_hash: payload?.destination_hash || "",
            app_data: payload?.app_data || "",
            receivedAt: new Date().toLocaleTimeString(),
        });
        if (announces.length > MAX_ANNOUNCES) {
            announces = announces.slice(0, MAX_ANNOUNCES);
        }
        await refreshPaths();
        render();
    });

    api.onRefresh(refresh);
    await refresh();
}
