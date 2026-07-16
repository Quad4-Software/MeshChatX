// SPDX-License-Identifier: 0BSD

// Package lod computes level-of-detail property patches for vis-network nodes.
package lod

// NodeIn is the minimal node state needed to compute an LOD patch.
type NodeIn struct {
	ID            string         `json:"id"`
	Group         string         `json:"group"`
	Shape         string         `json:"shape"`
	Size          float64        `json:"size"`
	OriginalShape string         `json:"_originalShape"`
	OriginalSize  float64        `json:"_originalSize"`
	Color         map[string]any `json:"color"`
	Font          *FontIn        `json:"font"`
}

// FontIn carries the current font size when present.
type FontIn struct {
	Size *float64 `json:"size"`
}

// Update is a sparse vis-network node patch for one LOD change.
type Update struct {
	ID    string         `json:"id"`
	Shape string         `json:"shape,omitempty"`
	Size  *float64       `json:"size,omitempty"`
	Font  map[string]any `json:"font,omitempty"`
	Color map[string]any `json:"color,omitempty"`
}

var (
	fontSize0          = map[string]any{"size": 0.0}
	fontHighLight11    = map[string]any{"size": 11.0, "color": "#ffffff"}
	fontHighDark11     = map[string]any{"size": 11.0, "color": "#000000"}
	fontHighLight16    = map[string]any{"size": 16.0, "color": "#ffffff"}
	fontHighDark16     = map[string]any{"size": 16.0, "color": "#000000"}
	colorBlueLight     = nodeColor("#3b82f6", "#eff6ff")
	colorBlueDark      = nodeColor("#3b82f6", "#1e40af")
	size10             = 10.0
	size15             = 15.0
	size25             = 25.0
	size50             = 50.0
)

// LevelFromScale maps a vis-network camera scale to low/medium/high.
func LevelFromScale(scale float64) string {
	if scale < 0.2 {
		return "low"
	}
	if scale < 0.5 {
		return "medium"
	}
	return "high"
}

// ComputeUpdates returns only nodes whose LOD props actually change.
func ComputeUpdates(nodes []NodeIn, level string, darkMode bool) []Update {
	if len(nodes) == 0 {
		return nil
	}
	blue := colorBlueLight
	if darkMode {
		blue = colorBlueDark
	}
	fontMe := fontHighDark16
	fontPeer := fontHighDark11
	if darkMode {
		fontMe = fontHighLight16
		fontPeer = fontHighLight11
	}

	out := make([]Update, 0, len(nodes)/4+1)
	for i := range nodes {
		n := &nodes[i]
		next := propsFor(n, level, fontMe, fontPeer, blue)
		if !changed(n, next) {
			continue
		}
		out = append(out, next)
	}
	return out
}

func propsFor(n *NodeIn, level string, fontMe, fontPeer, blue map[string]any) Update {
	u := Update{ID: n.ID}
	switch level {
	case "low":
		if n.ID == "me" {
			u.Size = &size15
		} else {
			u.Size = &size10
		}
		u.Shape = "dot"
		u.Font = fontSize0
		if n.Group == "interface" && n.Color != nil {
			u.Color = n.Color
		} else {
			u.Color = blue
		}
	case "medium":
		shape := n.OriginalShape
		if shape == "" {
			shape = "circularImage"
		}
		u.Shape = shape
		u.Size = originalSizePtr(n)
		u.Font = fontSize0
	default:
		shape := n.OriginalShape
		if shape == "" {
			shape = "circularImage"
		}
		u.Shape = shape
		u.Size = originalSizePtr(n)
		if n.ID == "me" {
			u.Font = fontMe
		} else {
			u.Font = fontPeer
		}
	}
	return u
}

func originalSizePtr(n *NodeIn) *float64 {
	if n.OriginalSize != 0 {
		// Return a pointer into a stable set of common sizes when possible.
		switch n.OriginalSize {
		case 10:
			return &size10
		case 15:
			return &size15
		case 25:
			return &size25
		case 50:
			return &size50
		}
		v := n.OriginalSize
		return &v
	}
	if n.ID == "me" {
		return &size50
	}
	return &size25
}

func changed(n *NodeIn, next Update) bool {
	if next.Shape != "" && next.Shape != n.Shape {
		return true
	}
	if next.Size != nil && *next.Size != n.Size {
		return true
	}
	if next.Font != nil {
		ns, ok := next.Font["size"]
		if ok {
			var cur float64
			if n.Font != nil && n.Font.Size != nil {
				cur = *n.Font.Size
			}
			switch v := ns.(type) {
			case float64:
				if v != cur {
					return true
				}
			case int:
				if float64(v) != cur {
					return true
				}
			}
		}
	}
	return false
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
