// SPDX-License-Identifier: 0BSD

// Package layout settles node positions with a fast force simulation.
// Runs in WASM so vis-network can keep its JS physics solver off
// (that solver is the main FPS bottleneck for large graphs).
package layout

import (
	"math"
)

const (
	// DefaultRepulsion is 1/r^2 strength when Request.Repulsion is 0.
	// vis-network barnesHut uses gravitationalConstant -3500. Keep this near
	// that scale so WASM settle does not inflate the graph.
	DefaultRepulsion = 1800.0
	// DefaultSpringK is hooke stiffness when Request.SpringK is 0.
	DefaultSpringK = 0.032
	// DefaultSpringLen is rest length when an edge omits Length.
	// vis-network barnesHut springLength is 200. Peers sit a bit further out.
	DefaultSpringLen = 240.0
	// DefaultHubSpringLen is rest length for thick hub edges (me to interface).
	DefaultHubSpringLen = 200.0
	// DefaultCellSize is the repulsion grid bucket in world units.
	DefaultCellSize = 180.0
	// DefaultMinSep is used when a body has no Radius.
	DefaultMinSep = 48.0
	// CollisionPad is extra gap beyond the two node radii.
	CollisionPad = 16.0
	// CollisionK is extra push when two discs overlap the min gap.
	// Keep this below 1 so stacked nodes unstick without launching.
	CollisionK = 0.85
	// LiveRepulsion is WebGL live-tick repulsion.
	LiveRepulsion = 1800.0
	// LiveSpringK is WebGL live-tick spring stiffness.
	LiveSpringK = 0.016
	// LiveDamping is WebGL live-tick velocity keep fraction.
	LiveDamping = 0.78
	// LiveMaxSpeed caps WebGL live-tick motion per step.
	LiveMaxSpeed = 4.0
	// LiveRestSpeed zeros live velocity below this length.
	LiveRestSpeed = 0.25
	// LiveSleepShift is the max per-tick move that still counts as rest.
	LiveSleepShift = 0.15
)

// SpringLength returns rest length from vis-style edge width.
func SpringLength(width float64) float64 {
	if width >= 2.5 {
		return DefaultHubSpringLen
	}
	return DefaultSpringLen
}

// Node is one body in the layout simulation.
type Node struct {
	ID     string  `json:"id"`
	X      float64 `json:"x"`
	Y      float64 `json:"y"`
	Vx     float64 `json:"vx"`
	Vy     float64 `json:"vy"`
	Mass   float64 `json:"mass"`
	Fixed  bool    `json:"fixed"`
	Radius float64 `json:"radius"`
}

// Edge is a spring between two node ids.
type Edge struct {
	From   string  `json:"from"`
	To     string  `json:"to"`
	Length float64 `json:"length"`
}

// Request configures a layout settle pass.
type Request struct {
	Nodes      []Node  `json:"nodes"`
	Edges      []Edge  `json:"edges"`
	Iterations int     `json:"iterations"`
	Gravity    float64 `json:"gravity"`
	Repulsion  float64 `json:"repulsion"`
	SpringK    float64 `json:"spring_k"`
	Damping    float64 `json:"damping"`
	MaxSpeed   float64 `json:"max_speed"`
}

// Result is settled positions keyed by node id.
type Result struct {
	Positions  map[string]XY `json:"positions"`
	Iterations int           `json:"iterations"`
}

// XY is a 2D point.
type XY struct {
	X float64 `json:"x"`
	Y float64 `json:"y"`
}

type body struct {
	id     string
	x, y   float64
	vx, vy float64
	mass   float64
	fixed  bool
	radius float64
}

