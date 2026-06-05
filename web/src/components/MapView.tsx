import { useEffect, useRef } from "react";
import L from "leaflet";
import "leaflet/dist/leaflet.css";
import type { Flat } from "../api";
import { discountPct, formatKzt } from "../format";

type Props = {
  items: Flat[];
  onSelect: (flat: Flat) => void;
};

function priceLabel(price: number): string {
  const mln = price / 1_000_000;
  return `${mln >= 100 ? Math.round(mln) : mln.toFixed(1)} млн ₸`;
}

/**
 * Interactive Leaflet map of catalog objects.
 *
 * Base layers:
 *  - Esri World Imagery (satellite) — default
 *  - OpenStreetMap (street) — switchable via the layer control
 *
 * Each flat is a price-pill marker; clicking opens the object. Markers whose
 * coordinates are approximate (geo_precise === false) are shown hollow.
 */
export default function MapView({ items, onSelect }: Props) {
  const containerRef = useRef<HTMLDivElement | null>(null);
  const mapRef = useRef<L.Map | null>(null);
  const layerRef = useRef<L.LayerGroup | null>(null);
  const onSelectRef = useRef(onSelect);
  onSelectRef.current = onSelect;

  // Init map once.
  useEffect(() => {
    if (mapRef.current || !containerRef.current) return;

    const satellite = L.tileLayer(
      "https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{z}/{y}/{x}",
      {
        maxZoom: 19,
        attribution:
          "Tiles &copy; Esri — Source: Esri, Maxar, Earthstar Geographics, and the GIS User Community",
      },
    );
    const osm = L.tileLayer("https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png", {
      maxZoom: 19,
      attribution: "&copy; OpenStreetMap contributors",
    });

    const map = L.map(containerRef.current, {
      center: [48.0, 67.0],
      zoom: 5,
      layers: [satellite],
      scrollWheelZoom: true,
    });
    L.control
      .layers(
        { "Спутник (Esri)": satellite, "Схема (OpenStreetMap)": osm },
        {},
        { position: "topright", collapsed: false },
      )
      .addTo(map);

    layerRef.current = L.layerGroup().addTo(map);
    mapRef.current = map;

    return () => {
      map.remove();
      mapRef.current = null;
      layerRef.current = null;
    };
  }, []);

  // Update markers when items change.
  useEffect(() => {
    const map = mapRef.current;
    const group = layerRef.current;
    if (!map || !group) return;
    group.clearLayers();

    const pts: L.LatLngExpression[] = [];
    items.forEach((f) => {
      if (typeof f.lat !== "number" || typeof f.lng !== "number") return;
      const disc = discountPct(f.bank_price, f.market_price);
      const approx = f.geo_precise === false;
      const icon = L.divIcon({
        className: "",
        html: `<div class="lmark${approx ? " lmark-approx" : ""}">${priceLabel(
          f.bank_price,
        )}<span class="lmark-disc">-${disc}%</span></div>`,
        iconSize: [0, 0],
        iconAnchor: [0, 0],
      });
      const m = L.marker([f.lat, f.lng], { icon });
      const photo = f.photo
        ? `<img src="${f.photo}" alt="" style="width:100%;height:96px;object-fit:cover;border-radius:8px;margin-bottom:6px"/>`
        : "";
      m.bindPopup(
        `<div style="min-width:180px">${photo}` +
          `<strong>${formatKzt(f.bank_price)}</strong><br/>` +
          `<span style="color:#475569">${f.rooms} комн · ${f.area} м² · -${disc}%</span><br/>` +
          `<span style="color:#475569">${f.address}</span>` +
          `${approx ? '<br/><em style="color:#b45309">координаты приблизительные</em>' : ""}` +
          `</div>`,
      );
      m.on("click", () => onSelectRef.current(f));
      m.addTo(group);
      pts.push([f.lat, f.lng]);
    });

    if (pts.length) {
      map.fitBounds(L.latLngBounds(pts), { padding: [40, 40], maxZoom: 13 });
    }
  }, [items]);

  return (
    <div className="mapwrap">
      <div
        ref={containerRef}
        className="leaflet-map"
        role="application"
        aria-label="Карта залоговых объектов"
      />
      <p className="muted">
        Объектов на карте: {items.length} · базовый слой: спутник Esri, дополнительный —
        OpenStreetMap
      </p>
    </div>
  );
}
