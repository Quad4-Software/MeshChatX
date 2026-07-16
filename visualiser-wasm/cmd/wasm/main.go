// SPDX-License-Identifier: 0BSD

// Command wasm exposes network visualiser hot-path helpers to the browser.
package main

import (
	"encoding/json"
	"syscall/js"

	"github.com/Quad4-Software/MeshChatX/visualiser-wasm/internal/filter"
	"github.com/Quad4-Software/MeshChatX/visualiser-wasm/internal/graph"
	"github.com/Quad4-Software/MeshChatX/visualiser-wasm/internal/icon"
	"github.com/Quad4-Software/MeshChatX/visualiser-wasm/internal/layout"
	"github.com/Quad4-Software/MeshChatX/visualiser-wasm/internal/lod"
)

const apiVersion = "1.1.0"

func main() {
	js.Global().Set("meshchatxVisualiserVersion", apiVersion)
	js.Global().Set("meshchatxVisualiserPathHashes", js.FuncOf(wrapJSON(pathHashesHandler)))
	js.Global().Set("meshchatxVisualiserDedupeIcons", js.FuncOf(wrapJSON(dedupeIconsHandler)))
	js.Global().Set("meshchatxVisualiserBuildPathGraph", js.FuncOf(wrapJSON(buildPathGraphHandler)))
	js.Global().Set("meshchatxVisualiserBuildFullGraph", js.FuncOf(wrapJSON(buildFullGraphHandler)))
	js.Global().Set("meshchatxVisualiserLayout", js.FuncOf(wrapJSON(layoutHandler)))
	js.Global().Set("meshchatxVisualiserLODUpdates", js.FuncOf(wrapJSON(lodUpdatesHandler)))
	js.Global().Set("meshchatxVisualiserLODLevel", js.FuncOf(lodLevelHandler))

	select {}
}

type handlerFunc func(args []js.Value) (any, error)

func wrapJSON(fn handlerFunc) func(js.Value, []js.Value) any {
	return func(_ js.Value, args []js.Value) any {
		out, err := fn(args)
		if err != nil {
			return js.ValueOf(map[string]any{
				"ok":    false,
				"error": err.Error(),
			})
		}
		buf, err := json.Marshal(out)
		if err != nil {
			return js.ValueOf(map[string]any{
				"ok":    false,
				"error": err.Error(),
			})
		}
		return js.ValueOf(string(buf))
	}
}

func readJSONArg(args []js.Value, idx int, dest any) error {
	if idx >= len(args) {
		return errMissingArg
	}
	raw := args[idx].String()
	return json.Unmarshal([]byte(raw), dest)
}

var errMissingArg = errString("missing json argument")

type errString string

func (e errString) Error() string { return string(e) }

func pathHashesHandler(args []js.Value) (any, error) {
	var pathTable []filter.PathEntry
	if err := readJSONArg(args, 0, &pathTable); err != nil {
		return nil, err
	}
	var hopMax *float64
	if len(args) > 1 && !args[1].IsNull() && !args[1].IsUndefined() {
		if args[1].Type() == js.TypeNumber {
			v := args[1].Float()
			hopMax = &v
		} else if args[1].Type() == js.TypeString {
			s := args[1].String()
			if s != "" && s != "null" {
				var v float64
				if err := json.Unmarshal([]byte(s), &v); err == nil {
					hopMax = &v
				}
			}
		}
	}
	return filter.PathHashesWithinHopFilter(pathTable, hopMax), nil
}

func dedupeIconsHandler(args []js.Value) (any, error) {
	var queue []icon.QueueItem
	if err := readJSONArg(args, 0, &queue); err != nil {
		return nil, err
	}
	return icon.DedupeQueueEntries(queue), nil
}

func buildPathGraphHandler(args []js.Value) (any, error) {
	var req graph.Request
	if err := readJSONArg(args, 0, &req); err != nil {
		return nil, err
	}
	return graph.BuildPathGraph(req), nil
}

func buildFullGraphHandler(args []js.Value) (any, error) {
	var req graph.FullRequest
	if err := readJSONArg(args, 0, &req); err != nil {
		return nil, err
	}
	return graph.BuildFullGraph(req), nil
}

func layoutHandler(args []js.Value) (any, error) {
	var req layout.Request
	if err := readJSONArg(args, 0, &req); err != nil {
		return nil, err
	}
	return layout.Settle(req), nil
}

func lodUpdatesHandler(args []js.Value) (any, error) {
	var payload struct {
		Nodes    []lod.NodeIn `json:"nodes"`
		LOD      string       `json:"lod"`
		DarkMode bool         `json:"dark_mode"`
	}
	if err := readJSONArg(args, 0, &payload); err != nil {
		return nil, err
	}
	return lod.ComputeUpdates(payload.Nodes, payload.LOD, payload.DarkMode), nil
}

func lodLevelHandler(_ js.Value, args []js.Value) any {
	if len(args) == 0 || args[0].Type() != js.TypeNumber {
		return "high"
	}
	return lod.LevelFromScale(args[0].Float())
}
