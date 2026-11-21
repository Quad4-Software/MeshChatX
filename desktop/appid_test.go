package main

import "testing"

func TestLinuxApplicationID(t *testing.T) {
	tests := []struct {
		name     string
		flatpak  string
		uniqueID string
		want     string
	}{
		{name: "default is the packaged app id", want: "com.meshchatx.app"},
		{name: "flatpak id wins", flatpak: "io.example.Sandboxed", want: "io.example.Sandboxed"},
		{name: "unique id applies off flatpak", uniqueID: "com.meshchatx.dev", want: "com.meshchatx.dev"},
		{
			name:     "flatpak id beats unique id inside the sandbox",
			flatpak:  "io.example.Sandboxed",
			uniqueID: "com.meshchatx.dev",
			want:     "io.example.Sandboxed",
		},
		{name: "blank flatpak id falls through", flatpak: "  ", uniqueID: "com.meshchatx.dev", want: "com.meshchatx.dev"},
		{name: "blank unique id falls through", uniqueID: "  ", want: "com.meshchatx.app"},
	}
	for _, tc := range tests {
		t.Run(tc.name, func(t *testing.T) {
			t.Setenv("FLATPAK_ID", tc.flatpak)
			t.Setenv("MESHCHATX_UNIQUE_ID", tc.uniqueID)
			if got := linuxApplicationID(); got != tc.want {
				t.Fatalf("linuxApplicationID() = %q, want %q", got, tc.want)
			}
		})
	}
}
