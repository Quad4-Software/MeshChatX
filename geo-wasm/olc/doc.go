// Package olc implements Open Location Code (OLC).
//
// OLC encodes latitude and longitude into short alphanumeric codes that
// can be used as digital addresses. This package is dependency-free and follows
// the public Open Location Code algorithm described at
// https://github.com/google/open-location-code.
//
// Prefer EncodeTo or AppendEncode in allocation-sensitive code paths. Decode of
// a full code does not allocate on the success path.
//
// Validation uses the official Open Location Code CSV corpus under testdata/.
package olc
