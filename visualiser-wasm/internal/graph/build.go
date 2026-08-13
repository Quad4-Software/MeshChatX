// SPDX-License-Identifier: 0BSD

package graph

import (
	"strconv"
	"strings"

	"github.com/Quad4-Software/MeshChatX/visualiser-wasm/internal/filter"
	"github.com/Quad4-Software/MeshChatX/visualiser-wasm/internal/hashpos"
	"github.com/Quad4-Software/MeshChatX/visualiser-wasm/internal/icon"
)

// XY is a 2D position.
type XY struct {
	X float64 `json:"x"`
	Y float64 `json:"y"`
}

// UserIcon is an lxmf custom icon descriptor.
type UserIcon struct {
	IconName         string `json:"icon_name"`
	ForegroundColour string `json:"foreground_colour"`
	BackgroundColour string `json:"background_colour"`
}

// Announce is the announce fields needed for graph build.
type Announce struct {
	DestinationHash   string `json:"destination_hash"`
	Aspect            string `json:"aspect"`
	DisplayName       string `json:"display_name"`
	CustomDisplayName string `json:"custom_display_name"`
	IdentityHash      string `json:"identity_hash"`
	LastSeen          string `json:"last_seen"`
}

// Conversation carries optional lxmf user icon data.
type Conversation struct {
	LxmfUserIcon *UserIcon `json:"lxmf_user_icon"`
}

// Request is the buildPathGraph input payload.
type Request struct {
	PathTable      []filter.PathEntry      `json:"path_table"`
	Announces      map[string]Announce     `json:"announces"`
	Conversations  map[string]Conversation `json:"conversations"`
	IconCache      map[string]string       `json:"icon_cache"`
	Positions      map[string]XY           `json:"positions"`
	HopMax         *float64                `json:"hop_max"`
	Search         string                  `json:"search"`
	DarkMode       bool                    `json:"dark_mode"`
	LOD            string                  `json:"lod"`
	Aspects        []string                `json:"aspects"`
	QueueIcons     bool                    `json:"queue_icons"`
	IconGeneration int                     `json:"icon_generation"`
}

// NodeOut is one announce node for vis-network.
type NodeOut struct {
	ID              string         `json:"id"`
	Group           string         `json:"group"`
	Size            float64        `json:"size"`
	OriginalSize    float64        `json:"_originalSize"`
	Shape           string         `json:"shape"`
	OriginalShape   string         `json:"_originalShape"`
	Image           string         `json:"image,omitempty"`
	Label           string         `json:"label"`
	Title           string         `json:"title"`
	Font            map[string]any `json:"font"`
	Color           map[string]any `json:"color"`
	X               float64        `json:"x"`
	Y               float64        `json:"y"`
	ParentInterface string         `json:"_parentInterface,omitempty"`
}

// EdgeOut is one path edge for vis-network.
type EdgeOut struct {
	ID     string         `json:"id"`
	From   string         `json:"from"`
	To     string         `json:"to"`
	Color  map[string]any `json:"color"`
	Width  float64        `json:"width"`
	Hidden bool           `json:"hidden"`
}

// Result is the buildPathGraph output payload.
type Result struct {
	Nodes            []NodeOut        `json:"nodes"`
	Edges            []EdgeOut        `json:"edges"`
	IconQueue        []icon.QueueItem `json:"icon_queue"`
	ProcessedNodeIDs []string         `json:"processed_node_ids"`
	ProcessedEdgeIDs []string         `json:"processed_edge_ids"`
}

var defaultAspects = []string{"lxmf.delivery", "nomadnetwork.node"}

// Shared immutable style maps reused across nodes and edges to cut allocs.
var (
	fontHighLight = map[string]any{"color": "#ffffff", "size": 11.0}
	fontHighDark  = map[string]any{"color": "#000000", "size": 11.0}
	fontHidden    = map[string]any{"size": 0.0}

	colorLxmfDirectLight  = nodeColor("#10b981", "#ecfdf5")
	colorLxmfDirectDark   = nodeColor("#10b981", "#064e3b")
	colorLxmfMultiLight   = nodeColor("#3b82f6", "#eff6ff")
	colorLxmfMultiDark    = nodeColor("#3b82f6", "#1e40af")
	colorNomadDirectLight = nodeColor("#10b981", "#ecfdf5")
	colorNomadDirectDark  = nodeColor("#10b981", "#064e3b")
	colorNomadMultiLight  = nodeColor("#8b5cf6", "#f5f3ff")
	colorNomadMultiDark   = nodeColor("#8b5cf6", "#4c1d95")

	edgeDirectLight = map[string]any{"color": "#10b981", "opacity": 1.0}
	edgeDirectDark  = map[string]any{"color": "#34d399", "opacity": 1.0}
	edgeMultiLight  = map[string]any{"color": "#3b82f6", "opacity": 0.5}
	edgeMultiDark   = map[string]any{"color": "#60a5fa", "opacity": 0.5}

	imgUser1Hop   = "/assets/images/network-visualiser/user_1hop.png"
	imgUser       = "/assets/images/network-visualiser/user.png"
	imgServer1Hop = "/assets/images/network-visualiser/server_1hop.png"
	imgServer     = "/assets/images/network-visualiser/server.png"
)

