// SPDX-License-Identifier: 0BSD

// Package hashpos derives stable layout angles from node ids.
package hashpos

import "math"

// fnv1a32 hashes s with FNV-1a without heap allocation.
func fnv1a32(s string) uint32 {
	const (
		offset = 2166136261
		prime  = 16777619
	)
	h := uint32(offset)
	for i := 0; i < len(s); i++ {
		h ^= uint32(s[i])
		h *= prime
	}
	return h
}

// fnv1a32Salt hashes id + NUL + salt with FNV-1a without heap allocation.
func fnv1a32Salt(id, salt string) uint32 {
	const (
		offset = 2166136261
		prime  = 16777619
	)
	h := uint32(offset)
	for i := 0; i < len(id); i++ {
		h ^= uint32(id[i])
		h *= prime
	}
	h ^= 0
	h *= prime
	for i := 0; i < len(salt); i++ {
		h ^= uint32(salt[i])
		h *= prime
	}
	return h
}

// Angle01 returns a deterministic angle in [0, 2*Pi) for id.
func Angle01(id string) float64 {
	u := fnv1a32(id)
	return (float64(u%10000) / 10000.0) * 2 * math.Pi
}

// Dist01 returns a deterministic unit fraction in [0, 1) for id and salt.
func Dist01(id, salt string) float64 {
	u := fnv1a32Salt(id, salt)
	return float64(u%10000) / 10000.0
}

// XY places a point at radius base+span*Dist01 around the origin.
func XY(id string, base, span float64) (x, y float64) {
	a := Angle01(id)
	d := base + Dist01(id, "r")*span
	return math.Cos(a) * d, math.Sin(a) * d
}

// Around places a point near parent using a deterministic offset.
func Around(id string, px, py, base, span float64) (x, y float64) {
	a := Angle01(id)
	d := base + Dist01(id, "r")*span
	return px + math.Cos(a)*d, py + math.Sin(a)*d
}
