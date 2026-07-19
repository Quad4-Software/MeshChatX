// SPDX-License-Identifier: 0BSD

package graph

import (
	"math"
	"strings"

	"github.com/Quad4-Software/MeshChatX/visualiser-wasm/internal/filter"
	"github.com/Quad4-Software/MeshChatX/visualiser-wasm/internal/hashpos"
	"github.com/Quad4-Software/MeshChatX/visualiser-wasm/internal/icon"
)

// InterfaceIn is a preformatted interface row from the JS side.
type InterfaceIn struct {
	Name   string `json:"name"`
	Label  string `json:"label"`
	Title  string `json:"title"`
	Online bool   `json:"online"`
}

// DiscoveredIn is a preformatted discovered-interface row.
type DiscoveredIn struct {
	ID        string   `json:"id"`
	Label     string   `json:"label"`
	Title     string   `json:"title"`
	Connected bool     `json:"connected"`
	Hops      *float64 `json:"hops"`
}

// FullRequest builds the entire visualiser graph in one WASM pass.
type FullRequest struct {
	MeLabel            string                  `json:"me_label"`
	MeTitle            string                  `json:"me_title"`
	MeImage            string                  `json:"me_image"`
	IdentityHash       string                  `json:"identity_hash"`
	Interfaces         []InterfaceIn           `json:"interfaces"`
	PathOnlyInterfaces []InterfaceIn           `json:"path_only_interfaces"`
	Discovered         []DiscoveredIn          `json:"discovered"`
	PathTable          []filter.PathEntry      `json:"path_table"`
	Announces          map[string]Announce     `json:"announces"`
	Conversations      map[string]Conversation `json:"conversations"`
	IconCache          map[string]string       `json:"icon_cache"`
	Positions          map[string]XY           `json:"positions"`
	HopMax             *float64                `json:"hop_max"`
	Search             string                  `json:"search"`
	DarkMode           bool                    `json:"dark_mode"`
	LOD                string                  `json:"lod"`
	Aspects            []string                `json:"aspects"`
	QueueIcons         bool                    `json:"queue_icons"`
	IconGeneration     int                     `json:"icon_generation"`
	ShowDiscovered     bool                    `json:"show_discovered"`
}

// FullResult is nodes/edges for the whole mesh plus layout seeds.
type FullResult struct {
	Nodes            []NodeOut        `json:"nodes"`
	Edges            []EdgeOut        `json:"edges"`
	IconQueue        []icon.QueueItem `json:"icon_queue"`
	ProcessedNodeIDs []string         `json:"processed_node_ids"`
	ProcessedEdgeIDs []string         `json:"processed_edge_ids"`
	LayoutNodes      []LayoutBody     `json:"layout_nodes"`
	LayoutEdges      []LayoutSpring   `json:"layout_edges"`
}

// LayoutBody is a compact body for the WASM force settle.
type LayoutBody struct {
	ID    string  `json:"id"`
	X     float64 `json:"x"`
	Y     float64 `json:"y"`
	Mass  float64 `json:"mass"`
	Fixed bool    `json:"fixed"`
}

// LayoutSpring is a compact spring for the WASM force settle.
type LayoutSpring struct {
	From   string  `json:"from"`
	To     string  `json:"to"`
	Length float64 `json:"length"`
}

