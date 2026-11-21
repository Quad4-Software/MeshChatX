package main

import "testing"

func TestShutdownPageURL(t *testing.T) {
	got := shutdownPageURL("http://127.0.0.1:9338", "dark")
	want := "http://127.0.0.1:9338/__shell/shutdown.html?theme=dark"
	if got != want {
		t.Fatalf("shutdownPageURL = %q, want %q", got, want)
	}
}

func TestQuitStateMachine(t *testing.T) {
	s := &shellState{}
	if s.isQuitting() {
		t.Fatal("fresh shell state must not report quitting")
	}
	s.setQuitting()
	if !s.isQuitting() {
		t.Fatal("setQuitting was not recorded")
	}
	// quitApp is a no-op once quitting is set: it must not panic with a nil
	// app and must not navigate or re-quit.
	s.quitApp()
}
