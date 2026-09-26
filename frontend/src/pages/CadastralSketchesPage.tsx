import React, { useState, useEffect, useMemo } from 'react';
import { tngisApi, TngisLookupResponse, TngisVertex } from '../api/tngis';
import {
  MultiParcelInput,
  CadastralVertex,
  generateCoordinatesCsv,
} from '../utils/cadastralGeometry';
import { CombinedCadastralSketch } from '../components/gis/CombinedCadastralSketch';
import { CadastralMap } from '../components/gis/CadastralMap';
import { Card, CardContent } from '../components/ui/Card';
import { Badge } from '../components/ui/Badge';
import { Button } from '../components/ui/Button';
import { Input } from '../components/ui/Input';
import {
  Compass,
  Plus,
  Trash2,
  Search,
  Layers,
  MapPin,
  RefreshCw,
  Download,
  Sparkles,
  Grid,
  Columns,
  Table as TableIcon,
  CheckCircle2,
  AlertCircle,
  FileSpreadsheet,
  Building,
} from 'lucide-react';

interface SurveyParcelRow {
  id: string;
  surveyNumber: string;
  subdivision: string;
  color: string;
}

const PARCEL_COLORS = ['#059669', '#2563eb', '#d97706', '#9333ea', '#e11d48', '#0891b2'];

