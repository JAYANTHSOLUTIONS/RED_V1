import React, { useMemo, useState, useRef } from 'react';
import {
  MultiParcelInput,
  projectMultiParcelsToSvg,
  generateCoordinatesCsv,
  CadastralVertex,
} from '../../utils/cadastralGeometry';
import {
  Compass,
  Download,
  Printer,
  Ruler,
  Layers,
  AlertTriangle,
  Image as ImageIcon,
  MapPin,
  CheckCircle2,
  FileSpreadsheet,
  Maximize2,
  Sparkles,
} from 'lucide-react';

export interface CombinedCadastralSketchProps {
  parcels: MultiParcelInput[];
  district?: string;
  taluk?: string;
  village?: string;
  title?: string;
  className?: string;
}

export const CombinedCadastralSketch: React.FC<CombinedCadastralSketchProps> = ({
  parcels,
  district = 'Kancheepuram',
  taluk = 'Walajabad',
  village = 'Walajabad',
  title = 'Combined Village Map Sketch',
  className = '',
}) => {
  const [showDimensions, setShowDimensions] = useState<boolean>(true);
  const [showVertexLabels, setShowVertexLabels] = useState<boolean>(true);
  const [selectedParcelId, setSelectedParcelId] = useState<string | null>(null);
  const sketchContainerRef = useRef<HTMLDivElement | null>(null);

  const svgWidth = 880;
  const svgHeight = 620;
  const svgPadding = 90;

  // Filter valid parcels (parcels with at least 3 vertices)
  const validParcels = useMemo(() => {
    return parcels.filter((p) => p.vertices && p.vertices.length >= 3);
  }, [parcels]);

  // Project all parcels onto a unified SVG space
  const projection = useMemo(() => {
    return projectMultiParcelsToSvg(validParcels, svgWidth, svgHeight, svgPadding);
  }, [validParcels, svgWidth, svgHeight, svgPadding]);

  // Graphic scale bar calculation
  const scaleBarInfo = useMemo(() => {
    const metersPerPixel = projection.scaleMetersPerPixel;
    const targetMeters = metersPerPixel * 100;
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
      pixelWidth: Math.max(pixelWidth, 45),
    };
  }, [projection.scaleMetersPerPixel]);

  // Handle isolated printable page export
  const handlePrintSketch = () => {
    const sketchElement = sketchContainerRef.current || document.getElementById('combined-village-sketch-sheet');
    if (!sketchElement) {
      window.print();
      return;
    }

    const printWindow = window.open('', '_blank', 'width=1040,height=860');
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
          <title>${title} - ${village}, ${taluk}</title>
          ${styles}
          <style>
            body {
              background: #ffffff !important;
              margin: 0;
              padding: 24px;
              color: #090d16;
              font-family: ui-sans-serif, system-ui, -apple-system, sans-serif;
            }
            #combined-village-sketch-sheet {
              border: 1px solid #d1d5db !important;
              box-shadow: none !important;
              padding: 24px !important;
              max-width: 960px;
              margin: 0 auto;
              background: #ffffff !important;
            }
            @media print {
              body { padding: 0; }
              #combined-village-sketch-sheet { border: none !important; padding: 0 !important; }
            }
          </style>
        </head>
        <body>
          <div id="combined-village-sketch-sheet">
            ${sketchElement.innerHTML}
          </div>
          <script>
            setTimeout(() => {
              window.print();
              window.close();
            }, 400);
          </script>
        </body>
      </html>
    `);
    printWindow.document.close();
  };

  // Handle PNG Image Download
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
        a.download = `combined_village_sketch_${village.toLowerCase().replace(/\s+/g, '_')}.png`;
        document.body.appendChild(a);
        a.click();
        document.body.removeChild(a);
      }
      URL.revokeObjectURL(blobURL);
    };
    image.src = blobURL;
  };

  // Handle SVG Vector Download
  const handleDownloadSvg = () => {
    const svgEl = sketchContainerRef.current?.querySelector('svg');
    if (!svgEl) return;

    const serializer = new XMLSerializer();
    const source = serializer.serializeToString(svgEl);
    const blob = new Blob([source], { type: 'image/svg+xml;charset=utf-8' });
    const url = URL.createObjectURL(blob);

    const a = document.createElement('a');
    a.href = url;
    a.download = `combined_village_sketch_${village.toLowerCase().replace(/\s+/g, '_')}.svg`;
    document.body.appendChild(a);
    a.click();
    document.body.removeChild(a);
    URL.revokeObjectURL(url);
  };

  // Export Combined Coordinates CSV
  const handleDownloadCombinedCsv = () => {
    if (validParcels.length === 0) return;

    const lines: string[] = [
      `# RED Real Estate Consultancy - Combined Cadastral Parcel Coordinates`,
      `# Village: ${village} | Taluk: ${taluk} | District: ${district}`,
      `# Total Survey Parcels: ${validParcels.length}`,
      `# Datum: WGS-84 (EPSG:4326)`,
      `# Generated At: ${new Date().toISOString()}`,
      `survey_number,subdivision,vertex_number,latitude,longitude`,
    ];

    validParcels.forEach((p) => {
      p.vertices.forEach((v) => {
        lines.push(
          `"${p.surveyNumber}","${p.subdivision || ''}",${v.vertexNumber},${v.latitude.toFixed(6)},${v.longitude.toFixed(6)}`
        );
      });
    });

    const csvContent = lines.join('\n');
    const blob = new Blob([csvContent], { type: 'text/csv;charset=utf-8' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = `combined_cadastral_vertices_${village.toLowerCase().replace(/\s+/g, '_')}.csv`;
    document.body.appendChild(a);
    a.click();
    document.body.removeChild(a);
    URL.revokeObjectURL(url);
  };

  if (validParcels.length === 0) {
    return (
      <div className="p-12 text-center bg-slate-900/60 border border-slate-800 rounded-3xl backdrop-blur-xl space-y-3">
        <AlertTriangle className="h-10 w-10 text-amber-400 mx-auto animate-pulse" />
        <h3 className="text-sm font-bold text-slate-200">
          No Valid Boundary Vertices to Render Combined Map
        </h3>
        <p className="text-xs text-slate-400 max-w-md mx-auto leading-relaxed">
          Please enter one or more survey numbers and subdivisions in the terminal on the left and click "Extract & Render Village Map".
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

  const { combinedMetrics, projectedParcels } = projection;

  return (
    <div className={`space-y-5 ${className}`}>
      {/* ACTION & VIEWPORT TOOLBAR */}
      <div className="flex flex-wrap items-center justify-between gap-3 p-3.5 bg-slate-900/80 backdrop-blur-xl rounded-2xl border border-slate-800 text-xs no-print shadow-lg">
        {/* Left Controls */}
        <div className="flex flex-wrap items-center gap-2">
          <button
            type="button"
            onClick={() => setShowDimensions(!showDimensions)}
            className={`px-3 py-1.5 rounded-xl border text-xs font-semibold transition-all flex items-center gap-1.5 cursor-pointer ${
              showDimensions
                ? 'bg-emerald-500/20 border-emerald-500/50 text-emerald-300 shadow-[0_0_12px_rgba(16,185,129,0.2)]'
                : 'bg-slate-800/80 border-slate-700 text-slate-300 hover:bg-slate-700/80'
            }`}
          >
            <Ruler className="h-3.5 w-3.5" />
            <span>Dimensions ({showDimensions ? 'ON' : 'OFF'})</span>
          </button>

          <button
            type="button"
            onClick={() => setShowVertexLabels(!showVertexLabels)}
            className={`px-3 py-1.5 rounded-xl border text-xs font-semibold transition-all flex items-center gap-1.5 cursor-pointer ${
              showVertexLabels
                ? 'bg-emerald-500/20 border-emerald-500/50 text-emerald-300 shadow-[0_0_12px_rgba(16,185,129,0.2)]'
                : 'bg-slate-800/80 border-slate-700 text-slate-300 hover:bg-slate-700/80'
            }`}
          >
            <Layers className="h-3.5 w-3.5" />
            <span>Vertex Badges ({showVertexLabels ? 'ON' : 'OFF'})</span>
          </button>
        </div>

        {/* Right Export Actions */}
        <div className="flex items-center gap-2">
          <button
            type="button"
            onClick={handleDownloadCombinedCsv}
            title="Download Combined Coordinates CSV"
            className="px-3 py-1.5 rounded-xl bg-slate-800/80 border border-slate-700 text-slate-200 hover:bg-slate-700 hover:border-emerald-500/50 transition-all flex items-center gap-1.5 font-medium cursor-pointer"
          >
            <FileSpreadsheet className="h-3.5 w-3.5 text-emerald-400" />
            <span>CSV</span>
          </button>

          <button
            type="button"
            onClick={handleDownloadSvg}
            title="Download Vector SVG"
            className="px-3 py-1.5 rounded-xl bg-slate-800/80 border border-slate-700 text-slate-200 hover:bg-slate-700 hover:border-emerald-500/50 transition-all flex items-center gap-1.5 font-medium cursor-pointer"
          >
            <Download className="h-3.5 w-3.5" />
            <span>SVG</span>
          </button>

          <button
            type="button"
            onClick={handleDownloadPng}
            title="Download PNG Image"
            className="px-3 py-1.5 rounded-xl bg-slate-800/80 border border-slate-700 text-slate-200 hover:bg-slate-700 hover:border-emerald-500/50 transition-all flex items-center gap-1.5 font-medium cursor-pointer"
          >
            <ImageIcon className="h-3.5 w-3.5 text-blue-400" />
            <span>PNG</span>
          </button>

          <button
            type="button"
            onClick={handlePrintSketch}
            title="Print Combined Sketch Sheet Only"
            className="px-4 py-1.5 rounded-xl bg-gradient-to-r from-emerald-500 to-teal-600 hover:from-emerald-400 hover:to-teal-500 text-white font-bold transition-all flex items-center gap-1.5 shadow-[0_0_20px_rgba(16,185,129,0.3)] cursor-pointer"
          >
            <Printer className="h-3.5 w-3.5" />
            <span>Print Combined Sketch</span>
          </button>
        </div>
      </div>

      {/* COMBINED VILLAGE MAP SKETCH SHEET */}
      <div
        ref={sketchContainerRef}
        id="combined-village-sketch-sheet"
        className="p-6 bg-slate-950 border border-slate-800 rounded-3xl shadow-2xl space-y-5 print:p-0 print:border-0 print:shadow-none print:bg-white"
      >
        {/* OFFICIAL STAMP & CADASTRAL HEADER */}
        <div className="pb-4 border-b-2 border-emerald-500/40 flex flex-col md:flex-row md:items-start md:justify-between gap-4">
          <div className="space-y-1.5">
            <div className="flex items-center gap-2 flex-wrap">
              <span className="font-serif text-lg font-black tracking-wider text-transparent bg-clip-text bg-gradient-to-r from-emerald-400 via-teal-300 to-cyan-400 uppercase">
                RED REAL ESTATE CONSULTANCY
              </span>
              <span className="text-[10px] px-2.5 py-0.5 rounded-full bg-emerald-500/10 text-emerald-300 font-mono font-bold border border-emerald-500/30">
                WGS-84 VILLAGE CADASTRA
              </span>
            </div>
            <h2 className="text-base font-bold text-slate-100 tracking-tight flex items-center gap-2">
              <span>{title}</span>
            </h2>
            <div className="flex items-center gap-2 flex-wrap text-xs text-slate-400">
              <span className="font-semibold text-slate-300">Survey Parcels:</span>
              {projectedParcels.map((pp) => (
                <span
                  key={pp.id}
                  className="px-2.5 py-0.5 rounded-md text-[11px] font-mono font-bold text-white shadow-sm"
                  style={{ backgroundColor: pp.color }}
                >
                  Sy. {pp.surveyNumber}{pp.subdivision ? `/${pp.subdivision}` : ''}
                </span>
              ))}
            </div>
          </div>

          <div className="text-right text-xs space-y-1 text-slate-400 font-mono">
            <div>Village: <span className="font-sans font-bold text-slate-100">{village}</span></div>
            <div>Taluk: <span className="font-sans font-semibold text-slate-200">{taluk}</span></div>
            <div>District: <span className="font-sans font-semibold text-slate-200">{district}</span></div>
            <div className="text-[10px] text-slate-500 mt-1">Generated: {generatedDateStr}</div>
          </div>
        </div>

        {/* COMBINED METRICS HUD CARDS */}
        <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
          <div className="p-3.5 rounded-2xl bg-gradient-to-br from-slate-900 to-slate-950 border border-slate-800/80 shadow-md">
            <span className="text-[10px] font-bold tracking-wider text-emerald-400 block uppercase">
              Combined Geodesic Area
            </span>
            <div className="font-mono font-black text-slate-100 text-base mt-1">
              {combinedMetrics.totalAreaSqMeters.toLocaleString('en-IN')} m²
            </div>
            <span className="text-[10px] text-slate-400 font-mono">
              {combinedMetrics.totalAreaAcres} Acres ({combinedMetrics.totalAreaCents} Cents)
            </span>
          </div>

          <div className="p-3.5 rounded-2xl bg-gradient-to-br from-slate-900 to-slate-950 border border-slate-800/80 shadow-md">
            <span className="text-[10px] font-bold tracking-wider text-emerald-400 block uppercase">
              Total Combined Perimeter
            </span>
            <div className="font-mono font-black text-slate-100 text-base mt-1">
              {combinedMetrics.totalPerimeterMeters.toLocaleString('en-IN')} meters
            </div>
            <span className="text-[10px] text-slate-400 font-mono">
              ~{(combinedMetrics.totalPerimeterMeters * 3.28084).toFixed(1)} feet
            </span>
          </div>

          <div className="p-3.5 rounded-2xl bg-gradient-to-br from-slate-900 to-slate-950 border border-slate-800/80 shadow-md">
            <span className="text-[10px] font-bold tracking-wider text-slate-400 block uppercase">
              Survey Parcels Assembled
            </span>
            <div className="font-mono font-black text-slate-100 text-base mt-1">
              {validParcels.length} Parcels
            </div>
            <span className="text-[10px] text-slate-400 font-mono">
              {combinedMetrics.totalVerticesCount} Extracted Boundary Points
            </span>
          </div>

          <div className="p-3.5 rounded-2xl bg-gradient-to-br from-slate-900 to-slate-950 border border-slate-800/80 shadow-md">
            <span className="text-[10px] font-bold tracking-wider text-slate-400 block uppercase">
              Global Reference Centroid
            </span>
            <div className="font-mono font-bold text-slate-200 text-xs mt-1 truncate">
              {combinedMetrics.globalCentroid.latitude.toFixed(5)}°N, {combinedMetrics.globalCentroid.longitude.toFixed(5)}°E
            </div>
            <span className="text-[10px] text-teal-400 font-medium font-mono">
              EPSG:4326 Conformal Mesh
            </span>
          </div>
        </div>

        {/* MAIN MULTI-PARCEL DYNAMIC SVG CANVAS */}
        <div className="relative border border-slate-800/90 rounded-2xl bg-slate-900/90 overflow-hidden flex items-center justify-center p-3 shadow-inner">
          <svg
            viewBox={projection.viewBox}
            className="w-full h-auto max-h-[640px] select-none"
            style={{ shapeRendering: 'geometricPrecision' }}
          >
            <defs>
              <pattern id="cadastralNeonGrid" width="40" height="40" patternUnits="userSpaceOnUse">
                <path d="M 40 0 L 0 0 0 40" fill="none" stroke="rgba(255, 255, 255, 0.04)" strokeWidth="1" />
              </pattern>
            </defs>

            {/* Dark CAD Grid Background */}
            <rect width={svgWidth} height={svgHeight} fill="#090d16" />
            <rect width={svgWidth} height={svgHeight} fill="url(#cadastralNeonGrid)" />

            {/* Render Each Survey Parcel Polygon */}
            {projectedParcels.map((pp) => {
              const isSelected = selectedParcelId === pp.id;
              return (
                <g key={`parcel-path-${pp.id}`}>
                  {/* Parcel Polygon Path */}
                  <path
                    d={pp.pathData}
                    fill={pp.color.replace('#', 'rgba(').replace('#059669', 'rgba(16, 185, 129, 0.22)').replace('#2563eb', 'rgba(59, 130, 246, 0.22)').replace('#d97706', 'rgba(245, 158, 11, 0.22)').replace('#9333ea', 'rgba(168, 85, 247, 0.22)').replace('#e11d48', 'rgba(244, 63, 94, 0.22)').replace('#0891b2', 'rgba(6, 182, 212, 0.22)')}
                    stroke={pp.color}
                    strokeWidth={isSelected ? '4' : '2.8'}
                    strokeLinejoin="round"
                    strokeLinecap="round"
                    className="cursor-pointer transition-all hover:opacity-95"
                    onClick={() => setSelectedParcelId(pp.id === selectedParcelId ? null : pp.id)}
                  />

                  {/* Parcel Centroid Label Badge */}
                  <g transform={`translate(${pp.centroidSvg.x}, ${pp.centroidSvg.y})`}>
                    <rect
                      x="-42"
                      y="-14"
                      width="84"
                      height="28"
                      rx="8"
                      fill="#0f172a"
                      stroke={pp.color}
                      strokeWidth="1.8"
                      className="shadow-xl"
                    />
                    <text
                      x="0"
                      y="-2"
                      textAnchor="middle"
                      fontSize="10"
                      fontFamily="ui-sans-serif, system-ui, sans-serif"
                      fontWeight="900"
                      fill={pp.color}
                    >
                      Sy. {pp.surveyNumber}{pp.subdivision ? `/${pp.subdivision}` : ''}
                    </text>
                    <text
                      x="0"
                      y="9"
                      textAnchor="middle"
                      fontSize="8"
                      fontFamily="ui-monospace, monospace"
                      fill="#94a3b8"
                    >
                      {pp.metrics.areaSqMeters} m²
                    </text>
                  </g>
                </g>
              );
            })}

            {/* Segment Dimensions (If Enabled) */}
            {showDimensions &&
              projectedParcels.map((pp) =>
                pp.segments.map((seg) => (
                  <g key={`dim-${pp.id}-${seg.fromVertex}-${seg.toVertex}`}>
                    <rect
                      x={seg.midpointSvg.x - 21}
                      y={seg.midpointSvg.y - 7.5}
                      width="42"
                      height="15"
                      rx="4"
                      fill="#0f172a"
                      stroke={pp.color}
                      strokeWidth="0.8"
                    />
                    <text
                      x={seg.midpointSvg.x}
                      y={seg.midpointSvg.y + 3.5}
                      textAnchor="middle"
                      fontSize="9"
                      fontFamily="ui-monospace, monospace"
                      fontWeight="700"
                      fill={pp.color}
                    >
                      {seg.lengthMeters}m
                    </text>
                  </g>
                ))
              )}

            {/* Vertex Nodes and Number Badges */}
            {projectedParcels.map((pp) =>
              pp.svgPoints.map((pt) => (
                <g key={`v-${pp.id}-${pt.vertexNumber}`} className="cursor-pointer">
                  <circle
                    cx={pt.x}
                    cy={pt.y}
                    r="5"
                    fill="#0f172a"
                    stroke={pp.color}
                    strokeWidth="2.5"
                  />
                  {showVertexLabels && (
                    <g transform={`translate(${pt.x + 7}, ${pt.y - 7})`}>
                      <rect
                        x="-2"
                        y="-10"
                        width="18"
                        height="14"
                        rx="3"
                        fill="#0f172a"
                        stroke={pp.color}
                        strokeWidth="0.8"
                      />
                      <text
                        x="7"
                        y="0"
                        textAnchor="middle"
                        fontSize="8.5"
                        fontFamily="ui-sans-serif, system-ui, sans-serif"
                        fontWeight="extrabold"
                        fill={pp.color}
                      >
                        {pt.vertexNumber}
                      </text>
                    </g>
                  )}
                </g>
              ))
            )}

            {/* PROFESSIONAL NORTH ARROW (Top Right Widget) */}
            <g transform="translate(815, 70)">
              <circle cx="0" cy="0" r="24" fill="#0f172a" stroke="#10b981" strokeWidth="1.5" className="shadow-2xl" />
              <polygon points="0,-18 7,4 0,0" fill="#059669" />
              <polygon points="0,-18 -7,4 0,0" fill="#10b981" />
              <polygon points="0,18 6,-1 0,0" fill="#334155" />
              <polygon points="0,18 -6,-1 0,0" fill="#475569" />
              <circle cx="0" cy="0" r="2.5" fill="#ffffff" />
              <text x="0" y="-21" textAnchor="middle" fontSize="11" fontWeight="900" fontFamily="sans-serif" fill="#10b981">
                N
              </text>
            </g>

            {/* GRAPHIC SCALE BAR (Bottom Left Widget) */}
            <g transform="translate(45, 585)">
              <rect x="-8" y="-20" width={scaleBarInfo.pixelWidth + 36} height="32" rx="6" fill="#0f172a" stroke="#334155" strokeWidth="1" />
              <line x1="0" y1="0" x2={scaleBarInfo.pixelWidth} y2="0" stroke="#f8fafc" strokeWidth="3" />
              <line x1="0" y1="-6" x2="0" y2="6" stroke="#f8fafc" strokeWidth="2" />
              <line x1={scaleBarInfo.pixelWidth / 2} y1="-4" x2={scaleBarInfo.pixelWidth / 2} y2="4" stroke="#f8fafc" strokeWidth="1.5" />
              <line x1={scaleBarInfo.pixelWidth} y1="-6" x2={scaleBarInfo.pixelWidth} y2="6" stroke="#f8fafc" strokeWidth="2" />
              <text x="0" y="-9" fontSize="9" fontFamily="monospace" fill="#94a3b8">0</text>
              <text x={scaleBarInfo.pixelWidth} y="-9" textAnchor="middle" fontSize="9" fontFamily="monospace" fontWeight="bold" fill="#f8fafc">
                {scaleBarInfo.meters} m
              </text>
            </g>

            {/* Coordinate Mesh Footer */}
            <g transform="translate(710, 595)">
              <text x="0" y="0" fontSize="9" fontFamily="monospace" fill="#64748b">
                WGS-84 Cadastral Mesh
              </text>
            </g>
          </svg>
        </div>

        {/* INDIVIDUAL PARCELS BREAKDOWN LEGEND */}
        <div className="border border-slate-800 rounded-2xl overflow-hidden bg-slate-900/60 backdrop-blur-xl">
          <div className="bg-slate-900 px-4 py-3 border-b border-slate-800 font-bold text-xs text-slate-200 flex items-center justify-between">
            <span className="uppercase tracking-wider flex items-center gap-2">
              <Layers className="h-4 w-4 text-emerald-400" />
              Survey Parcels Legend & Geometry Matrix
            </span>
            <span className="font-mono text-[11px] font-normal text-slate-400">
              {projectedParcels.length} Active Parcels
            </span>
          </div>

          <div className="divide-y divide-slate-800/60 text-xs">
            {projectedParcels.map((pp) => (
              <div key={pp.id} className="p-3.5 flex flex-wrap items-center justify-between gap-3 hover:bg-slate-800/40 transition-colors">
                <div className="flex items-center gap-3">
                  <span
                    className="w-4 h-4 rounded-full shrink-0 shadow-md ring-2 ring-slate-800"
                    style={{ backgroundColor: pp.color }}
                  />
                  <div>
                    <span className="font-mono font-extrabold text-slate-100 text-xs">
                      Survey No: {pp.surveyNumber}{pp.subdivision ? `/${pp.subdivision}` : ''}
                    </span>
                    <span className="text-slate-400 text-[11px] ml-2 font-mono">
                      ({pp.vertices.length} Vertices)
                    </span>
                  </div>
                </div>

                <div className="flex items-center gap-6 text-xs font-mono">
                  <div>
                    <span className="text-slate-400 text-[10px] uppercase block">Area:</span>
                    <span className="font-bold text-slate-100 text-xs">
                      {pp.metrics.areaSqMeters} m²
                    </span>
                    <span className="text-slate-400 text-[10px] ml-1.5">
                      ({pp.metrics.areaAcres} Ac / {pp.metrics.areaCents} Cents)
                    </span>
                  </div>
                  <div>
                    <span className="text-slate-400 text-[10px] uppercase block">Perimeter:</span>
                    <span className="font-bold text-slate-200 text-xs">
                      {pp.metrics.perimeterMeters} m
                    </span>
                  </div>
                </div>
              </div>
            ))}
          </div>
        </div>

        {/* LEGAL DISCLAIMER */}
        <div className="pt-3 border-t border-slate-800 text-[10px] text-slate-400 space-y-1 leading-relaxed">
          <p className="font-semibold text-slate-300">
            * Legal Disclaimer & Technical Note:
          </p>
          <p>
            This combined village map sketch is generated by assembling individual WGS-84 cadastral boundary polygons extracted from official Tamil Nadu GIS datasets. It is designed for real estate spatial planning, boundary verification, and property appraisal purposes, and does not replace official revenue sketches issued by the Tamil Nadu Survey Department.
          </p>
        </div>
      </div>
    </div>
  );
};
