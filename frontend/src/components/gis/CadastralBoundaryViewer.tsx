import React, { useState, useMemo, useRef, useEffect } from 'react';
import {
  CadastralVertex,
  validateBoundaryVertices,
  generateCoordinatesCsv,
  ValidationResult,
} from '../../utils/cadastralGeometry';
import { CadastralMap } from './CadastralMap';
import { CadastralSketch } from './CadastralSketch';
import { Card, CardContent, CardHeader, CardTitle } from '../ui/Card';
import { Badge } from '../ui/Badge';
import {
  Compass,
  Map as MapIcon,
  Table as TableIcon,
  Columns,
  Download,
  Copy,
  Check,
  ExternalLink,
  AlertTriangle,
  Layers,
  Sparkles,
  Info,
} from 'lucide-react';

export type CadastralViewMode = 'sketch' | 'map' | 'split' | 'table';

export interface CadastralBoundaryViewerProps {
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
  className?: string;
  initialMode?: CadastralViewMode;
}

export const CadastralBoundaryViewer: React.FC<CadastralBoundaryViewerProps> = ({
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
  className = '',
  initialMode = 'sketch',
}) => {
  const [viewMode, setViewMode] = useState<CadastralViewMode>(initialMode);
  const [selectedVertexNumber, setSelectedVertexNumber] = useState<number | null>(null);
  const [copiedAll, setCopiedAll] = useState<boolean>(false);
  const [copiedVertexNum, setCopiedVertexNum] = useState<number | null>(null);
  const tableContainerRef = useRef<HTMLDivElement | null>(null);

  // Validate boundary geometry
  const validation: ValidationResult = useMemo(() => {
    return validateBoundaryVertices(vertices);
  }, [vertices]);

  const activeVertices = validation.validVertices;

  // Scroll table into view when selected vertex changes
  useEffect(() => {
    if (selectedVertexNumber !== null && tableContainerRef.current) {
      const targetRow = tableContainerRef.current.querySelector(
        `[data-vertex-row="${selectedVertexNumber}"]`
      );
      if (targetRow) {
        targetRow.scrollIntoView({ behavior: 'smooth', block: 'nearest' });
      }
    }
  }, [selectedVertexNumber]);

  // CSV Download Handler
  const handleDownloadCsv = () => {
    if (activeVertices.length === 0) return;
    const csvContent = generateCoordinatesCsv(activeVertices, propertyTitle);
    const blob = new Blob([csvContent], { type: 'text/csv;charset=utf-8;' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = `cadastral_vertices_${surveyNumber || 'parcel'}.csv`;
    document.body.appendChild(a);
    a.click();
    document.body.removeChild(a);
    URL.revokeObjectURL(url);
  };

  // Copy All CSV Handler
  const handleCopyAllCsv = () => {
    if (activeVertices.length === 0) return;
    const csvContent = generateCoordinatesCsv(activeVertices, propertyTitle);
    navigator.clipboard.writeText(csvContent);
    setCopiedAll(true);
    setTimeout(() => setCopiedAll(false), 2000);
  };

  // Copy Single Vertex Handler
  const handleCopySingle = (v: CadastralVertex) => {
    navigator.clipboard.writeText(`${v.latitude}, ${v.longitude}`);
    setCopiedVertexNum(v.vertexNumber);
    setTimeout(() => setCopiedVertexNum(null), 2000);
  };

  return (
    <Card className={`border-emerald-100 dark:border-emerald-900/50 shadow-xs ${className}`}>
      {/* CARD HEADER WITH VIEW SWITCHER */}
      <CardHeader className="pb-3 border-b border-gray-100 dark:border-gray-800 bg-emerald-50/40 dark:bg-emerald-950/20">
        <div className="flex flex-col lg:flex-row lg:items-center lg:justify-between gap-3">
          <div className="flex items-center gap-2.5">
            <div className="p-2 rounded-xl bg-emerald-100 dark:bg-emerald-900/40 text-emerald-700 dark:text-emerald-300 shadow-xs">
              <Compass className="h-5 w-5" />
            </div>
            <div>
              <div className="flex items-center gap-2">
                <CardTitle className="text-xs font-bold uppercase tracking-wider text-emerald-900 dark:text-emerald-300">
                  Cadastral Boundary Sketch & GIS Mapping
                </CardTitle>
                <Badge
                  variant="outline"
                  className="text-[10px] text-emerald-700 dark:text-emerald-300 border-emerald-300 font-mono font-bold"
                >
                  {activeVertices.length} {activeVertices.length === 1 ? 'Vertex' : 'Vertices'}
                </Badge>
              </div>
              <p className="text-[11px] text-gray-500 dark:text-gray-400 mt-0.5">
                Exact closed polygon generated from extracted WGS-84 coordinates (V₁ → Vₙ → V₁)
              </p>
            </div>
          </div>

          {/* VIEW MODE TABS */}
          <div className="flex items-center gap-1.5 p-1 bg-gray-100/90 dark:bg-gray-800/90 rounded-xl border border-gray-200 dark:border-gray-700 text-xs">
            <button
              type="button"
              onClick={() => setViewMode('sketch')}
              className={`px-3 py-1.5 rounded-lg font-medium transition-all flex items-center gap-1.5 cursor-pointer ${
                viewMode === 'sketch'
                  ? 'bg-white dark:bg-gray-700 text-emerald-700 dark:text-emerald-300 shadow-xs font-bold'
                  : 'text-gray-600 dark:text-gray-400 hover:text-gray-900'
              }`}
            >
              <Compass className="h-3.5 w-3.5" />
              <span>Sketch View</span>
            </button>

            <button
              type="button"
              onClick={() => setViewMode('map')}
              className={`px-3 py-1.5 rounded-lg font-medium transition-all flex items-center gap-1.5 cursor-pointer ${
                viewMode === 'map'
                  ? 'bg-white dark:bg-gray-700 text-emerald-700 dark:text-emerald-300 shadow-xs font-bold'
                  : 'text-gray-600 dark:text-gray-400 hover:text-gray-900'
              }`}
            >
              <MapIcon className="h-3.5 w-3.5" />
              <span>Map View</span>
            </button>

            <button
              type="button"
              onClick={() => setViewMode('split')}
              className={`px-3 py-1.5 rounded-lg font-medium transition-all flex items-center gap-1.5 cursor-pointer ${
                viewMode === 'split'
                  ? 'bg-white dark:bg-gray-700 text-emerald-700 dark:text-emerald-300 shadow-xs font-bold'
                  : 'text-gray-600 dark:text-gray-400 hover:text-gray-900'
              }`}
            >
              <Columns className="h-3.5 w-3.5" />
              <span>Split View</span>
            </button>

            <button
              type="button"
              onClick={() => setViewMode('table')}
              className={`px-3 py-1.5 rounded-lg font-medium transition-all flex items-center gap-1.5 cursor-pointer ${
                viewMode === 'table'
                  ? 'bg-white dark:bg-gray-700 text-emerald-700 dark:text-emerald-300 shadow-xs font-bold'
                  : 'text-gray-600 dark:text-gray-400 hover:text-gray-900'
              }`}
            >
              <TableIcon className="h-3.5 w-3.5" />
              <span>Table</span>
            </button>
          </div>
        </div>
      </CardHeader>

      <CardContent className="p-5 space-y-5">
        {/* VALIDATION WARNINGS (IF ANY) */}
        {!validation.isValid && (
          <div className="p-3 bg-amber-50 dark:bg-amber-950/30 border border-amber-200 dark:border-amber-800 rounded-xl text-xs space-y-1">
            <div className="flex items-center gap-2 font-bold text-amber-900 dark:text-amber-200">
              <AlertTriangle className="h-4 w-4 text-amber-600" />
              <span>Boundary Geometry Review Required</span>
            </div>
            {validation.errors.map((err, idx) => (
              <p key={idx} className="text-amber-800 dark:text-amber-300 text-[11px] pl-6">
                • {err}
              </p>
            ))}
          </div>
        )}

        {validation.warnings.length > 0 && (
          <div className="p-2.5 bg-blue-50 dark:bg-blue-950/20 border border-blue-200 dark:border-blue-900 rounded-xl text-xs space-y-0.5">
            <div className="flex items-center gap-1.5 font-semibold text-blue-900 dark:text-blue-300 text-[11px]">
              <Info className="h-3.5 w-3.5 text-blue-600" />
              <span>Geometry Notes:</span>
            </div>
            {validation.warnings.map((warn, idx) => (
              <p key={idx} className="text-blue-800 dark:text-blue-300 text-[11px] pl-5">
                • {warn}
              </p>
            ))}
          </div>
        )}

        {/* MAIN VISUALIZATION AREA ACCORDING TO VIEW MODE */}
        {viewMode === 'sketch' && (
          <CadastralSketch
            vertices={activeVertices}
            propertyTitle={propertyTitle}
            surveyNumber={surveyNumber}
            subdivision={subdivision}
            village={village}
            taluk={taluk}
            district={district}
            officialAreaHectares={officialAreaHectares}
            officialAreaAres={officialAreaAres}
            officialLandType={officialLandType}
            selectedVertexNumber={selectedVertexNumber}
            onSelectVertex={(vNum) => setSelectedVertexNumber(vNum)}
          />
        )}

        {viewMode === 'map' && (
          <div className="space-y-2">
            <CadastralMap
              vertices={activeVertices}
              selectedVertexNumber={selectedVertexNumber}
              onSelectVertex={(vNum) => setSelectedVertexNumber(vNum)}
              propertyTitle={propertyTitle}
              className="h-[560px] w-full"
            />
            <div className="flex items-center justify-between text-[11px] text-gray-500 px-1">
              <span>Interactive OpenStreetMap • Click any numbered marker to inspect coordinates</span>
              <span>Datum: WGS-84 (EPSG:4326)</span>
            </div>
          </div>
        )}

        {viewMode === 'split' && (
          <div className="grid grid-cols-1 xl:grid-cols-2 gap-5">
            <div>
              <div className="text-xs font-bold text-gray-700 dark:text-gray-300 mb-2 flex items-center gap-1.5">
                <Compass className="h-4 w-4 text-emerald-600" />
                Cadastral Survey Sketch (SVG)
              </div>
              <CadastralSketch
                vertices={activeVertices}
                propertyTitle={propertyTitle}
                surveyNumber={surveyNumber}
                subdivision={subdivision}
                village={village}
                taluk={taluk}
                district={district}
                officialAreaHectares={officialAreaHectares}
                officialAreaAres={officialAreaAres}
                officialLandType={officialLandType}
                selectedVertexNumber={selectedVertexNumber}
                onSelectVertex={(vNum) => setSelectedVertexNumber(vNum)}
              />
            </div>
            <div>
              <div className="text-xs font-bold text-gray-700 dark:text-gray-300 mb-2 flex items-center gap-1.5">
                <MapIcon className="h-4 w-4 text-emerald-600" />
                Live Satellite / Geographic Map
              </div>
              <CadastralMap
                vertices={activeVertices}
                selectedVertexNumber={selectedVertexNumber}
                onSelectVertex={(vNum) => setSelectedVertexNumber(vNum)}
                propertyTitle={propertyTitle}
                className="h-[620px] w-full"
              />
            </div>
          </div>
        )}

        {/* FULL COORDINATE TABLE (Synchronized Interaction) */}
        <div className="pt-3 border-t border-gray-100 dark:border-gray-800 space-y-3">
          <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-2">
            <div className="flex items-center gap-2">
              <TableIcon className="h-4 w-4 text-emerald-600" />
              <h4 className="text-xs font-bold uppercase tracking-wider text-gray-800 dark:text-gray-200">
                Synchronized Coordinate Table
              </h4>
              <span className="text-[11px] text-gray-400">
                (Click any row to focus on Map & Sketch)
              </span>
            </div>

            <div className="flex items-center gap-2">
              <button
                type="button"
                onClick={handleCopyAllCsv}
                className="px-2.5 py-1 text-[11px] rounded-lg border border-gray-200 dark:border-gray-700 hover:bg-gray-50 text-gray-700 dark:text-gray-200 font-medium flex items-center gap-1 cursor-pointer transition-colors"
                title="Copy coordinates table as CSV"
              >
                {copiedAll ? (
                  <>
                    <Check className="h-3 w-3 text-emerald-600" />
                    <span className="text-emerald-600 font-bold">Copied!</span>
                  </>
                ) : (
                  <>
                    <Copy className="h-3 w-3 text-gray-400" />
                    <span>Copy All</span>
                  </>
                )}
              </button>

              <button
                type="button"
                onClick={handleDownloadCsv}
                className="px-2.5 py-1 text-[11px] rounded-lg bg-emerald-600 hover:bg-emerald-700 text-white font-medium flex items-center gap-1 cursor-pointer transition-colors shadow-xs"
                title="Download coordinates CSV file"
              >
                <Download className="h-3 w-3" />
                <span>Download CSV</span>
              </button>
            </div>
          </div>

          {/* TABLE SCROLL CONTAINER */}
          <div
            ref={tableContainerRef}
            className="overflow-x-auto max-h-72 overflow-y-auto border border-gray-200 dark:border-gray-700 rounded-xl bg-white dark:bg-gray-900"
          >
            <table className="w-full text-left text-xs border-collapse">
              <thead className="bg-gray-50/90 dark:bg-gray-800/90 sticky top-0 border-b border-gray-200 dark:border-gray-700 text-gray-500 font-semibold z-10 backdrop-blur-xs">
                <tr>
                  <th className="py-2.5 px-4 w-24">Vertex #</th>
                  <th className="py-2.5 px-4">Latitude (°N)</th>
                  <th className="py-2.5 px-4">Longitude (°E)</th>
                  <th className="py-2.5 px-4">WGS-84 Pair</th>
                  <th className="py-2.5 px-4 text-right">Actions</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-gray-100 dark:divide-gray-800 font-mono text-[11px]">
                {activeVertices.map((v) => {
                  const isSelected = selectedVertexNumber === v.vertexNumber;
                  const isCopied = copiedVertexNum === v.vertexNumber;
                  const mapsUrl = `https://www.google.com/maps?q=${v.latitude},${v.longitude}`;

                  return (
                    <tr
                      key={v.vertexNumber}
                      data-vertex-row={v.vertexNumber}
                      onClick={() => setSelectedVertexNumber(v.vertexNumber)}
                      className={`cursor-pointer transition-colors ${
                        isSelected
                          ? 'bg-emerald-100/70 dark:bg-emerald-900/40 font-bold border-l-4 border-l-emerald-600'
                          : 'hover:bg-emerald-50/40 dark:hover:bg-emerald-950/20'
                      }`}
                    >
                      <td className="py-2 px-4 font-sans text-gray-800 dark:text-gray-200">
                        <span
                          className={`inline-flex items-center justify-center w-6 h-6 rounded-full text-[10px] font-bold ${
                            isSelected
                              ? 'bg-emerald-600 text-white shadow-xs'
                              : 'bg-emerald-100 dark:bg-emerald-900/50 text-emerald-800 dark:text-emerald-300'
                          }`}
                        >
                          {v.vertexNumber}
                        </span>
                      </td>
                      <td className="py-2 px-4 text-emerald-700 dark:text-emerald-400 font-medium">
                        {v.latitude.toFixed(6)}
                      </td>
                      <td className="py-2 px-4 text-teal-700 dark:text-teal-400 font-medium">
                        {v.longitude.toFixed(6)}
                      </td>
                      <td className="py-2 px-4 text-gray-600 dark:text-gray-400 select-all">
                        {v.latitude}, {v.longitude}
                      </td>
                      <td className="py-2 px-4 text-right font-sans" onClick={(e) => e.stopPropagation()}>
                        <div className="flex items-center justify-end gap-1">
                          <button
                            type="button"
                            onClick={() => handleCopySingle(v)}
                            title="Copy GPS Coordinates"
                            className="p-1 rounded hover:bg-gray-100 dark:hover:bg-gray-700 text-gray-500 dark:text-gray-300 cursor-pointer"
                          >
                            {isCopied ? (
                              <Check className="h-3.5 w-3.5 text-emerald-600" />
                            ) : (
                              <Copy className="h-3.5 w-3.5" />
                            )}
                          </button>
                          <a
                            href={mapsUrl}
                            target="_blank"
                            rel="noreferrer"
                            title="Open Point on Google Maps"
                            className="p-1 rounded hover:bg-blue-50 dark:hover:bg-blue-900/30 text-blue-600 dark:text-blue-400 cursor-pointer"
                          >
                            <ExternalLink className="h-3.5 w-3.5" />
                          </a>
                        </div>
                      </td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </div>
        </div>
      </CardContent>
    </Card>
  );
};
