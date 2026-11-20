# Offline maps

MeshChatX can show maps with no internet connection at all. Two local
archive formats are supported, stored in the map storage directory shown
in Map, Tools, Offline.

## MBTiles

Raster tiles in a SQLite container. Good for small regions and low zooms.
The bundled starter archive covers the whole world at low zoom.

## PMTiles

A single-file archive read through HTTP range requests, so the app only
reads the bytes it needs even from a multi-hundred-GB file. Both raster
(PNG, JPEG, WebP, AVIF) and vector (MVT) archives work. Vector archives
render with the same Protomaps light style as the online planet basemap.
Icon sprites are skipped offline and text labels degrade quietly when no
glyph data is available.

Useful sources:

- Download a regional extract or the whole planet from
  https://maps.protomaps.com or https://download.geofabrik.de derived
  builds, or build your own with the `pmtiles` CLI, for example
  `pmtiles extract planet.pmtiles region.pmtiles --bbox=24,59,32,70`.
- Keep the file under a few hundred MB for a phone, or use the full
  planet archive on a desktop.

To use one: place the `.pmtiles` file in the map storage directory (or
upload it from the Offline panel), pick it in the file list so it is
marked active, and switch on Offline Mode. The backend serves the file
through `/api/v1/map/pmtiles/<name>` with byte ranges, ETag and
Last-Modified validators, so repeat views are cheap and the name is
validated against the directory listing before any bytes are read.
