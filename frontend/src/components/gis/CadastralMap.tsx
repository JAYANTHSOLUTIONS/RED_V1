import React, { useEffect, useRef } from 'react';
import L from 'leaflet';
import 'leaflet/dist/leaflet.css';
import { CadastralVertex } from '../../utils/cadastralGeometry';
import { Maximize2, Navigation } from 'lucide-react';

export interface CadastralMapProps {
  vertices: CadastralVertex[];
  selectedVertexNumber?: number | null;
  onSelectVertex?: (vertexNumber: number) => void;
  propertyTitle?: string;
  className?: string;
}

export const CadastralMap: React.FC<CadastralMapProps> = ({
  vertices,
  selectedVertexNumber,
  onSelectVertex,
  propertyTitle = 'Property',
  className = 'h-[460px] w-full',
}) => {
  const mapContainerRef = useRef<HTMLDivElement | null>(null);
  const mapInstanceRef = useRef<L.Map | null>(null);
  const polygonLayerRef = useRef<L.Polygon | null>(null);
  const markerLayersRef = useRef<Map<number, L.Marker>>(new Map());

  // Initialize Map
  useEffect(() => {
    if (!mapContainerRef.current) return;

    if (!mapInstanceRef.current) {
      const map = L.map(mapContainerRef.current, {
        attributionControl: true,
        zoomControl: true,
      });

      L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', {
        maxZoom: 20,
        attribution: '&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a>',
      }).addTo(map);

      mapInstanceRef.current = map;
    }

    return () => {
      if (mapInstanceRef.current) {
        mapInstanceRef.current.remove();
        mapInstanceRef.current = null;
      }
    };
  }, []);

  // Update Polygon & Markers when vertices change
  useEffect(() => {
    const map = mapInstanceRef.current;
    if (!map) return;

    // Clear previous layers
    if (polygonLayerRef.current) {
      polygonLayerRef.current.remove();
      polygonLayerRef.current = null;
    }
    markerLayersRef.current.forEach((marker) => marker.remove());
    markerLayersRef.current.clear();

    if (!vertices || vertices.length < 3) {
      // If no valid polygon, set default center
      if (vertices && vertices.length > 0) {
        map.setView([vertices[0].latitude, vertices[0].longitude], 17);
      }
      return;
    }

    const latLngs: [number, number][] = vertices.map((v) => [v.latitude, v.longitude]);

    // Add Polygon Layer (Closed automatically by Leaflet polygon)
    const polygon = L.polygon(latLngs, {
      color: '#059669', // emerald-600
      fillColor: '#10b981', // emerald-500
      fillOpacity: 0.22,
      weight: 3,
      lineJoin: 'round',
    }).addTo(map);
    polygonLayerRef.current = polygon;

    // Add numbered circular markers for every vertex
    vertices.forEach((v) => {
      const isSelected = selectedVertexNumber === v.vertexNumber;

      const markerHtml = `
        <div style="
          width: 26px;
          height: 26px;
          background: ${isSelected ? '#047857' : '#ffffff'};
          color: ${isSelected ? '#ffffff' : '#065f46'};
          border: 2px solid ${isSelected ? '#10b981' : '#059669'};
          box-shadow: ${isSelected ? '0 0 12px rgba(16, 185, 129, 0.9)' : '0 2px 6px rgba(0,0,0,0.25)'};
          border-radius: 9999px;
          display: flex;
          align-items: center;
          justify-content: center;
          font-family: ui-sans-serif, system-ui, sans-serif;
          font-size: 11px;
          font-weight: 700;
          cursor: pointer;
          transform: ${isSelected ? 'scale(1.25)' : 'scale(1)'};
          transition: transform 0.15s ease, background-color 0.15s ease;
        ">
          ${v.vertexNumber}
        </div>
      `;

      const icon = L.divIcon({
        className: 'cadastral-vertex-icon',
        html: markerHtml,
        iconSize: [26, 26],
        iconAnchor: [13, 13],
      });

      const marker = L.marker([v.latitude, v.longitude], { icon }).addTo(map);

      const popupHtml = `
        <div style="font-family: ui-sans-serif, system-ui, sans-serif; padding: 4px; min-width: 170px;">
          <div style="font-size: 11px; font-weight: 800; color: #065f46; text-transform: uppercase; letter-spacing: 0.05em; margin-bottom: 4px;">
            Vertex #${v.vertexNumber}
          </div>
          <div style="font-size: 12px; font-family: monospace; color: #1f2937; margin-bottom: 2px;">
            <strong>Lat:</strong> ${v.latitude.toFixed(6)}°N
          </div>
          <div style="font-size: 12px; font-family: monospace; color: #1f2937; margin-bottom: 6px;">
            <strong>Lon:</strong> ${v.longitude.toFixed(6)}°E
          </div>
          <div style="display: flex; justify-content: space-between; align-items: center; border-top: 1px solid #e5e7eb; padding-top: 4px; font-size: 10px; color: #6b7280;">
            <span>WGS-84 Cadastral Point</span>
            <a href="https://www.google.com/maps?q=${v.latitude},${v.longitude}" target="_blank" rel="noreferrer" style="color: #2563eb; text-decoration: underline;">
              Maps ↗
            </a>
          </div>
        </div>
      `;
      marker.bindPopup(popupHtml);

      marker.on('click', () => {
        if (onSelectVertex) {
          onSelectVertex(v.vertexNumber);
        }
      });

      markerLayersRef.current.set(v.vertexNumber, marker);
    });

    // Fit map bounds to entire polygon with padding
    const bounds = polygon.getBounds();
    if (bounds.isValid()) {
      map.fitBounds(bounds, { padding: [40, 40], maxZoom: 19 });
    }
  }, [vertices, onSelectVertex]);

  // Update selected marker highlight without full redraw
  useEffect(() => {
    const map = mapInstanceRef.current;
    if (!map) return;

    markerLayersRef.current.forEach((marker, vNum) => {
      const isSelected = selectedVertexNumber === vNum;
      const v = vertices.find((item) => item.vertexNumber === vNum);
      if (!v) return;

      const markerHtml = `
        <div style="
          width: 26px;
          height: 26px;
          background: ${isSelected ? '#047857' : '#ffffff'};
          color: ${isSelected ? '#ffffff' : '#065f46'};
          border: 2px solid ${isSelected ? '#10b981' : '#059669'};
          box-shadow: ${isSelected ? '0 0 12px rgba(16, 185, 129, 0.9)' : '0 2px 6px rgba(0,0,0,0.25)'};
          border-radius: 9999px;
          display: flex;
          align-items: center;
          justify-content: center;
          font-family: ui-sans-serif, system-ui, sans-serif;
          font-size: 11px;
          font-weight: 700;
          cursor: pointer;
          transform: ${isSelected ? 'scale(1.28)' : 'scale(1)'};
          transition: transform 0.15s ease, background-color 0.15s ease;
        ">
          ${v.vertexNumber}
        </div>
      `;

      marker.setIcon(
        L.divIcon({
          className: 'cadastral-vertex-icon',
          html: markerHtml,
          iconSize: [26, 26],
          iconAnchor: [13, 13],
        })
      );

      if (isSelected) {
        marker.openPopup();
        map.panTo([v.latitude, v.longitude], { animate: true, duration: 0.5 });
      }
    });
  }, [selectedVertexNumber, vertices]);

  const handleFitBoundary = () => {
    const map = mapInstanceRef.current;
    const polygon = polygonLayerRef.current;
    if (map && polygon) {
      const bounds = polygon.getBounds();
      if (bounds.isValid()) {
        map.fitBounds(bounds, { padding: [40, 40], maxZoom: 19 });
      }
    }
  };

  return (
    <div className={`relative rounded-xl overflow-hidden border border-gray-200 dark:border-gray-800 bg-gray-100 dark:bg-gray-900 ${className}`}>
      <div ref={mapContainerRef} className="h-full w-full z-0" />

      {/* Floating Fit Boundary Control */}
      <div className="absolute top-3 right-3 z-1000 flex flex-col gap-1.5">
        <button
          type="button"
          onClick={handleFitBoundary}
          title="Fit View to Boundary"
          className="p-2 rounded-lg bg-white/95 dark:bg-gray-800/95 shadow-md border border-gray-200 dark:border-gray-700 text-gray-700 dark:text-gray-200 hover:bg-emerald-50 dark:hover:bg-emerald-950/50 hover:text-emerald-700 transition-colors flex items-center justify-center cursor-pointer"
        >
          <Maximize2 className="h-4 w-4" />
        </button>
      </div>

      {/* Overlay status when <3 points */}
      {(!vertices || vertices.length < 3) && (
        <div className="absolute inset-0 z-1000 bg-gray-50/90 dark:bg-gray-900/90 backdrop-blur-xs flex flex-col items-center justify-center p-6 text-center">
          <Navigation className="h-8 w-8 text-gray-400 mb-2 animate-pulse" />
          <p className="text-xs font-semibold text-gray-700 dark:text-gray-300">
            Insufficient boundary coordinates to render parcel polygon
          </p>
          <p className="text-[11px] text-gray-500 dark:text-gray-400 mt-0.5">
            Minimum 3 ordered WGS-84 vertices are required.
          </p>
        </div>
      )}
    </div>
  );
};
