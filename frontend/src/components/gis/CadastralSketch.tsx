import React, { useMemo, useState, useRef } from 'react';
import {
  CadastralVertex,
  projectToSvg,
  calculateCadastralMetrics,
  CadastralMetrics,
} from '../../utils/cadastralGeometry';
import {
  Compass,
  Download,
  Printer,
  Ruler,
  Layers,
  Check,
  AlertTriangle,
  Image as ImageIcon,
} from 'lucide-react';

export interface CadastralSketchProps {
  vertices: CadastralVertex[];
  propertyTitle?: string;
  surveyNumber?: string;
  subdivision?: string;
  village?: string;
  taluk?: string;
  district?: string;
  officialAreaHectares?: string;
  officialAreaAres?: string;
  officialLandType?: string;
  selectedVertexNumber?: number | null;
  onSelectVertex?: (vertexNumber: number) => void;
  className?: string;
}

export const CadastralSketch: React.FC<CadastralSketchProps> = ({
  vertices,
  propertyTitle = 'Cadastral Parcel',
  surveyNumber,
  subdivision,
  village,
  taluk,
  district,
  officialAreaHectares,
  officialAreaAres,
  officialLandType,
  selectedVertexNumber,
  onSelectVertex,
  className = '',
}) => {
  const [showDimensions, setShowDimensions] = useState<boolean>(false);
  const [showVertexLabels, setShowVertexLabels] = useState<boolean>(true);
  const [exporting, setExporting] = useState<boolean>(false);
  const sketchContainerRef = useRef<HTMLDivElement | null>(null);

  // SVG Drawing Dimensions
  const svgWidth = 840;
  const svgHeight = 580;
  const svgPadding = 80;

  // Project vertices to conformal local 2D SVG space
  const projection = useMemo(() => {
    return projectToSvg(vertices, svgWidth, svgHeight, svgPadding);
  }, [vertices, svgWidth, svgHeight, svgPadding]);

  // Calculate high-precision geodesic metrics
  const metrics: CadastralMetrics = useMemo(() => {
    return calculateCadastralMetrics(vertices);
  }, [vertices]);

  // Compute Official Area if available
  const officialAreaDisplay = useMemo(() => {
    const h = parseFloat(officialAreaHectares || '0');
    const a = parseFloat(officialAreaAres || '0');
    if (h > 0 || a > 0) {
      const totalAres = h * 100 + a;
      const sqMeters = totalAres * 100;
      const acres = totalAres / 40.4686;
      return `${h} Ha, ${a} Ares (${sqMeters.toLocaleString('en-IN')} m² / ${acres.toFixed(2)} Acres)`;
    }
    return null;
  }, [officialAreaHectares, officialAreaAres]);

  // Compute graphic scale bar length in meters & pixels
  const scaleBarInfo = useMemo(() => {
    const metersPerPixel = projection.scaleMetersPerPixel;
    // Aim for a scale bar around 80px to 140px on screen
    const targetMeters = metersPerPixel * 100;
    // Pick clean rounded meter intervals (5, 10, 20, 50, 100, 200, 500)
    const intervals = [1, 2, 5, 10, 20, 25, 50, 100, 200, 500, 1000];
    let chosenMeters = intervals[0];
    for (const step of intervals) {
      if (step >= targetMeters * 0.7) {
        chosenMeters = step;
        break;
      }
    }
    const pixelWidth = chosenMeters / metersPerPixel;
    return {
      meters: chosenMeters,
      pixelWidth: Math.max(pixelWidth, 40),
    };
  }, [projection.scaleMetersPerPixel]);

  // Export / Print Sketch Function (Prints ONLY the cadastral sketch sheet)
  const handlePrintSketch = () => {
    const sketchElement = sketchContainerRef.current || document.getElementById('cadastral-sketch-sheet');
    if (!sketchElement) {
      window.print();
      return;
    }

    const printWindow = window.open('', '_blank', 'width=980,height=820');
    if (!printWindow) {
      window.print();
      return;
    }

    const styles = Array.from(document.querySelectorAll('style, link[rel="stylesheet"]'))
      .map((s) => s.outerHTML)
      .join('\n');

    printWindow.document.write(`
      <!DOCTYPE html>
      <html>
        <head>
          <title>Cadastral Boundary Sketch - ${surveyNumber || propertyTitle}</title>
          ${styles}
          <style>
            body {
              background: #ffffff !important;
              margin: 0;
              padding: 24px;
              color: #111827;
              font-family: ui-sans-serif, system-ui, -apple-system, sans-serif;
            }
            #cadastral-sketch-sheet {
              border: 1px solid #d1d5db !important;
              box-shadow: none !important;
              padding: 24px !important;
              max-width: 900px;
              margin: 0 auto;
              background: #ffffff !important;
            }
            @media print {
              body { padding: 0; }
              #cadastral-sketch-sheet { border: none !important; padding: 0 !important; }
            }
          </style>
        </head>
        <body>
          <div id="cadastral-sketch-sheet">
            ${sketchElement.innerHTML}
          </div>
          <script>
            setTimeout(() => {
              window.print();
              window.close();
            }, 350);
          </script>
        </body>
      </html>
    `);
    printWindow.document.close();
  };

  // Export High-Res PNG Image
  const handleDownloadPng = () => {
    const svgEl = sketchContainerRef.current?.querySelector('svg');
    if (!svgEl) return;

    const serializer = new XMLSerializer();
    const svgString = serializer.serializeToString(svgEl);
    const svgBlob = new Blob([svgString], { type: 'image/svg+xml;charset=utf-8' });
    const URL = window.URL || window.webkitURL || window;
    const blobURL = URL.createObjectURL(svgBlob);

    const image = new Image();
    image.onload = () => {
      const canvas = document.createElement('canvas');
      canvas.width = svgWidth * 2;
      canvas.height = svgHeight * 2;
      const context = canvas.getContext('2d');
      if (context) {
        context.fillStyle = '#ffffff';
        context.fillRect(0, 0, canvas.width, canvas.height);
        context.drawImage(image, 0, 0, canvas.width, canvas.height);

        const pngUrl = canvas.toDataURL('image/png');
        const a = document.createElement('a');
        a.href = pngUrl;
        a.download = `cadastral_sketch_${surveyNumber || 'parcel'}.png`;
        document.body.appendChild(a);
        a.click();
        document.body.removeChild(a);
      }
      URL.revokeObjectURL(blobURL);
    };
    image.src = blobURL;
  };

  // Export SVG file
  const handleDownloadSvg = () => {
    const svgEl = sketchContainerRef.current?.querySelector('svg');
    if (!svgEl) return;

    const serializer = new XMLSerializer();
    const source = serializer.serializeToString(svgEl);
    const blob = new Blob([source], { type: 'image/svg+xml;charset=utf-8' });
    const url = URL.createObjectURL(blob);

    const a = document.createElement('a');
    a.href = url;
    a.download = `cadastral_sketch_${surveyNumber || 'parcel'}.svg`;
    document.body.appendChild(a);
    a.click();
    document.body.removeChild(a);
    URL.revokeObjectURL(url);
  };

  if (vertices.length < 3) {
    return (
      <div className="p-8 text-center bg-gray-50 dark:bg-gray-900 border border-gray-200 dark:border-gray-800 rounded-xl space-y-2">
        <AlertTriangle className="h-8 w-8 text-amber-500 mx-auto" />
        <h4 className="text-xs font-bold text-gray-700 dark:text-gray-300">
          Cannot Generate Cadastral Sketch
        </h4>
        <p className="text-[11px] text-gray-500 dark:text-gray-400 max-w-sm mx-auto">
          A minimum of 3 valid ordered coordinates are required to form a closed survey polygon.
        </p>
      </div>
    );
  }

  const generatedDateStr = new Date().toLocaleDateString('en-IN', {
    day: '2-digit',
    month: 'short',
    year: 'numeric',
    hour: '2-digit',
    minute: '2-digit',
  });

  return (
    <div className={`space-y-4 ${className}`}>
      {/* ACTION TOOLBAR */}
      <div className="flex flex-wrap items-center justify-between gap-3 p-3 bg-gray-50 dark:bg-gray-800/80 rounded-xl border border-gray-200 dark:border-gray-700 text-xs no-print">
        <div className="flex flex-wrap items-center gap-2">
          {/* Toggle Dimensions */}
          <button
            type="button"
            onClick={() => setShowDimensions(!showDimensions)}
            className={`px-3 py-1.5 rounded-lg border font-medium transition-colors flex items-center gap-1.5 cursor-pointer ${
              showDimensions
                ? 'bg-emerald-600 border-emerald-600 text-white'
                : 'bg-white dark:bg-gray-800 border-gray-300 dark:border-gray-600 text-gray-700 dark:text-gray-200 hover:bg-gray-100'
            }`}
          >
            <Ruler className="h-3.5 w-3.5" />
            <span>Dimensions ({showDimensions ? 'ON' : 'OFF'})</span>
          </button>

          {/* Toggle Vertex Labels */}
          <button
            type="button"
            onClick={() => setShowVertexLabels(!showVertexLabels)}
            className={`px-3 py-1.5 rounded-lg border font-medium transition-colors flex items-center gap-1.5 cursor-pointer ${
              showVertexLabels
                ? 'bg-emerald-600 border-emerald-600 text-white'
                : 'bg-white dark:bg-gray-800 border-gray-300 dark:border-gray-600 text-gray-700 dark:text-gray-200 hover:bg-gray-100'
            }`}
          >
            <Layers className="h-3.5 w-3.5" />
            <span>Vertex Labels ({showVertexLabels ? 'ON' : 'OFF'})</span>
          </button>
        </div>

        {/* Export / Print Actions */}
        <div className="flex items-center gap-2">
          <button
            type="button"
            onClick={handleDownloadSvg}
            title="Download Vector SVG"
            className="px-3 py-1.5 rounded-lg bg-white dark:bg-gray-800 border border-gray-300 dark:border-gray-600 text-gray-700 dark:text-gray-200 hover:bg-emerald-50 hover:text-emerald-700 hover:border-emerald-300 transition-colors flex items-center gap-1.5 font-medium cursor-pointer"
          >
            <Download className="h-3.5 w-3.5" />
            <span>SVG</span>
          </button>

          <button
            type="button"
            onClick={handleDownloadPng}
            title="Download PNG Image of Sketch"
            className="px-3 py-1.5 rounded-lg bg-white dark:bg-gray-800 border border-gray-300 dark:border-gray-600 text-gray-700 dark:text-gray-200 hover:bg-emerald-50 hover:text-emerald-700 hover:border-emerald-300 transition-colors flex items-center gap-1.5 font-medium cursor-pointer"
          >
            <ImageIcon className="h-3.5 w-3.5 text-blue-600" />
            <span>Download PNG</span>
          </button>

          <button
            type="button"
            onClick={handlePrintSketch}
            title="Print ONLY the Cadastral Sketch Sheet (PDF / Printer)"
            className="px-3.5 py-1.5 rounded-lg bg-emerald-600 hover:bg-emerald-700 text-white transition-colors flex items-center gap-1.5 font-bold cursor-pointer shadow-xs"
          >
            <Printer className="h-3.5 w-3.5" />
            <span>Print Sketch Only</span>
          </button>
        </div>
      </div>

      {/* CADASTRAL SKETCH SHEET (PRINTABLE CONTAINER) */}
      <div
        ref={sketchContainerRef}
        id="cadastral-sketch-sheet"
        className="p-6 bg-white dark:bg-gray-950 border border-gray-300 dark:border-gray-800 rounded-2xl shadow-xs space-y-4 print:p-0 print:border-0 print:shadow-none"
      >
        {/* OFFICIAL-GRADE CADASTRAL HEADER */}
        <div className="pb-4 border-b-2 border-emerald-800/80 dark:border-emerald-700 flex flex-col md:flex-row md:items-start md:justify-between gap-4">
          <div className="space-y-1">
            <div className="flex items-center gap-2">
              <span className="font-serif text-lg font-extrabold text-emerald-950 dark:text-emerald-300 tracking-wide uppercase">
                RED REAL ESTATE CONSULTANCY
              </span>
              <span className="text-[10px] px-2 py-0.5 rounded-sm bg-emerald-100 dark:bg-emerald-900/60 text-emerald-800 dark:text-emerald-300 font-mono font-bold">
                WGS-84 / EPSG:4326
              </span>
            </div>
            <h3 className="text-base font-bold text-gray-900 dark:text-gray-100 tracking-tight">
              CADASTRAL PROPERTY BOUNDARY SKETCH
            </h3>
            <p className="text-xs text-gray-600 dark:text-gray-400">
              Parcel: <strong>{propertyTitle}</strong>
              {surveyNumber && (
                <span>
                  {' '}
                  | Survey No: <strong>{surveyNumber}</strong>
                  {subdivision ? `/${subdivision}` : ''}
                </span>
              )}
            </p>
          </div>

          <div className="text-right text-xs space-y-0.5 text-gray-600 dark:text-gray-400 font-mono">
            {village && <div>Village: <span className="font-sans font-semibold text-gray-900 dark:text-gray-100">{village}</span></div>}
            {taluk && <div>Taluk: <span className="font-sans font-semibold text-gray-900 dark:text-gray-100">{taluk}</span></div>}
            {district && <div>District: <span className="font-sans font-semibold text-gray-900 dark:text-gray-100">{district}</span></div>}
            <div className="text-[10px] text-gray-400 mt-1">Generated: {generatedDateStr}</div>
          </div>
        </div>

        {/* METRICS SUMMARY BAR */}
        <div className="grid grid-cols-2 sm:grid-cols-4 gap-3 p-3.5 bg-emerald-50/50 dark:bg-emerald-950/20 border border-emerald-200/80 dark:border-emerald-800/60 rounded-xl text-xs">
          <div>
            <span className="text-[10px] text-emerald-800 dark:text-emerald-300 font-medium block">
              Calculated Geodesic Area
            </span>
            <div className="font-mono font-bold text-emerald-950 dark:text-emerald-100 text-sm mt-0.5">
              {metrics.areaSqMeters.toLocaleString('en-IN')} m²
            </div>
            <span className="text-[10px] text-gray-500 dark:text-gray-400 font-mono">
              {metrics.areaAcres} Acres ({metrics.areaCents} Cents)
            </span>
          </div>

          <div>
            <span className="text-[10px] text-emerald-800 dark:text-emerald-300 font-medium block">
              Boundary Perimeter
            </span>
            <div className="font-mono font-bold text-emerald-950 dark:text-emerald-100 text-sm mt-0.5">
              {metrics.perimeterMeters} meters
            </div>
            <span className="text-[10px] text-gray-500 dark:text-gray-400 font-mono">
              ~{metrics.perimeterFeet} feet
            </span>
          </div>

          <div>
            <span className="text-[10px] text-gray-600 dark:text-gray-400 font-medium block">
              Official Recorded Area
            </span>
            <div className="font-bold text-gray-900 dark:text-gray-100 text-xs mt-0.5">
              {officialAreaDisplay || 'Refer Patta / A-Reg'}
            </div>
            {officialLandType && (
              <span className="text-[10px] text-gray-500 dark:text-gray-400 block truncate">
                {officialLandType}
              </span>
            )}
          </div>

          <div>
            <span className="text-[10px] text-gray-600 dark:text-gray-400 font-medium block">
              Cadastral Boundary Polygon
            </span>
            <div className="font-mono font-bold text-emerald-800 dark:text-emerald-300 text-sm mt-0.5">
              {vertices.length} Vertices
            </div>
            <span className="text-[10px] text-emerald-600 dark:text-emerald-400 font-medium">
              Closed Polygon V₁→Vₙ→V₁
            </span>
          </div>
        </div>

        {/* DYNAMIC SVG CANVAS */}
        <div className="relative border border-gray-200 dark:border-gray-800 rounded-xl bg-slate-50/70 dark:bg-gray-900/60 overflow-hidden flex items-center justify-center p-2">
          <svg
            viewBox={projection.viewBox}
            className="w-full h-auto max-h-[560px] select-none"
            style={{ shapeRendering: 'geometricPrecision' }}
          >
            <defs>
              {/* Subtle grid pattern for cadastral drafting aesthetics */}
              <pattern id="cadastralGrid" width="40" height="40" patternUnits="userSpaceOnUse">
                <path d="M 40 0 L 0 0 0 40" fill="none" stroke="rgba(16, 185, 129, 0.05)" strokeWidth="1" />
              </pattern>
            </defs>

            {/* Background Grid */}
            <rect width={svgWidth} height={svgHeight} fill="url(#cadastralGrid)" />

            {/* Closed Polygon Body */}
            <path
              d={projection.pathData}
              fill="rgba(16, 185, 129, 0.16)"
              stroke="#047857"
              strokeWidth="2.5"
              strokeLinejoin="round"
              strokeLinecap="round"
            />

            {/* Segment Dimensions (Lengths in meters) */}
            {showDimensions &&
              projection.segments.map((seg, idx) => {
                // If many vertices (>20), only show dimensions for longer segments or alternate to avoid clutter
                if (projection.segments.length > 20 && seg.lengthMeters < 5 && idx % 2 !== 0) {
                  return null;
                }
                return (
                  <g key={`dim-${seg.fromVertex}-${seg.toVertex}`}>
                    <rect
                      x={seg.midpointSvg.x - 22}
                      y={seg.midpointSvg.y - 8}
                      width="44"
                      height="16"
                      rx="3"
                      fill="#ffffff"
                      stroke="#10b981"
                      strokeWidth="0.8"
                      className="dark:fill-gray-900"
                    />
                    <text
                      x={seg.midpointSvg.x}
                      y={seg.midpointSvg.y + 3.5}
                      textAnchor="middle"
                      fontSize="9"
                      fontFamily="ui-monospace, monospace"
                      fontWeight="600"
                      fill="#065f46"
                      className="dark:fill-emerald-300"
                    >
                      {seg.lengthMeters}m
                    </text>
                  </g>
                );
              })}

            {/* Vertex Nodes and Labels */}
            {projection.svgPoints.map((pt) => {
              const isSelected = selectedVertexNumber === pt.vertexNumber;
              const radius = isSelected ? 8 : 5;

              return (
                <g
                  key={`v-${pt.vertexNumber}`}
                  onClick={() => onSelectVertex && onSelectVertex(pt.vertexNumber)}
                  className="cursor-pointer group"
                >
                  {/* Outer selection ring */}
                  {isSelected && (
                    <circle
                      cx={pt.x}
                      cy={pt.y}
                      r="14"
                      fill="none"
                      stroke="#10b981"
                      strokeWidth="2"
                      strokeDasharray="3 3"
                      className="animate-pulse"
                    />
                  )}

                  {/* Vertex Center Dot */}
                  <circle
                    cx={pt.x}
                    cy={pt.y}
                    r={radius}
                    fill={isSelected ? '#047857' : '#ffffff'}
                    stroke={isSelected ? '#10b981' : '#059669'}
                    strokeWidth="2"
                    className="transition-transform group-hover:scale-125"
                  />

                  {/* Vertex Number Badge/Text */}
                  {showVertexLabels && (
                    <g transform={`translate(${pt.x + 8}, ${pt.y - 8})`}>
                      <rect
                        x="-3"
                        y="-10"
                        width="18"
                        height="13"
                        rx="2"
                        fill={isSelected ? '#047857' : 'rgba(255, 255, 255, 0.95)'}
                        stroke={isSelected ? '#10b981' : '#059669'}
                        strokeWidth="0.8"
                        className="dark:fill-gray-900"
                      />
                      <text
                        x="6"
                        y="-1"
                        textAnchor="middle"
                        fontSize="8.5"
                        fontFamily="ui-sans-serif, system-ui, sans-serif"
                        fontWeight="bold"
                        fill={isSelected ? '#ffffff' : '#065f46'}
                        className="dark:fill-emerald-300"
                      >
                        {pt.vertexNumber}
                      </text>
                    </g>
                  )}
                </g>
              );
            })}

            {/* PROFESSIONAL NORTH ARROW (Top Right) */}
            <g transform="translate(770, 65)">
              <circle cx="0" cy="0" r="22" fill="#ffffff" stroke="#059669" strokeWidth="1.5" className="dark:fill-gray-900" />
              {/* North Pointer Needle */}
              <polygon points="0,-16 6,4 0,0" fill="#047857" />
              <polygon points="0,-16 -6,4 0,0" fill="#059669" />
              {/* South Pointer */}
              <polygon points="0,16 5,-1 0,0" fill="#d1d5db" />
              <polygon points="0,16 -5,-1 0,0" fill="#9ca3af" />
              <circle cx="0" cy="0" r="2" fill="#ffffff" />
              <text x="0" y="-19" textAnchor="middle" fontSize="10" fontWeight="900" fontFamily="sans-serif" fill="#047857">
                N
              </text>
            </g>

            {/* GRAPHIC SCALE BAR (Bottom Left) */}
            <g transform="translate(45, 545)">
              <rect x="-6" y="-18" width={scaleBarInfo.pixelWidth + 30} height="28" rx="4" fill="rgba(255, 255, 255, 0.9)" stroke="#d1d5db" strokeWidth="0.8" className="dark:fill-gray-900" />
              {/* Scale ruler line */}
              <line x1="0" y1="0" x2={scaleBarInfo.pixelWidth} y2="0" stroke="#1f2937" strokeWidth="2.5" className="dark:stroke-gray-200" />
              <line x1="0" y1="-5" x2="0" y2="5" stroke="#1f2937" strokeWidth="2" className="dark:stroke-gray-200" />
              <line x1={scaleBarInfo.pixelWidth / 2} y1="-3" x2={scaleBarInfo.pixelWidth / 2} y2="3" stroke="#1f2937" strokeWidth="1.5" className="dark:stroke-gray-200" />
              <line x1={scaleBarInfo.pixelWidth} y1="-5" x2={scaleBarInfo.pixelWidth} y2="5" stroke="#1f2937" strokeWidth="2" className="dark:stroke-gray-200" />
              <text x="0" y="-8" fontSize="8" fontFamily="monospace" fill="#4b5563" className="dark:fill-gray-400">0</text>
              <text x={scaleBarInfo.pixelWidth} y="-8" textAnchor="middle" fontSize="8" fontFamily="monospace" fontWeight="bold" fill="#111827" className="dark:fill-gray-100">
                {scaleBarInfo.meters} m
              </text>
            </g>

            {/* Coordinate System Badge in Drawing */}
            <g transform="translate(680, 555)">
              <text x="0" y="0" fontSize="9" fontFamily="monospace" fill="#6b7280" className="dark:fill-gray-400">
                WGS-84 Cadastral Mesh
              </text>
            </g>
          </svg>
        </div>

        {/* CADASTRAL FOOTER / DISCLAIMER */}
        <div className="pt-3 border-t border-gray-200 dark:border-gray-800 text-[10px] text-gray-500 dark:text-gray-400 space-y-1 leading-relaxed">
          <p className="font-semibold text-gray-600 dark:text-gray-300">
            * Legal Disclaimer & Technical Note:
          </p>
          <p>
            Boundary geometry shown is generated from geo-referenced WGS-84 coordinates available in RED_V1 and is provided for reference and analytical visualization purposes. It is not a substitute for an official government revenue survey, certified Field Measurement Book (FMB) sketch, or certified cadastral record issued by the Survey and Land Records Department of Tamil Nadu.
          </p>
        </div>
      </div>
    </div>
  );
};
