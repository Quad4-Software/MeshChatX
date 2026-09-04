// SPDX-License-Identifier: 0BSD

// Command wasm exposes MGRS/UTM/OLC helpers to the MeshChatX map UI.
package main

import (
	"encoding/json"
	"syscall/js"

	"github.com/Quad4-Software/MeshChatX/geo-wasm/internal/geoparse"
	"github.com/Quad4-Software/MeshChatX/geo-wasm/mgrs"
	"github.com/Quad4-Software/MeshChatX/geo-wasm/olc"
)

const apiVersion = "1.0.0"

func main() {
	js.Global().Set("meshchatxGeoVersion", apiVersion)
	js.Global().Set("meshchatxGeoLatLonToGrid", js.FuncOf(wrapJSON(latLonToGridHandler)))
	js.Global().Set("meshchatxGeoGridToLatLon", js.FuncOf(wrapJSON(gridToLatLonHandler)))
	js.Global().Set("meshchatxGeoMgrsEncode", js.FuncOf(wrapJSON(mgrsEncodeHandler)))
	js.Global().Set("meshchatxGeoMgrsDecode", js.FuncOf(wrapJSON(mgrsDecodeHandler)))
	js.Global().Set("meshchatxGeoMgrsFormatSpaced", js.FuncOf(wrapJSON(mgrsFormatHandler)))
	js.Global().Set("meshchatxGeoOlcEncode", js.FuncOf(wrapJSON(olcEncodeHandler)))
	js.Global().Set("meshchatxGeoOlcDecode", js.FuncOf(wrapJSON(olcDecodeHandler)))
	js.Global().Set("meshchatxGeoOlcShorten", js.FuncOf(wrapJSON(olcShortenHandler)))
	js.Global().Set("meshchatxGeoOlcRecoverNearest", js.FuncOf(wrapJSON(olcRecoverHandler)))
	js.Global().Set("meshchatxGeoOlcIsValid", js.FuncOf(wrapJSON(olcIsValidHandler)))
	js.Global().Set("meshchatxGeoParse", js.FuncOf(wrapJSON(parseHandler)))
	js.Global().Set("meshchatxGeoFormat", js.FuncOf(wrapJSON(formatHandler)))
	select {}
}

type handlerFunc func(args []js.Value) (any, error)

func wrapJSON(fn handlerFunc) func(js.Value, []js.Value) any {
	return func(_ js.Value, args []js.Value) any {
		out, err := fn(args)
		if err != nil {
			return js.ValueOf(map[string]any{
				"ok":    false,
				"error": err.Error(),
			})
		}
		buf, err := json.Marshal(out)
		if err != nil {
			return js.ValueOf(map[string]any{
				"ok":    false,
				"error": err.Error(),
			})
		}
		return js.ValueOf(string(buf))
	}
}

func readJSONArg(args []js.Value, idx int, dest any) error {
	if idx >= len(args) {
		return errString("missing json argument")
	}
	return json.Unmarshal([]byte(args[idx].String()), dest)
}

type errString string

func (e errString) Error() string { return string(e) }

func latLonToGridHandler(args []js.Value) (any, error) {
	var in struct {
		Lat float64 `json:"lat"`
		Lon float64 `json:"lon"`
	}
	if err := readJSONArg(args, 0, &in); err != nil {
		return nil, err
	}
	g, err := mgrs.LatLonToGrid(in.Lat, in.Lon)
	if err != nil {
		return nil, err
	}
	return map[string]any{
		"ok": true, "zone": g.Zone, "north": g.North,
		"easting": g.Easting, "northing": g.Northing,
	}, nil
}

func gridToLatLonHandler(args []js.Value) (any, error) {
	var in struct {
		Zone     int     `json:"zone"`
		North    bool    `json:"north"`
		Easting  float64 `json:"easting"`
		Northing float64 `json:"northing"`
	}
	if err := readJSONArg(args, 0, &in); err != nil {
		return nil, err
	}
	pt, err := mgrs.GridToLatLon(mgrs.Grid{
		Zone: in.Zone, North: in.North, Easting: in.Easting, Northing: in.Northing,
	})
	if err != nil {
		return nil, err
	}
	return map[string]any{"ok": true, "lat": pt.Lat, "lon": pt.Lon}, nil
}

func mgrsEncodeHandler(args []js.Value) (any, error) {
	var in struct {
		Lat        float64 `json:"lat"`
		Lon        float64 `json:"lon"`
		DigitPairs int     `json:"digitPairs"`
	}
	if err := readJSONArg(args, 0, &in); err != nil {
		return nil, err
	}
	if in.DigitPairs <= 0 {
		in.DigitPairs = mgrs.DefaultDigitPairs
	}
	ref, err := mgrs.Encode(in.Lat, in.Lon, in.DigitPairs)
	if err != nil {
		return nil, err
	}
	spaced, err := mgrs.FormatSpaced(ref)
	if err != nil {
		spaced = ref
	}
	return map[string]any{"ok": true, "compact": ref, "spaced": spaced}, nil
}

