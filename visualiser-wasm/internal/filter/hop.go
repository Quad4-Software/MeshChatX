// SPDX-License-Identifier: 0BSD

// Package filter implements hop and search filters for the network visualiser.
package filter

import "strings"

// PathEntry is a compact path-table row.
type PathEntry struct {
	Hash      string   `json:"hash"`
	Interface string   `json:"interface"`
	Hops      *float64 `json:"hops"`
}

// PathHashesWithinHopFilter returns unique destination hashes within hopMax.
// A nil hopMax means no hop ceiling. Rows with nil hops are skipped.
func PathHashesWithinHopFilter(pathTable []PathEntry, hopMax *float64) []string {
	if len(pathTable) == 0 {
		return nil
	}
	seen := make(map[string]struct{}, len(pathTable)/2+1)
	out := make([]string, 0, len(pathTable)/4+1)
	for i := range pathTable {
		e := &pathTable[i]
		if e.Hops == nil || e.Hash == "" {
			continue
		}
		if hopMax != nil && *e.Hops > *hopMax {
			continue
		}
		if _, ok := seen[e.Hash]; ok {
			continue
		}
		seen[e.Hash] = struct{}{}
		out = append(out, e.Hash)
	}
	return out
}

// MatchesSearch reports whether text matches queryLower (already lowercased).
// An empty query matches everything.
// ASCII-only text avoids allocating a lowered copy.
func MatchesSearch(queryLower, text string) bool {
	if queryLower == "" {
		return true
	}
	if text == "" {
		return false
	}
	if isASCII(text) {
		return containsFoldASCII(text, queryLower)
	}
	return strings.Contains(strings.ToLower(text), queryLower)
}

func isASCII(s string) bool {
	for i := 0; i < len(s); i++ {
		if s[i] >= 0x80 {
			return false
		}
	}
	return true
}

func containsFoldASCII(haystack, needleLower string) bool {
	n := len(needleLower)
	if n == 0 {
		return true
	}
	if n > len(haystack) {
		return false
	}
	for i := 0; i+n <= len(haystack); i++ {
		ok := true
		for j := 0; j < n; j++ {
			c := haystack[i+j]
			if c >= 'A' && c <= 'Z' {
				c += 'a' - 'A'
			}
			if c != needleLower[j] {
				ok = false
				break
			}
		}
		if ok {
			return true
		}
	}
	return false
}
