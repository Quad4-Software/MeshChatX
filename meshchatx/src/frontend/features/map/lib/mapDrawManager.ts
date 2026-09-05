// SPDX-License-Identifier: 0BSD

import type OlMap from "ol/Map.js";
import type VectorSource from "ol/source/Vector.js";
import Draw, { createBox } from "ol/interaction/Draw.js";
import Modify from "ol/interaction/Modify.js";
import Select from "ol/interaction/Select.js";
import Snap from "ol/interaction/Snap.js";
import Translate from "ol/interaction/Translate.js";

export interface DrawManagerConfig {
    map: OlMap;
    drawSource: VectorSource;
    onDrawEnd?: (feature: any) => void;
    onSelectFeature?: (feature: any) => void;
}

export class MapDrawManager {
    private map: OlMap;
    private drawSource: VectorSource;
    private currentDraw: Draw | null = null;
    private modify: Modify | null = null;
    private select: Select | null = null;
    private snap: Snap | null = null;
    private translate: Translate | null = null;
    private onDrawEndCallback?: (feature: any) => void;
    private onSelectFeatureCallback?: (feature: any) => void;

    constructor(config: DrawManagerConfig) {
        this.map = config.map;
        this.drawSource = config.drawSource;
        this.onDrawEndCallback = config.onDrawEnd;
        this.onSelectFeatureCallback = config.onSelectFeature;

        this.setupSelectAndModify();
    }

    private setupSelectAndModify() {
        this.select = new Select({
            layers: (layer) => layer.getZIndex() === 10,
        });
        this.select.on("select", (e: any) => {
            const selected = e.selected && e.selected[0];
            this.onSelectFeatureCallback?.(selected || null);
        });

        this.modify = new Modify({
            features: this.select.getFeatures(),
        });

        this.translate = new Translate({
            features: this.select.getFeatures(),
        });

        this.snap = new Snap({
            source: this.drawSource,
        });

        this.map.addInteraction(this.select);
        this.map.addInteraction(this.modify);
        this.map.addInteraction(this.translate);
        this.map.addInteraction(this.snap);
    }

    public setMode(mode: string) {
        if (this.currentDraw) {
            this.map.removeInteraction(this.currentDraw);
            this.currentDraw = null;
        }

        if (mode === "select" || mode === "pointer" || mode === "none") {
            this.select?.setActive(true);
            this.modify?.setActive(true);
            this.translate?.setActive(true);
            return;
        }

        this.select?.setActive(false);
        this.modify?.setActive(false);
        this.translate?.setActive(false);

        let drawType: any = "Point";
        let geometryFunction: any = undefined;

        if (mode === "point" || mode === "note") {
            drawType = "Point";
        } else if (mode === "line" || mode === "bearing") {
            drawType = "LineString";
        } else if (mode === "polygon") {
            drawType = "Polygon";
        } else if (mode === "circle") {
            drawType = "Circle";
        } else if (mode === "box") {
            drawType = "Circle";
            geometryFunction = createBox();
        }

        this.currentDraw = new Draw({
            source: this.drawSource,
            type: drawType,
            geometryFunction,
        });

        this.currentDraw.on("drawend", (e: any) => {
            if (mode === "note") {
                e.feature.set("isNote", true);
            }
            this.onDrawEndCallback?.(e.feature);
        });

        this.map.addInteraction(this.currentDraw);
    }

    public clearSelection() {
        this.select?.getFeatures().clear();
    }

    public getSelectedFeatures(): any[] {
        return this.select?.getFeatures().getArray() || [];
    }

    public destroy() {
        if (this.currentDraw) this.map.removeInteraction(this.currentDraw);
        if (this.modify) this.map.removeInteraction(this.modify);
        if (this.select) this.map.removeInteraction(this.select);
        if (this.snap) this.map.removeInteraction(this.snap);
        if (this.translate) this.map.removeInteraction(this.translate);
    }
}