// BuildFullGraph constructs me + interfaces + discovered + announce nodes/edges.
func BuildFullGraph(req FullRequest) FullResult {
	searchLower := strings.ToLower(req.Search)
	fontColor := "#000000"
	if req.DarkMode {
		fontColor = "#ffffff"
	}
	pos := req.Positions
	if pos == nil {
		pos = map[string]XY{}
	}

	est := len(req.PathTable) + len(req.Interfaces) + len(req.PathOnlyInterfaces) + len(req.Discovered) + 1
	nodes := make([]NodeOut, 0, est)
	edges := make([]EdgeOut, 0, est)
	iconQueue := make([]icon.QueueItem, 0, 32)
	nodeIDs := make([]string, 0, est)
	edgeIDs := make([]string, 0, est)
	layoutNodes := make([]LayoutBody, 0, est)
	layoutEdges := make([]LayoutSpring, 0, est)
	seen := make(map[string]struct{}, est)

	addNode := func(n NodeOut, mass float64, fixed bool) {
		if _, ok := seen[n.ID]; ok {
			return
		}
		seen[n.ID] = struct{}{}
		nodes = append(nodes, n)
		nodeIDs = append(nodeIDs, n.ID)
		layoutNodes = append(layoutNodes, LayoutBody{ID: n.ID, X: n.X, Y: n.Y, Mass: mass, Fixed: fixed})
	}
	addEdge := func(e EdgeOut, length float64) {
		edges = append(edges, e)
		edgeIDs = append(edgeIDs, e.ID)
		layoutEdges = append(layoutEdges, LayoutSpring{From: e.From, To: e.To, Length: length})
	}

	meLabel := req.MeLabel
	if meLabel == "" {
		meLabel = "Local Node"
	}
	if filter.MatchesSearch(searchLower, meLabel) || filter.MatchesSearch(searchLower, req.IdentityHash) {
		mp := resolveOr(pos, "me", 0, 0)
		font := map[string]any{"color": fontColor, "size": 16.0, "bold": true}
		me := NodeOut{
			ID:            "me",
			Group:         "me",
			Size:          50,
			OriginalSize:  50,
			Shape:         "circularImage",
			OriginalShape: "circularImage",
			Image:         req.MeImage,
			Label:         meLabel,
			Title:         req.MeTitle,
			Font:          font,
			Color:         colorBlue(req.DarkMode),
			X:             mp.X,
			Y:             mp.Y,
		}
		applyLOD(&me, req.LOD, fontHighFor(req.DarkMode))
		addNode(me, 4, true)
	}

	radius := 400.0
	ifaceN := len(req.Interfaces)
	for j, entry := range req.Interfaces {
		if !filter.MatchesSearch(searchLower, entry.Label) && !filter.MatchesSearch(searchLower, entry.Name) {
			continue
		}
		angle := 0.0
		if ifaceN > 0 {
			angle = (float64(j) / float64(ifaceN)) * 2 * math.Pi
		}
		init := XY{X: math.Cos(angle) * radius, Y: math.Sin(angle) * radius}
		p := resolveOr(pos, entry.Name, init.X, init.Y)
		node := NodeOut{
			ID:            entry.Name,
			Group:         "interface",
			Label:         entry.Label,
			Title:         entry.Title,
			Size:          35,
			OriginalSize:  35,
			Shape:         "circularImage",
			OriginalShape: "circularImage",
			Image:         ifaceImage(entry.Online),
			Color:         ifaceColor(entry.Online, req.DarkMode),
			Font:          map[string]any{"color": fontColor, "size": 12.0, "bold": true},
			X:             p.X,
			Y:             p.Y,
		}
		applyLOD(&node, req.LOD, fontHighFor(req.DarkMode))
		addNode(node, 2.5, false)
		if _, ok := seen["me"]; ok {
			eid := "me~" + entry.Name
			col := edgeDirect(req.DarkMode)
			if !entry.Online {
				col = edgeOffline(req.DarkMode)
			}
			addEdge(EdgeOut{ID: eid, From: "me", To: entry.Name, Color: col, Width: 3, Hidden: false}, 300)
		}
	}

	pathIfaceN := len(req.PathOnlyInterfaces)
	for j, entry := range req.PathOnlyInterfaces {
		if _, ok := seen[entry.Name]; ok {
			continue
		}
		if !filter.MatchesSearch(searchLower, entry.Label) && !filter.MatchesSearch(searchLower, entry.Name) {
			continue
		}
		angle := 0.0
		if pathIfaceN > 0 {
			angle = (float64(j) / float64(pathIfaceN)) * 2 * math.Pi
		}
		init := XY{X: math.Cos(angle) * radius, Y: math.Sin(angle) * radius}
		p := resolveOr(pos, entry.Name, init.X, init.Y)
		node := NodeOut{
			ID:            entry.Name,
			Group:         "interface",
			Label:         entry.Label,
			Title:         entry.Title,
			Size:          35,
			OriginalSize:  35,
			Shape:         "circularImage",
			OriginalShape: "circularImage",
			Image:         "/assets/images/network-visualiser/interface_connected.png",
			Color:         ifaceColor(true, req.DarkMode),
			Font:          map[string]any{"color": fontColor, "size": 12.0, "bold": true},
			X:             p.X,
			Y:             p.Y,
		}
		applyLOD(&node, req.LOD, fontHighFor(req.DarkMode))
		addNode(node, 2.5, false)
		if _, ok := seen["me"]; ok {
			eid := "me~" + entry.Name
			addEdge(EdgeOut{ID: eid, From: "me", To: entry.Name, Color: edgeDirect(req.DarkMode), Width: 3, Hidden: false}, 300)
		}
	}

	if req.ShowDiscovered {
		for _, disc := range req.Discovered {
			if req.HopMax != nil && disc.Hops != nil && *disc.Hops > *req.HopMax {
				continue
			}
			if !filter.MatchesSearch(searchLower, disc.Label) {
				continue
			}
			x, y := hashpos.XY(disc.ID, 800, 200)
			p := resolveOr(pos, disc.ID, x, y)
			node := NodeOut{
				ID:            disc.ID,
				Group:         "discovered",
				Label:         disc.Label,
				Title:         disc.Title,
				Size:          25,
				OriginalSize:  25,
				Shape:         "circularImage",
				OriginalShape: "circularImage",
				Image:         ifaceImage(disc.Connected),
				Color:         discoveredColor(disc.Connected, req.DarkMode),
				Font:          map[string]any{"color": fontColor, "size": 10.0},
				X:             p.X,
				Y:             p.Y,
			}
			applyLOD(&node, req.LOD, fontHighFor(req.DarkMode))
			addNode(node, 1.2, false)
			if _, ok := seen["me"]; ok {
				eid := "me~" + disc.ID
				col := map[string]any{"color": "#06b6d4", "opacity": 0.35}
				if req.DarkMode {
					col["color"] = "#155e75"
				}
				addEdge(EdgeOut{ID: eid, From: "me", To: disc.ID, Color: col, Width: 1, Hidden: false}, 320)
			}
		}
	}

	pathRes := BuildPathGraph(Request{
		PathTable:      req.PathTable,
		Announces:      req.Announces,
		Conversations:  req.Conversations,
		IconCache:      req.IconCache,
		Positions:      pos,
		HopMax:         req.HopMax,
		Search:         req.Search,
		DarkMode:       req.DarkMode,
		LOD:            req.LOD,
		Aspects:        req.Aspects,
		QueueIcons:     req.QueueIcons,
		IconGeneration: req.IconGeneration,
	})
	for _, n := range pathRes.Nodes {
		addNode(n, 1, false)
	}
	for _, e := range pathRes.Edges {
		length := 300.0
		if e.Width >= 2 {
			length = 260
		}
		addEdge(e, length)
	}
	iconQueue = append(iconQueue, pathRes.IconQueue...)

	return FullResult{
		Nodes:            nodes,
		Edges:            edges,
		IconQueue:        iconQueue,
		ProcessedNodeIDs: nodeIDs,
		ProcessedEdgeIDs: edgeIDs,
		LayoutNodes:      layoutNodes,
		LayoutEdges:      layoutEdges,
	}
}

