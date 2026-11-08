// Package notify wraps the Wails notifications service with the Electron
// shell's message-notification semantics: title/body clamping, silent flag,
// per-destination tracking and click-to-focus.
package notify

import (
	"strings"
	"sync"

	"github.com/wailsapp/wails/v3/pkg/services/notifications"
)

const (
	MaxTitleLen = 200
	MaxBodyLen  = 1000
	MaxHashLen  = 128
)

// Tracker mirrors electron/messageNotifications.js: notification ids grouped
// by destination hash so close-message-notifications can dismiss them.
type Tracker struct {
	mu     sync.Mutex
	byDest map[string]map[string]bool
}

func NewTracker() *Tracker {
	return &Tracker{byDest: map[string]map[string]bool{}}
}

func normalizeHash(h string) string {
	return strings.ToLower(strings.TrimSpace(h))
}

func (t *Tracker) Track(destinationHash, id string) {
	key := normalizeHash(destinationHash)
	if key == "" {
		key = "__untagged__"
	}
	t.mu.Lock()
	defer t.mu.Unlock()
	set := t.byDest[key]
	if set == nil {
		set = map[string]bool{}
		t.byDest[key] = set
	}
	set[id] = true
}

func (t *Tracker) Untrack(destinationHash, id string) {
	key := normalizeHash(destinationHash)
	if key == "" {
		key = "__untagged__"
	}
	t.mu.Lock()
	defer t.mu.Unlock()
	if set := t.byDest[key]; set != nil {
		delete(set, id)
		if len(set) == 0 {
			delete(t.byDest, key)
		}
	}
}

// NotificationRemover is the slice of the Wails notifications service the
// tracker needs; *notifications.NotificationService satisfies it.
type NotificationRemover interface {
	RemoveNotification(identifier string) error
}

// CloseFor returns the number of notifications dismissed.
func (t *Tracker) CloseFor(service NotificationRemover, destinationHash string) int {
	key := normalizeHash(destinationHash)
	if key == "" {
		return t.CloseAll(service)
	}
	t.mu.Lock()
	ids := make([]string, 0)
	if set := t.byDest[key]; set != nil {
		for id := range set {
			ids = append(ids, id)
		}
		delete(t.byDest, key)
	}
	t.mu.Unlock()
	closed := 0
	for _, id := range ids {
		if err := service.RemoveNotification(id); err == nil {
			closed++
		}
	}
	return closed
}

func (t *Tracker) CloseAll(service NotificationRemover) int {
	t.mu.Lock()
	var ids []string
	for _, set := range t.byDest {
		for id := range set {
			ids = append(ids, id)
		}
	}
	t.byDest = map[string]map[string]bool{}
	t.mu.Unlock()
	closed := 0
	for _, id := range ids {
		if err := service.RemoveNotification(id); err == nil {
			closed++
		}
	}
	return closed
}

// Manager handles show-notification / close-message-notifications.
type Manager struct {
	service *notifications.NotificationService
	tracker *Tracker
	onClick func()
	mu      sync.Mutex
	counter int
}

func NewManager(service *notifications.NotificationService) *Manager {
	return &Manager{service: service, tracker: NewTracker()}
}

func (m *Manager) SetOnClick(fn func()) { m.onClick = fn }

// Show posts a notification. silent suppresses sound.
func (m *Manager) Show(title, body string, silent bool, destinationHash string) {
	if m.service == nil {
		return
	}
	if len(title) > MaxTitleLen {
		title = title[:MaxTitleLen]
	}
	if len(body) > MaxBodyLen {
		body = body[:MaxBodyLen]
	}
	hash := destinationHash
	if len(hash) > MaxHashLen {
		hash = hash[:MaxHashLen]
	}
	m.mu.Lock()
	m.counter++
	id := hash
	if id == "" {
		id = "msg-" + itoa(m.counter)
	} else {
		id = hash + "-" + itoa(m.counter)
	}
	m.mu.Unlock()
	opts := notifications.NotificationOptions{
		ID:    id,
		Title: title,
		Body:  body,
	}
	if silent {
		opts.Sound = &notifications.NotificationSound{Silent: true}
	}
	m.tracker.Track(hash, id)
	if err := m.service.SendNotification(opts); err != nil {
		m.tracker.Untrack(hash, id)
		return
	}
}

func (m *Manager) CloseMessageNotifications(destinationHash *string) int {
	if m.service == nil {
		return 0
	}
	if destinationHash == nil || *destinationHash == "" {
		return m.tracker.CloseAll(m.service)
	}
	return m.tracker.CloseFor(m.service, *destinationHash)
}

func itoa(i int) string {
	if i == 0 {
		return "0"
	}
	var buf [20]byte
	pos := len(buf)
	for i > 0 {
		pos--
		buf[pos] = byte('0' + i%10)
		i /= 10
	}
	return string(buf[pos:])
}
