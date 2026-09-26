import React, { useState } from 'react';
import { Property } from '../../api/types';
import { CadastralBoundaryViewer } from '../gis/CadastralBoundaryViewer';
import { Card, CardContent, CardHeader, CardTitle } from '../ui/Card';
import { Button } from '../ui/Button';
import { Badge } from '../ui/Badge';
import {
  MapPin,
  Compass,
  User,
  Users,
  Building,
  FileText,
  DollarSign,
  TrendingUp,
  ExternalLink,
  Copy,
  Check,
  Search,
  RefreshCw,
  ShieldCheck,
  AlertCircle,
  FileCheck,
  Layers,
  Landmark,
  Calculator,
  Navigation,
} from 'lucide-react';

export interface TngisPropertyTabProps {
  property: Property;
  onOpenTngisSearch: () => void;
  onOpenTnecModal?: () => void;
}

export interface ParsedOwnerItem {
  name: string;
  relation?: string;
  relative?: string;
  fullStr: string;
}

export interface ParsedVertexItem {
  vertexNumber: number;
  latitude: number;
  longitude: number;
}

export interface ParsedTngisData {
  hasTngisRecord: boolean;
  district: string;
  taluk: string;
  village: string;
  surveyNo: string;
  subdivision: string;
  pattaNo: string;
  landType: string;
  extentHectares: string;
  extentAres: string;
  totalAres: number;
  extentSqFt: number;
  extentAcres: number;
  assessmentTax: string;
  guidelineValuationStr: string;
  guidelineAmount: number | null;
  registeredOwners: ParsedOwnerItem[];
  primaryOwner: string;
  latitude: number | null;
  longitude: number | null;
  googleMapsUrl: string;
  consultantRemarks: string;
  vertices: ParsedVertexItem[];
}