// Settle runs a damped spring + grid-repulsion layout in-place.
func Settle(req Request) Result {
	n := len(req.Nodes)
	out := Result{Positions: make(map[string]XY, n)}
	if n == 0 {
		return out
	}

	iters := req.Iterations
	if iters <= 0 {
		iters = pickIterations(n)
	}
	if iters > 400 {
		iters = 400
	}

	gravity := req.Gravity
	// Negative gravity means "off" (live Tick). Zero means use the default
	// centering pull for one-shot settle. Live layout must not vacuum nodes
	// toward the origin or users cannot shape the graph.
	if gravity < 0 {
		gravity = 0
	} else if gravity == 0 {
		gravity = 0.01
	}
	repulsion := req.Repulsion
	if repulsion == 0 {
		repulsion = DefaultRepulsion
	}
	springK := req.SpringK
	if springK == 0 {
		springK = DefaultSpringK
	}
	damping := req.Damping
	if damping == 0 {
		// Multiply kept velocity each step. Lower = more friction, less twitch.
		damping = 0.68
	}
	maxSpeed := req.MaxSpeed
	if maxSpeed == 0 {
		maxSpeed = 18
	}

	bodies := make([]body, n)
	index := make(map[string]int, n)
	for i := range req.Nodes {
		nd := &req.Nodes[i]
		mass := nd.Mass
		if mass <= 0 {
			mass = 1
		}
		radius := nd.Radius
		if radius <= 0 {
			radius = DefaultMinSep * 0.5
		}
		bodies[i] = body{
			id:     nd.ID,
			x:      nd.X,
			y:      nd.Y,
			vx:     nd.Vx,
			vy:     nd.Vy,
			mass:   mass,
			fixed:  nd.Fixed || nd.ID == "me",
			radius: radius,
		}
		index[nd.ID] = i
	}

	type spring struct {
		a, b int
		len  float64
	}
	springs := make([]spring, 0, len(req.Edges))
	for i := range req.Edges {
		e := &req.Edges[i]
		ai, okA := index[e.From]
		bi, okB := index[e.To]
		if !okA || !okB || ai == bi {
			continue
		}
		length := e.Length
		if length <= 0 {
			length = DefaultSpringLen
		}
		springs = append(springs, spring{a: ai, b: bi, len: length})
	}

	cellSize := DefaultCellSize
	for step := 0; step < iters; step++ {
		fx := make([]float64, n)
		fy := make([]float64, n)

		// Weak pull toward origin keeps the mesh centred.
		for i := range bodies {
			if bodies[i].fixed {
				continue
			}
			fx[i] -= bodies[i].x * gravity * bodies[i].mass
			fy[i] -= bodies[i].y * gravity * bodies[i].mass
		}

		// Grid-bucketed repulsion (near O(n) average).
		buckets := make(map[[2]int][]int, n/2+1)
		for i := range bodies {
			cx := int(math.Floor(bodies[i].x / cellSize))
			cy := int(math.Floor(bodies[i].y / cellSize))
			key := [2]int{cx, cy}
			buckets[key] = append(buckets[key], i)
		}
		for i := range bodies {
			cx := int(math.Floor(bodies[i].x / cellSize))
			cy := int(math.Floor(bodies[i].y / cellSize))
			for dx := -1; dx <= 1; dx++ {
				for dy := -1; dy <= 1; dy++ {
					list := buckets[[2]int{cx + dx, cy + dy}]
					for _, j := range list {
						if j <= i {
							continue
						}
						dxp := bodies[i].x - bodies[j].x
						dyp := bodies[i].y - bodies[j].y
						dist2 := dxp*dxp + dyp*dyp + 0.01
						dist := math.Sqrt(dist2)
						inv := 1.0 / dist
						force := repulsion * bodies[i].mass * bodies[j].mass * inv * inv
						minDist := bodies[i].radius + bodies[j].radius + CollisionPad
						if dist < minDist {
							force += (minDist - dist) * CollisionK
						}
						fxn := dxp * inv * force
						fyn := dyp * inv * force
						if !bodies[i].fixed {
							fx[i] += fxn
							fy[i] += fyn
						}
						if !bodies[j].fixed {
							fx[j] -= fxn
							fy[j] -= fyn
						}
					}
				}
			}
		}

		// Springs
		for _, s := range springs {
			a := &bodies[s.a]
			b := &bodies[s.b]
			dxp := b.x - a.x
			dyp := b.y - a.y
			dist := math.Sqrt(dxp*dxp + dyp*dyp)
			if dist < 0.01 {
				dist = 0.01
			}
			delta := dist - s.len
			force := springK * delta
			ux := dxp / dist
			uy := dyp / dist
			if !a.fixed {
				fx[s.a] += ux * force
				fy[s.a] += uy * force
			}
			if !b.fixed {
				fx[s.b] -= ux * force
				fy[s.b] -= uy * force
			}
		}

		// Integrate
		for i := range bodies {
			if bodies[i].fixed {
				bodies[i].vx = 0
				bodies[i].vy = 0
				continue
			}
			bodies[i].vx = (bodies[i].vx + fx[i]/bodies[i].mass) * damping
			bodies[i].vy = (bodies[i].vy + fy[i]/bodies[i].mass) * damping
			speed := math.Hypot(bodies[i].vx, bodies[i].vy)
			if speed > maxSpeed {
				scale := maxSpeed / speed
				bodies[i].vx *= scale
				bodies[i].vy *= scale
			}
			bodies[i].x += bodies[i].vx
			bodies[i].y += bodies[i].vy
		}
	}

	for i := range bodies {
		out.Positions[bodies[i].id] = XY{X: bodies[i].x, Y: bodies[i].y}
		// Write velocities back onto the request nodes when ids match so
		// live layout can carry momentum across Tick frames.
		if idx, ok := index[bodies[i].id]; ok {
			req.Nodes[idx].X = bodies[i].x
			req.Nodes[idx].Y = bodies[i].y
			req.Nodes[idx].Vx = bodies[i].vx
			req.Nodes[idx].Vy = bodies[i].vy
		}
	}
	out.Iterations = iters
	return out
}

func pickIterations(n int) int {
	if n >= 1500 {
		return 45
	}
	if n >= 600 {
		return 70
	}
	if n >= 200 {
		return 100
	}
	return 140
}
