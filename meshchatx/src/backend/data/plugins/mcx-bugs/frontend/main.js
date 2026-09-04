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

async function call(api, capability, args = {}) {
    if (typeof api.callManager === "function") {
        return api.callManager(capability, args);
    }
    return api.invoke("call", { capability, args });
}

/**
 * @param {{ t: (key: string) => string, invoke: Function, callManager?: Function, setUi: Function, onAction: Function, onRefresh: Function, onInput?: Function, getInputValue: Function, setInputValue?: Function, toast?: Function, clipboardWrite?: Function, download?: Function }} api
 */
export async function activate(api) {
    let status = {
        collector_running: false,
        destination_hash: null,
        collector_name: "",
        collectors: 0,
        reports: 0,
        issues: 0,
    };
    let collectors = [];
    let reports = [];
    let issues = [];
    let pending = [];
    let preview = null;
    let activeTab = "issues";
    let selectedHash = "";
    let selectedFingerprint = "";
    let viewingIssue = null;
    let viewingReport = null;
    let lastMessage = "";
    let lastMessageType = "info";

    function setMessage(message, type = "info") {
        lastMessage = message;
        lastMessageType = type;
    }

    function render() {
        const running = Boolean(status.collector_running);
        const destHash = status.destination_hash ? String(status.destination_hash) : "";
        const searchQuery = api.getInputValue("collector-search") || "";
        const issueSearch = (api.getInputValue("issue-search") || "").toLowerCase();
        const filteredCollectors = searchQuery
            ? collectors.filter(
                  (c) =>
                      (c.destination_hash || "").toLowerCase().includes(searchQuery.toLowerCase()) ||
                      (c.name || "").toLowerCase().includes(searchQuery.toLowerCase())
              )
            : collectors;
        const filteredIssues = issueSearch
            ? issues.filter(
                  (issue) =>
                      String(issue.title || "")
                          .toLowerCase()
                          .includes(issueSearch) ||
                      String(issue.fingerprint || "")
                          .toLowerCase()
                          .includes(issueSearch) ||
                      String(issue.status || "")
                          .toLowerCase()
                          .includes(issueSearch)
              )
            : issues;

        const tabsNode = {
            type: "tabs",
            active: activeTab,
            tabs: [
                { id: "issues", label: formatLabel(api, "tab_issues") },
                { id: "send", label: formatLabel(api, "tab_send") },
                { id: "collect", label: formatLabel(api, "tab_collect") },
            ],
            panels: [
                {
                    id: "issues",
                    children: [
                        {
                            type: "text",
                            variant: "caption",
                            value: formatLabel(api, "privacy_checklist"),
                        },
                        {
                            type: "input",
                            id: "issue-search",
                            label: formatLabel(api, "search_issues"),
                            placeholder: formatLabel(api, "search_placeholder"),
                            value: api.getInputValue("issue-search") || "",
                        },
                        {
                            type: "section",
                            title: formatLabel(api, "issues_section"),
                            children: [
                                filteredIssues.length
                                    ? {
                                          type: "table",
                                          columns: ["Title", "Count", "Status", "Last seen", ""],
                                          rows: filteredIssues.map((issue) => [
                                              String(issue.title || "-"),
                                              formatLabel(api, "count_label", {
                                                  count: issue.count || 1,
                                              }),
                                              {
                                                  type: "badge",
                                                  variant:
                                                      issue.status === "resolved"
                                                          ? "success"
                                                          : issue.status === "seen"
                                                            ? "info"
                                                            : "warning",
                                                  label: formatLabel(api, `status_${issue.status || "new"}`),
                                              },
                                              issue.last_seen
                                                  ? new Date(Number(issue.last_seen) * 1000).toLocaleString()
                                                  : "-",
                                              {
                                                  type: "actions",
                                                  items: [
                                                      {
                                                          id: `issue-view-${issue.fingerprint}`,
                                                          label: formatLabel(api, "view"),
                                                          variant: "secondary",
                                                      },
                                                  ],
                                              },
                                          ]),
                                          emptyText: formatLabel(api, "no_issues"),
                                      }
                                    : {
                                          type: "empty",
                                          value: formatLabel(api, "no_issues"),
                                      },
                                {
                                    type: "actions",
                                    items: [
                                        {
                                            id: "refresh",
                                            label: formatLabel(api, "refresh"),
                                            variant: "secondary",
                                        },
                                    ],
                                },
                            ],
                        },
                        viewingIssue
                            ? {
                                  type: "section",
                                  title: formatLabel(api, "issue_detail_section"),
                                  children: [
                                      {
                                          type: "text",
                                          variant: "subtitle",
                                          value: viewingIssue.title || "-",
                                      },
                                      {
                                          type: "widget",
                                          name: "HashBadge",
                                          props: {
                                              hash: viewingIssue.fingerprint || "",
                                              label: "fp",
                                          },
                                      },
                                      {
                                          type: "text",
                                          variant: "body",
                                          value: viewingIssue.description || "-",
                                      },
                                      {
                                          type: "widget",
                                          name: "IssueStackView",
                                          props: {
                                              stack: viewingIssue.exception?.stack || viewingIssue.log_text || "",
                                              maxHeight: "14rem",
                                          },
                                      },
                                      {
                                          type: "actions",
                                          items: [
                                              {
                                                  id: "issue-close",
                                                  label: formatLabel(api, "close"),
                                                  variant: "secondary",
                                              },
                                              {
                                                  id: "issue-seen",
                                                  label: formatLabel(api, "mark_seen"),
                                                  variant: "secondary",
                                              },
                                              {
                                                  id: "issue-resolve",
                                                  label: formatLabel(api, "resolve"),
                                                  variant: "secondary",
                                              },
                                              {
                                                  id: "issue-copy",
                                                  label: formatLabel(api, "copy"),
                                                  variant: "secondary",
                                              },
                                              {
                                                  id: "issue-send",
                                                  label: formatLabel(api, "send_issue"),
                                              },
                                          ],
                                      },
                                  ],
                              }
                            : null,
                    ].filter(Boolean),
                },
                {
                    id: "send",
                    children: [
                        {
                            type: "text",
                            variant: "caption",
                            value: formatLabel(api, "privacy_checklist"),
                        },
                        {
                            type: "section",
                            title: formatLabel(api, "sender_section"),
                            children: [
                                selectedFingerprint
                                    ? {
                                          type: "text",
                                          variant: "caption",
                                          value: formatLabel(api, "selected_issue", {
                                              fingerprint: shortHash(selectedFingerprint),
                                          }),
                                      }
                                    : null,
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
                                {
                                    type: "actions",
                                    items: [
                                        {
                                            id: "reset-destination",
                                            variant: "secondary",
                                            label: formatLabel(api, "reset_destination"),
                                        },
                                        ...(running && destHash
                                            ? [
                                                  {
                                                      id: "use-local",
                                                      variant: "secondary",
                                                      label: formatLabel(api, "use_my_collector"),
                                                  },
                                              ]
                                            : []),
                                        {
                                            id: "preview",
                                            variant: "secondary",
                                            label: formatLabel(api, "preview"),
                                        },
                                        {
                                            id: "send",
                                            label: formatLabel(api, "send"),
                                        },
                                        {
                                            id: "enqueue",
                                            variant: "secondary",
                                            label: formatLabel(api, "enqueue"),
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
                                          type: "empty",
                                          value: collectors.length
                                              ? formatLabel(api, "no_search_results")
                                              : formatLabel(api, "no_collectors"),
                                      },
                                preview
                                    ? {
                                          type: "code",
                                          value: preview.log_text ? String(preview.log_text).slice(0, 8000) : "",
                                          maxHeight: "12rem",
                                      }
                                    : {
                                          type: "text",
                                          variant: "caption",
                                          value: formatLabel(api, "no_preview"),
                                      },
                            ].filter(Boolean),
                        },
                    ],
                },
                {
                    id: "collect",
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
                                                  id: "save-name",
                                                  variant: "secondary",
                                                  label: formatLabel(api, "save_name"),
                                              },
                                              {
                                                  id: "announce",
                                                  variant: "secondary",
                                                  label: formatLabel(api, "announce"),
                                              },
                                              {
                                                  id: "stop-collector",
                                                  variant: "danger",
                                                  label: formatLabel(api, "stop_collector"),
                                              },
                                          ]
                                        : [
                                              {
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
                                                                  String(entry.description || "").slice(0, 160) || "-",
                                                          },
                                                      ],
                                                  },
                                                  {
                                                      type: "actions",
                                                      items: [
                                                          {
                                                              id: `view-${idx}`,
                                                              variant: "secondary",
                                                              label: formatLabel(api, "view"),
                                                          },
                                                          {
                                                              id: `copy-${idx}`,
                                                              variant: "secondary",
                                                              label: formatLabel(api, "copy"),
                                                          },
                                                          {
                                                              id: `export-${idx}`,
                                                              variant: "secondary",
                                                              label: formatLabel(api, "export"),
                                                          },
                                                          {
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
                                          type: "empty",
                                          value: formatLabel(api, "no_reports"),
                                      },
                                reports.length
                                    ? {
                                          type: "actions",
                                          items: [
                                              {
                                                  id: "clear-reports",
                                                  variant: "danger",
                                                  label: formatLabel(api, "clear_all"),
                                              },
                                          ],
                                      }
                                    : null,
                            ].filter(Boolean),
                        },
                        pending.length
                            ? {
                                  type: "section",
                                  title: formatLabel(api, "pending_section"),
                                  children: pending.map((entry) => ({
                                      type: "row",
                                      children: [
                                          {
                                              type: "text",
                                              variant: "body",
                                              value: entry.title || entry.id,
                                          },
                                          {
                                              type: "button",
                                              id: `cancel-pending-${entry.id}`,
                                              variant: "danger",
                                              label: formatLabel(api, "cancel_pending"),
                                          },
                                      ],
                                  })),
                              }
                            : null,
                        viewingReport
                            ? {
                                  type: "section",
                                  title: formatLabel(api, "view_report_section"),
                                  children: [
                                      {
                                          type: "actions",
                                          items: [
                                              {
                                                  id: "close-view",
                                                  variant: "secondary",
                                                  label: formatLabel(api, "close"),
                                              },
                                              {
                                                  id: "copy-view",
                                                  variant: "secondary",
                                                  label: formatLabel(api, "copy"),
                                              },
                                          ],
                                      },
                                      {
                                          type: "code",
                                          value: JSON.stringify(viewingReport, null, 2).slice(0, 12000),
                                          maxHeight: "16rem",
                                      },
                                  ],
                              }
                            : null,
                    ].filter(Boolean),
                },
            ],
        };

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
                lastMessage
                    ? {
                          type: "text",
                          variant:
                              lastMessageType === "error" ? "stat" : lastMessageType === "success" ? "body" : "caption",
                          value: lastMessage,
                      }
                    : null,
                tabsNode,
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

    async function copyText(text) {
        if (typeof api.clipboardWrite === "function") {
            await api.clipboardWrite(text);
            return;
        }
        throw new Error("clipboard unavailable");
    }

    async function refresh() {
        status = (await call(api, "bugReport.status")) || status;
        const listed = await call(api, "bugReport.listCollectors");
        collectors = listed?.collectors || [];
        const received = await call(api, "bugReport.listReports", { limit: 50 });
        reports = received?.reports || [];
        const issueList = await call(api, "bugReport.listIssues", { limit: 100 });
        issues = issueList?.issues || [];
        const pendingList = await call(api, "bugReport.listPendingSends");
        pending = pendingList?.pending || [];
        render();
    }

    api.onAction(async (actionId) => {
        try {
            if (actionId === "tab:issues" || actionId === "tab:send" || actionId === "tab:collect") {
                activeTab = actionId.slice("tab:".length);
                render();
                return;
            }
            if (actionId === "refresh") {
                await refresh();
                return;
            }
            if (actionId === "reset-destination") {
                selectedHash = "";
                if (api.setInputValue) {
                    api.setInputValue("collector-hash", "");
                }
                setMessage(formatLabel(api, "destination_reset"), "info");
                render();
                return;
            }
            if (actionId === "use-local") {
                selectedHash = String(status.destination_hash || "");
                if (api.setInputValue) {
                    api.setInputValue("collector-hash", selectedHash);
                }
                setMessage(formatLabel(api, "local_set"), "success");
                render();
                return;
            }
            if (actionId.startsWith("use-")) {
                selectedHash = actionId.slice("use-".length);
                if (api.setInputValue) {
                    api.setInputValue("collector-hash", selectedHash);
                }
                setMessage(formatLabel(api, "destination_set", { hash: shortHash(selectedHash) }), "success");
                render();
                return;
            }
            if (actionId === "preview") {
                preview = await call(api, "bugReport.preview", { limit: 200 });
                setMessage(
                    formatLabel(api, "preview_stats", {
                        lines: preview?.line_count || 0,
                        chars: preview?.chars || 0,
                    }),
                    "info"
                );
                render();
                return;
            }
            if (actionId === "send" || actionId === "enqueue") {
                const hash = (api.getInputValue("collector-hash") || selectedHash || "").trim();
                if (!isHexHash(hash)) {
                    setMessage(formatLabel(api, "invalid_hash", { value: hash || "" }), "error");
                    render();
                    return;
                }
                selectedHash = hash;
                const args = {
                    destination_hash: hash,
                    title: api.getInputValue("title") || "",
                    description: api.getInputValue("description") || "",
                    fingerprint: selectedFingerprint || undefined,
                    enqueue_on_timeout: actionId === "enqueue",
                };
                const result =
                    actionId === "enqueue"
                        ? await call(api, "bugReport.enqueueSend", args)
                        : await call(api, "bugReport.send", args);
                if (result?.queued) {
                    setMessage(formatLabel(api, "queued_ok"), "success");
                    toast(api, formatLabel(api, "queued_ok"), "success");
                } else {
                    setMessage(formatLabel(api, "send_ok", { bytes: result?.bytes || 0 }), "success");
                    toast(api, formatLabel(api, "send_ok", { bytes: result?.bytes || 0 }), "success");
                }
                await refresh();
                return;
            }
            if (actionId === "start-collector") {
                await call(api, "bugReport.startCollector", { announce: true });
                setMessage(formatLabel(api, "collector_started"), "success");
                await refresh();
                return;
            }
            if (actionId === "stop-collector") {
                await call(api, "bugReport.stopCollector");
                setMessage(formatLabel(api, "collector_stopped"), "info");
                await refresh();
                return;
            }
            if (actionId === "announce") {
                await call(api, "bugReport.announce");
                setMessage(formatLabel(api, "announce_ok"), "success");
                await refresh();
                return;
            }
            if (actionId === "save-name") {
                await call(api, "bugReport.setCollectorName", {
                    name: api.getInputValue("collector-name") || "",
                });
                await call(api, "bugReport.announce");
                setMessage(formatLabel(api, "name_saved"), "success");
                await refresh();
                return;
            }
            if (actionId.startsWith("issue-view-")) {
                const fp = actionId.slice("issue-view-".length);
                const result = await call(api, "bugReport.getIssue", { fingerprint: fp });
                viewingIssue = result?.issue || null;
                selectedFingerprint = fp;
                render();
                return;
            }
            if (actionId === "issue-close") {
                viewingIssue = null;
                render();
                return;
            }
            if (actionId === "issue-seen" || actionId === "issue-resolve") {
                const statusValue = actionId === "issue-resolve" ? "resolved" : "seen";
                if (viewingIssue?.fingerprint) {
                    await call(api, "bugReport.setIssueStatus", {
                        fingerprint: viewingIssue.fingerprint,
                        status: statusValue,
                    });
                    setMessage(formatLabel(api, "issue_status_set", { status: statusValue }), "success");
                    await refresh();
                    const result = await call(api, "bugReport.getIssue", {
                        fingerprint: viewingIssue.fingerprint,
                    });
                    viewingIssue = result?.issue || null;
                    render();
                }
                return;
            }
            if (actionId === "issue-copy") {
                try {
                    await copyText(JSON.stringify(viewingIssue, null, 2));
                    setMessage(formatLabel(api, "report_copied"), "success");
                } catch (error) {
                    setMessage(formatLabel(api, "copy_failed", { error: String(error) }), "error");
                }
                render();
                return;
            }
            if (actionId === "issue-send") {
                selectedFingerprint = viewingIssue?.fingerprint || "";
                if (api.setInputValue) {
                    api.setInputValue("title", viewingIssue?.title || "");
                    api.setInputValue("description", viewingIssue?.description || "");
                }
                activeTab = "send";
                render();
                return;
            }
            if (actionId.startsWith("view-")) {
                const idx = Number(actionId.slice("view-".length));
                viewingReport = reports[idx] || null;
                render();
                return;
            }
            if (actionId === "close-view") {
                viewingReport = null;
                render();
                return;
            }
            if (actionId.startsWith("copy-") || actionId === "copy-view") {
                const payload =
                    actionId === "copy-view" ? viewingReport : reports[Number(actionId.slice("copy-".length))];
                try {
                    await copyText(JSON.stringify(payload, null, 2));
                    setMessage(formatLabel(api, "report_copied"), "success");
                } catch (error) {
                    setMessage(formatLabel(api, "copy_failed", { error: String(error) }), "error");
                }
                render();
                return;
            }
            if (actionId.startsWith("export-")) {
                const idx = Number(actionId.slice("export-".length));
                const entry = reports[idx];
                if (entry) {
                    const filename = `bug-report-${entry.id || idx}.json`;
                    downloadJson(entry, filename);
                    setMessage(formatLabel(api, "report_exported", { filename }), "success");
                    render();
                }
                return;
            }
            if (actionId.startsWith("delete-")) {
                const idx = Number(actionId.slice("delete-".length));
                const entry = reports[idx];
                await call(api, "bugReport.deleteReport", { index: idx });
                setMessage(formatLabel(api, "report_deleted", { title: entry?.title || "-" }), "success");
                await refresh();
                return;
            }
            if (actionId === "clear-reports") {
                await call(api, "bugReport.clearReports");
                setMessage(formatLabel(api, "reports_cleared"), "success");
                await refresh();
                return;
            }
            if (actionId.startsWith("cancel-pending-")) {
                const id = actionId.slice("cancel-pending-".length);
                await call(api, "bugReport.cancelPendingSend", { id });
                await refresh();
            }
        } catch (error) {
            setMessage(String(error?.message || error), "error");
            toast(api, String(error?.message || error), "error");
            render();
        }
    });

    api.onInput((id, value) => {
        if (id === "collector-hash") {
            selectedHash = value;
        }
        if (id === "collector-search" || id === "issue-search") {
            render();
        }
    });

    api.onRefresh(async () => {
        await refresh();
    });

    await refresh();
}
