import { useEffect, useRef } from "react";
import L, { type LatLngExpression, type LeafletMouseEvent } from "leaflet";
import {
  CircleMarker,
  MapContainer,
  Marker,
  Polygon,
  Polyline,
  TileLayer,
  useMap,
  useMapEvents,
} from "react-leaflet";
import "leaflet/dist/leaflet.css";

const INDIA_CENTER: [number, number] = [20.5937, 78.9629];
const DEFAULT_ZOOM = 5;
const LOCATION_ZOOM = 16;

type PositionTuple = [number, number];

const PIN_ICON = L.divIcon({
  className: "annadata-pin",
  html: `<svg width="34" height="44" viewBox="0 0 34 44" fill="none" xmlns="http://www.w3.org/2000/svg">
    <path d="M17 2C9.27 2 3 8.27 3 16c0 10.7 11.9 25.3 13.5 27.1.48.58 1.52.58 2 0 1.6-1.8 13.5-16.4 13.5-27.1C31 8.27 24.73 2 17 2Z" fill="#047857" stroke="#065f46" stroke-width="1.5"/>
    <circle cx="17" cy="15.5" r="6.5" fill="#ffffff"/>
    <circle cx="17" cy="15.5" r="3.2" fill="#059669"/>
  </svg>`,
  iconSize: [34, 44],
  iconAnchor: [17, 42],
  popupAnchor: [0, -40],
});

interface FieldMapProps {
  position?: PositionTuple | null;
  onPositionChange?: (pos: PositionTuple) => void;
  positionDraggable?: boolean;
  drawMode?: boolean;
  drawingPoints?: PositionTuple[];
  onDrawingPointAdd?: (pos: PositionTuple) => void;
  onDrawingPointRemove?: (index: number) => void;
  onDrawingClear?: () => void;
  polygon?: PositionTuple[];
  heightClass?: string;
  zoomControl?: boolean;
}

function ClickCatcher({
  onPositionChange,
  drawMode,
  onDrawingPointAdd,
}: {
  onPositionChange?: (pos: PositionTuple) => void;
  drawMode?: boolean;
  onDrawingPointAdd?: (pos: PositionTuple) => void;
}) {
  useMapEvents({
    click(event: LeafletMouseEvent) {
      const pos: PositionTuple = [event.latlng.lat, event.latlng.lng];
      if (drawMode && onDrawingPointAdd) {
        onDrawingPointAdd(pos);
      } else if (onPositionChange) {
        onPositionChange(pos);
      }
    },
  });
  return null;
}

function PanTo({ position }: { position?: PositionTuple | null }) {
  const map = useMap();
  useEffect(() => {
    if (position) map.panTo(position);
  }, [map, position]);
  return null;
}

export default function FieldMap({
  position,
  onPositionChange,
  positionDraggable = false,
  drawMode = false,
  drawingPoints = [],
  onDrawingPointAdd,
  onDrawingPointRemove,
  onDrawingClear,
  polygon,
  heightClass = "h-[380px]",
  zoomControl = true,
}: FieldMapProps) {
  const markerRef = useRef<L.Marker | null>(null);

  const center: LatLngExpression = position ?? INDIA_CENTER;
  const zoom = position ? LOCATION_ZOOM : DEFAULT_ZOOM;

  return (
    <div className={`${heightClass} w-full overflow-hidden rounded-xl border border-gray-200`}>
      <MapContainer center={center} zoom={zoom} zoomControl={zoomControl} scrollWheelZoom>
        <TileLayer
          attribution='&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors'
          url="https://tile.openstreetmap.org/{z}/{x}/{y}.png"
        />
        <ClickCatcher
          onPositionChange={onPositionChange}
          drawMode={drawMode}
          onDrawingPointAdd={onDrawingPointAdd}
        />
        <PanTo position={position} />

        {position && (
          <Marker
            position={position}
            icon={PIN_ICON}
            draggable={positionDraggable}
            ref={(instance) => {
              markerRef.current = instance ?? null;
            }}
            eventHandlers={{
              dragend: () => {
                const latlng = markerRef.current?.getLatLng();
                if (latlng && onPositionChange) {
                  onPositionChange([latlng.lat, latlng.lng]);
                }
              },
            }}
          />
        )}

        {polygon && polygon.length >= 3 && (
          <Polygon positions={polygon} pathOptions={{ color: "#047857", fillOpacity: 0.18 }} />
        )}

        {drawingPoints && drawingPoints.length > 0 && (
          <>
            <Polyline
              positions={drawingPoints}
              pathOptions={{ color: "#047857", dashArray: "5 6", weight: 2 }}
            />
            {drawingPoints.length >= 3 && (
              <Polygon
                positions={[...drawingPoints, drawingPoints[0]]}
                pathOptions={{ color: "#065f46", fillColor: "#047857", fillOpacity: 0.18 }}
              />
            )}
            {drawingPoints.map((point, index) => (
              <CircleMarker
                key={`${point[0]}-${point[1]}-${index}`}
                center={point}
                radius={6}
                pathOptions={{
                  color: "#065f46",
                  fillColor: "#ffffff",
                  fillOpacity: 1,
                  weight: 2,
                }}
                eventHandlers={{
                  click: () => onDrawingPointRemove?.(index),
                }}
              />
            ))}
          </>
        )}
      </MapContainer>
      {drawMode && drawingPoints.length > 0 && (
        <div className="pointer-events-none relative z-[500] -mt-11 mr-2 flex justify-end gap-1">
          <button
            type="button"
            onClick={() => onDrawingPointRemove?.(drawingPoints.length - 1)}
            className="pointer-events-auto rounded-md bg-white px-2.5 py-1.5 text-xs font-medium text-gray-700 shadow ring-1 ring-gray-200 hover:bg-gray-50"
          >
            Undo last point
          </button>
          <button
            type="button"
            onClick={onDrawingClear}
            className="pointer-events-auto rounded-md bg-white px-2.5 py-1.5 text-xs font-medium text-red-600 shadow ring-1 ring-gray-200 hover:bg-red-50"
          >
            Clear
          </button>
        </div>
      )}
    </div>
  );
}

// Re-export so consumers never import leaflet position types by hand.
export type { PositionTuple };