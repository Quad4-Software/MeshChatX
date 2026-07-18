// SPDX-License-Identifier: 0BSD

// Package scene holds an interactive mesh graph for the WebGL renderer.
// Positions and force ticks run in WASM. Pixel draw stays in JS WebGL.
package scene

import (
	"math"

	"github.com/Quad4-Software/MeshChatX/visualiser-wasm/internal/layout"
)

// Kind constants packed into draw buffers.
const (
	KindMe         = 0
	KindIfaceOn    = 1
	KindIfaceOff   = 2
	KindPeer       = 3
	KindDiscovered = 4
)

// NodeStride floats per node draw record: x y size r g b a kind
const NodeStride = 8

// EdgeStride floats per edge draw record: x1 y1 x2 y2 r g b a
const EdgeStride = 8

// Node is one drawable / simulatable body.
type Node struct {
	ID    string  `json:"id"`
	X     float64 `json:"x"`
	Y     float64 `json:"y"`
	Mass  float64 `json:"mass"`
	Fixed bool    `json:"fixed"`
	Kind  int     `json:"kind"`
	Size  float64 `json:"size"`
	R     float64 `json:"r"`
	G     float64 `json:"g"`
	B     float64 `json:"b"`
	A     float64 `json:"a"`
}

// Edge connects two node ids.
type Edge struct {
	From  string  `json:"from"`
	To    string  `json:"to"`
	Width float64 `json:"width"`
	R     float64 `json:"r"`
	G     float64 `json:"g"`
	B     float64 `json:"b"`
	A     float64 `json:"a"`
}

// SetRequest replaces scene contents.
type SetRequest struct {
	Nodes  []Node  `json:"nodes"`
	Edges  []Edge  `json:"edges"`
	Width  float64 `json:"width"`
	Height float64 `json:"height"`
	CamX   float64 `json:"cam_x"`
	CamY   float64 `json:"cam_y"`
	Zoom   float64 `json:"zoom"`
}

// CameraState is the 2D view transform (world -> screen via zoom/pan).
type CameraState struct {
	X    float64 `json:"x"`
	Y    float64 `json:"y"`
	Zoom float64 `json:"zoom"`
}

// Scene is the mutable WASM-side graph for WebGL.
type Scene struct {
	nodes   []Node
	edges   []Edge
	index   map[string]int
	vx      []float64
	vy      []float64
	width   float64
	height  float64
	camX    float64
	camY    float64
	zoom    float64
	dragIdx int
}

// New returns an empty scene centred on the origin.
func New() *Scene {
	return &Scene{
		index:   map[string]int{},
		width:   800,
		height:  600,
		zoom:    1,
		dragIdx: -1,
	}
}

// Set replaces nodes and edges. Preserves camera unless zoom is > 0 in req.
func (s *Scene) Set(req SetRequest) {
	s.nodes = append([]Node(nil), req.Nodes...)
	s.edges = append([]Edge(nil), req.Edges...)
	s.index = make(map[string]int, len(s.nodes))
	for i := range s.nodes {
		n := &s.nodes[i]
		if n.Mass <= 0 {
			n.Mass = 1
		}
		if n.Size <= 0 {
			n.Size = defaultSize(n.Kind)
		}
		if n.A <= 0 {
			n.A = 1
		}
		if n.R == 0 && n.G == 0 && n.B == 0 {
			n.R, n.G, n.B = defaultColor(n.Kind)
		}
		if n.ID == "me" {
			n.Fixed = true
			n.Kind = KindMe
		}
		s.index[n.ID] = i
	}
	if req.Width > 0 {
		s.width = req.Width
	}
	if req.Height > 0 {
		s.height = req.Height
	}
	if req.Zoom > 0 {
		s.zoom = req.Zoom
		s.camX = req.CamX
		s.camY = req.CamY
	}
	s.dragIdx = -1
	s.vx = make([]float64, len(s.nodes))
	s.vy = make([]float64, len(s.nodes))
}

func defaultSize(kind int) float64 {
	switch kind {
	case KindMe:
		return 18
	case KindIfaceOn, KindIfaceOff:
		return 12
	case KindDiscovered:
		return 9
	default:
		return 10
	}
}

