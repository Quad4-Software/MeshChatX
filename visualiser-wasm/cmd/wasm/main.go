// SPDX-License-Identifier: 0BSD

// Command wasm exposes network visualiser hot-path helpers to the browser.
package main

import (
	"encoding/json"
	"syscall/js"
	"unsafe"

	"github.com/Quad4-Software/MeshChatX/visualiser-wasm/internal/filter"
	"github.com/Quad4-Software/MeshChatX/visualiser-wasm/internal/graph"
	"github.com/Quad4-Software/MeshChatX/visualiser-wasm/internal/icon"
	"github.com/Quad4-Software/MeshChatX/visualiser-wasm/internal/layout"
	"github.com/Quad4-Software/MeshChatX/visualiser-wasm/internal/lod"
	"github.com/Quad4-Software/MeshChatX/visualiser-wasm/internal/scene"
)

const apiVersion = "1.2.0"

var visualiserScene = scene.New()

var (
	nodeDrawScratch []float32
	edgeDrawScratch []float32
)

func main() {
	js.Global().Set("meshchatxVisualiserVersion", apiVersion)
	js.Global().Set("meshchatxVisualiserPathHashes", js.FuncOf(wrapJSON(pathHashesHandler)))
	js.Global().Set("meshchatxVisualiserDedupeIcons", js.FuncOf(wrapJSON(dedupeIconsHandler)))
	js.Global().Set("meshchatxVisualiserBuildPathGraph", js.FuncOf(wrapJSON(buildPathGraphHandler)))
	js.Global().Set("meshchatxVisualiserBuildFullGraph", js.FuncOf(wrapJSON(buildFullGraphHandler)))
	js.Global().Set("meshchatxVisualiserLayout", js.FuncOf(wrapJSON(layoutHandler)))
	js.Global().Set("meshchatxVisualiserLODUpdates", js.FuncOf(wrapJSON(lodUpdatesHandler)))
	js.Global().Set("meshchatxVisualiserLODLevel", js.FuncOf(lodLevelHandler))

	js.Global().Set("meshchatxVisualiserSceneSet", js.FuncOf(wrapJSON(sceneSetHandler)))
	js.Global().Set("meshchatxVisualiserSceneTick", js.FuncOf(sceneTickHandler))
	js.Global().Set("meshchatxVisualiserSceneResize", js.FuncOf(sceneResizeHandler))
	js.Global().Set("meshchatxVisualiserSceneSetCamera", js.FuncOf(sceneSetCameraHandler))
	js.Global().Set("meshchatxVisualiserScenePanBy", js.FuncOf(scenePanByHandler))
	js.Global().Set("meshchatxVisualiserSceneZoomAt", js.FuncOf(sceneZoomAtHandler))
	js.Global().Set("meshchatxVisualiserScenePick", js.FuncOf(scenePickHandler))
	js.Global().Set("meshchatxVisualiserSceneDragStart", js.FuncOf(sceneDragStartHandler))
	js.Global().Set("meshchatxVisualiserSceneDragTo", js.FuncOf(sceneDragToHandler))
	js.Global().Set("meshchatxVisualiserSceneDragEnd", js.FuncOf(sceneDragEndHandler))
	js.Global().Set("meshchatxVisualiserSceneGetCamera", js.FuncOf(wrapJSON(sceneGetCameraHandler)))
	js.Global().Set("meshchatxVisualiserSceneGetPositions", js.FuncOf(wrapJSON(sceneGetPositionsHandler)))
	js.Global().Set("meshchatxVisualiserSceneCounts", js.FuncOf(wrapJSON(sceneCountsHandler)))
	js.Global().Set("meshchatxVisualiserSceneGetDrawBuffers", js.FuncOf(sceneGetDrawBuffersHandler))

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

func sceneSetHandler(args []js.Value) (any, error) {
	var req scene.SetRequest
	if err := readJSONArg(args, 0, &req); err != nil {
		return nil, err
	}
	visualiserScene.Set(req)
	n, e := visualiserScene.Counts()
	return map[string]any{"ok": true, "nodes": n, "edges": e}, nil
}

func sceneTickHandler(_ js.Value, args []js.Value) any {
	steps := 2
	if len(args) > 0 && args[0].Type() == js.TypeNumber {
		steps = int(args[0].Int())
	}
	return visualiserScene.Tick(steps)
}

func sceneResizeHandler(_ js.Value, args []js.Value) any {
	if len(args) < 2 {
		return nil
	}
	visualiserScene.Resize(args[0].Float(), args[1].Float())
	return nil
}

func sceneSetCameraHandler(_ js.Value, args []js.Value) any {
	if len(args) < 3 {
		return nil
	}
	visualiserScene.SetCamera(args[0].Float(), args[1].Float(), args[2].Float())
	return nil
}

func scenePanByHandler(_ js.Value, args []js.Value) any {
	if len(args) < 2 {
		return nil
	}
	visualiserScene.PanBy(args[0].Float(), args[1].Float())
	return nil
}

func sceneZoomAtHandler(_ js.Value, args []js.Value) any {
	if len(args) < 3 {
		return nil
	}
	visualiserScene.ZoomAt(args[0].Float(), args[1].Float(), args[2].Float())
	return nil
}

func scenePickHandler(_ js.Value, args []js.Value) any {
	if len(args) < 2 {
		return ""
	}
	maxDist := 14.0
	if len(args) > 2 && args[2].Type() == js.TypeNumber {
		maxDist = args[2].Float()
	}
	return visualiserScene.PickNearest(args[0].Float(), args[1].Float(), maxDist)
}

func sceneDragStartHandler(_ js.Value, args []js.Value) any {
	if len(args) < 1 {
		return false
	}
	return visualiserScene.DragStart(args[0].String())
}

func sceneDragToHandler(_ js.Value, args []js.Value) any {
	if len(args) < 2 {
		return nil
	}
	visualiserScene.DragTo(args[0].Float(), args[1].Float())
	return nil
}

func sceneDragEndHandler(_ js.Value, _ []js.Value) any {
	visualiserScene.DragEnd()
	return nil
}

func sceneGetCameraHandler(_ []js.Value) (any, error) {
	cam := visualiserScene.Camera()
	return map[string]any{"ok": true, "x": cam.X, "y": cam.Y, "zoom": cam.Zoom}, nil
}

func sceneGetPositionsHandler(_ []js.Value) (any, error) {
	pos := visualiserScene.PositionsMap()
	out := make(map[string]any, len(pos))
	for id, xy := range pos {
		out[id] = map[string]any{"x": xy.X, "y": xy.Y}
	}
	return map[string]any{"ok": true, "positions": out}, nil
}

func sceneCountsHandler(_ []js.Value) (any, error) {
	n, e := visualiserScene.Counts()
	return map[string]any{"ok": true, "nodes": n, "edges": e}, nil
}

func float32ToJS(data []float32) js.Value {
	if len(data) == 0 {
		return js.Global().Get("Float32Array").New(0)
	}
	byteLen := len(data) * 4
	u8 := js.Global().Get("Uint8Array").New(byteLen)
	src := unsafe.Slice((*byte)(unsafe.Pointer(&data[0])), byteLen)
	js.CopyBytesToJS(u8, src)
	return js.Global().Get("Float32Array").New(u8.Get("buffer"))
}

func sceneGetDrawBuffersHandler(_ js.Value, _ []js.Value) any {
	nodeDrawScratch = visualiserScene.PackNodes(nodeDrawScratch)
	edgeDrawScratch = visualiserScene.PackEdges(edgeDrawScratch)
	cam := visualiserScene.Camera()
	n, _ := visualiserScene.Counts()
	obj := js.Global().Get("Object").New()
	obj.Set("ok", true)
	obj.Set("nodes", float32ToJS(nodeDrawScratch))
	obj.Set("edges", float32ToJS(edgeDrawScratch))
	obj.Set("nodeCount", n)
	obj.Set("edgeCount", len(edgeDrawScratch)/scene.EdgeStride)
	obj.Set("camX", cam.X)
	obj.Set("camY", cam.Y)
	obj.Set("zoom", cam.Zoom)
	return obj
}