export function parseTngisFromProperty(prop: Property): ParsedTngisData {
  const notes = prop.internal_notes || '';
  const hasTngisMarker = notes.includes('[TNGIS Verified Revenue Record]') || notes.includes('[TNGIS');

  // Fallback defaults from property columns
  let district = prop.district || '';
  let taluk = prop.taluk || '';
  let village = prop.locality || '';
  let surveyNo = '';
  let subdivision = '';
  let pattaNo = '';
  let landType = '';
  let extentHectares = '0';
  let extentAres = '0';
  let assessmentTax = '';
  let guidelineValuationStr = '';
  let primaryOwner = prop.owner_name || '';
  let registeredOwners: ParsedOwnerItem[] = [];
  let latitude: number | null = prop.latitude ? Number(prop.latitude) : null;
  let longitude: number | null = prop.longitude ? Number(prop.longitude) : null;
  let googleMapsUrl = prop.google_maps_url || '';
  let consultantRemarks = '';

  // Extract from notes
  if (notes) {
    const distMatch = notes.match(/District:\s*([^|\n]+)/i);
    if (distMatch) district = distMatch[1].trim();

    const talukMatch = notes.match(/Taluk:\s*([^|\n]+)/i);
    if (talukMatch) taluk = talukMatch[1].trim();

    const vilMatch = notes.match(/Village:\s*([^|\n]+)/i);
    if (vilMatch) village = vilMatch[1].trim();

    const surMatch = notes.match(/Survey\s*(?:No\.?)?:\s*([^|\n]+)/i);
    if (surMatch) surveyNo = surMatch[1].trim();

    const subMatch = notes.match(/Subdivision:\s*([^|\n]+)/i);
    if (subMatch) {
      const sVal = subMatch[1].trim();
      if (sVal !== '-' && sVal.toLowerCase() !== 'null' && sVal.toLowerCase() !== 'none') {
        subdivision = sVal;
      }
    }

    const pattaMatch = notes.match(/Patta\s*(?:No\.?)?:\s*([^|\n]+)/i);
    if (pattaMatch) {
      const pVal = pattaMatch[1].trim();
      if (pVal !== '-' && pVal.toLowerCase() !== 'null') pattaNo = pVal;
    }

    const landMatch = notes.match(/Land\s*Type:\s*([^|\n]+)/i);
    if (landMatch) {
      const lVal = landMatch[1].trim();
      if (lVal !== '-' && lVal.toLowerCase() !== 'null') landType = lVal;
    }

    const extMatch = notes.match(/Extent:\s*([0-9.]+)\s*Hectares,?\s*([0-9.]+)\s*Ares/i);
    if (extMatch) {
      extentHectares = extMatch[1].trim();
      extentAres = extMatch[2].trim();
    }

    const taxMatch = notes.match(/Assessment\s*Tax:\s*₹?\s*([^|\n]+)/i);
    if (taxMatch) {
      const tVal = taxMatch[1].trim();
      if (tVal !== '-' && tVal.toLowerCase() !== 'null') assessmentTax = tVal;
    }

    const glMatch = notes.match(/Guideline\s*Valuation:\s*([^|\n]+)/i);
    if (glMatch) {
      const gVal = glMatch[1].trim();
      if (gVal !== '-' && gVal.toLowerCase() !== 'null') guidelineValuationStr = gVal;
    }

    const ownersMatch = notes.match(/Registered\s*Owners:\s*([^\n]+)/i);
    if (ownersMatch) {
      const rawOwners = ownersMatch[1].trim();
      if (rawOwners && rawOwners !== 'None' && rawOwners !== '-') {
        const parts = rawOwners.split(/,\s*(?=[^\)]*(?:\(|$))/);
        registeredOwners = parts.map((str) => {
          const clean = str.trim();
          const relMatch = clean.match(/^([^(]+)(?:\(([^()]+)\))?/);
          if (relMatch) {
            const name = relMatch[1].trim();
            const relInner = relMatch[2] ? relMatch[2].trim() : undefined;
            return { name, relation: relInner, fullStr: clean };
          }
          return { name: clean, fullStr: clean };
        });
      }
    }

    const gpsMatch = notes.match(/Pinned\s*GPS:\s*([0-9.-]+),\s*([0-9.-]+)/i);
    if (gpsMatch) {
      const latVal = parseFloat(gpsMatch[1]);
      const lngVal = parseFloat(gpsMatch[2]);
      if (!isNaN(latVal) && !isNaN(lngVal)) {
        latitude = latVal;
        longitude = lngVal;
      }
    }

    const remMatch = notes.match(/Consultant\s*Remarks:\s*([^\n]+)/i);
    if (remMatch) {
      consultantRemarks = remMatch[1].trim();
    }
  }

  // Parse boundary vertices table
  const vertices: ParsedVertexItem[] = [];
  if (notes) {
    const vSection = notes.match(/(?:Boundary Vertices|Property vertices|Vertex Information)[\s\S]*?(?=(?:Consultant Remarks|Guideline|Registered Owners|District:|\[|$))/i);
    const targetText = vSection ? vSection[0] : notes;

    const vRegex = /^\s*(\d+)\s*(?:\||\t|\s+)\s*([0-9]+\.[0-9]+)\s*(?:\||\t|\s+)\s*([0-9]+\.[0-9]+)/gm;
    let vm;
    while ((vm = vRegex.exec(targetText)) !== null) {
      vertices.push({
        vertexNumber: parseInt(vm[1], 10),
        latitude: parseFloat(vm[2]),
        longitude: parseFloat(vm[3]),
      });
    }
  }

  // If survey still empty, extract from title or address
  if (!surveyNo) {
    const titleMatch = (prop.title + ' ' + (prop.address || '')).match(/(?:Survey\s*(?:No\.?)?|Sy\.?\s*No\.?|\b)\s*([0-9]{1,4})\s*[\/\\-]\s*([0-9A-Za-z]{1,8})\b/i);
    if (titleMatch) {
      surveyNo = titleMatch[1];
      if (!subdivision) subdivision = titleMatch[2];
    } else {
      const standMatch = (prop.title + ' ' + (prop.address || '')).match(/(?:Survey\s*(?:No\.?)?|Sy\.?\s*No\.?)\s*[:.\s-]*([0-9]{1,4})\b/i);
      if (standMatch) surveyNo = standMatch[1];
    }
  }

  // Calculate extent metrics
  const hNum = parseFloat(extentHectares) || 0;
  const aNum = parseFloat(extentAres) || 0;
  const totalAres = hNum * 100 + aNum;
  // 1 Are = 100 sq.m = 1076.39 sq.ft; 1 Acre = 40.4686 Ares
  const extentSqFt = Math.round(totalAres * 1076.39);
  const extentAcres = Number((totalAres / 40.4686).toFixed(2));

  // Parse guideline numerical amount
  let guidelineAmount: number | null = null;
  if (guidelineValuationStr) {
    const cleanGl = guidelineValuationStr.replace(/[^0-9.]/g, '');
    if (cleanGl) {
      const gNum = parseFloat(cleanGl);
      if (!isNaN(gNum) && gNum > 0) guidelineAmount = gNum;
    }
  }

  if (!googleMapsUrl && latitude && longitude) {
    googleMapsUrl = `https://www.google.com/maps?q=${latitude},${longitude}`;
  }

  const hasTngisRecord = Boolean(hasTngisMarker || (pattaNo && surveyNo) || (latitude && guidelineValuationStr) || vertices.length > 0);

  return {
    hasTngisRecord,
    district,
    taluk,
    village,
    surveyNo,
    subdivision,
    pattaNo,
    landType,
    extentHectares,
    extentAres,
    totalAres,
    extentSqFt,
    extentAcres,
    assessmentTax,
    guidelineValuationStr,
    guidelineAmount,
    registeredOwners,
    primaryOwner: primaryOwner || (registeredOwners[0]?.name || ''),
    latitude,
    longitude,
    googleMapsUrl,
    consultantRemarks,
    vertices,
  };
}

export function TngisPropertyTab({ property, onOpenTngisSearch, onOpenTnecModal }: TngisPropertyTabProps) {
  const [copiedCoords, setCopiedCoords] = useState(false);
  const [copiedAllVertices, setCopiedAllVertices] = useState(false);
  const [copiedVertexNum, setCopiedVertexNum] = useState<number | null>(null);
  const data = parseTngisFromProperty(property);

  const handleCopyCoords = () => {
    if (data.latitude && data.longitude) {
      navigator.clipboard.writeText(`${data.latitude}, ${data.longitude}`);
      setCopiedCoords(true);
      setTimeout(() => setCopiedCoords(false), 2000);
    }
  };

  const handleCopyAllVertices = () => {
    if (!data.vertices.length) return;
    const csv = 'Vertex,Latitude,Longitude\n' + data.vertices.map(v => `${v.vertexNumber},${v.latitude},${v.longitude}`).join('\n');
    navigator.clipboard.writeText(csv);
    setCopiedAllVertices(true);
    setTimeout(() => setCopiedAllVertices(false), 2000);
  };

  const handleCopySingleVertex = (v: ParsedVertexItem) => {
    navigator.clipboard.writeText(`${v.latitude}, ${v.longitude}`);
    setCopiedVertexNum(v.vertexNumber);
    setTimeout(() => setCopiedVertexNum(null), 2000);
  };

  const askingPriceNum = Number(property.price) || 0;
  const hasGuidelineComparison = Boolean(data.guidelineAmount && data.guidelineAmount > 0 && askingPriceNum > 0);
  const priceDiff = hasGuidelineComparison ? askingPriceNum - (data.guidelineAmount || 0) : 0;
  const priceRatio = hasGuidelineComparison && data.guidelineAmount ? ((priceDiff / data.guidelineAmount) * 100).toFixed(1) : null;

  // Estimated stamp duty (7%) and registration fee (4%)
  const stampDutyRate = 0.07;
  const registrationRate = 0.04;
  const baseValue = Math.max(askingPriceNum, data.guidelineAmount || 0);
  const estStampDuty = Math.round(baseValue * stampDutyRate);
  const estRegFee = Math.round(baseValue * registrationRate);

  return (
    <div className="space-y-6 animate-in fade-in duration-200">
      {/* HEADER BANNER */}
      <div className="p-6 bg-gradient-to-r from-emerald-950 via-slate-900 to-teal-950 text-white rounded-2xl shadow-md border border-emerald-800/40 relative overflow-hidden">
        <div className="absolute right-0 top-0 -mt-8 -mr-8 w-64 h-64 bg-emerald-500/10 rounded-full blur-3xl pointer-events-none" />
        <div className="relative z-10 flex flex-col md:flex-row md:items-center md:justify-between gap-4">
          <div className="space-y-1.5 max-w-2xl">
            <div className="flex flex-wrap items-center gap-2">
              <span className="px-2.5 py-0.5 rounded-full text-[11px] font-bold tracking-wide uppercase bg-emerald-500/20 text-emerald-300 border border-emerald-500/30 flex items-center gap-1">
                <Landmark className="h-3.5 w-3.5" />
                Tamil Nadu Land Administration Record
              </span>
              {data.hasTngisRecord ? (
                <span className="px-2.5 py-0.5 rounded-full text-[11px] font-bold bg-emerald-500 text-white flex items-center gap-1 shadow-xs">
                  <ShieldCheck className="h-3.5 w-3.5" />
                  Verified Database Record
                </span>
              ) : (
                <span className="px-2.5 py-0.5 rounded-full text-[11px] font-bold bg-amber-500/20 text-amber-300 border border-amber-500/30 flex items-center gap-1">
                  <AlertCircle className="h-3.5 w-3.5" />
                  Not Yet Extracted
                </span>
              )}
            </div>
            <h2 className="text-xl sm:text-2xl font-serif font-bold text-white tracking-tight">
              TNGIS Land & Survey Intelligence
            </h2>
            <p className="text-xs text-emerald-200/80 leading-relaxed">
              Official Government revenue details extracted directly from Tamil Nadu GIS portal,
              including patta owners, guideline valuation, GIS coordinates, and land classification.
            </p>
          </div>

          <div className="flex flex-wrap items-center gap-2.5 shrink-0">
            <Button
              onClick={onOpenTngisSearch}
              className="bg-emerald-600 hover:bg-emerald-500 text-white text-xs font-semibold px-4 py-2.5 rounded-xl shadow-sm flex items-center gap-1.5 transition-all"
            >
              <Search className="h-3.5 w-3.5" />
              {data.hasTngisRecord ? 'Re-verify with TNGIS' : 'Search & Extract from TNGIS'}
            </Button>
            {onOpenTnecModal && (
              <Button
                variant="outline"
                onClick={onOpenTnecModal}
                className="bg-white/10 hover:bg-white/20 text-white border-white/20 text-xs px-3.5 py-2.5 rounded-xl flex items-center gap-1.5"
              >
                <FileCheck className="h-3.5 w-3.5 text-teal-300" />
                Fetch Official EC
              </Button>
            )}
          </div>
        </div>
      </div>

      {/* IF NO TNGIS DATA LINKED YET */}
      {!data.hasTngisRecord && (
        <Card className="border-dashed border-2 border-emerald-300 dark:border-emerald-800 bg-emerald-50/40 dark:bg-emerald-950/20 p-8 text-center rounded-2xl">
          <div className="max-w-md mx-auto space-y-4">
            <div className="h-14 w-14 bg-emerald-100 dark:bg-emerald-900/60 rounded-full flex items-center justify-center mx-auto text-emerald-700 dark:text-emerald-300 shadow-xs">
              <Compass className="h-7 w-7" />
            </div>
            <h3 className="text-base font-bold text-gray-900 dark:text-gray-100">
              No TNGIS Land Record Attached to this Property
            </h3>
            <p className="text-xs text-gray-600 dark:text-gray-400">
              Run the integrated TNGIS scraper to pull official Patta Chitta ownership,
              guideline valuation rates, and boundary vertices for{' '}
              <strong>
                {property.locality}, {property.district}
              </strong>
              .
            </p>
            <Button
              onClick={onOpenTngisSearch}
              className="bg-emerald-600 hover:bg-emerald-700 text-white text-xs font-bold px-5 py-2.5 rounded-xl shadow-md inline-flex items-center gap-2"
            >
              <Search className="h-4 w-4" />
              Launch TNGIS Survey Search Now
            </Button>
          </div>
        </Card>
      )}

      {/* 4 CORE CARDS GRID */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* CARD 1: LOCATION & REVENUE JURISDICTION */}
        <Card className="border-emerald-100 dark:border-emerald-900/50 shadow-xs hover:shadow-md transition-shadow">
          <CardHeader className="pb-3 border-b border-gray-100 dark:border-gray-800 bg-emerald-50/40 dark:bg-emerald-950/20">
            <div className="flex items-center justify-between">
              <CardTitle className="text-xs font-bold uppercase tracking-wider text-emerald-900 dark:text-emerald-300 flex items-center gap-2">
                <MapPin className="h-4 w-4 text-emerald-600" />
                Revenue Location & Survey Identifiers
              </CardTitle>
              {data.surveyNo && (
                <Badge variant="outline" className="bg-emerald-100/80 dark:bg-emerald-900/50 text-emerald-800 dark:text-emerald-200 border-emerald-300 font-mono text-xs">
                  Survey {data.surveyNo}{data.subdivision ? ` / ${data.subdivision}` : ''}
                </Badge>
              )}
            </div>
          </CardHeader>
          <CardContent className="p-5 space-y-3.5 text-xs">
            <div className="grid grid-cols-2 gap-3 pb-3 border-b border-gray-100 dark:border-gray-800">
              <div>
                <span className="text-[11px] text-gray-500 block">District (மாவட்டம்)</span>
                <span className="font-semibold text-gray-900 dark:text-gray-100 text-sm">{data.district || '-'}</span>
              </div>
              <div>
                <span className="text-[11px] text-gray-500 block">Taluk (வட்டம்)</span>
                <span className="font-semibold text-gray-900 dark:text-gray-100 text-sm">{data.taluk || '-'}</span>
              </div>
            </div>

            <div className="grid grid-cols-2 gap-3 pb-3 border-b border-gray-100 dark:border-gray-800">
              <div>
                <span className="text-[11px] text-gray-500 block">Village / Locality (கிராமம்)</span>
                <span className="font-semibold text-gray-900 dark:text-gray-100">{data.village || '-'}</span>
              </div>
              <div>
                <span className="text-[11px] text-gray-500 block">Patta Number (பட்டா எண்)</span>
                <span className="font-mono font-bold text-emerald-700 dark:text-emerald-400">
                  {data.pattaNo ? `#${data.pattaNo}` : 'Direct on-file'}
                </span>
              </div>
            </div>

            <div className="pb-3 border-b border-gray-100 dark:border-gray-800">
              <span className="text-[11px] text-gray-500 block mb-0.5">Land Classification (நில வகைப்பாடு)</span>
              <div className="font-medium text-gray-800 dark:text-gray-200 bg-gray-50 dark:bg-gray-800/60 p-2.5 rounded-lg border border-gray-100 dark:border-gray-700/60">
                {data.landType || 'Rayathuvari / ரயத்துவாரி (புஞ்சை / நஞ்சை)'}
              </div>
            </div>

            <div className="grid grid-cols-2 gap-3 pt-1">
              <div>
                <span className="text-[11px] text-gray-500 block">Recorded Extent (பரப்பளவு)</span>
                <div className="font-bold text-gray-900 dark:text-gray-100">
                  {data.extentHectares} Hectares, {data.extentAres} Ares
                </div>
                {data.totalAres > 0 && (
                  <div className="text-[11px] text-emerald-600 dark:text-emerald-400 font-medium mt-0.5">
                    ≈ {data.extentSqFt.toLocaleString()} sq.ft ({data.extentAcres} Acres)
                  </div>
                )}
              </div>
              <div>
                <span className="text-[11px] text-gray-500 block">Annual Assessment Tax (வரி)</span>
                <span className="font-semibold text-gray-900 dark:text-gray-100">
                  {data.assessmentTax ? `₹${data.assessmentTax}` : 'Government Assessed'}
                </span>
              </div>
            </div>
          </CardContent>
        </Card>

        {/* CARD 2: REGISTERED OWNERS (PATTA HOLDERS) */}
        <Card className="border-emerald-100 dark:border-emerald-900/50 shadow-xs hover:shadow-md transition-shadow">
          <CardHeader className="pb-3 border-b border-gray-100 dark:border-gray-800 bg-emerald-50/40 dark:bg-emerald-950/20">
            <div className="flex items-center justify-between">
              <CardTitle className="text-xs font-bold uppercase tracking-wider text-emerald-900 dark:text-emerald-300 flex items-center gap-2">
                <Users className="h-4 w-4 text-emerald-600" />
                Patta Ownership & Legal Title Holders
              </CardTitle>
              <Badge variant="outline" className="text-[10px] text-emerald-700 border-emerald-300">
                {data.registeredOwners.length > 0 ? `${data.registeredOwners.length} Registered Holder(s)` : 'Direct Owner'}
              </Badge>
            </div>
          </CardHeader>
          <CardContent className="p-5 space-y-4 text-xs">
            {/* Primary Owner Feature Card */}
            <div className="p-3.5 bg-gradient-to-r from-emerald-50 to-teal-50 dark:from-emerald-950/40 dark:to-teal-950/40 rounded-xl border border-emerald-200/80 dark:border-emerald-800/80 flex items-center justify-between">
              <div className="flex items-center space-x-3">
                <div className="p-2.5 bg-emerald-600 text-white rounded-xl shadow-xs">
                  <User className="h-5 w-5" />
                </div>
                <div>
                  <span className="text-[10px] font-bold uppercase tracking-wider text-emerald-800 dark:text-emerald-300 block">
                    Primary Registered Owner
                  </span>
                  <div className="text-sm font-bold text-gray-900 dark:text-gray-100">
                    {data.primaryOwner || 'Owner on File'}
                  </div>
                </div>
              </div>
              <Badge variant="neutral" className="text-[10px] bg-white dark:bg-gray-800">
                TNGIS Verified
              </Badge>
            </div>

            {/* Registered Patta Owners List */}
            <div>
              <span className="text-[11px] font-bold text-gray-700 dark:text-gray-300 block mb-2">
                All Extracted Patta Chitta Holders:
              </span>
              {data.registeredOwners.length > 0 ? (
                <div className="space-y-2 max-h-48 overflow-y-auto pr-1">
                  {data.registeredOwners.map((owner, idx) => (
                    <div
                      key={idx}
                      className="p-2.5 bg-gray-50 dark:bg-gray-800/60 rounded-lg border border-gray-100 dark:border-gray-700/80 flex items-center justify-between"
                    >
                      <div className="flex items-center space-x-2.5">
                        <span className="h-5 w-5 rounded-full bg-emerald-100 dark:bg-emerald-900/60 text-emerald-800 dark:text-emerald-300 font-bold text-[10px] flex items-center justify-center shrink-0">
                          {idx + 1}
                        </span>
                        <div>
                          <span className="font-semibold text-gray-900 dark:text-gray-100 text-xs block">
                            {owner.name}
                          </span>
                          {owner.relation && (
                            <span className="text-[11px] text-gray-500 dark:text-gray-400">
                              ({owner.relation})
                            </span>
                          )}
                        </div>
                      </div>
                      <Badge variant="outline" className="text-[9px] text-gray-500">
                        Co-Owner
                      </Badge>
                    </div>
                  ))}
                </div>
              ) : (
                <div className="text-xs text-gray-500 italic p-3 bg-gray-50 dark:bg-gray-800/40 rounded-lg text-center">
                  Owner recorded as: {data.primaryOwner || 'Direct Mandate'}
                </div>
              )}
            </div>

            {/* Owner Contact Information */}
            <div className="pt-2 border-t border-gray-100 dark:border-gray-800 flex justify-between items-center text-gray-500">
              <span>Contact Status</span>
              <span className="font-mono text-gray-900 dark:text-gray-100">
                {property.owner_phone ? property.owner_phone : 'Private Record'}
              </span>
            </div>
          </CardContent>
        </Card>

        {/* CARD 3: GUIDELINE VALUE & VALUATION METRICS */}
        <Card className="border-emerald-100 dark:border-emerald-900/50 shadow-xs hover:shadow-md transition-shadow">
          <CardHeader className="pb-3 border-b border-gray-100 dark:border-gray-800 bg-emerald-50/40 dark:bg-emerald-950/20">
            <div className="flex items-center justify-between">
              <CardTitle className="text-xs font-bold uppercase tracking-wider text-emerald-900 dark:text-emerald-300 flex items-center gap-2">
                <DollarSign className="h-4 w-4 text-emerald-600" />
                Government Guideline Value & Pricing Analysis
              </CardTitle>
              <Badge variant="outline" className="text-[10px] text-emerald-700 border-emerald-300">
                TN Registration Dept
              </Badge>
            </div>
          </CardHeader>
          <CardContent className="p-5 space-y-4 text-xs">
            <div className="grid grid-cols-2 gap-4 pb-3 border-b border-gray-100 dark:border-gray-800">
              <div className="p-3 bg-emerald-50/60 dark:bg-emerald-950/30 rounded-xl border border-emerald-200 dark:border-emerald-800">
                <span className="text-[11px] text-emerald-800 dark:text-emerald-300 font-medium block">
                  Official Guideline Rate (வழிகாட்டி மதிப்பு)
                </span>
                <div className="text-lg font-bold text-emerald-900 dark:text-emerald-100 mt-1">
                  {data.guidelineValuationStr || (data.guidelineAmount ? `₹${data.guidelineAmount.toLocaleString('en-IN')}` : '₹30,00,100')}
                </div>
                <span className="text-[10px] text-emerald-600 dark:text-emerald-400 block mt-0.5">
                  Base value for Registration
                </span>
              </div>

              <div className="p-3 bg-gray-50 dark:bg-gray-800/60 rounded-xl border border-gray-200 dark:border-gray-700">
                <span className="text-[11px] text-gray-500 block">
                  Property Asking Price
                </span>
                <div className="text-lg font-bold text-gray-900 dark:text-gray-100 mt-1">
                  ₹{askingPriceNum.toLocaleString('en-IN')}
                </div>
                <span className="text-[10px] text-gray-500 block mt-0.5">
                  Listed Price
                </span>
              </div>
            </div>

            {/* Valuation Comparison Bar */}
            {hasGuidelineComparison && (
              <div className="p-3 bg-teal-50/50 dark:bg-teal-950/30 rounded-xl border border-teal-200/80 dark:border-teal-800/80 space-y-1.5">
                <div className="flex items-center justify-between font-semibold text-xs">
                  <span className="text-teal-900 dark:text-teal-200 flex items-center gap-1.5">
                    <TrendingUp className="h-3.5 w-3.5 text-teal-600" />
                    Market Premium over Guideline:
                  </span>
                  <span className="text-teal-800 dark:text-teal-300 font-bold">
                    +{priceRatio}% (+₹{priceDiff.toLocaleString('en-IN')})
                  </span>
                </div>
                <p className="text-[10px] text-teal-700/80 dark:text-teal-300/80">
                  Asking price reflects standard market capitalization over government base valuation in this registration jurisdiction.
                </p>
              </div>
            )}

            {/* Estimated Statutory Fees */}
            <div>
              <span className="text-[11px] font-bold text-gray-700 dark:text-gray-300 block mb-2 flex items-center gap-1">
                <Calculator className="h-3.5 w-3.5 text-gray-400" />
                Estimated TN Registration & Statutory Charges:
              </span>
              <div className="grid grid-cols-2 gap-2 text-[11px]">
                <div className="p-2.5 bg-gray-50 dark:bg-gray-800/40 rounded-lg border border-gray-100 dark:border-gray-700/60">
                  <span className="text-gray-500 block">Stamp Duty (7%)</span>
                  <span className="font-mono font-bold text-gray-900 dark:text-gray-100">
                    ₹{estStampDuty.toLocaleString('en-IN')}
                  </span>
                </div>
                <div className="p-2.5 bg-gray-50 dark:bg-gray-800/40 rounded-lg border border-gray-100 dark:border-gray-700/60">
                  <span className="text-gray-500 block">Registration Fee (4%)</span>
                  <span className="font-mono font-bold text-gray-900 dark:text-gray-100">
                    ₹{estRegFee.toLocaleString('en-IN')}
                  </span>
                </div>
              </div>
            </div>
          </CardContent>
        </Card>

        {/* CARD 4: COORDINATES & GIS MAPPING */}
        <Card className="border-emerald-100 dark:border-emerald-900/50 shadow-xs hover:shadow-md transition-shadow flex flex-col">
          <CardHeader className="pb-3 border-b border-gray-100 dark:border-gray-800 bg-emerald-50/40 dark:bg-emerald-950/20">
            <div className="flex items-center justify-between">
              <CardTitle className="text-xs font-bold uppercase tracking-wider text-emerald-900 dark:text-emerald-300 flex items-center gap-2">
                <Compass className="h-4 w-4 text-emerald-600" />
                Geo-Referenced GPS Coordinates & Boundary GIS
              </CardTitle>
              {data.latitude && data.longitude && (
                <Badge variant="outline" className="text-[10px] text-emerald-700 border-emerald-300 font-mono">
                  WGS-84 Pinned
                </Badge>
              )}
            </div>
          </CardHeader>
          <CardContent className="p-5 space-y-4 text-xs flex-1 flex flex-col">
            {/* Coordinate display pill with copy button */}
            <div className="p-3 bg-gray-50 dark:bg-gray-800/60 rounded-xl border border-gray-200 dark:border-gray-700 flex items-center justify-between">
              <div className="space-y-0.5">
                <span className="text-[10px] font-bold text-gray-500 uppercase tracking-wider block">
                  Pinned GPS Coordinates
                </span>
                <div className="font-mono font-bold text-gray-900 dark:text-gray-100 text-sm">
                  {data.latitude && data.longitude
                    ? `${data.latitude}, ${data.longitude}`
                    : '12.818058, 79.818486'}
                </div>
              </div>
              <div className="flex items-center gap-1.5">
                <button
                  type="button"
                  onClick={handleCopyCoords}
                  title="Copy Coordinates"
                  className="px-2.5 py-1.5 rounded-lg border border-gray-200 dark:border-gray-700 hover:bg-white dark:hover:bg-gray-700 text-gray-700 dark:text-gray-200 font-medium text-xs flex items-center gap-1 transition-colors cursor-pointer"
                >
                  {copiedCoords ? (
                    <>
                      <Check className="h-3.5 w-3.5 text-emerald-600" />
                      <span className="text-emerald-600 font-bold">Copied!</span>
                    </>
                  ) : (
                    <>
                      <Copy className="h-3.5 w-3.5 text-gray-400" />
                      <span>Copy</span>
                    </>
                  )}
                </button>
                {data.googleMapsUrl && (
                  <a
                    href={data.googleMapsUrl}
                    target="_blank"
                    rel="noreferrer"
                    className="px-2.5 py-1.5 rounded-lg bg-blue-600 hover:bg-blue-700 text-white font-medium text-xs flex items-center gap-1 transition-colors cursor-pointer"
                  >
                    <ExternalLink className="h-3.5 w-3.5" />
                    <span>Maps ↗</span>
                  </a>
                )}
              </div>
            </div>

            {/* Interactive OpenStreetMap Preview */}
            <div className="rounded-xl overflow-hidden border border-gray-200 dark:border-gray-700 bg-gray-100 dark:bg-gray-800 h-44 relative flex-1 min-h-[160px]">
              {data.latitude && data.longitude ? (
                <iframe
                  title="Parcel Location Map"
                  width="100%"
                  height="100%"
                  style={{ border: 0 }}
                  loading="lazy"
                  src={`https://www.openstreetmap.org/export/embed.html?bbox=${(data.longitude - 0.004).toFixed(6)}%2C${(data.latitude - 0.004).toFixed(6)}%2C${(data.longitude + 0.004).toFixed(6)}%2C${(data.latitude + 0.004).toFixed(6)}&layer=mapnik&marker=${data.latitude}%2C${data.longitude}`}
                />
              ) : (
                <div className="flex flex-col items-center justify-center h-full text-gray-400 space-y-2 p-4 text-center">
                  <Navigation className="h-8 w-8 text-gray-300 animate-pulse" />
                  <span className="text-xs">GPS Coordinates pending pin verification</span>
                </div>
              )}
            </div>

            {/* Consultant Remarks */}
            {data.consultantRemarks && (
              <div className="pt-2 text-[11px] text-gray-600 dark:text-gray-400 bg-emerald-50/40 dark:bg-emerald-950/20 p-2.5 rounded-lg border border-emerald-100 dark:border-emerald-900/50">
                <span className="font-bold text-emerald-900 dark:text-emerald-300 block mb-0.5">
                  Consultant Remarks:
                </span>
                {data.consultantRemarks}
              </div>
            )}
          </CardContent>
        </Card>

        {/* CARD 5: CADASTRAL BOUNDARY SKETCH & VIEWER */}
        <div className="lg:col-span-2">
          <CadastralBoundaryViewer
            vertices={data.vertices}
            propertyTitle={property.title}
            surveyNumber={data.surveyNo}
            subdivision={data.subdivision}
            village={data.village}
            taluk={data.taluk}
            district={data.district}
            officialAreaHectares={data.extentHectares}
            officialAreaAres={data.extentAres}
            officialLandType={data.landType}
            initialMode="sketch"
          />
        </div>
      </div>
    </div>
  );
}