func defaultColor(kind int) (r, g, b float64) {
	switch kind {
	case KindMe:
		return 0.23, 0.51, 0.96
	case KindIfaceOn:
		return 0.06, 0.73, 0.51
	case KindIfaceOff:
		return 0.45, 0.45, 0.50
	case KindDiscovered:
		return 0.66, 0.33, 0.97
	default:
		return 0.85, 0.85, 0.90
	}
}

// Resize updates the viewport size used for picking.
func (s *Scene) Resize(w, h float64) {
	if w > 0 {
		s.width = w
	}
	if h > 0 {
		s.height = h
	}
}

// Camera returns the current view.
func (s *Scene) Camera() CameraState {
	return CameraState{X: s.camX, Y: s.camY, Zoom: s.zoom}
}

// SetCamera sets pan/zoom (zoom clamped).
func (s *Scene) SetCamera(x, y, zoom float64) {
	s.camX = x
	s.camY = y
	if zoom < 0.05 {
		zoom = 0.05
	}
	if zoom > 8 {
		zoom = 8
	}
	s.zoom = zoom
}

// PanBy moves the camera in world units.
func (s *Scene) PanBy(dx, dy float64) {
	s.camX += dx
	s.camY += dy
}

// ZoomAt zooms around a screen point (css pixels, origin top-left).
func (s *Scene) ZoomAt(screenX, screenY, factor float64) {
	if factor <= 0 {
		return
	}
	wx, wy := s.screenToWorld(screenX, screenY)
	s.zoom *= factor
	if s.zoom < 0.05 {
		s.zoom = 0.05
	}
	if s.zoom > 8 {
		s.zoom = 8
	}
	nx, ny := s.screenToWorld(screenX, screenY)
	s.camX += wx - nx
	s.camY += wy - ny
}

func (s *Scene) screenToWorld(sx, sy float64) (float64, float64) {
	// Screen centre is cam world position.
	cx := s.width * 0.5
	cy := s.height * 0.5
	wx := s.camX + (sx-cx)/s.zoom
	wy := s.camY + (sy-cy)/s.zoom
	return wx, wy
}

// Tick runs a few force iterations when live layout is on.
func (s *Scene) Tick(steps int) {
	if len(s.nodes) == 0 {
		return
	}
	if steps <= 0 {
		steps = 1
	}
	if steps > 3 {
		steps = 3
	}
	if len(s.vx) != len(s.nodes) || len(s.vy) != len(s.nodes) {
		s.vx = make([]float64, len(s.nodes))
		s.vy = make([]float64, len(s.nodes))
	}
	layoutNodes := make([]layout.Node, len(s.nodes))
	for i := range s.nodes {
		n := &s.nodes[i]
		fixed := n.Fixed
		if s.dragIdx == i {
			fixed = true
		}
		layoutNodes[i] = layout.Node{
			ID:    n.ID,
			X:     n.X,
			Y:     n.Y,
			Vx:    s.vx[i],
			Vy:    s.vy[i],
			Mass:  n.Mass,
			Fixed: fixed,
		}
	}
	layoutEdges := make([]layout.Edge, 0, len(s.edges))
	for i := range s.edges {
		e := &s.edges[i]
		length := 200.0
		if e.Width >= 2.5 {
			length = 170
		}
		layoutEdges = append(layoutEdges, layout.Edge{
			From:   e.From,
			To:     e.To,
			Length: length,
		})
	}
	// Softer than one-shot Settle defaults so live layout does not twitch.
	// Gravity -1 disables origin pull so dragged layouts stay put.
	_ = layout.Settle(layout.Request{
		Nodes:      layoutNodes,
		Edges:      layoutEdges,
		Iterations: steps,
		Gravity:    -1,
		Repulsion:  550,
		SpringK:    0.018,
		Damping:    0.52,
		MaxSpeed:   6,
	})
	const restSpeed = 0.12
	for i := range s.nodes {
		if s.dragIdx == i {
			s.vx[i] = 0
			s.vy[i] = 0
			continue
		}
		s.nodes[i].X = layoutNodes[i].X
		s.nodes[i].Y = layoutNodes[i].Y
		s.vx[i] = layoutNodes[i].Vx
		s.vy[i] = layoutNodes[i].Vy
		if math.Hypot(s.vx[i], s.vy[i]) < restSpeed {
			s.vx[i] = 0
			s.vy[i] = 0
		}
	}
}