// BuildPathGraph constructs announce nodes and edges from the path table.
func BuildPathGraph(req Request) Result {
	aspects := req.Aspects
	if len(aspects) == 0 {
		aspects = defaultAspects
	}
	aspectSet := make(map[string]struct{}, len(aspects))
	for _, a := range aspects {
		aspectSet[a] = struct{}{}
	}

	searchLower := strings.ToLower(req.Search)
	fontHigh := fontHighDark
	if req.DarkMode {
		fontHigh = fontHighLight
	}

	est := len(req.PathTable)
	if est > 4096 {
		est = 4096
	}
	nodes := make([]NodeOut, 0, est/2+1)
	edges := make([]EdgeOut, 0, est/2+1)
	iconQueue := make([]icon.QueueItem, 0, 32)
	nodeIDs := make([]string, 0, est/2+1)
	edgeIDs := make([]string, 0, est/2+1)

	pos := req.Positions
	if pos == nil {
		pos = map[string]XY{}
	}
	cache := req.IconCache
	if cache == nil {
		cache = map[string]string{}
	}
	announces := req.Announces
	if announces == nil {
		announces = map[string]Announce{}
	}
	conversations := req.Conversations
	if conversations == nil {
		conversations = map[string]Conversation{}
	}

	for i := range req.PathTable {
		entry := &req.PathTable[i]
		if entry.Hops == nil || entry.Hash == "" {
			continue
		}
		if req.HopMax != nil && *entry.Hops > *req.HopMax {
			continue
		}
		announce, ok := announces[entry.Hash]
		if !ok {
			continue
		}
		if _, allow := aspectSet[announce.Aspect]; !allow {
			continue
		}

		displayName := announce.CustomDisplayName
		if displayName == "" {
			displayName = announce.DisplayName
		}
		if !filter.MatchesSearch(searchLower, displayName) &&
			!filter.MatchesSearch(searchLower, announce.DestinationHash) &&
			!filter.MatchesSearch(searchLower, announce.IdentityHash) {
			continue
		}

		x, y := resolvePosition(entry.Hash, entry.Interface, pos)
		edgeID := entry.Interface + "~" + entry.Hash
		direct := *entry.Hops == 1

		node := NodeOut{
			ID:              entry.Hash,
			Group:           "announce",
			Size:            25,
			OriginalSize:    25,
			Label:           displayName,
			Title:           buildTitle(displayName, announce.Aspect, *entry.Hops, entry.Interface, announce.LastSeen),
			Font:            fontHigh,
			X:               x,
			Y:               y,
			ParentInterface: entry.Interface,
		}

		conv := conversations[announce.DestinationHash]
		switch announce.Aspect {
		case "lxmf.delivery":
			applyLxmfNode(&node, &conv, direct, req.DarkMode, req.QueueIcons, req.IconGeneration, cache, &iconQueue)
		case "nomadnetwork.node":
			applyNomadNode(&node, direct, req.DarkMode)
		}

		applyLOD(&node, req.LOD, fontHigh)
		nodes = append(nodes, node)
		nodeIDs = append(nodeIDs, node.ID)

		edges = append(edges, EdgeOut{
			ID:     edgeID,
			From:   entry.Interface,
			To:     entry.Hash,
			Color:  edgeColor(direct, req.DarkMode),
			Width:  edgeWidth(direct),
			Hidden: false,
		})
		edgeIDs = append(edgeIDs, edgeID)
	}

	return Result{
		Nodes:            nodes,
		Edges:            edges,
		IconQueue:        iconQueue,
		ProcessedNodeIDs: nodeIDs,
		ProcessedEdgeIDs: edgeIDs,
	}
}

