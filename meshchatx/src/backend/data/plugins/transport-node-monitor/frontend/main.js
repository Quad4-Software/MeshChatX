export async function activate(api) {
    let watchedNodes = [];
    let paths = [];

    async function refresh() {
        const state = await api.invoke("getState");
        watchedNodes = state?.watched_nodes || [];
        const pathResult = await api.invoke("readPaths", { destination_hash: null });
        paths = pathResult?.paths || [];
        api.setUi({
            type: "column",
            children: [
                {
                    type: "text",
                    variant: "title",
                    value: api.t("plugins.transport_node_monitor.title"),
                },
                {
                    type: "text",
                    value: api.t("plugins.transport_node_monitor.description"),
                },
                {
                    type: "input",
                    id: "watch-hash",
                    label: api.t("plugins.transport_node_monitor.watch_hash"),
                    placeholder: api.t("plugins.transport_node_monitor.watch_hash_placeholder"),
                },
                {
                    type: "button",
                    id: "add-watch",
                    label: api.t("plugins.transport_node_monitor.add_watch"),
                },
                {
                    type: "list",
                    items: watchedNodes.map((hash) => ({
                        type: "row",
                        children: [
                            { type: "text", value: hash },
                            {
                                type: "text",
                                value:
                                    paths.find((entry) => entry.destination_hash === hash)?.hops?.toString() ??
                                    api.t("plugins.transport_node_monitor.no_path"),
                            },
                        ],
                    })),
                },
            ],
        });
    }

    api.onAction(async (actionId) => {
        if (actionId !== "add-watch") {
            return;
        }
        const input = api.getInputValue("watch-hash");
        const hash = (input || "").trim().toLowerCase();
        if (!hash || watchedNodes.includes(hash)) {
            return;
        }
        watchedNodes = [...watchedNodes, hash];
        await api.invoke("setWatchedNodes", { nodes: watchedNodes });
        await refresh();
    });

    api.onEvent("announce.received", async () => {
        await refresh();
    });

    api.onRefresh(refresh);

    await refresh();
}
