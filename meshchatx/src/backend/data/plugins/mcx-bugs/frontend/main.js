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
        return hash || "-";
    }
    return `${hash.slice(0, 10)}…${hash.slice(-6)}`;
}

function isHexHash(value) {
    if (typeof value !== "string" || value.length === 0) {
        return false;
    }
    if (value.length < 32 || value.length > 64 || value.length % 2 !== 0) {
        return false;
    }
    return /^[0-9a-fA-F]+$/.test(value);
}

function toast(api, message, type, duration) {
    if (typeof api.toast === "function") {
        api.toast(message, type || "info", duration);
    }
}

/**
 * @param {{ t: (key: string) => string, invoke: Function, setUi: Function, onAction: Function, onRefresh: Function, onInput?: Function, getInputValue: Function, setInputValue?: Function, toast?: Function }} api
 */
export async function activate(api) {
    let status = {
        collector_running: false,
        destination_hash: null,
        collector_name: "",
        collectors: 0,
        reports: 0,
    };
    let collectors = [];
    let reports = [];
    let preview = null;
    let activeTab = "send";
    let selectedHash = "";
    let viewingReport = null;
    let lastMessage = "";
    let lastMessageType = "info";

    async function call(capability, args = {}) {
        return api.invoke("call", { capability, args });
    }

    function setMessage(message, type = "info") {
        lastMessage = message;
        lastMessageType = type;
    }

    function render() {
        const running = Boolean(status.collector_running);
        const destHash = status.destination_hash ? String(status.destination_hash) : "";

        const searchQuery = api.getInputValue("collector-search") || "";
        const filteredCollectors = searchQuery
            ? collectors.filter(
                  (c) =>
                      (c.destination_hash || "").toLowerCase().includes(searchQuery.toLowerCase()) ||
                      (c.name || "").toLowerCase().includes(searchQuery.toLowerCase())
              )
            : collectors;

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
                            id: "tab-send",
                            variant: activeTab === "send" ? undefined : "secondary",
                            label: formatLabel(api, "tab_send"),
                        },
                        {
                            type: "button",
                            id: "tab-collect",
                            variant: activeTab === "collect" ? undefined : "secondary",
                            label: formatLabel(api, "tab_collect"),
                        },
                    ],
                },
                lastMessage
                    ? {
                          type: "text",
                          variant:
                              lastMessageType === "error" ? "stat" : lastMessageType === "success" ? "body" : "caption",
                          value: lastMessage,
                      }
                    : null,
                activeTab === "send"
                    ? {
                          type: "section",
                          title: formatLabel(api, "sender_section"),
                          children: [
                              {
                                  type: "input",
                                  id: "title",
                                  label: formatLabel(api, "title_label"),
                                  placeholder: formatLabel(api, "title_placeholder"),
                                  value: api.getInputValue("title") || "",
                              },
                              {
                                  type: "input",
                                  id: "description",
                                  label: formatLabel(api, "description_label"),
                                  placeholder: formatLabel(api, "description_placeholder"),
                                  value: api.getInputValue("description") || "",
                                  multiline: true,
                              },
                              {
                                  type: "input",
                                  id: "collector-hash",
                                  label: formatLabel(api, "collector_hash"),
                                  placeholder: formatLabel(api, "collector_hash_placeholder"),
                                  value: selectedHash,
                              },
                              selectedHash
                                  ? {
                                        type: "text",
                                        variant: "caption",
                                        value: formatLabel(api, "selected_collector", {
                                            hash: shortHash(selectedHash),
                                        }),
                                    }
                                  : null,
                              {
                                  type: "actions",
                                  items: [
                                      {
                                          type: "button",
                                          id: "reset-destination",
                                          variant: "secondary",
                                          label: formatLabel(api, "reset_destination"),
                                      },
                                      ...(running && destHash
                                          ? [
                                                {
                                                    type: "button",
                                                    id: "use-local",
                                                    variant: "secondary",
                                                    label: formatLabel(api, "use_my_collector"),
                                                },
                                            ]
                                          : []),
                                      {
                                          type: "button",
                                          id: "preview",
                                          variant: "secondary",
                                          label: formatLabel(api, "preview"),
                                      },
                                      {
                                          type: "button",
                                          id: "send",
                                          label: formatLabel(api, "send"),
                                      },
                                  ],
                              },
                              {
                                  type: "input",
                                  id: "collector-search",
                                  label: formatLabel(api, "search_collectors"),
                                  placeholder: formatLabel(api, "search_placeholder"),
                                  value: api.getInputValue("collector-search") || "",
                              },
                              filteredCollectors.length
                                  ? {
                                        type: "list",
                                        variant: "cards",
                                        items: filteredCollectors.map((entry) => ({
                                            type: "row",
                                            variant: "card",
                                            children: [
                                                {
                                                    type: "text",
                                                    variant: "mono",
                                                    value: shortHash(entry.destination_hash),
                                                },
                                                {
                                                    type: "text",
                                                    variant: "caption",
                                                    value: entry.name || "-",
                                                },
                                                {
                                                    type: "button",
                                                    id: `use-${entry.destination_hash}`,
                                                    variant: "secondary",
                                                    label: formatLabel(api, "use_collector"),
                                                },
                                            ],
                                        })),
                                    }
                                  : {
                                        type: "text",
                                        variant: "caption",
                                        value: collectors.length
                                            ? formatLabel(api, "no_search_results")
                                            : formatLabel(api, "no_collectors"),
                                    },
                              {
                                  type: "actions",
                                  items: [
                                      {
                                          type: "button",
                                          id: "refresh",
                                          variant: "secondary",
                                          label: formatLabel(api, "refresh"),
                                      },
                                  ],
                              },
                              preview
                                  ? {
                                        type: "text",
                                        variant: "mono",
                                        value: preview.log_text ? String(preview.log_text).slice(0, 3000) : "",
                                    }
                                  : null,
                          ].filter(Boolean),
                      }
                    : activeTab === "collect"
                      ? {
                            type: "column",
                            children: [
                                {
                                    type: "section",
                                    title: formatLabel(api, "collector_section"),
                                    description: running
                                        ? formatLabel(api, "status_running", { hash: shortHash(destHash) })
                                        : formatLabel(api, "status_idle"),
                                    children: [
                                        {
                                            type: "input",
                                            id: "collector-name",
                                            label: formatLabel(api, "collector_name_label"),
                                            placeholder: formatLabel(api, "collector_name_placeholder"),
                                            value: api.getInputValue("collector-name") || status.collector_name || "",
                                        },
                                        {
                                            type: "actions",
                                            items: running
                                                ? [
                                                      {
                                                          type: "button",
                                                          id: "save-name",
                                                          variant: "secondary",
                                                          label: formatLabel(api, "save_name"),
                                                      },
                                                      {
                                                          type: "button",
                                                          id: "announce",
                                                          variant: "secondary",
                                                          label: formatLabel(api, "announce"),
                                                      },
                                                      {
                                                          type: "button",
                                                          id: "stop-collector",
                                                          variant: "danger",
                                                          label: formatLabel(api, "stop_collector"),
                                                      },
                                                  ]
                                                : [
                                                      {
                                                          type: "button",
                                                          id: "start-collector",
                                                          label: formatLabel(api, "start_collector"),
                                                      },
                                                  ],
                                        },
                                        running
                                            ? {
                                                  type: "text",
                                                  variant: "mono",
                                                  value: destHash,
                                              }
                                            : null,
                                    ].filter(Boolean),
                                },
                                {
                                    type: "section",
                                    title: formatLabel(api, "reports_section"),
                                    children: [
                                        reports.length
                                            ? {
                                                  type: "list",
                                                  variant: "cards",
                                                  items: reports.map((entry, idx) => ({
                                                      type: "row",
                                                      variant: "card",
                                                      children: [
                                                          {
                                                              type: "column",
                                                              children: [
                                                                  {
                                                                      type: "text",
                                                                      variant: "subtitle",
                                                                      value: entry.title || "-",
                                                                  },
                                                                  {
                                                                      type: "text",
                                                                      variant: "caption",
                                                                      value: formatLabel(api, "report_from", {
                                                                          source: shortHash(entry.source),
                                                                      }),
                                                                  },
                                                                  {
                                                                      type: "text",
                                                                      variant: "body",
                                                                      value:
                                                                          String(entry.description || "").slice(
                                                                              0,
                                                                              160
                                                                          ) || "-",
                                                                  },
                                                              ],
                                                          },
                                                          {
                                                              type: "actions",
                                                              items: [
                                                                  {
                                                                      type: "button",
                                                                      id: `view-${idx}`,
                                                                      variant: "secondary",
                                                                      label: formatLabel(api, "view"),
                                                                  },
                                                                  {
                                                                      type: "button",
                                                                      id: `copy-${idx}`,
                                                                      variant: "secondary",
                                                                      label: formatLabel(api, "copy"),
                                                                  },
                                                                  {
                                                                      type: "button",
                                                                      id: `export-${idx}`,
                                                                      variant: "secondary",
                                                                      label: formatLabel(api, "export"),
                                                                  },
                                                                  {
                                                                      type: "button",
                                                                      id: `delete-${idx}`,
                                                                      variant: "danger",
                                                                      label: formatLabel(api, "delete"),
                                                                  },
                                                              ],
                                                          },
                                                      ],
                                                  })),
                                              }
                                            : {
                                                  type: "text",
                                                  variant: "caption",
                                                  value: formatLabel(api, "no_reports"),
                                              },
                                        reports.length
                                            ? {
                                                  type: "actions",
                                                  items: [
                                                      {
                                                          type: "button",
                                                          id: "clear-reports",
                                                          variant: "danger",
                                                          label: formatLabel(api, "clear_all"),
                                                      },
                                                  ],
                                              }
                                            : null,
                                    ].filter(Boolean),
                                },
                                viewingReport
                                    ? {
                                          type: "section",
                                          title: formatLabel(api, "view_report_section"),
                                          children: [
                                              {
                                                  type: "actions",
                                                  items: [
                                                      {
                                                          type: "button",
                                                          id: "close-view",
                                                          variant: "secondary",
                                                          label: formatLabel(api, "close"),
                                                      },
                                                      {
                                                          type: "button",
                                                          id: "copy-view",
                                                          variant: "secondary",
                                                          label: formatLabel(api, "copy"),
                                                      },
                                                  ],
                                              },
                                              {
                                                  type: "text",
                                                  variant: "mono",
                                                  value: JSON.stringify(viewingReport, null, 2).slice(0, 4000),
                                              },
                                          ],
                                      }
                                    : null,
                            ].filter(Boolean),
                        }
                      : null,
            ].filter(Boolean),
        });
    }

    function downloadJson(data, filename) {
        const text = JSON.stringify(data, null, 2);
        if (typeof api.download === "function") {
            api.download(filename, text);
        } else {
            toast(api, "Download not supported in this environment", "error");
        }
    }

    async function refresh() {
        status = (await call("bugReport.status")) || status;
        const listed = await call("bugReport.listCollectors");
        collectors = listed?.collectors || [];
        const received = await call("bugReport.listReports", { limit: 20 });
        reports = received?.reports || [];
        render();
    }

    api.onAction(async (actionId) => {
        try {
            if (actionId === "tab-send") {
                activeTab = "send";
                render();
                return;
            }
            if (actionId === "tab-collect") {
                activeTab = "collect";
                await refresh();
                render();
                return;
            }
            if (typeof actionId === "string" && actionId.startsWith("use-") && actionId !== "use-local") {
                const hash = actionId.slice(4);
                if (isHexHash(hash)) {
                    selectedHash = hash.toLowerCase();
                    setMessage(
                        formatLabel(api, "destination_set", {
                            hash: shortHash(selectedHash),
                        }),
                        "success"
                    );
                    toast(
                        api,
                        formatLabel(api, "destination_set", {
                            hash: shortHash(selectedHash),
                        }),
                        "success"
                    );
                } else {
                    setMessage(formatLabel(api, "invalid_hash", { value: hash }), "error");
                    toast(api, formatLabel(api, "invalid_hash", { value: hash }), "error");
                }
                render();
                return;
            }
            if (actionId === "use-local") {
                const fresh = await call("bugReport.status");
                status = fresh || status;
                const localHash = status.destination_hash ? String(status.destination_hash) : "";
                if (isHexHash(localHash)) {
                    selectedHash = localHash.toLowerCase();
                    setMessage(formatLabel(api, "local_set") + ` (${shortHash(selectedHash)})`, "success");
                    toast(api, formatLabel(api, "local_set") + ` (${shortHash(selectedHash)})`, "success");
                } else {
                    const msg = "No local collector running. Start one first.";
                    setMessage(msg, "warning");
                    toast(api, msg, "warning");
                }
                render();
                return;
            }
            if (actionId === "reset-destination") {
                selectedHash = "";
                setMessage(formatLabel(api, "destination_reset"), "info");
                toast(api, formatLabel(api, "destination_reset"), "info");
                render();
                return;
            }
            if (actionId === "refresh") {
                await refresh();
                return;
            }
            if (actionId === "preview") {
                preview = await call("bugReport.preview", { limit: 200 });
                setMessage(
                    formatLabel(api, "preview_stats", {
                        lines: preview?.line_count || 0,
                        chars: preview?.chars || 0,
                    }),
                    "info"
                );
                toast(
                    api,
                    formatLabel(api, "preview_stats", {
                        lines: preview?.line_count || 0,
                        chars: preview?.chars || 0,
                    }),
                    "info"
                );
                render();
                return;
            }
            if (actionId === "send") {
                if (!isHexHash(selectedHash)) {
                    const fresh = await call("bugReport.status");
                    status = fresh || status;
                    const localHash = status.destination_hash ? String(status.destination_hash) : "";
                    if (isHexHash(localHash)) {
                        selectedHash = localHash.toLowerCase();
                    }
                }
                if (!isHexHash(selectedHash)) {
                    const msg = formatLabel(api, "invalid_hash", {
                        value: selectedHash || "(empty)",
                    });
                    setMessage(msg, "error");
                    toast(api, msg, "error");
                    render();
                    return;
                }
                const result = await call("bugReport.send", {
                    destination_hash: selectedHash,
                    title: api.getInputValue("title") || "",
                    description: api.getInputValue("description") || "",
                    limit: 200,
                });
                const msg = formatLabel(api, "send_ok", {
                    bytes: result?.bytes || 0,
                });
                setMessage(msg, "success");
                toast(api, msg, "success");
                await refresh();
                return;
            }
            if (actionId === "start-collector") {
                const name = api.getInputValue("collector-name") || "";
                if (name) {
                    await call("bugReport.setCollectorName", { name });
                }
                status = await call("bugReport.startCollector", {
                    announce: true,
                });
                const msg = formatLabel(api, "collector_started");
                setMessage(msg, "success");
                toast(api, msg, "success");
                await refresh();
                return;
            }
            if (actionId === "save-name") {
                const name = api.getInputValue("collector-name") || "";
                status = await call("bugReport.setCollectorName", { name });
                await call("bugReport.announce");
                const msg = formatLabel(api, "name_saved");
                setMessage(msg, "success");
                toast(api, msg, "success");
                await refresh();
                return;
            }
            if (actionId === "stop-collector") {
                status = await call("bugReport.stopCollector");
                const msg = formatLabel(api, "collector_stopped");
                setMessage(msg, "info");
                toast(api, msg, "info");
                await refresh();
                return;
            }
            if (actionId === "announce") {
                status = await call("bugReport.announce");
                const msg = formatLabel(api, "announce_ok");
                setMessage(msg, "info");
                toast(api, msg, "info");
                render();
                return;
            }
            if (typeof actionId === "string" && actionId.startsWith("view-")) {
                const idx = parseInt(actionId.slice(5), 10);
                viewingReport = reports[idx] || null;
                if (viewingReport) {
                    activeTab = "collect";
                }
                render();
                return;
            }
            if (actionId === "close-view") {
                viewingReport = null;
                render();
                return;
            }
            if (actionId === "copy-view") {
                if (viewingReport) {
                    const text = JSON.stringify(viewingReport, null, 2);
                    try {
                        await navigator.clipboard.writeText(text);
                        const msg = formatLabel(api, "report_copied");
                        setMessage(msg, "success");
                        toast(api, msg, "success");
                    } catch (err) {
                        const msg = formatLabel(api, "copy_failed", {
                            error: String(err),
                        });
                        setMessage(msg, "error");
                        toast(api, msg, "error");
                    }
                }
                render();
                return;
            }
            if (typeof actionId === "string" && actionId.startsWith("delete-")) {
                const idx = parseInt(actionId.slice(7), 10);
                const entry = reports[idx];
                await call("bugReport.deleteReport", { index: idx });
                const msg = formatLabel(api, "report_deleted", {
                    title: entry?.title || "",
                });
                setMessage(msg, "info");
                toast(api, msg, "info");
                await refresh();
                return;
            }
            if (typeof actionId === "string" && actionId.startsWith("copy-")) {
                const idx = parseInt(actionId.slice(5), 10);
                const entry = reports[idx];
                const text = JSON.stringify(entry, null, 2);
                try {
                    await navigator.clipboard.writeText(text);
                    const msg = formatLabel(api, "report_copied");
                    setMessage(msg, "success");
                    toast(api, msg, "success");
                } catch (err) {
                    const msg = formatLabel(api, "copy_failed", {
                        error: String(err),
                    });
                    setMessage(msg, "error");
                    toast(api, msg, "error");
                }
                render();
                return;
            }
            if (typeof actionId === "string" && actionId.startsWith("export-")) {
                const idx = parseInt(actionId.slice(7), 10);
                const entry = reports[idx];
                const stamp = entry.received_at
                    ? new Date(typeof entry.received_at === "number" ? entry.received_at * 1000 : entry.received_at)
                          .toISOString()
                          .replace(/[:.]/g, "-")
                    : Date.now();
                const filename = `bug-report-${stamp}.json`;
                downloadJson(entry, filename);
                const msg = formatLabel(api, "report_exported", {
                    filename,
                });
                setMessage(msg, "success");
                toast(api, msg, "success");
                render();
                return;
            }
            if (actionId === "clear-reports") {
                await call("bugReport.clearReports");
                const msg = formatLabel(api, "reports_cleared");
                setMessage(msg, "info");
                toast(api, msg, "info");
                await refresh();
                return;
            }
        } catch (error) {
            const message = error?.message || String(error);
            setMessage(message, "error");
            toast(api, message, "error");
            render();
        }
    });

    api.onRefresh(refresh);
    if (typeof api.onInput === "function") {
        api.onInput((id) => {
            if (id === "collector-search") {
                render();
            }
            if (id === "collector-hash") {
                selectedHash = (api.getInputValue("collector-hash") || "").trim().toLowerCase();
                render();
            }
        });
    }
    await refresh();
}