func resolveOr(pos map[string]XY, id string, x, y float64) XY {
	if prev, ok := pos[id]; ok {
		return prev
	}
	p := XY{X: x, Y: y}
	pos[id] = p
	return p
}

func fontHighFor(dark bool) map[string]any {
	if dark {
		return fontHighLight
	}
	return fontHighDark
}

func colorBlue(dark bool) map[string]any {
	if dark {
		return colorLxmfMultiDark
	}
	return colorLxmfMultiLight
}

func ifaceImage(online bool) string {
	if online {
		return "/assets/images/network-visualiser/interface_connected.png"
	}
	return "/assets/images/network-visualiser/interface_disconnected.png"
}

func ifaceColor(online, dark bool) map[string]any {
	if online {
		bg := "#ecfdf5"
		if dark {
			bg = "#064e3b"
		}
		return nodeColor("#10b981", bg)
	}
	bg := "#fef2f2"
	if dark {
		bg = "#7f1d1d"
	}
	return nodeColor("#ef4444", bg)
}

func edgeDirect(dark bool) map[string]any {
	if dark {
		return edgeDirectDark
	}
	return edgeDirectLight
}

func edgeOffline(dark bool) map[string]any {
	c := "#ef4444"
	if dark {
		c = "#f87171"
	}
	return map[string]any{"color": c, "opacity": 1.0}
}

func discoveredColor(connected, dark bool) map[string]any {
	if connected {
		bg := "#ecfeff"
		if dark {
			bg = "#164e63"
		}
		return nodeColor("#06b6d4", bg)
	}
	bg := "#f1f5f9"
	if dark {
		bg = "#1e293b"
	}
	return nodeColor("#64748b", bg)
}