func mgrsDecodeHandler(args []js.Value) (any, error) {
	var in struct {
		Reference  string `json:"reference"`
		CenterCell bool   `json:"centerCell"`
	}
	if err := readJSONArg(args, 0, &in); err != nil {
		return nil, err
	}
	pt, err := mgrs.Decode(in.Reference, in.CenterCell)
	if err != nil {
		return nil, err
	}
	return map[string]any{"ok": true, "lat": pt.Lat, "lon": pt.Lon}, nil
}

func mgrsFormatHandler(args []js.Value) (any, error) {
	var in struct {
		Reference string `json:"reference"`
	}
	if err := readJSONArg(args, 0, &in); err != nil {
		return nil, err
	}
	spaced, err := mgrs.FormatSpaced(in.Reference)
	if err != nil {
		return nil, err
	}
	return map[string]any{"ok": true, "spaced": spaced}, nil
}

func olcEncodeHandler(args []js.Value) (any, error) {
	var in struct {
		Lat     float64 `json:"lat"`
		Lon     float64 `json:"lon"`
		CodeLen int     `json:"codeLen"`
	}
	if err := readJSONArg(args, 0, &in); err != nil {
		return nil, err
	}
	if in.CodeLen <= 0 {
		in.CodeLen = 10
	}
	return map[string]any{"ok": true, "code": olc.Encode(in.Lat, in.Lon, in.CodeLen)}, nil
}

func olcDecodeHandler(args []js.Value) (any, error) {
	var in struct {
		Code string `json:"code"`
	}
	if err := readJSONArg(args, 0, &in); err != nil {
		return nil, err
	}
	area, err := olc.Decode(in.Code)
	if err != nil {
		return nil, err
	}
	lat, lon := area.Center()
	return map[string]any{
		"ok": true, "lat": lat, "lon": lon,
		"latLo": area.LatLo, "lngLo": area.LngLo,
		"latHi": area.LatHi, "lngHi": area.LngHi, "len": area.Len,
	}, nil
}

func olcShortenHandler(args []js.Value) (any, error) {
	var in struct {
		Code string  `json:"code"`
		Lat  float64 `json:"lat"`
		Lon  float64 `json:"lon"`
	}
	if err := readJSONArg(args, 0, &in); err != nil {
		return nil, err
	}
	short, err := olc.Shorten(in.Code, in.Lat, in.Lon)
	if err != nil {
		return nil, err
	}
	return map[string]any{"ok": true, "code": short}, nil
}

func olcRecoverHandler(args []js.Value) (any, error) {
	var in struct {
		Code string  `json:"code"`
		Lat  float64 `json:"lat"`
		Lon  float64 `json:"lon"`
	}
	if err := readJSONArg(args, 0, &in); err != nil {
		return nil, err
	}
	full, err := olc.RecoverNearest(in.Code, in.Lat, in.Lon)
	if err != nil {
		return nil, err
	}
	area, err := olc.Decode(full)
	if err != nil {
		return nil, err
	}
	lat, lon := area.Center()
	return map[string]any{"ok": true, "code": full, "lat": lat, "lon": lon}, nil
}

func olcIsValidHandler(args []js.Value) (any, error) {
	var in struct {
		Code string `json:"code"`
	}
	if err := readJSONArg(args, 0, &in); err != nil {
		return nil, err
	}
	return map[string]any{
		"ok": true, "valid": olc.IsValid(in.Code),
		"short": olc.IsShort(in.Code), "full": olc.IsFull(in.Code),
	}, nil
}

func formatHandler(args []js.Value) (any, error) {
	var in struct {
		Lat     float64 `json:"lat"`
		Lon     float64 `json:"lon"`
		Format  string  `json:"format"`
		RefLat  float64 `json:"refLat"`
		RefLon  float64 `json:"refLon"`
		HasRef  bool    `json:"hasRef"`
		CodeLen int     `json:"codeLen"`
	}
	if err := readJSONArg(args, 0, &in); err != nil {
		return nil, err
	}
	text, extra, err := geoparse.Format(in.Lat, in.Lon, in.Format, in.HasRef, in.RefLat, in.RefLon, in.CodeLen)
	if err != nil {
		return nil, err
	}
	out := map[string]any{"ok": true, "format": in.Format, "text": text}
	for k, v := range extra {
		out[k] = v
	}
	return out, nil
}

func parseHandler(args []js.Value) (any, error) {
	var in struct {
		Text   string  `json:"text"`
		RefLat float64 `json:"refLat"`
		RefLon float64 `json:"refLon"`
		HasRef bool    `json:"hasRef"`
	}
	if err := readJSONArg(args, 0, &in); err != nil {
		return nil, err
	}
	r, err := geoparse.Parse(in.Text, in.HasRef, in.RefLat, in.RefLon)
	if err != nil {
		return nil, err
	}
	return map[string]any{"ok": true, "lat": r.Lat, "lon": r.Lon, "kind": r.Kind}, nil
}