func resolvePosition(hash, iface string, pos map[string]XY) (float64, float64) {
	if prev, ok := pos[hash]; ok {
		return prev.X, prev.Y
	}
	if ip, ok := pos[iface]; ok {
		x, y := hashpos.Around(hash, ip.X, ip.Y, 140, 90)
		pos[hash] = XY{X: x, Y: y}
		return x, y
	}
	x, y := hashpos.XY(hash, 400, 160)
	pos[hash] = XY{X: x, Y: y}
	return x, y
}

func buildTitle(displayName, aspect string, hops float64, via, lastSeen string) string {
	var b strings.Builder
	b.Grow(96 + len(displayName) + len(aspect) + len(via) + len(lastSeen))
	b.WriteString(displayName)
	b.WriteByte('\n')
	b.WriteString("Aspect: ")
	b.WriteString(aspect)
	b.WriteByte('\n')
	b.WriteString("Hops: ")
	b.WriteString(trimFloat(hops))
	b.WriteByte('\n')
	b.WriteString("Via: ")
	b.WriteString(via)
	b.WriteByte('\n')
	b.WriteString("Last Seen: ")
	b.WriteString(lastSeen)
	return b.String()
}

func trimFloat(v float64) string {
	return strconv.FormatFloat(v, 'f', -1, 64)
}

func applyLxmfNode(
	node *NodeOut,
	conv *Conversation,
	direct, darkMode, queueIcons bool,
	generation int,
	cache map[string]string,
	iconQueue *[]icon.QueueItem,
) {
	node.Shape = "circularImage"
	node.OriginalShape = "circularImage"
	if conv != nil && conv.LxmfUserIcon != nil {
		ic := conv.LxmfUserIcon
		cacheKey := ic.IconName + "-" + ic.ForegroundColour + "-" + ic.BackgroundColour + "-64"
		if url := cache[cacheKey]; url != "" {
			node.Image = url
		} else {
			if direct {
				node.Image = imgUser1Hop
			} else {
				node.Image = imgUser
			}
			if queueIcons {
				*iconQueue = append(*iconQueue, icon.QueueItem{
					NodeID:     node.ID,
					CacheKey:   cacheKey,
					IconName:   ic.IconName,
					FG:         ic.ForegroundColour,
					BG:         ic.BackgroundColour,
					Size:       64,
					Generation: generation,
				})
			}
		}
		node.Size = 30
		node.OriginalSize = 30
	} else if direct {
		node.Image = imgUser1Hop
	} else {
		node.Image = imgUser
	}
	if direct {
		if darkMode {
			node.Color = colorLxmfDirectDark
		} else {
			node.Color = colorLxmfDirectLight
		}
	} else if darkMode {
		node.Color = colorLxmfMultiDark
	} else {
		node.Color = colorLxmfMultiLight
	}
}

func applyNomadNode(node *NodeOut, direct, darkMode bool) {
	node.Shape = "circularImage"
	node.OriginalShape = "circularImage"
	if direct {
		node.Image = imgServer1Hop
	} else {
		node.Image = imgServer
	}
	if direct {
		if darkMode {
			node.Color = colorNomadDirectDark
		} else {
			node.Color = colorNomadDirectLight
		}
	} else if darkMode {
		node.Color = colorNomadMultiDark
	} else {
		node.Color = colorNomadMultiLight
	}
}

func applyLOD(node *NodeOut, level string, fontHigh map[string]any) {
	switch level {
	case "low":
		node.Shape = "dot"
		if node.ID == "me" {
			node.Size = 15
		} else {
			node.Size = 10
		}
		node.Font = fontHidden
	case "medium":
		node.Shape = node.OriginalShape
		node.Size = node.OriginalSize
		node.Font = fontHidden
	default:
		node.Shape = node.OriginalShape
		node.Size = node.OriginalSize
		node.Font = fontHigh
	}
}

func edgeColor(direct, darkMode bool) map[string]any {
	if direct {
		if darkMode {
			return edgeDirectDark
		}
		return edgeDirectLight
	}
	if darkMode {
		return edgeMultiDark
	}
	return edgeMultiLight
}

func edgeWidth(direct bool) float64 {
	if direct {
		return 2.5
	}
	return 1
}

func nodeColor(border, background string) map[string]any {
	return map[string]any{
		"border":     border,
		"background": background,
		"highlight": map[string]any{
			"border":     border,
			"background": background,
		},
		"hover": map[string]any{
			"border":     border,
			"background": background,
		},
	}
}