// PositionsMap returns id -> xy for caching.
func (s *Scene) PositionsMap() map[string]layout.XY {
	out := make(map[string]layout.XY, len(s.nodes))
	for i := range s.nodes {
		n := &s.nodes[i]
		out[n.ID] = layout.XY{X: n.X, Y: n.Y}
	}
	return out
}

// PickNearest returns the node id under a screen point, or "".
func (s *Scene) PickNearest(screenX, screenY, maxDistPx float64) string {
	if maxDistPx <= 0 {
		maxDistPx = 14
	}
	wx, wy := s.screenToWorld(screenX, screenY)
	best := ""
	bestD2 := math.MaxFloat64
	maxWorld := maxDistPx / s.zoom
	maxD2 := maxWorld * maxWorld
	for i := range s.nodes {
		n := &s.nodes[i]
		dx := n.X - wx
		dy := n.Y - wy
		d2 := dx*dx + dy*dy
		hitR := n.Size / s.zoom
		if hitR < maxWorld {
			hitR = maxWorld
		}
		if d2 <= hitR*hitR && d2 < bestD2 && d2 <= maxD2*4 {
			bestD2 = d2
			best = n.ID
		}
	}
	return best
}

// DragStart begins dragging a node by id.
func (s *Scene) DragStart(id string) bool {
	i, ok := s.index[id]
	if !ok {
		return false
	}
	s.dragIdx = i
	return true
}

// DragTo moves the dragged node to a screen point.
func (s *Scene) DragTo(screenX, screenY float64) {
	if s.dragIdx < 0 || s.dragIdx >= len(s.nodes) {
		return
	}
	wx, wy := s.screenToWorld(screenX, screenY)
	s.nodes[s.dragIdx].X = wx
	s.nodes[s.dragIdx].Y = wy
}

// DragEnd clears the drag target.
func (s *Scene) DragEnd() {
	s.dragIdx = -1
}

// Counts returns node and edge lengths.
func (s *Scene) Counts() (nodes, edges int) {
	return len(s.nodes), len(s.edges)
}

// PackNodes fills a float32 draw buffer (len = n * NodeStride).
func (s *Scene) PackNodes(dst []float32) []float32 {
	need := len(s.nodes) * NodeStride
	if cap(dst) < need {
		dst = make([]float32, need)
	} else {
		dst = dst[:need]
	}
	for i := range s.nodes {
		n := &s.nodes[i]
		o := i * NodeStride
		dst[o+0] = float32(n.X)
		dst[o+1] = float32(n.Y)
		dst[o+2] = float32(n.Size)
		dst[o+3] = float32(n.R)
		dst[o+4] = float32(n.G)
		dst[o+5] = float32(n.B)
		dst[o+6] = float32(n.A)
		dst[o+7] = float32(n.Kind)
	}
	return dst
}

// PackEdges fills a float32 draw buffer (len = m * EdgeStride).
func (s *Scene) PackEdges(dst []float32) []float32 {
	need := len(s.edges) * EdgeStride
	if cap(dst) < need {
		dst = make([]float32, need)
	} else {
		dst = dst[:need]
	}
	w := 0
	for i := range s.edges {
		e := &s.edges[i]
		ai, okA := s.index[e.From]
		bi, okB := s.index[e.To]
		if !okA || !okB {
			continue
		}
		a := &s.nodes[ai]
		b := &s.nodes[bi]
		o := w * EdgeStride
		dst[o+0] = float32(a.X)
		dst[o+1] = float32(a.Y)
		dst[o+2] = float32(b.X)
		dst[o+3] = float32(b.Y)
		r, g, bl, al := e.R, e.G, e.B, e.A
		if al <= 0 {
			al = 0.45
		}
		if r == 0 && g == 0 && bl == 0 {
			r, g, bl = 0.45, 0.45, 0.55
		}
		dst[o+4] = float32(r)
		dst[o+5] = float32(g)
		dst[o+6] = float32(bl)
		dst[o+7] = float32(al)
		w++
	}
	return dst[:w*EdgeStride]
}
