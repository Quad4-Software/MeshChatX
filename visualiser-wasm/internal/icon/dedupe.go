// SPDX-License-Identifier: 0BSD

// Package icon collapses deferred icon paint work for the visualiser.
package icon

// QueueItem is one deferred custom-icon paint request.
type QueueItem struct {
	NodeID     string  `json:"nodeId"`
	CacheKey   string  `json:"cacheKey"`
	IconName   string  `json:"iconName"`
	FG         string  `json:"fg"`
	BG         string  `json:"bg"`
	Size       float64 `json:"size"`
	Generation int     `json:"generation"`
}

// DedupedBucket is one unique cache key with all node ids that share it.
type DedupedBucket struct {
	CacheKey   string   `json:"cacheKey"`
	NodeIDs    []string `json:"nodeIds"`
	IconName   string   `json:"iconName"`
	FG         string   `json:"fg"`
	BG         string   `json:"bg"`
	Size       float64  `json:"size"`
	Generation int      `json:"generation"`
}

// DedupeQueueEntries collapses duplicate cacheKey entries into one paint job.
func DedupeQueueEntries(queue []QueueItem) []DedupedBucket {
	if len(queue) == 0 {
		return nil
	}
	order := make([]string, 0, 16)
	byKey := make(map[string]*DedupedBucket, 16)
	seenNodes := make(map[string]map[string]struct{}, 16)

	for i := range queue {
		item := &queue[i]
		if item.CacheKey == "" || item.NodeID == "" {
			continue
		}
		bucket, ok := byKey[item.CacheKey]
		if !ok {
			bucket = &DedupedBucket{
				CacheKey:   item.CacheKey,
				NodeIDs:    make([]string, 0, 4),
				IconName:   item.IconName,
				FG:         item.FG,
				BG:         item.BG,
				Size:       item.Size,
				Generation: item.Generation,
			}
			byKey[item.CacheKey] = bucket
			seenNodes[item.CacheKey] = make(map[string]struct{}, 4)
			order = append(order, item.CacheKey)
		}
		seen := seenNodes[item.CacheKey]
		if _, dup := seen[item.NodeID]; dup {
			continue
		}
		seen[item.NodeID] = struct{}{}
		bucket.NodeIDs = append(bucket.NodeIDs, item.NodeID)
	}

	out := make([]DedupedBucket, 0, len(order))
	for _, key := range order {
		out = append(out, *byKey[key])
	}
	return out
}
