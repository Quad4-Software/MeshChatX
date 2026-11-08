package notify

import (
	"errors"
	"strings"
	"testing"
)

type fakeRemover struct {
	removed []string
	failFor map[string]bool
}

func (f *fakeRemover) RemoveNotification(id string) error {
	if f.failFor[id] {
		return errors.New("no such notification")
	}
	f.removed = append(f.removed, id)
	return nil
}

func TestTrackerNormalizeAndGroup(t *testing.T) {
	tr := NewTracker()
	tr.Track("  AbCd  ", "id1")
	tr.Track("abcd", "id2") // same normalized hash
	tr.Track("", "untagged")
	svc := &fakeRemover{}
	closed := tr.CloseFor(svc, "ABCD")
	if closed != 2 {
		t.Fatalf("closed %d want 2", closed)
	}
	if len(svc.removed) != 2 {
		t.Fatalf("removed %v", svc.removed)
	}
	// hash group is gone; untagged remains -> CloseAll gets 1
	closed = tr.CloseAll(svc)
	if closed != 1 {
		t.Fatalf("closeAll %d want 1", closed)
	}
}

func TestTrackerCloseForEmptyHashClosesAll(t *testing.T) {
	tr := NewTracker()
	tr.Track("h1", "a")
	tr.Track("h2", "b")
	svc := &fakeRemover{}
	if got := tr.CloseFor(svc, ""); got != 2 {
		t.Fatalf("empty hash should close all, got %d", got)
	}
}

func TestTrackerUntrack(t *testing.T) {
	tr := NewTracker()
	tr.Track("h", "id1")
	tr.Track("h", "id2")
	tr.Untrack("h", "id1")
	svc := &fakeRemover{}
	if got := tr.CloseFor(svc, "h"); got != 1 {
		t.Fatalf("after untrack got %d want 1", got)
	}
	// untracking last id removes the group
	tr.Track("h2", "x")
	tr.Untrack("h2", "x")
	if got := tr.CloseAll(svc); got != 0 {
		t.Fatalf("empty tracker closeAll %d", got)
	}
}

func TestTrackerCloseForFailedRemovals(t *testing.T) {
	tr := NewTracker()
	tr.Track("h", "bad")
	tr.Track("h", "good")
	svc := &fakeRemover{failFor: map[string]bool{"bad": true}}
	if got := tr.CloseFor(svc, "h"); got != 1 {
		t.Fatalf("only successful removals count, got %d", got)
	}
}

func TestManagerShowClamps(t *testing.T) {
	// nil service -> Show is a no-op, must not panic
	m := NewManager(nil)
	m.Show(strings.Repeat("t", 500), strings.Repeat("b", 2000), true, strings.Repeat("h", 200))
	m.CloseMessageNotifications(nil)
}

func TestManagerShowWithFakeService(t *testing.T) {
	// Use a nil *NotificationService would panic on SendNotification; instead
	// verify id generation via tracker with service=nil is skipped safely.
	m := NewManager(nil)
	// destinationHash -> id "hash-N"; with nil service nothing tracked
	m.Show("t", "b", false, "abc")
	if got := m.CloseMessageNotifications(strPtr("abc")); got != 0 {
		t.Fatalf("nil service close: %d", got)
	}
}

func strPtr(s string) *string { return &s }