export default function CadastralSketchesPage() {
  // Location controls
  const [district, setDistrict] = useState<string>('Kancheepuram');
  const [taluk, setTaluk] = useState<string>('Walajabad');
  const [village, setVillage] = useState<string>('Walajabad');

  // Multi-survey input rows
  const [parcelRows, setParcelRows] = useState<SurveyParcelRow[]>([
    { id: 'row-1', surveyNumber: '217', subdivision: '6', color: PARCEL_COLORS[0] },
    { id: 'row-2', surveyNumber: '217', subdivision: '1B2', color: PARCEL_COLORS[1] },
    { id: 'row-3', surveyNumber: '370', subdivision: '4', color: PARCEL_COLORS[2] },
  ]);

  // Extraction states & Extracted multi-parcel results
  const [loading, setLoading] = useState<boolean>(false);
  const [extractingStatus, setExtractingStatus] = useState<string>('');
  const [extractedParcels, setExtractedParcels] = useState<MultiParcelInput[]>([]);
  const [extractionErrors, setExtractionErrors] = useState<string[]>([]);

  // Active view tab
  const [activeTab, setActiveTab] = useState<'sketch' | 'map' | 'split' | 'table'>('sketch');

  // Add new survey row
  const handleAddRow = () => {
    const nextIdx = parcelRows.length;
    const newRow: SurveyParcelRow = {
      id: `row-${Date.now()}-${nextIdx}`,
      surveyNumber: '',
      subdivision: '',
      color: PARCEL_COLORS[nextIdx % PARCEL_COLORS.length],
    };
    setParcelRows([...parcelRows, newRow]);
  };

  // Remove survey row
  const handleRemoveRow = (id: string) => {
    if (parcelRows.length <= 1) return;
    setParcelRows(parcelRows.filter((r) => r.id !== id));
  };

  // Update row values
  const handleUpdateRow = (id: string, field: 'surveyNumber' | 'subdivision', value: string) => {
    setParcelRows(
      parcelRows.map((row) => (row.id === id ? { ...row, [field]: value } : row))
    );
  };

  // Pre-fill demo parcels
  const handleLoadDemoParcels = () => {
    setDistrict('Kancheepuram');
    setTaluk('Walajabad');
    setVillage('Walajabad');
    setParcelRows([
      { id: 'row-1', surveyNumber: '217', subdivision: '6', color: PARCEL_COLORS[0] },
      { id: 'row-2', surveyNumber: '217', subdivision: '1B2', color: PARCEL_COLORS[1] },
      { id: 'row-3', surveyNumber: '370', subdivision: '4', color: PARCEL_COLORS[2] },
    ]);
  };

  // Extract boundaries for all entered survey rows
  const handleExtractAllBoundaries = async () => {
    const validRows = parcelRows.filter((r) => r.surveyNumber.trim().length > 0);
    if (validRows.length === 0) {
      setExtractionErrors(['Please enter at least one valid Survey Number.']);
      return;
    }

    setLoading(true);
    setExtractionErrors([]);
    setExtractingStatus('Initializing cadastral boundary extraction...');
    const results: MultiParcelInput[] = [];
    const errors: string[] = [];

    for (let i = 0; i < validRows.length; i++) {
      const row = validRows[i];
      const sNo = row.surveyNumber.trim();
      const sDiv = row.subdivision.trim();
      setExtractingStatus(`Extracting coordinates for Survey ${sNo}${sDiv ? `/${sDiv}` : ''} (${i + 1}/${validRows.length})...`);

      try {
        const resp: TngisLookupResponse = await tngisApi.lookup({
          district: district.trim(),
          taluk: taluk.trim(),
          village: village.trim(),
          survey_number: sNo,
          subdivision: sDiv,
          live_scrape: false,
        });

        if (resp && resp.coordinates && resp.coordinates.vertices && resp.coordinates.vertices.length >= 3) {
          const mappedVertices: CadastralVertex[] = resp.coordinates.vertices.map((v) => ({
            vertexNumber: v.vertex_number,
            latitude: v.latitude,
            longitude: v.longitude,
          }));

          const ownerNames = resp.owners ? resp.owners.map((o) => o.owner) : [];

          results.push({
            id: row.id,
            surveyNumber: sNo,
            subdivision: sDiv,
            color: row.color,
            vertices: mappedVertices,
            landType: resp.land_details?.land_type_eng || resp.land_details?.land_type || 'Rayathuvari',
            extentHectares: resp.land_details?.extent_hectares || '0',
            extentAres: resp.land_details?.extent_ares || '0',
            owners: ownerNames,
          });
        } else {
          errors.push(`Survey ${sNo}${sDiv ? `/${sDiv}` : ''}: No WGS-84 boundary vertices extracted from revenue dataset.`);
        }
      } catch (err: any) {
        console.error(`Failed lookup for survey ${sNo}/${sDiv}:`, err);
        errors.push(`Survey ${sNo}${sDiv ? `/${sDiv}` : ''}: Extraction request failed.`);
      }
    }

    setExtractedParcels(results);
    setExtractionErrors(errors);
    setLoading(false);
    setExtractingStatus('');
  };

  // Automatically trigger extraction on initial load
  useEffect(() => {
    handleExtractAllBoundaries();
  }, []);

  // Combined vertices across all extracted parcels for map & table views
  const allVerticesCombined = useMemo(() => {
    const list: (CadastralVertex & { parcelId: string; surveyRef: string; color: string })[] = [];
    extractedParcels.forEach((p) => {
      p.vertices.forEach((v) => {
        list.push({
          ...v,
          parcelId: p.id,
          surveyRef: `${p.surveyNumber}${p.subdivision ? `/${p.subdivision}` : ''}`,
          color: p.color,
        });
      });
    });
    return list;
  }, [extractedParcels]);

  return (
    <div className="space-y-6 pb-12">
      {/* PAGE HERO BANNER */}
      <div className="p-6 bg-gradient-to-r from-emerald-950 via-slate-900 to-teal-950 text-white rounded-2xl shadow-md border border-emerald-800/40 relative overflow-hidden">
        <div className="absolute right-0 top-0 -mt-10 -mr-10 w-72 h-72 bg-emerald-500/10 rounded-full blur-3xl pointer-events-none" />
        <div className="relative z-10 flex flex-col lg:flex-row lg:items-center lg:justify-between gap-4">
          <div className="space-y-1.5 max-w-3xl">
            <div className="flex flex-wrap items-center gap-2">
              <span className="px-2.5 py-0.5 rounded-full text-[11px] font-bold tracking-wide uppercase bg-emerald-500/20 text-emerald-300 border border-emerald-500/30 flex items-center gap-1">
                <Compass className="h-3.5 w-3.5" />
                Multi-Survey Cadastral Engine
              </span>
              <span className="px-2.5 py-0.5 rounded-full text-[11px] font-bold bg-emerald-500 text-white shadow-xs">
                {extractedParcels.length} Survey Parcel{extractedParcels.length === 1 ? '' : 's'} Plotted
              </span>
            </div>
            <h1 className="text-xl font-bold tracking-tight">
              Combined Village Map & Cadastral Boundary Sketch
            </h1>
            <p className="text-xs text-emerald-100/80 leading-relaxed">
              Enter multiple survey numbers & subdivisions for any village in Tamil Nadu. The GIS engine extracts geo-referenced WGS-84 boundary coordinates and generates an official combined village map sketch with color coding, scale bar, and North arrow.
            </p>
          </div>

          <div className="flex items-center gap-2">
            <Button
              onClick={handleLoadDemoParcels}
              variant="outline"
              className="bg-white/10 hover:bg-white/20 text-white border-white/20 text-xs font-semibold px-3.5 py-2 rounded-xl"
            >
              <Sparkles className="h-3.5 w-3.5 mr-1.5 text-amber-300" />
              Load Sample Parcels
            </Button>
          </div>
        </div>
      </div>

      {/* INPUT PANEL & MAP GENERATOR WORKSPACE */}
      <div className="grid grid-cols-1 lg:grid-cols-12 gap-6 items-start">
        {/* LEFT PANEL: LOCATION & MULTI-SURVEY INPUT (4 COLS) */}
        <div className="lg:col-span-4 space-y-4">
          <Card className="border-gray-200 dark:border-gray-800 shadow-xs">
            <div className="p-4 border-b border-gray-100 dark:border-gray-800 space-y-3">
              <div className="flex items-center justify-between">
                <h3 className="text-xs font-bold uppercase tracking-wider text-gray-700 dark:text-gray-300 flex items-center gap-1.5">
                  <MapPin className="h-3.5 w-3.5 text-emerald-600" />
                  1. Revenue Location Selection
                </h3>
                <Badge variant="outline" className="text-[10px] text-emerald-700 dark:text-emerald-300 border-emerald-300 bg-emerald-50 dark:bg-emerald-950/40">
                  Tamil Nadu GIS
                </Badge>
              </div>

              {/* Location Selector Fields */}
              <div className="grid grid-cols-1 sm:grid-cols-3 gap-2">
                <div>
                  <label className="text-[10px] font-medium text-gray-500 dark:text-gray-400 block mb-1">
                    District
                  </label>
                  <Input
                    value={district}
                    onChange={(e) => setDistrict(e.target.value)}
                    placeholder="e.g. Kancheepuram"
                    className="text-xs h-8"
                  />
                </div>
                <div>
                  <label className="text-[10px] font-medium text-gray-500 dark:text-gray-400 block mb-1">
                    Taluk
                  </label>
                  <Input
                    value={taluk}
                    onChange={(e) => setTaluk(e.target.value)}
                    placeholder="e.g. Walajabad"
                    className="text-xs h-8"
                  />
                </div>
                <div>
                  <label className="text-[10px] font-medium text-gray-500 dark:text-gray-400 block mb-1">
                    Village
                  </label>
                  <Input
                    value={village}
                    onChange={(e) => setVillage(e.target.value)}
                    placeholder="e.g. Walajabad"
                    className="text-xs h-8"
                  />
                </div>
              </div>
            </div>

            {/* MULTI-SURVEY NUMBERS & SUBDIVISIONS INPUT */}
            <div className="p-4 space-y-3">
              <div className="flex items-center justify-between">
                <h3 className="text-xs font-bold uppercase tracking-wider text-gray-700 dark:text-gray-300 flex items-center gap-1.5">
                  <Layers className="h-3.5 w-3.5 text-emerald-600" />
                  2. Enter Multiple Survey Numbers
                </h3>
                <span className="text-[11px] font-mono text-gray-400">
                  {parcelRows.length} Rows
                </span>
              </div>

              {/* Parcel Input Rows */}
              <div className="space-y-2.5 max-h-[360px] overflow-y-auto pr-1">
                {parcelRows.map((row, idx) => (
                  <div
                    key={row.id}
                    className="flex items-center gap-2 p-2 rounded-xl bg-gray-50 dark:bg-gray-800/60 border border-gray-200 dark:border-gray-700/80"
                  >
                    {/* Row Index Badge with Color indicator */}
                    <span
                      className="w-6 h-6 rounded-full flex items-center justify-center text-[10px] font-bold text-white shrink-0 shadow-2xs"
                      style={{ backgroundColor: row.color }}
                    >
                      {idx + 1}
                    </span>

                    {/* Survey No Input */}
                    <div className="flex-1 min-w-0">
                      <Input
                        value={row.surveyNumber}
                        onChange={(e) => handleUpdateRow(row.id, 'surveyNumber', e.target.value)}
                        placeholder="Survey No (e.g. 217)"
                        className="text-xs h-8 font-mono font-semibold"
                      />
                    </div>

                    {/* Divider slash */}
                    <span className="text-gray-400 font-bold text-xs">/</span>

                    {/* Subdivision Input */}
                    <div className="w-24 shrink-0">
                      <Input
                        value={row.subdivision}
                        onChange={(e) => handleUpdateRow(row.id, 'subdivision', e.target.value)}
                        placeholder="Subdiv (e.g. 6)"
                        className="text-xs h-8 font-mono font-semibold"
                      />
                    </div>

                    {/* Delete Row Button */}
                    <button
                      type="button"
                      onClick={() => handleRemoveRow(row.id)}
                      disabled={parcelRows.length <= 1}
                      title="Remove Row"
                      className="p-1.5 rounded-lg text-gray-400 hover:text-rose-600 hover:bg-rose-50 dark:hover:bg-rose-950/40 transition-colors disabled:opacity-30 disabled:cursor-not-allowed cursor-pointer"
                    >
                      <Trash2 className="h-4 w-4" />
                    </button>
                  </div>
                ))}
              </div>

              {/* Row Control Buttons */}
              <div className="flex items-center justify-between pt-1">
                <button
                  type="button"
                  onClick={handleAddRow}
                  className="text-xs font-semibold text-emerald-700 dark:text-emerald-400 hover:underline flex items-center gap-1 cursor-pointer"
                >
                  <Plus className="h-3.5 w-3.5" />
                  Add Another Survey Parcel
                </button>

                <button
                  type="button"
                  onClick={() => setParcelRows([{ id: 'row-1', surveyNumber: '', subdivision: '', color: PARCEL_COLORS[0] }])}
                  className="text-[11px] text-gray-400 hover:text-gray-600 hover:underline cursor-pointer"
                >
                  Clear All
                </button>
              </div>

              {/* Extraction Submit Action Button */}
              <div className="pt-2">
                <Button
                  onClick={handleExtractAllBoundaries}
                  disabled={loading}
                  className="w-full bg-emerald-600 hover:bg-emerald-700 text-white text-xs font-bold py-2.5 rounded-xl shadow-md flex items-center justify-center gap-2 cursor-pointer"
                >
                  {loading ? (
                    <>
                      <RefreshCw className="h-4 w-4 animate-spin" />
                      <span>{extractingStatus || 'Extracting Boundaries...'}</span>
                    </>
                  ) : (
                    <>
                      <Search className="h-4 w-4" />
                      <span>Extract Boundaries & Generate Combined Sketch</span>
                    </>
                  )}
                </Button>
              </div>

              {/* Extraction Warnings or Error List */}
              {extractionErrors.length > 0 && (
                <div className="p-3 rounded-xl bg-amber-50 dark:bg-amber-950/30 border border-amber-200 dark:border-amber-800 text-xs text-amber-800 dark:text-amber-300 space-y-1">
                  <div className="font-bold flex items-center gap-1.5">
                    <AlertCircle className="h-4 w-4 shrink-0 text-amber-600" />
                    <span>Extraction Notices:</span>
                  </div>
                  <ul className="list-disc list-inside text-[11px] space-y-0.5 text-amber-700 dark:text-amber-400">
                    {extractionErrors.map((err, idx) => (
                      <li key={idx}>{err}</li>
                    ))}
                  </ul>
                </div>
              )}
            </div>
          </Card>
        </div>

        {/* RIGHT PANEL: COMBINED VILLAGE MAP SKETCH VIEWER (8 COLS) */}
        <div className="lg:col-span-8 space-y-4">
          {/* VIEW TABS BAR */}
          <div className="flex flex-wrap items-center justify-between gap-2 p-1.5 bg-white dark:bg-gray-900 rounded-xl border border-gray-200 dark:border-gray-800 text-xs font-medium">
            <div className="flex items-center gap-1 bg-gray-100 dark:bg-gray-800 p-1 rounded-lg">
              <button
                type="button"
                onClick={() => setActiveTab('sketch')}
                className={`px-3 py-1.5 rounded-md transition-all flex items-center gap-1.5 cursor-pointer ${
                  activeTab === 'sketch'
                    ? 'bg-emerald-600 text-white font-bold shadow-xs'
                    : 'text-gray-600 dark:text-gray-300 hover:text-gray-900'
                }`}
              >
                <Grid className="h-3.5 w-3.5" />
                <span>Combined Sketch</span>
              </button>

              <button
                type="button"
                onClick={() => setActiveTab('map')}
                className={`px-3 py-1.5 rounded-md transition-all flex items-center gap-1.5 cursor-pointer ${
                  activeTab === 'map'
                    ? 'bg-emerald-600 text-white font-bold shadow-xs'
                    : 'text-gray-600 dark:text-gray-300 hover:text-gray-900'
                }`}
              >
                <MapPin className="h-3.5 w-3.5" />
                <span>Leaflet Map</span>
              </button>

              <button
                type="button"
                onClick={() => setActiveTab('split')}
                className={`px-3 py-1.5 rounded-md transition-all flex items-center gap-1.5 cursor-pointer ${
                  activeTab === 'split'
                    ? 'bg-emerald-600 text-white font-bold shadow-xs'
                    : 'text-gray-600 dark:text-gray-300 hover:text-gray-900'
                }`}
              >
                <Columns className="h-3.5 w-3.5" />
                <span>Split View</span>
              </button>

              <button
                type="button"
                onClick={() => setActiveTab('table')}
                className={`px-3 py-1.5 rounded-md transition-all flex items-center gap-1.5 cursor-pointer ${
                  activeTab === 'table'
                    ? 'bg-emerald-600 text-white font-bold shadow-xs'
                    : 'text-gray-600 dark:text-gray-300 hover:text-gray-900'
                }`}
              >
                <TableIcon className="h-3.5 w-3.5" />
                <span>Parcel Table</span>
              </button>
            </div>

            <div className="flex items-center gap-2 pr-1 font-mono text-[11px] text-gray-500">
              <CheckCircle2 className="h-3.5 w-3.5 text-emerald-600" />
              <span>{extractedParcels.length} Extracted Parcels</span>
            </div>
          </div>

          {/* TAB CONTENT RENDERERS */}
          {extractedParcels.length > 0 ? (
            <div>
              {/* TAB 1: COMBINED SKETCH SHEET */}
              {activeTab === 'sketch' && (
                <CombinedCadastralSketch
                  parcels={extractedParcels}
                  district={district}
                  taluk={taluk}
                  village={village}
                  title={`Combined Village Map Sketch - ${village}`}
                />
              )}

              {/* TAB 2: LEAFLET MAP */}
              {activeTab === 'map' && (
                <Card className="p-4 border-gray-200 dark:border-gray-800 space-y-3">
                  <div className="flex items-center justify-between text-xs">
                    <span className="font-bold text-gray-900 dark:text-gray-100 flex items-center gap-1.5">
                      <MapPin className="h-4 w-4 text-emerald-600" />
                      OpenStreetMap Interactive Cadastral Viewer
                    </span>
                    <span className="text-gray-400 font-mono text-[11px]">
                      {allVerticesCombined.length} Total Coordinates
                    </span>
                  </div>

                  <CadastralMap
                    vertices={allVerticesCombined.map((v) => ({
                      vertexNumber: v.vertexNumber,
                      latitude: v.latitude,
                      longitude: v.longitude,
                    }))}
                    propertyTitle={`Combined Parcels in ${village}`}
                    className="h-[540px] w-full"
                  />
                </Card>
              )}

              {/* TAB 3: SPLIT VIEW */}
              {activeTab === 'split' && (
                <div className="grid grid-cols-1 xl:grid-cols-2 gap-4">
                  <CombinedCadastralSketch
                    parcels={extractedParcels}
                    district={district}
                    taluk={taluk}
                    village={village}
                  />

                  <Card className="p-4 border-gray-200 dark:border-gray-800 space-y-3">
                    <h4 className="text-xs font-bold text-gray-900 dark:text-gray-100 flex items-center gap-1.5">
                      <MapPin className="h-4 w-4 text-emerald-600" />
                      Live Geographic Map
                    </h4>
                    <CadastralMap
                      vertices={allVerticesCombined.map((v) => ({
                        vertexNumber: v.vertexNumber,
                        latitude: v.latitude,
                        longitude: v.longitude,
                      }))}
                      className="h-[520px] w-full"
                    />
                  </Card>
                </div>
              )}

              {/* TAB 4: PARCEL TABLE & VERTICES DIRECTORY */}
              {activeTab === 'table' && (
                <Card className="border-gray-200 dark:border-gray-800 space-y-4 p-4">
                  <div className="flex items-center justify-between border-b border-gray-100 dark:border-gray-800 pb-3">
                    <div>
                      <h3 className="text-xs font-bold text-gray-900 dark:text-gray-100">
                        Extracted Cadastral Parcels Directory
                      </h3>
                      <p className="text-[11px] text-gray-500">
                        {village} Village, {taluk} Taluk, {district} District
                      </p>
                    </div>

                    <Button
                      onClick={() => {
                        const csvStr = generateCoordinatesCsv(
                          allVerticesCombined,
                          `Combined Parcels - ${village}`
                        );
                        const blob = new Blob([csvStr], { type: 'text/csv' });
                        const url = URL.createObjectURL(blob);
                        const a = document.createElement('a');
                        a.href = url;
                        a.download = `combined_vertices_${village.toLowerCase()}.csv`;
                        a.click();
                      }}
                      variant="outline"
                      className="text-xs py-1 h-8"
                    >
                      <Download className="h-3.5 w-3.5 mr-1" />
                      Download Vertices CSV
                    </Button>
                  </div>

                  <div className="space-y-6">
                    {extractedParcels.map((p) => (
                      <div key={p.id} className="border border-gray-200 dark:border-gray-800 rounded-xl overflow-hidden">
                        <div className="bg-gray-50 dark:bg-gray-800/80 p-3 border-b border-gray-200 dark:border-gray-800 flex flex-wrap items-center justify-between gap-2 text-xs">
                          <div className="flex items-center gap-2">
                            <span className="w-3.5 h-3.5 rounded-full shrink-0 shadow-2xs" style={{ backgroundColor: p.color }} />
                            <span className="font-bold text-gray-900 dark:text-gray-100 font-mono">
                              Survey No: {p.surveyNumber}{p.subdivision ? `/${p.subdivision}` : ''}
                            </span>
                            <Badge variant="outline" className="text-[10px] text-emerald-700 bg-emerald-50">
                              {p.landType || 'Rayathuvari'}
                            </Badge>
                          </div>

                          <div className="flex items-center gap-3 font-mono text-[11px] text-gray-600 dark:text-gray-300">
                            <span>Extent: {p.extentHectares} Ha, {p.extentAres} Ares</span>
                            <span>Owners: {p.owners && p.owners.length > 0 ? p.owners.join(', ') : 'Registered Patta Holder'}</span>
                          </div>
                        </div>

                        {/* Vertices Table */}
                        <div className="overflow-x-auto">
                          <table className="w-full text-left text-xs">
                            <thead className="bg-gray-100/70 dark:bg-gray-900/60 text-[10px] font-bold text-gray-500 uppercase tracking-wider">
                              <tr>
                                <th className="p-2.5 pl-4">Vertex #</th>
                                <th className="p-2.5">Latitude (°N)</th>
                                <th className="p-2.5">Longitude (°E)</th>
                                <th className="p-2.5 pr-4 text-right">Maps Link</th>
                              </tr>
                            </thead>
                            <tbody className="divide-y divide-gray-100 dark:divide-gray-800 font-mono">
                              {p.vertices.map((v) => (
                                <tr key={v.vertexNumber} className="hover:bg-gray-50 dark:hover:bg-gray-800/40">
                                  <td className="p-2.5 pl-4 font-bold text-emerald-700 dark:text-emerald-400">
                                    V{v.vertexNumber}
                                  </td>
                                  <td className="p-2.5">{v.latitude.toFixed(6)}°</td>
                                  <td className="p-2.5">{v.longitude.toFixed(6)}°</td>
                                  <td className="p-2.5 pr-4 text-right font-sans">
                                    <a
                                      href={`https://www.google.com/maps?q=${v.latitude},${v.longitude}`}
                                      target="_blank"
                                      rel="noreferrer"
                                      className="text-[11px] text-blue-600 dark:text-blue-400 hover:underline"
                                    >
                                      Open Google Maps ↗
                                    </a>
                                  </td>
                                </tr>
                              ))}
                            </tbody>
                          </table>
                        </div>
                      </div>
                    ))}
                  </div>
                </Card>
              )}
            </div>
          ) : (
            <Card className="border-gray-200 dark:border-gray-800 p-12 text-center space-y-3">
              <Compass className="h-10 w-10 text-emerald-600 mx-auto animate-spin" />
              <h3 className="text-sm font-bold text-gray-900 dark:text-gray-100">
                Extracting Boundaries & Assembling Combined Village Map...
              </h3>
              <p className="text-xs text-gray-500 max-w-sm mx-auto">
                Connecting to Tamil Nadu GIS dataset and fetching polygon coordinate vertices.
              </p>
            </Card>
          )}
        </div>
      </div>
    </div>
  );
}
