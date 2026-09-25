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

function toast(api, message, type, duration) {
    if (typeof api.toast === "function") {
        api.toast(message, type || "info", duration);
    }
}

/**
 * @param {{ t: (key: string) => string, invoke: Function, setUi: Function, onAction: Function, onRefresh: Function, toast?: Function }} api
 */
export async function activate(api) {
    let counter = 0;
    let lastMessage = "";

    function render() {
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
                    type: "section",
                    title: formatLabel(api, "counter_label"),
                    children: [
                        {
                            type: "text",
                            variant: "caption",
                            value: formatLabel(api, "counter_hint"),
                        },
                        {
                            type: "text",
                            variant: "stat",
                            value: formatLabel(api, "counter_value", { value: counter }),
                        },
                        {
                            type: "row",
                            children: [
                                {
                                    type: "button",
                                    id: "increment",
                                    label: formatLabel(api, "increment"),
                                    variant: "primary",
                                },
                                {
                                    type: "button",
                                    id: "ping",
                                    label: formatLabel(api, "ping"),
                                },
                            ],
                        },
                    ],
                },
                lastMessage
                    ? {
                          type: "text",
                          variant: "caption",
                          value: lastMessage,
                      }
                    : null,
            ].filter(Boolean),
        });
    }

    async function refresh() {
        const result = await api.invoke("counter", { op: "get" });
        if (result && typeof result.value === "number") {
            counter = result.value;
        }
        render();
    }

    api.onAction(async (actionId) => {
        try {
            if (actionId === "increment") {
                const result = await api.invoke("counter", { op: "inc" });
                if (result && typeof result.value === "number") {
                    counter = result.value;
                }
                render();
                return;
            }
            if (actionId === "ping") {
                const result = await api.invoke("ping", {});
                lastMessage = formatLabel(api, "pong", {
                    activated: result?.activated ? "yes" : "no",
                });
                toast(api, lastMessage, "success");
                render();
                return;
            }
        } catch {
            lastMessage = formatLabel(api, "invoke_failed");
            toast(api, lastMessage, "error");
            render();
        }
    });

    api.onRefresh(async () => {
        await refresh();
    });

    await refresh();
}
