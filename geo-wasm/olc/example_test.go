package olc_test

import (
	"fmt"

	"github.com/Quad4-Software/MeshChatX/geo-wasm/olc"
)

func ExampleEncode() {
	fmt.Println(olc.Encode(-1.286386, 36.817223, 10))
	// Output: 6GCRPR78+CV
}

func ExampleDecode() {
	area, err := olc.Decode("6GCRPR78+CV")
	if err != nil {
		panic(err)
	}
	lat, lng := area.Center()
	fmt.Printf("%.6f %.6f\n", lat, lng)
	// Output: -1.286437 36.817187
}

func ExampleEncodeTo() {
	var buf [olc.MaxEncodedLen]byte
	n, err := olc.EncodeTo(buf[:], -1.286386, 36.817223, 10)
	if err != nil {
		panic(err)
	}
	fmt.Println(string(buf[:n]))
	// Output: 6GCRPR78+CV
}

func ExampleShorten() {
	short, err := olc.Shorten("6GCRPR78+CV", -1.286386, 36.817223)
	if err != nil {
		panic(err)
	}
	fmt.Println(short)
	// Output: +CV
}

func ExampleRecoverNearest() {
	full, err := olc.RecoverNearest("+CV", -1.286386, 36.817223)
	if err != nil {
		panic(err)
	}
	fmt.Println(full)
	// Output: 6GCRPR78+CV
}
