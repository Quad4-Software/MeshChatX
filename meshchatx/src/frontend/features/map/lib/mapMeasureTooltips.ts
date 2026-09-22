// SPDX-License-Identifier: 0BSD

import Overlay from "ol/Overlay";
import { unByKey } from "ol/Observable";
import LineString from "ol/geom/LineString";
import Polygon from "ol/geom/Polygon";
import Circle from "ol/geom/Circle";
import type Geometry from "ol/geom/Geometry";
import type Feature from "ol/Feature";
import type Map from "ol/Map";
import type MapBrowserEvent from "ol/MapBrowserEvent";
import type { EventsKey } from "ol/events";
import { formatLength, formatArea } from "./mapActions.js";

export function measureOutputForGeometry(geom: Geometry): { output: string; tooltipCoord: number[] } | null {
    if (geom instanceof Polygon) {
        return {
            output: formatArea(geom),
            tooltipCoord: geom.getInteriorPoint().getCoordinates(),
        };
    }
    if (geom instanceof LineString) {
        return {
            output: formatLength(geom),
            tooltipCoord: geom.getLastCoordinate(),
        };
    }
    if (geom instanceof Circle) {
        const radius = geom.getRadius();
        const center = geom.getCenter();
        const edge = [center[0] + radius, center[1]];
        const line = new LineString([center, edge]);
        return {
            output: `Radius: ${formatLength(line)}`,
            tooltipCoord: edge,
        };
    }
    return null;
}

export class MapMeasureTooltipManager {
    private map: Map;
    private measureTooltip: Overlay | null = null;
    private measureTooltipElement: HTMLDivElement | null = null;
    private helpTooltip: Overlay | null = null;
    private helpTooltipElement: HTMLDivElement | null = null;
    private drawListenerKey: EventsKey | EventsKey[] | null = null;
    private pointerMoveHandler: ((evt: MapBrowserEvent<PointerEvent>) => void) | null = null;

    constructor(map: Map) {
        this.map = map;
    }

    createMeasureTooltip(): void {
        this.cleanupMeasureTooltip();
        this.measureTooltipElement = document.createElement("div");
        this.measureTooltipElement.className = "ol-tooltip ol-tooltip-measure";
        this.measureTooltip = new Overlay({
            element: this.measureTooltipElement,
            offset: [0, -15],
            positioning: "bottom-center",
            stopEvent: false,
            insertFirst: false,
        });
        this.measureTooltip.set("isMeasureTooltip", true);
        this.map.addOverlay(this.measureTooltip);
    }

    cleanupMeasureTooltip(): void {
        if (this.measureTooltip) {
            this.map.removeOverlay(this.measureTooltip);
            this.measureTooltip = null;
        }
        this.measureTooltipElement = null;
    }

    createHelpTooltip(): void {
        if (this.helpTooltipElement?.parentNode) {
            this.helpTooltipElement.parentNode.removeChild(this.helpTooltipElement);
        }
        this.helpTooltipElement = document.createElement("div");
        this.helpTooltipElement.className = "ol-tooltip hidden";
        this.helpTooltip = new Overlay({
            element: this.helpTooltipElement,
            offset: [15, 0],
            positioning: "center-left",
        });
        this.map.addOverlay(this.helpTooltip);
    }

    cleanupHelpTooltip(): void {
        if (this.helpTooltip) {
            this.map.removeOverlay(this.helpTooltip);
            this.helpTooltip = null;
        }
        this.helpTooltipElement = null;
    }

    attachDrawMeasureListener(sketch: Feature): void {
        this.cleanupDrawListener();
        this.createMeasureTooltip();
        const geom = sketch.getGeometry();
        if (!geom) return;
        this.drawListenerKey = geom.on("change", (e) => {
            const target = (e as { target?: Geometry }).target;
            if (!target) return;
            const result = measureOutputForGeometry(target);
            if (result && this.measureTooltipElement && this.measureTooltip) {
                this.measureTooltipElement.innerHTML = result.output;
                this.measureTooltip.setPosition(result.tooltipCoord);
            }
        });
    }

    cleanupDrawListener(): void {
        if (this.drawListenerKey) {
            unByKey(this.drawListenerKey);
            this.drawListenerKey = null;
        }
    }

    enablePointerHelp(onSketch: () => boolean): void {
        this.createHelpTooltip();
        this.pointerMoveHandler = (evt) => {
            if (evt.dragging || !this.helpTooltipElement || !this.helpTooltip) return;
            let helpMsg = "Click to start drawing";
            if (onSketch()) {
                helpMsg = "Click to continue drawing, double-click to finish";
            }
            this.helpTooltipElement.innerHTML = helpMsg;
            this.helpTooltip.setPosition(evt.coordinate);
            this.helpTooltipElement.classList.remove("hidden");
        };
        this.map.on("pointermove", this.pointerMoveHandler as any);
    }

    disablePointerHelp(): void {
        if (this.pointerMoveHandler) {
            this.map.un("pointermove", this.pointerMoveHandler as any);
            this.pointerMoveHandler = null;
        }
        this.cleanupHelpTooltip();
    }

    finalizeStaticTooltip(): void {
        if (this.measureTooltipElement) {
            this.measureTooltipElement.className = "ol-tooltip ol-tooltip-static";
            if (this.measureTooltip) {
                this.measureTooltip.setOffset([0, -7]);
            }
        }
        this.measureTooltipElement = null;
        this.measureTooltip = null;
        this.createMeasureTooltip();
    }

    updateLiveMeasure(geom: Geometry, coord: number[]): void {
        const result = measureOutputForGeometry(geom);
        if (!result) return;
        if (!this.measureTooltipElement || !this.measureTooltip) {
            this.createMeasureTooltip();
        }
        if (this.measureTooltipElement && this.measureTooltip) {
            this.measureTooltipElement.className = "ol-tooltip ol-tooltip-measure";
            this.measureTooltipElement.innerHTML = result.output;
            this.measureTooltip.setPosition(coord);
        }
    }

    setMeasureHtml(html: string, coord: number[]): void {
        if (!this.measureTooltipElement || !this.measureTooltip) {
            this.createMeasureTooltip();
        }
        if (this.measureTooltipElement && this.measureTooltip) {
            this.measureTooltipElement.className = "ol-tooltip ol-tooltip-measure";
            this.measureTooltipElement.innerHTML = html;
            this.measureTooltip.setPosition(coord);
        }
    }

    destroy(): void {
        this.cleanupDrawListener();
        this.disablePointerHelp();
        this.cleanupMeasureTooltip();
    }
}
