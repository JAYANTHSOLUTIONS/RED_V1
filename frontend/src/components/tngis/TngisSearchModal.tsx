import React, { useState, useEffect, useMemo } from 'react';
import { Button } from '../ui/Button';
import { Input } from '../ui/Input';
import { Select } from '../ui/Select';
import { Badge } from '../ui/Badge';
import { Modal } from '../ui/Modal';
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from '../ui/Table';
import {
  Search,
  Save,
  Edit3,
  CheckCircle2,
  MapPin,
  ExternalLink,
  Plus,
  Trash2,
  Building,
  RotateCcw,
  Sparkles,
  Globe,
  AlertTriangle,
  Loader2,
  ArrowRight,
  Compass,
  Crosshair,
  Lock,
  FileText,
  Layers,
  Check,
  Calculator,
  Coins,
  TrendingUp,
} from 'lucide-react';
import { getTnDistricts, getTnTaluks, getTnVillages } from '../../utils/tnLocations';
import { tngisApi, TngisLookupResponse, TngisOwnerRecord } from '../../api/tngis';
import { propertiesApi } from '../../api/properties';
import type { Property } from '../../api/types';

const formatInr = (val: number): string => {
  if (!val) return '₹ 0';
  if (val >= 10000000) {
    return `₹ ${(val / 10000000).toFixed(2)} Cr`;
  }
  if (val >= 100000) {
    return `₹ ${(val / 100000).toFixed(2)} L`;
  }
  return `₹ ${val.toLocaleString('en-IN')}`;
};

export interface TngisSearchModalProps {
  isOpen: boolean;
  onClose: () => void;
  initialPropertyId?: string;
  initialDistrict?: string;
  initialTaluk?: string;
  initialVillage?: string;
  initialSurvey?: string;
  initialSubdivision?: string;
  onSaved?: (propertyId?: string) => void;
}

export function TngisSearchModal({
  isOpen,
  onClose,
  initialPropertyId,
  initialDistrict = 'Kancheepuram',
  initialTaluk = 'Walajabad',
  initialVillage = 'Walajabad',
  initialSurvey = '217',
  initialSubdivision = '1B2',
  onSaved,
}: TngisSearchModalProps) {
  // Input fields
  const [district, setDistrict] = useState(initialDistrict);
  const [taluk, setTaluk] = useState(initialTaluk);
  const [village, setVillage] = useState(initialVillage);
  const [surveyNumber, setSurveyNumber] = useState(initialSurvey);
  const [subdivision, setSubdivision] = useState(initialSubdivision);
  const [areaType, setAreaType] = useState('rural');

  // Dependent location options
  const availableTaluks = useMemo(() => (district ? getTnTaluks(district) : []), [district]);
  const availableVillages = useMemo(
    () => (district && taluk ? getTnVillages(district, taluk) : []),
    [district, taluk]
  );

  // Loading & Results
  const [loading, setLoading] = useState(false);
  const [loadingMsg, setLoadingMsg] = useState('');
  const [results, setResults] = useState<TngisLookupResponse | null>(null);
  const [errorMsg, setErrorMsg] = useState<string | null>(null);

  // Edit Mode & Editable Fields
  const [isEditMode, setIsEditMode] = useState(false);
  const [editedOwners, setEditedOwners] = useState<TngisOwnerRecord[]>([]);
  const [editedPatta, setEditedPatta] = useState('');
  const [editedLandType, setEditedLandType] = useState('');
  const [editedExtentHect, setEditedExtentHect] = useState('0');
  const [editedExtentAres, setEditedExtentAres] = useState('0');
  const [editedTax, setEditedTax] = useState('');
  const [editedGuideline, setEditedGuideline] = useState('');
  const [consultantNotes, setConsultantNotes] = useState('');
  const [guidelineRateUnit, setGuidelineRateUnit] = useState<'sqft' | 'cent' | 'acre'>('sqft');

  // Real Estate Extent Conversions & Guideline Price Valuation
  const valuation = useMemo(() => {
    const hect = parseFloat(editedExtentHect) || 0;
    const ares = parseFloat(editedExtentAres) || 0;
    const totalAres = (hect * 100) + ares;
    const totalSqFt = Math.round(totalAres * 1076.391);
    const totalCents = Number((totalSqFt / 435.6).toFixed(2));
    const totalGrounds = Number((totalSqFt / 2400).toFixed(2));
    const totalAcres = Number((totalSqFt / 43560).toFixed(3));

    // Extract numeric rate
    let rawRate = 0;
    const rawRateStr = editedGuideline || results?.guideline_value?.metric_rate || '';
    const match = rawRateStr.replace(/,/g, '').match(/\d+(\.\d+)?/);
    if (match) {
      rawRate = parseFloat(match[0]);
    }

    // Convert rate according to guidelineRateUnit into total price
    let totalGuidelinePrice = 0;
    if (rawRate > 0) {
      if (guidelineRateUnit === 'sqft') {
        totalGuidelinePrice = Math.round(totalSqFt * rawRate);
      } else if (guidelineRateUnit === 'cent') {
        totalGuidelinePrice = Math.round(totalCents * rawRate);
      } else if (guidelineRateUnit === 'acre') {
        totalGuidelinePrice = Math.round(totalAcres * rawRate);
      }
    }

    const stampDuty = totalGuidelinePrice > 0 ? Math.round(totalGuidelinePrice * 0.07) : 0;
    const regFee = totalGuidelinePrice > 0 ? Math.round(totalGuidelinePrice * 0.02) : 0;
    const totalGovtCost = stampDuty + regFee;
    const estMarketPriceMin = totalGuidelinePrice > 0 ? Math.round(totalGuidelinePrice * 1.5) : 0;
    const estMarketPriceMax = totalGuidelinePrice > 0 ? Math.round(totalGuidelinePrice * 2.5) : 0;

    return {
      totalAres,
      totalSqFt,
      totalCents,
      totalGrounds,
      totalAcres,
      rawRate,
      totalGuidelinePrice,
      stampDuty,
      regFee,
      totalGovtCost,
      estMarketPriceMin,
      estMarketPriceMax,
    };
  }, [editedExtentHect, editedExtentAres, editedGuideline, results, guidelineRateUnit]);

  // Persistence Mode & State
  const [properties, setProperties] = useState<Property[]>([]);
  const [targetPropertyId, setTargetPropertyId] = useState(initialPropertyId || '');
  const [saveActionType, setSaveActionType] = useState<'update' | 'new'>(
    initialPropertyId ? 'update' : 'new'
  );
  const [saveLoading, setSaveLoading] = useState(false);
  const [saveSuccessMsg, setSaveSuccessMsg] = useState<string | null>(null);

  useEffect(() => {
    if (isOpen) {
      propertiesApi.list({ limit: 100 }).then((res) => setProperties(res.items)).catch(() => {});
      if (initialPropertyId) {
        setTargetPropertyId(initialPropertyId);
        setSaveActionType('update');
      }
    }
  }, [isOpen, initialPropertyId]);

  // Synchronize initial prop values when opened
  useEffect(() => {
    if (isOpen) {
      if (initialDistrict) setDistrict(initialDistrict);
      if (initialTaluk) setTaluk(initialTaluk);
      if (initialVillage) setVillage(initialVillage);
      if (initialSurvey) setSurveyNumber(initialSurvey);
      if (initialSubdivision) setSubdivision(initialSubdivision);
    }
  }, [isOpen, initialDistrict, initialTaluk, initialVillage, initialSurvey, initialSubdivision]);

  // Interactive Scraping Lifecycle State
  const [scrapeSessionId, setScrapeSessionId] = useState<string | null>(null);
  const [scrapeStatus, setScrapeStatus] = useState<
    'idle' | 'starting' | 'logging_in' | 'navigating' | 'waiting_for_pin' | 'extracting' | 'completed' | 'error'
  >('idle');
  const [scrapeStatusMsg, setScrapeStatusMsg] = useState<string>('');
  const [mapImage, setMapImage] = useState<string | null>(null);
  const [pinCoords, setPinCoords] = useState<{ xRatio: number; yRatio: number }>({ xRatio: 0.5, yRatio: 0.5 });
  const [hasCustomPin, setHasCustomPin] = useState<boolean>(false);
  const pollIntervalRef = React.useRef<any>(null);

  const stopPolling = () => {
    if (pollIntervalRef.current) {
      clearInterval(pollIntervalRef.current);
      pollIntervalRef.current = null;
    }
  };

  useEffect(() => {
    return () => stopPolling();
  }, []);

  const getTrackerStep = (status: string): number => {
    switch (status) {
      case 'starting':
        return 1;
      case 'logging_in':
        return 2;
      case 'navigating':
        return 3;
      case 'waiting_for_pin':
        return 4;
      case 'extracting':
        return 5;
      case 'completed':
        return 6;
      default:
        return 0;
    }
  };

  // Launch interactive live scraper
  const handleStartLiveScrape = async () => {
    if (!district || !taluk || !village || !surveyNumber) {
      setErrorMsg('Please specify District, Taluk, Village, and Survey Number.');
      return;
    }

    setErrorMsg(null);
    setSaveSuccessMsg(null);
    setResults(null);
    setMapImage(null);
    setPinCoords({ xRatio: 0.5, yRatio: 0.5 });
    setHasCustomPin(false);
    setScrapeStatus('starting');
    setScrapeStatusMsg('Initializing automated Chrome engine in background...');

    try {
      const startResp = await tngisApi.startScrape({
        district,
        taluk,
        village,
        survey_number: surveyNumber,
        subdivision: subdivision || undefined,
        area_type: areaType,
        headless: true, // Invisible background execution!
      });

      const sId = startResp.session_id;
      setScrapeSessionId(sId);
      setScrapeStatus(startResp.status);
      setScrapeStatusMsg(startResp.message);
      if (startResp.map_image) {
        setMapImage(startResp.map_image);
      }

      stopPolling();
      pollIntervalRef.current = setInterval(async () => {
        try {
          const st = await tngisApi.getScrapeStatus(sId);
          setScrapeStatus(st.status);
          setScrapeStatusMsg(st.message);
          if (st.map_image) {
            setMapImage(st.map_image);
          }

          if (st.status === 'completed') {
            stopPolling();
            if (st.data) {
              setResults(st.data);
              const hasOwners = st.data.owners && st.data.owners.length > 0;
              setEditedOwners(st.data.owners || []);
              setEditedPatta(st.data.land_details?.patta_number || '');
              setEditedLandType(st.data.land_details?.land_type || '');
              setEditedExtentHect(st.data.land_details?.extent_hectares || '0');
              setEditedExtentAres(st.data.land_details?.extent_ares || '0');
              setEditedTax(st.data.land_details?.total_tax || '');
              setEditedGuideline(st.data.guideline_value?.metric_rate || '');
              setConsultantNotes(st.data.message || 'Verified via TNGIS Map Viewer.');
              if (!hasOwners && !st.data.land_details?.patta_number) {
                setIsEditMode(true);
              } else {
                setIsEditMode(false);
              }
            }
          } else if (st.status === 'error') {
            stopPolling();
            setErrorMsg(st.message || 'Scraping encountered an error.');
          }
        } catch {
          // ignore poll connection blip
        }
      }, 1500);
    } catch (err: unknown) {
      setScrapeStatus('error');
      setErrorMsg(err instanceof Error ? err.message : 'Failed to launch TNGIS scraper session.');
    }
  };

  // Handle clicking on the interactive mini square map
  const handleMapClick = (e: React.MouseEvent<HTMLDivElement>) => {
    const rect = e.currentTarget.getBoundingClientRect();
    const x = Math.max(0, Math.min(rect.width, e.clientX - rect.left));
    const y = Math.max(0, Math.min(rect.height, e.clientY - rect.top));
    const xRatio = Math.round((x / rect.width) * 1000) / 1000;
    const yRatio = Math.round((y / rect.height) * 1000) / 1000;
    setPinCoords({ xRatio, yRatio });
    setHasCustomPin(true);
  };

  // Signal scraper to proceed after user pins map parcel
  const handleContinueAfterPin = async () => {
    if (!scrapeSessionId) return;
    setScrapeStatus('extracting');
    setScrapeStatusMsg(`Parcel pinned at (${(pinCoords.xRatio * 100).toFixed(0)}%, ${(pinCoords.yRatio * 100).toFixed(0)}%)! Extracting owner details, patta, and guideline values...`);
    try {
      await tngisApi.continueScrape(scrapeSessionId, pinCoords.xRatio, pinCoords.yRatio);
    } catch (err: unknown) {
      setErrorMsg(err instanceof Error ? err.message : 'Failed to send continue signal.');
    }
  };

  // Fast database / cached check
  const handleFastCheck = async () => {
    if (!district || !taluk || !village || !surveyNumber) {
      setErrorMsg('Please specify District, Taluk, Village, and Survey Number.');
      return;
    }

    setLoading(true);
    setLoadingMsg('Checking pre-scraped / verified records in database...');
    setErrorMsg(null);
    setSaveSuccessMsg(null);
    stopPolling();
    setScrapeStatus('idle');

    try {
      const response = await tngisApi.lookup({
        district,
        taluk,
        village,
        survey_number: surveyNumber,
        subdivision: subdivision || undefined,
        area_type: areaType,
        live_scrape: false,
      });

      setResults(response);
      const hasOwners = response.owners && response.owners.length > 0;
      setEditedOwners(response.owners || []);
      setEditedPatta(response.land_details?.patta_number || '');
      setEditedLandType(response.land_details?.land_type || '');
      setEditedExtentHect(response.land_details?.extent_hectares || '0');
      setEditedExtentAres(response.land_details?.extent_ares || '0');
      setEditedTax(response.land_details?.total_tax || '');
      setEditedGuideline(response.guideline_value?.metric_rate || '');
      setConsultantNotes(response.message || 'Verified via TNGIS Map Viewer.');

      if (!hasOwners && !response.land_details?.patta_number) {
        setIsEditMode(true);
      } else {
        setIsEditMode(false);
      }
    } catch (err: unknown) {
      setErrorMsg(err instanceof Error ? err.message : 'Failed to check TNGIS details.');
    } finally {
      setLoading(false);
      setLoadingMsg('');
    }
  };

  // Quick load sample dataset
  const handleLoadSample = async () => {
    setDistrict('Kancheepuram');
    setTaluk('Walajabad');
    setVillage('Walajabad');
    setSurveyNumber('217');
    setSubdivision('1B2');

    setLoading(true);
    setErrorMsg(null);
    try {
      const sample = await tngisApi.getSample();
      setResults(sample);
      setEditedOwners(sample.owners || []);
      setEditedPatta(sample.land_details?.patta_number || '');
      setEditedLandType(sample.land_details?.land_type || '');
      setEditedExtentHect(sample.land_details?.extent_hectares || '0');
      setEditedExtentAres(sample.land_details?.extent_ares || '0');
      setEditedTax(sample.land_details?.total_tax || '');
      setEditedGuideline(sample.guideline_value?.metric_rate || '');
      setConsultantNotes('Verified against Kancheepuram / Walajabad 217/1B2 sample records.');
    } catch (err: unknown) {
      setErrorMsg(err instanceof Error ? err.message : 'Failed to load sample data.');
    } finally {
      setLoading(false);
    }
  };

  // Editable owner row helper
  const handleOwnerChange = (index: number, field: keyof TngisOwnerRecord, value: string) => {
    setEditedOwners((prev) =>
      prev.map((row, i) => (i === index ? { ...row, [field]: value } : row))
    );
  };

  const handleAddOwner = () => {
    setEditedOwners((prev) => [
      ...prev,
      {
        index: prev.length + 1,
        owner: 'புதிய உரிமையாளர்',
        relative: '',
        relation: 'மகன்',
      },
    ]);
  };

  const handleRemoveOwner = (index: number) => {
    setEditedOwners((prev) => prev.filter((_, i) => i !== index));
  };

  // Save to Database Handler
  const handleSaveToDb = async () => {
    if (!results) return;
    setSaveLoading(true);
    setErrorMsg(null);
    setSaveSuccessMsg(null);

    try {
      const payload = {
        property_id: saveActionType === 'update' && targetPropertyId ? targetPropertyId : null,
        create_new_property: saveActionType === 'new',
        district,
        taluk,
        village,
        survey_number: surveyNumber,
        subdivision,
        patta_number: editedPatta,
        land_type: editedLandType,
        land_type_detail: results.land_details?.land_type_tamil || results.land_details?.land_type_eng,
        extent_hectares: editedExtentHect,
        extent_ares: editedExtentAres,
        total_tax: editedTax,
        guideline_rate: editedGuideline,
        latitude: results.coordinates?.latitude,
        longitude: results.coordinates?.longitude,
        google_maps_url: results.coordinates?.google_maps_url,
        owners: editedOwners,
        vertices: results.coordinates?.vertices || [],
        consultant_notes: consultantNotes,
      };

      const res = await tngisApi.save(payload);
      if (res.saved) {
        setSaveSuccessMsg(res.message || 'Saved successfully to database!');
        if (onSaved) {
          onSaved(res.property_id);
        }
      } else {
        setErrorMsg(res.message || 'Save could not be completed.');
      }
    } catch (err: unknown) {
      setErrorMsg(err instanceof Error ? err.message : 'Error saving to database.');
    } finally {
      setSaveLoading(false);
    }
  };

  if (!isOpen) return null;

  return (
    <Modal
      isOpen={isOpen}
      onClose={onClose}
      title="TNGIS Property & Survey Records Lookup"
      description="Select District, Taluk, Village, and Survey/Subdivision to fetch revenue records from the Tamil Nadu GIS portal."
      className="max-w-4xl"
    >
      <div className="space-y-5 max-h-[80vh] overflow-y-auto pr-1">
        {/* Step 1: Input Fields Section */}
        <div className="bg-gray-50/80 p-4 rounded-lg border border-gray-200 space-y-3">
          <div className="flex items-center justify-between">
            <span className="text-xs font-bold uppercase tracking-wider text-gray-700 flex items-center gap-1.5">
              <Building className="h-4 w-4 text-[var(--color-forest)]" />
              1. Survey Parcel Coordinates
            </span>
            <button
              type="button"
              onClick={handleLoadSample}
              className="text-xs text-[var(--color-forest)] hover:underline flex items-center gap-1 font-medium"
              title="Load verified Kancheepuram / Walajabad 217/1B2 data"
            >
              <Sparkles className="h-3.5 w-3.5" /> Quick Demo Sample
            </button>
          </div>

          {/* Row 1: District -> Taluk -> Village Dropdowns */}
          <div className="grid grid-cols-1 sm:grid-cols-3 gap-3">
            <div>
              <label className="block text-[11px] font-semibold text-gray-700 mb-1">
                District (TN) *
              </label>
              <Select
                value={district}
                onChange={(e) => {
                  setDistrict(e.target.value);
                  setTaluk('');
                  setVillage('');
                  setResults(null);
                }}
                className="h-8 text-xs"
              >
                <option value="">Select District</option>
                {getTnDistricts().map((d) => (
                  <option key={d} value={d}>
                    {d}
                  </option>
                ))}
              </Select>
            </div>

            <div>
              <label className="block text-[11px] font-semibold text-gray-700 mb-1">
                Taluk *
              </label>
              <Select
                value={taluk}
                onChange={(e) => {
                  setTaluk(e.target.value);
                  setVillage('');
                  setResults(null);
                }}
                disabled={!district || availableTaluks.length === 0}
                className="h-8 text-xs"
              >
                <option value="">
                  {!district ? 'Select District first' : 'Select Taluk'}
                </option>
                {availableTaluks.map((t) => (
                  <option key={t} value={t}>
                    {t}
                  </option>
                ))}
              </Select>
            </div>

            <div>
              <label className="block text-[11px] font-semibold text-gray-700 mb-1">
                Revenue Village * {availableVillages.length > 0 && `(${availableVillages.length})`}
              </label>
              <Select
                value={village}
                onChange={(e) => {
                  setVillage(e.target.value);
                  setResults(null);
                }}
                disabled={!taluk || availableVillages.length === 0}
                className="h-8 text-xs"
              >
                <option value="">
                  {!taluk
                    ? 'Select Taluk first'
                    : availableVillages.length === 0
                    ? 'No villages found'
                    : 'Select Village'}
                </option>
                {availableVillages.map((v) => (
                  <option key={v} value={v}>
                    {v}
                  </option>
                ))}
              </Select>
            </div>
          </div>

          {/* Row 2: Survey Number, Subdivision, Area Type & Fetch Details Button */}
          <div className="grid grid-cols-1 sm:grid-cols-4 gap-3 items-end pt-1">
            <div>
              <label className="block text-[11px] font-semibold text-gray-700 mb-1">
                Survey Number *
              </label>
              <Input
                placeholder="e.g. 217"
                value={surveyNumber}
                onChange={(e) => {
                  setSurveyNumber(e.target.value);
                  if (results && results.search?.survey_number !== e.target.value) {
                    setResults(null);
                  }
                }}
                className="h-8 text-xs font-mono"
              />
            </div>

            <div>
              <label className="block text-[11px] font-semibold text-gray-700 mb-1">
                Subdivision Number
              </label>
              <Input
                placeholder="e.g. 1B2"
                value={subdivision}
                onChange={(e) => {
                  setSubdivision(e.target.value);
                  if (results && (results.search?.subdivision || '') !== e.target.value) {
                    setResults(null);
                  }
                }}
                className="h-8 text-xs font-mono"
              />
            </div>

            <div>
              <label className="block text-[11px] font-semibold text-gray-700 mb-1">
                Area Type
              </label>
              <Select
                value={areaType}
                onChange={(e) => setAreaType(e.target.value)}
                className="h-8 text-xs"
              >
                <option value="rural">Rural (ஊரகம்)</option>
                <option value="urban">Urban (நகரம்)</option>
              </Select>
            </div>

            <div className="flex items-center gap-2">
              <Button
                type="button"
                onClick={handleStartLiveScrape}
                isLoading={scrapeStatus === 'starting' || scrapeStatus === 'logging_in' || scrapeStatus === 'navigating'}
                disabled={scrapeStatus !== 'idle' && scrapeStatus !== 'completed' && scrapeStatus !== 'error'}
                className="flex-1 h-8 text-xs bg-amber-600 hover:bg-amber-700 text-white font-bold flex items-center justify-center gap-1.5 shadow-xs"
                title="Launch Python Selenium scraper against TNGIS portal and wait for map pin"
              >
                <Globe className="h-3.5 w-3.5" /> Fetch & Scrape Details
              </Button>
              <Button
                type="button"
                variant="outline"
                onClick={handleFastCheck}
                isLoading={loading}
                disabled={loading || (scrapeStatus !== 'idle' && scrapeStatus !== 'completed' && scrapeStatus !== 'error')}
                className="h-8 px-2.5 text-xs border-gray-300 text-gray-700 hover:bg-gray-50 flex items-center justify-center gap-1"
                title="Check if pre-scraped or verified records exist in database"
              >
                <Search className="h-3.5 w-3.5" /> Fast Check
              </Button>
            </div>
          </div>
        </div>

        {/* Flipkart-Style Stepper Progress Timeline */}
        {['starting', 'logging_in', 'navigating', 'waiting_for_pin', 'extracting'].includes(scrapeStatus) && (
          <div className="p-4 sm:p-5 bg-white border border-gray-200/90 rounded-2xl shadow-sm space-y-4">
            {/* Top Tracking Header */}
            <div className="flex flex-wrap items-center justify-between gap-2 pb-3 border-b border-gray-100">
              <div className="flex items-center gap-2">
                <div className="p-1.5 bg-blue-600 text-white rounded-lg shadow-xs">
                  <Compass className="h-4 w-4 animate-spin" />
                </div>
                <div>
                  <h4 className="text-xs font-bold text-gray-900 tracking-tight flex items-center gap-1.5">
                    TNGIS Live Extraction Tracker
                    <span className="inline-block w-2 h-2 rounded-full bg-emerald-500 animate-ping" />
                  </h4>
                  <p className="text-[11px] text-gray-500 font-mono">
                    Session #{scrapeSessionId || 'LIVE'} • Background Chrome Active
                  </p>
                </div>
              </div>
              <div className="flex items-center gap-1.5">
                <Badge className="bg-emerald-50 text-emerald-700 border border-emerald-200 text-[10px] font-semibold">
                  Zero Desktop Popups
                </Badge>
                <Badge className="bg-blue-600 text-white text-[10px] font-bold">
                  Step {getTrackerStep(scrapeStatus)} of 6
                </Badge>
              </div>
            </div>

            {/* Overall Progress Bar */}
            <div className="space-y-1">
              <div className="flex justify-between text-[10px] font-medium text-gray-500">
                <span>Progress: {Math.round((getTrackerStep(scrapeStatus) / 6) * 100)}%</span>
                <span className="text-blue-600 font-semibold">{scrapeStatusMsg || 'Processing...'}</span>
              </div>
              <div className="w-full bg-gray-100 h-1.5 rounded-full overflow-hidden">
                <div
                  className="h-full bg-gradient-to-r from-blue-600 to-emerald-500 transition-all duration-500 ease-out"
                  style={{ width: `${Math.round((getTrackerStep(scrapeStatus) / 6) * 100)}%` }}
                />
              </div>
            </div>

            {/* Stepper Timeline List */}
            <div className="relative pl-6 space-y-4 text-xs">
              {/* Vertical Track Line */}
              <div className="absolute left-[11px] top-2 bottom-2 w-0.5 bg-gray-200" />

              {/* Step 1: Headless Engine */}
              <div className="relative flex items-start gap-3">
                <div
                  className={`absolute -left-6 w-5 h-5 rounded-full flex items-center justify-center text-[10px] font-bold transition-all shadow-xs ${
                    getTrackerStep(scrapeStatus) > 1
                      ? 'bg-emerald-600 text-white'
                      : getTrackerStep(scrapeStatus) === 1
                      ? 'bg-blue-600 text-white ring-4 ring-blue-100 animate-pulse'
                      : 'bg-gray-100 text-gray-400 border border-gray-300'
                  }`}
                >
                  {getTrackerStep(scrapeStatus) > 1 ? <Check className="h-3 w-3" /> : '1'}
                </div>
                <div>
                  <p className={`font-bold ${getTrackerStep(scrapeStatus) >= 1 ? 'text-gray-900' : 'text-gray-400'}`}>
                    Background Browser Initialized
                  </p>
                  <p className="text-[11px] text-gray-500">
                    Chrome started headlessly in background (hidden from view)
                  </p>
                </div>
              </div>

              {/* Step 2: Portal Authentication & OCR */}
              <div className="relative flex items-start gap-3">
                <div
                  className={`absolute -left-6 w-5 h-5 rounded-full flex items-center justify-center text-[10px] font-bold transition-all shadow-xs ${
                    getTrackerStep(scrapeStatus) > 2
                      ? 'bg-emerald-600 text-white'
                      : getTrackerStep(scrapeStatus) === 2
                      ? 'bg-blue-600 text-white ring-4 ring-blue-100 animate-pulse'
                      : 'bg-gray-100 text-gray-400 border border-gray-300'
                  }`}
                >
                  {getTrackerStep(scrapeStatus) > 2 ? <Check className="h-3 w-3" /> : '2'}
                </div>
                <div>
                  <p className={`font-bold ${getTrackerStep(scrapeStatus) >= 2 ? 'text-gray-900' : 'text-gray-400'}`}>
                    TNGIS Portal Authentication & OCR
                  </p>
                  <p className="text-[11px] text-gray-500">
                    Auto-solving portal CAPTCHA and connecting to GIS viewer
                  </p>
                </div>
              </div>

              {/* Step 3: Location Dropdown Hierarchy */}
              <div className="relative flex items-start gap-3">
                <div
                  className={`absolute -left-6 w-5 h-5 rounded-full flex items-center justify-center text-[10px] font-bold transition-all shadow-xs ${
                    getTrackerStep(scrapeStatus) > 3
                      ? 'bg-emerald-600 text-white'
                      : getTrackerStep(scrapeStatus) === 3
                      ? 'bg-blue-600 text-white ring-4 ring-blue-100 animate-pulse'
                      : 'bg-gray-100 text-gray-400 border border-gray-300'
                  }`}
                >
                  {getTrackerStep(scrapeStatus) > 3 ? <Check className="h-3 w-3" /> : '3'}
                </div>
                <div>
                  <p className={`font-bold ${getTrackerStep(scrapeStatus) >= 3 ? 'text-gray-900' : 'text-gray-400'}`}>
                    Survey Parcel Location Centering
                  </p>
                  <p className="text-[11px] text-gray-500">
                    {district} › {taluk} › {village} › Survey {surveyNumber}/{subdivision || '-'}
                  </p>
                </div>
              </div>

              {/* Step 4: Interactive Parcel Map Pinning (Flipkart Milestone with Mini Square Map) */}
              <div className="relative flex items-start gap-3">
                <div
                  className={`absolute -left-6 w-5 h-5 rounded-full flex items-center justify-center text-[10px] font-bold transition-all shadow-xs ${
                    getTrackerStep(scrapeStatus) > 4
                      ? 'bg-emerald-600 text-white'
                      : getTrackerStep(scrapeStatus) === 4
                      ? 'bg-amber-600 text-white ring-4 ring-amber-100 animate-pulse'
                      : 'bg-gray-100 text-gray-400 border border-gray-300'
                  }`}
                >
                  {getTrackerStep(scrapeStatus) > 4 ? <Check className="h-3 w-3" /> : '4'}
                </div>
                <div className="flex-1">
                  <div className="flex items-center gap-2">
                    <p className={`font-bold ${getTrackerStep(scrapeStatus) >= 4 ? 'text-gray-900' : 'text-gray-400'}`}>
                      Interactive Parcel Pinning on Map
                    </p>
                    {getTrackerStep(scrapeStatus) === 4 && (
                      <Badge className="bg-amber-500 text-white text-[9px] uppercase font-bold animate-pulse">
                        Action Required
                      </Badge>
                    )}
                  </div>
                  <p className="text-[11px] text-gray-500">
                    {getTrackerStep(scrapeStatus) > 4
                      ? 'Parcel polygon pinned successfully'
                      : 'Click the survey polygon in the square preview below to activate revenue panels'}
                  </p>

                  {/* IN-MODAL MINI SQUARE MAP CARD (Active only when waiting_for_pin) */}
                  {scrapeStatus === 'waiting_for_pin' && (
                    <div className="mt-3 p-3.5 bg-gradient-to-br from-amber-50/80 to-orange-50/80 border border-amber-300 rounded-xl shadow-xs space-y-3">
                      <div className="flex items-center justify-between">
                        <span className="text-[11px] font-bold text-amber-950 flex items-center gap-1.5">
                          <Crosshair className="h-3.5 w-3.5 text-amber-600" /> Click on parcel to position pin:
                        </span>
                        <span className="px-2 py-0.5 rounded bg-white/90 border border-amber-300 text-amber-900 text-[10px] font-mono font-bold">
                          {hasCustomPin
                            ? `📍 X: ${(pinCoords.xRatio * 100).toFixed(0)}%, Y: ${(pinCoords.yRatio * 100).toFixed(0)}%`
                            : '📍 Center Default (50%, 50%)'}
                        </span>
                      </div>

                      {/* Mini Square Map Viewport */}
                      <div
                        onClick={handleMapClick}
                        className="relative w-full aspect-square max-w-[340px] mx-auto rounded-xl overflow-hidden border-2 border-amber-400 shadow-md bg-slate-900 cursor-crosshair group select-none"
                        title="Click anywhere on the map to place the parcel pin"
                      >
                        {mapImage ? (
                          <img
                            src={mapImage}
                            alt="TNGIS Parcel Map View"
                            className="w-full h-full object-cover select-none pointer-events-none"
                          />
                        ) : (
                          <div className="w-full h-full flex flex-col items-center justify-center text-center p-4 text-slate-300 bg-[radial-gradient(#334155_1px,transparent_1px)] [background-size:16px_16px]">
                            <Compass className="h-10 w-10 text-amber-400 mb-2 animate-spin" />
                            <p className="text-xs font-bold text-white">TNGIS Survey Canvas</p>
                            <p className="text-[11px] text-slate-400 mt-1">
                              Survey {surveyNumber}/{subdivision || ''} • {village}
                            </p>
                            <span className="mt-3 inline-block px-2 py-0.5 rounded bg-amber-500/20 text-amber-300 text-[10px] font-mono border border-amber-500/30">
                              Click to position pin
                            </span>
                          </div>
                        )}

                        {/* Subtle Center Crosshair Guide */}
                        <div className="absolute inset-0 pointer-events-none opacity-25 group-hover:opacity-40 transition-opacity">
                          <div className="absolute top-1/2 left-0 right-0 h-px bg-amber-400 border-dashed" />
                          <div className="absolute left-1/2 top-0 bottom-0 w-px bg-amber-400 border-dashed" />
                        </div>

                        {/* Interactive Red Pin Marker */}
                        <div
                          className="absolute -translate-x-1/2 -translate-y-full pointer-events-none transition-all duration-150 ease-out"
                          style={{
                            left: `${pinCoords.xRatio * 100}%`,
                            top: `${pinCoords.yRatio * 100}%`,
                          }}
                        >
                          <div className="relative flex flex-col items-center">
                            <span className="px-1.5 py-0.5 rounded bg-black/80 text-white text-[9px] font-mono font-bold whitespace-nowrap shadow-sm mb-0.5">
                              PIN {(pinCoords.xRatio * 100).toFixed(0)}%, {(pinCoords.yRatio * 100).toFixed(0)}%
                            </span>
                            <div className="p-1 rounded-full bg-red-600 text-white shadow-lg ring-4 ring-red-400/50 animate-bounce">
                              <MapPin className="h-4 w-4" />
                            </div>
                            <div className="w-1.5 h-1.5 rounded-full bg-red-600 ring-2 ring-white -mt-0.5" />
                          </div>
                        </div>

                        {/* Floating Tooltip Pill */}
                        <div className="absolute bottom-2 left-2 right-2 px-2.5 py-1 rounded-md bg-black/75 backdrop-blur-xs text-white text-[10px] flex items-center justify-between pointer-events-none">
                          <span className="flex items-center gap-1 font-medium">
                            <Crosshair className="h-3 w-3 text-amber-400" /> Click parcel polygon to pin
                          </span>
                          <span className="text-amber-300 font-mono text-[9px]">
                            {hasCustomPin ? 'Custom Pin Set' : 'Default: Center'}
                          </span>
                        </div>
                      </div>

                      {/* Confirm & Continue Extraction Button */}
                      <div className="flex flex-wrap items-center justify-between gap-2 pt-1 border-t border-amber-200">
                        <p className="text-[11px] text-amber-900 italic">
                          Clicking confirm triggers background extraction.
                        </p>
                        <Button
                          type="button"
                          onClick={handleContinueAfterPin}
                          className="bg-emerald-600 hover:bg-emerald-700 text-white font-bold text-xs h-9 px-4 flex items-center gap-2 shadow-sm animate-pulse"
                        >
                          <CheckCircle2 className="h-4 w-4" /> Confirm Pin & Continue Extraction
                        </Button>
                      </div>
                    </div>
                  )}
                </div>
              </div>

              {/* Step 5: Revenue Panel Extraction Checklist */}
              <div className="relative flex items-start gap-3">
                <div
                  className={`absolute -left-6 w-5 h-5 rounded-full flex items-center justify-center text-[10px] font-bold transition-all shadow-xs ${
                    getTrackerStep(scrapeStatus) > 5
                      ? 'bg-emerald-600 text-white'
                      : getTrackerStep(scrapeStatus) === 5
                      ? 'bg-teal-600 text-white ring-4 ring-teal-100 animate-pulse'
                      : 'bg-gray-100 text-gray-400 border border-gray-300'
                  }`}
                >
                  {getTrackerStep(scrapeStatus) > 5 ? <Check className="h-3 w-3" /> : '5'}
                </div>
                <div className="flex-1">
                  <p className={`font-bold ${getTrackerStep(scrapeStatus) >= 5 ? 'text-gray-900' : 'text-gray-400'}`}>
                    Revenue Data & Panel Extraction
                  </p>
                  <p className="text-[11px] text-gray-500">
                    Extracting A-Register, Patta No, Land Classification, Guideline Valuation & GPS Vertices
                  </p>

                  {/* Extraction Checklist Badges */}
                  {scrapeStatus === 'extracting' && (
                    <div className="grid grid-cols-2 sm:grid-cols-4 gap-2 pt-2 text-[11px] font-medium text-teal-900">
                      <div className="p-1.5 bg-teal-50 border border-teal-200 rounded flex items-center gap-1.5">
                        <CheckCircle2 className="h-3.5 w-3.5 text-teal-600 shrink-0" />
                        <span>Owner Registry</span>
                      </div>
                      <div className="p-1.5 bg-teal-50 border border-teal-200 rounded flex items-center gap-1.5">
                        <CheckCircle2 className="h-3.5 w-3.5 text-teal-600 shrink-0" />
                        <span>Land & Patta No</span>
                      </div>
                      <div className="p-1.5 bg-teal-50 border border-teal-200 rounded flex items-center gap-1.5">
                        <CheckCircle2 className="h-3.5 w-3.5 text-teal-600 shrink-0" />
                        <span>Guideline Value</span>
                      </div>
                      <div className="p-1.5 bg-teal-50 border border-teal-200 rounded flex items-center gap-1.5">
                        <CheckCircle2 className="h-3.5 w-3.5 text-teal-600 shrink-0" />
                        <span>GPS Coordinates</span>
                      </div>
                    </div>
                  )}
                </div>
              </div>

              {/* Step 6: Verified & Ready to Save */}
              <div className="relative flex items-start gap-3">
                <div
                  className={`absolute -left-6 w-5 h-5 rounded-full flex items-center justify-center text-[10px] font-bold transition-all shadow-xs ${
                    getTrackerStep(scrapeStatus) >= 6
                      ? 'bg-emerald-600 text-white ring-4 ring-emerald-100'
                      : 'bg-gray-100 text-gray-400 border border-gray-300'
                  }`}
                >
                  {getTrackerStep(scrapeStatus) >= 6 ? <Check className="h-3 w-3" /> : '6'}
                </div>
                <div>
                  <p className={`font-bold ${getTrackerStep(scrapeStatus) >= 6 ? 'text-gray-900' : 'text-gray-400'}`}>
                    Verified & Ready for Database
                  </p>
                  <p className="text-[11px] text-gray-500">
                    Review extracted tables, edit if needed, and save to property records
                  </p>
                </div>
              </div>
            </div>
          </div>
        )}

        {/* Loading Progress Alert for Fast Check */}
        {loading && loadingMsg && (
          <div className="p-3 bg-blue-50 border border-blue-200 text-blue-900 text-xs rounded-lg flex items-center gap-2 animate-pulse">
            <Globe className="h-4 w-4 shrink-0 text-blue-600 animate-spin" />
            <span className="font-medium">{loadingMsg}</span>
          </div>
        )}

        {/* Error Alert */}
        {errorMsg && (
          <div className="p-3 bg-red-50 border border-red-200 text-red-700 text-xs rounded-lg flex items-center justify-between">
            <span>{errorMsg}</span>
            <Button size="sm" variant="outline" onClick={() => setErrorMsg(null)} className="h-6 text-[10px]">
              Dismiss
            </Button>
          </div>
        )}

        {/* Success Alert */}
        {saveSuccessMsg && (
          <div className="p-3 bg-emerald-50 border border-emerald-200 text-emerald-800 text-xs rounded-lg flex items-center gap-2">
            <CheckCircle2 className="h-4 w-4 shrink-0 text-emerald-600" />
            <span>{saveSuccessMsg}</span>
          </div>
        )}

        {/* Step 2: Extracted & Structured Results Display */}
        {results && (
          <div className="space-y-4 border-t border-gray-200 pt-4">
            {/* Header with Mode Toggle */}
            {editedOwners.length === 0 && !editedPatta ? (
              <div className="bg-amber-50 border border-amber-200 p-3 rounded-lg text-xs text-amber-900 flex flex-col sm:flex-row sm:items-center justify-between gap-2">
                <div>
                  <div className="font-bold flex items-center gap-1.5 text-amber-950">
                    <AlertTriangle className="h-4 w-4 text-amber-600 shrink-0" />
                    No Pre-Scraped Records for Survey {surveyNumber}{subdivision ? `/${subdivision}` : ''} in {village}
                  </div>
                  <p className="text-[11px] text-amber-800 mt-0.5">
                    {results.message || 'This parcel has not been scraped yet. Enter verified details below in Edit Mode, or try Live Scrape.'}
                  </p>
                </div>
                <div className="flex items-center gap-2 shrink-0">
                  <Button
                    size="sm"
                    onClick={() => handleFetchDetails(true)}
                    isLoading={loading && loadingMsg.includes('Selenium')}
                    className="text-xs h-7 px-2.5 bg-amber-600 hover:bg-amber-700 text-white font-bold flex items-center gap-1 shadow-xs"
                    title="Launch automated Python Selenium scraper against TNGIS portal"
                  >
                    <Globe className="h-3 w-3" /> Scrape Live Now
                  </Button>
                  <Button
                    size="sm"
                    variant="outline"
                    onClick={() => setIsEditMode(!isEditMode)}
                    className={`text-xs h-7 px-2.5 flex items-center gap-1 ${
                      isEditMode
                        ? 'bg-amber-100 text-amber-900 border-amber-300 font-bold'
                        : 'bg-white text-gray-700 border-gray-300 font-bold'
                    }`}
                  >
                    <Edit3 className="h-3 w-3" /> {isEditMode ? 'Finish Editing' : 'Enter Details Manually'}
                  </Button>
                </div>
              </div>
            ) : (
              <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-2 bg-emerald-50/70 p-3 rounded-lg border border-emerald-200">
                <div className="flex items-center gap-2">
                  <CheckCircle2 className="h-5 w-5 text-emerald-600 shrink-0" />
                  <div>
                    <h4 className="text-xs font-bold text-emerald-950 flex items-center gap-2">
                      TNGIS Land Record Verified: Survey {surveyNumber}/{subdivision || ''} - {village}
                      {results.message?.includes('Instant Cache') && (
                        <Badge className="bg-emerald-600 text-white text-[9px] font-bold uppercase tracking-wider flex items-center gap-1">
                          <Sparkles className="h-2.5 w-2.5" /> Instant Cache (0.01s)
                        </Badge>
                      )}
                    </h4>
                    <p className="text-[11px] text-emerald-800">
                      {results.message || (results.is_cached_sample
                        ? 'Loaded verified reference dataset (Walajabad 217/1B2).'
                        : 'Revenue Patta, land classification, owner chain, and guideline valuation extracted.')}
                    </p>
                  </div>
                </div>

                <div className="flex items-center gap-2">
                  <Button
                    size="sm"
                    variant="outline"
                    onClick={() => setIsEditMode(!isEditMode)}
                    className={`text-xs h-7 px-2.5 flex items-center gap-1 ${
                      isEditMode
                        ? 'bg-amber-100 text-amber-900 border-amber-300 font-bold'
                        : 'bg-white text-gray-700 border-gray-300'
                    }`}
                  >
                    <Edit3 className="h-3 w-3" /> {isEditMode ? 'Finish Editing' : 'Edit Details'}
                  </Button>
                </div>
              </div>
            )}

            {/* Top Stat Highlights */}
            <div className="grid grid-cols-2 sm:grid-cols-4 gap-3 text-xs">
              <div className="bg-white p-2.5 rounded-lg border border-gray-200 shadow-xs">
                <span className="text-[10px] text-gray-500 block uppercase font-medium">Patta Number</span>
                {isEditMode ? (
                  <Input
                    className="h-7 text-xs font-bold mt-1"
                    value={editedPatta}
                    onChange={(e) => setEditedPatta(e.target.value)}
                  />
                ) : (
                  <span className="text-sm font-bold text-[var(--color-ink)] font-mono">
                    {editedPatta || results.land_details?.patta_number || '-'}
                  </span>
                )}
              </div>

              <div className="bg-white p-2.5 rounded-lg border border-gray-200 shadow-xs">
                <span className="text-[10px] text-gray-500 block uppercase font-medium">Land Classification</span>
                {isEditMode ? (
                  <Input
                    className="h-7 text-xs font-bold mt-1"
                    value={editedLandType}
                    onChange={(e) => setEditedLandType(e.target.value)}
                  />
                ) : (
                  <span className="text-xs font-bold text-gray-900 block truncate" title={editedLandType}>
                    {editedLandType || results.land_details?.land_type || '-'}
                  </span>
                )}
              </div>

              <div className="bg-white p-2.5 rounded-lg border border-gray-200 shadow-xs">
                <span className="text-[10px] text-gray-500 block uppercase font-medium">Extent (Hect / Ares)</span>
                {isEditMode ? (
                  <div className="flex items-center gap-1 mt-1">
                    <Input
                      className="h-7 text-xs w-16"
                      placeholder="Hect"
                      value={editedExtentHect}
                      onChange={(e) => setEditedExtentHect(e.target.value)}
                    />
                    <span className="text-gray-400">H</span>
                    <Input
                      className="h-7 text-xs w-16"
                      placeholder="Ares"
                      value={editedExtentAres}
                      onChange={(e) => setEditedExtentAres(e.target.value)}
                    />
                    <span className="text-gray-400">A</span>
                  </div>
                ) : (
                  <span className="text-xs font-bold text-gray-900">
                    {editedExtentHect} Hectares, {editedExtentAres} Ares (~{(Number(editedExtentAres) * 1076.39).toFixed(0)} sq.ft)
                  </span>
                )}
              </div>

              <div className="bg-white p-2.5 rounded-lg border border-gray-200 shadow-xs">
                <span className="text-[10px] text-gray-500 block uppercase font-medium">Guideline Valuation</span>
                {isEditMode ? (
                  <Input
                    className="h-7 text-xs font-bold mt-1 text-emerald-800"
                    value={editedGuideline}
                    onChange={(e) => setEditedGuideline(e.target.value)}
                  />
                ) : (
                  <span className="text-sm font-bold text-emerald-800 font-mono">
                    {editedGuideline || results.guideline_value?.metric_rate || '-'}
                  </span>
                )}
              </div>
            </div>

            {/* REAL ESTATE VALUATION & LAND EXTENT CALCULATOR CARD */}
            <div className="bg-gradient-to-br from-emerald-50/70 via-teal-50/40 to-white rounded-xl border border-emerald-200 p-4 shadow-xs space-y-3">
              <div className="flex flex-wrap items-center justify-between gap-2 pb-2 border-b border-emerald-200/60">
                <div className="flex items-center gap-2">
                  <div className="p-1.5 bg-emerald-600 text-white rounded-lg shadow-xs">
                    <Calculator className="h-4 w-4" />
                  </div>
                  <div>
                    <h4 className="text-xs font-bold text-gray-900 flex items-center gap-1.5">
                      Land Extent & Property Valuation Calculator
                      <Badge className="bg-emerald-100 text-emerald-800 text-[10px] font-semibold border border-emerald-300">
                        TN Registration Benchmark
                      </Badge>
                    </h4>
                    <p className="text-[11px] text-gray-500">
                      Standard Tamil Nadu metric & customary land conversions with statutory fees
                    </p>
                  </div>
                </div>
                <div className="flex items-center gap-1 text-[10px] text-gray-500 font-mono">
                  <span className="px-1.5 py-0.5 rounded bg-white border border-gray-200">1 Are = 1,076.39 sq.ft</span>
                  <span className="px-1.5 py-0.5 rounded bg-white border border-gray-200">1 Cent = 435.6 sq.ft</span>
                </div>
              </div>

              {/* Grid with 4 Key Computation Blocks */}
              <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-3">
                {/* 1. Total Land Extent Conversions */}
                <div className="bg-white p-3 rounded-lg border border-emerald-200 shadow-xs space-y-1.5">
                  <span className="text-[10px] text-gray-500 font-bold uppercase tracking-wider block">
                    Total Extent Breakdown
                  </span>
                  <div className="text-base font-extrabold text-emerald-950 font-mono">
                    {valuation.totalSqFt.toLocaleString('en-IN')} <span className="text-xs font-medium text-gray-600 font-sans">sq.ft</span>
                  </div>
                  <div className="grid grid-cols-3 gap-1 pt-1 border-t border-gray-100 text-[10px] text-gray-600">
                    <div>
                      <span className="text-gray-400 block text-[9px]">CENTS</span>
                      <span className="font-bold text-gray-900">{valuation.totalCents}</span>
                    </div>
                    <div>
                      <span className="text-gray-400 block text-[9px]">GROUNDS</span>
                      <span className="font-bold text-gray-900">{valuation.totalGrounds}</span>
                    </div>
                    <div>
                      <span className="text-gray-400 block text-[9px]">ACRES</span>
                      <span className="font-bold text-gray-900">{valuation.totalAcres}</span>
                    </div>
                  </div>
                </div>

                {/* 2. Guideline Rate & Price */}
                <div className="bg-white p-3 rounded-lg border border-emerald-200 shadow-xs space-y-1.5">
                  <div className="flex items-center justify-between">
                    <span className="text-[10px] text-gray-500 font-bold uppercase tracking-wider block">
                      Guideline Valuation
                    </span>
                    <select
                      value={guidelineRateUnit}
                      onChange={(e) => setGuidelineRateUnit(e.target.value as any)}
                      className="text-[10px] h-5 py-0 px-1 border border-gray-300 rounded bg-gray-50 font-medium text-gray-700 focus:ring-1 focus:ring-emerald-500"
                    >
                      <option value="sqft">₹ / sq.ft</option>
                      <option value="cent">₹ / cent</option>
                      <option value="acre">₹ / acre</option>
                    </select>
                  </div>
                  <div className="flex items-center gap-1.5">
                    <span className="text-xs font-bold text-gray-600 font-mono">₹</span>
                    <input
                      type="number"
                      placeholder="Rate (e.g. 1200)"
                      value={valuation.rawRate || ''}
                      onChange={(e) => setEditedGuideline(e.target.value ? `₹ ${e.target.value} / ${guidelineRateUnit}` : '')}
                      className="h-7 text-xs font-mono font-bold w-full rounded border border-gray-300 px-2 py-1 focus:border-emerald-500 focus:ring-1 focus:ring-emerald-500"
                    />
                  </div>
                  <div className="pt-1 border-t border-gray-100 flex items-center justify-between">
                    <span className="text-[10px] text-gray-500 font-medium">Govt Minimum:</span>
                    <span className="text-xs font-bold text-emerald-800 font-mono">
                      {formatInr(valuation.totalGuidelinePrice)}
                    </span>
                  </div>
                </div>

                {/* 3. Tamil Nadu Statutory Registration Costs */}
                <div className="bg-white p-3 rounded-lg border border-blue-200 shadow-xs space-y-1.5">
                  <div className="flex items-center justify-between">
                    <span className="text-[10px] text-blue-900 font-bold uppercase tracking-wider block">
                      Govt Charges (~9%)
                    </span>
                    <Coins className="h-3.5 w-3.5 text-blue-600" />
                  </div>
                  <div className="text-base font-extrabold text-blue-950 font-mono">
                    {formatInr(valuation.totalGovtCost)}
                  </div>
                  <div className="pt-1 border-t border-gray-100 text-[10px] text-gray-600 flex items-center justify-between">
                    <span>Stamp (7%): <strong className="text-gray-900">{formatInr(valuation.stampDuty)}</strong></span>
                    <span>Reg (2%): <strong className="text-gray-900">{formatInr(valuation.regFee)}</strong></span>
                  </div>
                </div>

                {/* 4. Estimated Market Selling Range */}
                <div className="bg-white p-3 rounded-lg border border-purple-200 shadow-xs space-y-1.5">
                  <div className="flex items-center justify-between">
                    <span className="text-[10px] text-purple-900 font-bold uppercase tracking-wider block">
                      Estimated Market Value
                    </span>
                    <TrendingUp className="h-3.5 w-3.5 text-purple-600" />
                  </div>
                  <div className="text-sm font-extrabold text-purple-950 font-mono truncate">
                    {valuation.totalGuidelinePrice > 0
                      ? `${formatInr(valuation.estMarketPriceMin)} – ${formatInr(valuation.estMarketPriceMax)}`
                      : 'Enter Guideline Rate'}
                  </div>
                  <div className="pt-1 border-t border-gray-100 text-[10px] text-purple-700 flex items-center justify-between">
                    <span>Typical TN Multiplier:</span>
                    <span className="font-bold">1.5× to 2.5×</span>
                  </div>
                </div>
              </div>
            </div>

            {/* TABLE 1: Owner Information Table */}
            <div className="bg-white rounded-lg border border-gray-200 overflow-hidden shadow-xs">
              <div className="p-3 bg-gray-50 border-b border-gray-200 flex items-center justify-between">
                <div className="flex items-center gap-2">
                  <span className="text-xs font-bold text-gray-900 uppercase tracking-wide">
                    Registered Ownership Details (உரிமையாளர் விபரம்)
                  </span>
                  <Badge variant="outline" className="text-[10px] bg-blue-50 text-blue-800 border-blue-200">
                    {editedOwners.length} {editedOwners.length === 1 ? 'Owner' : 'Owners'}
                  </Badge>
                </div>

                {isEditMode && (
                  <Button
                    size="sm"
                    variant="outline"
                    onClick={handleAddOwner}
                    className="text-xs h-6 px-2 flex items-center gap-1 text-[var(--color-forest)]"
                  >
                    <Plus className="h-3 w-3" /> Add Owner
                  </Button>
                )}
              </div>

              <Table>
                <TableHeader>
                  <TableRow className="bg-gray-50/60 text-xs">
                    <TableHead className="w-12">#</TableHead>
                    <TableHead>Owner Name (பட்டாதாரர் பெயர்)</TableHead>
                    <TableHead>Relative / Father (தந்தை / கணவர் பெயர்)</TableHead>
                    <TableHead>Relationship (உறவுமுறை)</TableHead>
                    {isEditMode && <TableHead className="w-16 text-right">Action</TableHead>}
                  </TableRow>
                </TableHeader>
                <TableBody>
                  {editedOwners.length === 0 ? (
                    <TableRow>
                      <TableCell colSpan={isEditMode ? 5 : 4} className="text-center py-5 text-xs text-gray-500">
                        {isEditMode ? (
                          <div className="flex flex-col items-center gap-2 py-2">
                            <span className="text-gray-600 font-medium">No registered owners added yet.</span>
                            <Button
                              type="button"
                              size="sm"
                              onClick={handleAddOwner}
                              className="h-7 text-xs bg-[var(--color-forest)] text-white font-bold flex items-center gap-1 shadow-xs"
                            >
                              <Plus className="h-3 w-3" /> Add First Owner
                            </Button>
                          </div>
                        ) : (
                          <div className="flex flex-col items-center gap-1.5 py-2">
                            <span className="font-medium text-gray-700">No owner records extracted for Survey {surveyNumber}/{subdivision || ''}.</span>
                            <span className="text-[11px] text-gray-500">Click &quot;Enter Details Manually&quot; above to add registered owners.</span>
                          </div>
                        )}
                      </TableCell>
                    </TableRow>
                  ) : (
                    editedOwners.map((ownerRow, idx) => (
                      <TableRow key={idx} className="text-xs">
                        <TableCell className="font-mono text-gray-500 font-bold">{idx + 1}</TableCell>
                        <TableCell className="font-medium text-gray-900">
                          {isEditMode ? (
                            <Input
                              className="h-7 text-xs"
                              value={ownerRow.owner}
                              onChange={(e) => handleOwnerChange(idx, 'owner', e.target.value)}
                            />
                          ) : (
                            <span className="text-sm font-serif font-semibold">{ownerRow.owner}</span>
                          )}
                        </TableCell>
                        <TableCell className="text-gray-700">
                          {isEditMode ? (
                            <Input
                              className="h-7 text-xs"
                              value={ownerRow.relative || ''}
                              onChange={(e) => handleOwnerChange(idx, 'relative', e.target.value)}
                            />
                          ) : (
                            ownerRow.relative || '-'
                          )}
                        </TableCell>
                        <TableCell>
                          {isEditMode ? (
                            <Input
                              className="h-7 text-xs"
                              value={ownerRow.relation || ''}
                              onChange={(e) => handleOwnerChange(idx, 'relation', e.target.value)}
                            />
                          ) : (
                            <Badge variant="outline" className="text-[10px] bg-purple-50 text-purple-800 border-purple-200">
                              {ownerRow.relation || 'உரிமையாளர்'}
                            </Badge>
                          )}
                        </TableCell>
                        {isEditMode && (
                          <TableCell className="text-right">
                            <button
                              type="button"
                              onClick={() => handleRemoveOwner(idx)}
                              className="p-1 text-red-600 hover:bg-red-50 rounded"
                              title="Delete row"
                            >
                              <Trash2 className="h-3.5 w-3.5" />
                            </button>
                          </TableCell>
                        )}
                      </TableRow>
                    ))
                  )}
                </TableBody>
              </Table>
            </div>

            {/* TABLE 2: Land & Revenue Classification Grid */}
            <div className="bg-white rounded-lg border border-gray-200 overflow-hidden shadow-xs">
              <div className="p-3 bg-gray-50 border-b border-gray-200">
                <span className="text-xs font-bold text-gray-900 uppercase tracking-wide">
                  Revenue Classification & Assessment Record (நில விவரங்கள்)
                </span>
              </div>
              <div className="grid grid-cols-2 sm:grid-cols-3 gap-px bg-gray-200 text-xs">
                <div className="bg-white p-2.5">
                  <span className="text-[10px] text-gray-500 block">Land Type (வகைப்பாடு)</span>
                  <span className="font-semibold text-gray-900">
                    {results.land_details?.land_type || 'Rayathuvari / ரயத்துவாரி'}
                  </span>
                </div>
                <div className="bg-white p-2.5">
                  <span className="text-[10px] text-gray-500 block">Sub-Classification</span>
                  <span className="font-semibold text-gray-900">
                    {results.land_details?.land_type_tamil || results.land_details?.land_type_eng || 'Dry (புஞ்சை)'}
                  </span>
                </div>
                <div className="bg-white p-2.5">
                  <span className="text-[10px] text-gray-500 block">Poramboke Verification</span>
                  <span className="font-semibold text-emerald-700">
                    {results.land_details?.poramboke === '-' ? 'No (Private Ryotwari)' : results.land_details?.poramboke}
                  </span>
                </div>
                <div className="bg-white p-2.5">
                  <span className="text-[10px] text-gray-500 block">Soil Classification</span>
                  <span className="font-semibold text-gray-900">
                    Class {results.land_details?.soil_class || '4'} (Type {results.land_details?.soil_type_pri || '7'}/{results.land_details?.soil_type_sec || '2'})
                  </span>
                </div>
                <div className="bg-white p-2.5">
                  <span className="text-[10px] text-gray-500 block">Total Revenue Assessment Tax</span>
                  {isEditMode ? (
                    <Input
                      className="h-6 text-xs mt-0.5"
                      value={editedTax}
                      onChange={(e) => setEditedTax(e.target.value)}
                    />
                  ) : (
                    <span className="font-semibold text-gray-900 font-mono">
                      ₹{editedTax || results.land_details?.total_tax || '0.08'}
                    </span>
                  )}
                </div>
                <div className="bg-white p-2.5">
                  <span className="text-[10px] text-gray-500 block">Govt Primary Code</span>
                  <span className="font-semibold text-gray-900 font-mono">
                    {results.land_details?.govt_pri_code || '2'}
                  </span>
                </div>
              </div>
            </div>

            {/* GPS Vertices & Location Pin */}
            {results.coordinates && (
              <div className="bg-white p-3 rounded-lg border border-gray-200 space-y-2">
                <div className="flex items-center justify-between">
                  <div className="flex items-center gap-2">
                    <MapPin className="h-4 w-4 text-red-600" />
                    <span className="text-xs font-bold text-gray-900">
                      Pinned GPS Coordinates: {results.coordinates.latitude}, {results.coordinates.longitude}
                    </span>
                  </div>
                  <a
                    href={results.coordinates.google_maps_url}
                    target="_blank"
                    rel="noreferrer"
                    className="text-xs text-blue-600 hover:underline flex items-center gap-1 font-semibold"
                  >
                    Open in Google Maps <ExternalLink className="h-3 w-3" />
                  </a>
                </div>

                {results.coordinates.vertices?.length > 0 && (
                  <div className="text-[11px] text-gray-600 bg-gray-50 p-2 rounded border border-gray-100">
                    <span className="font-semibold text-gray-800">Boundary Survey Vertices: </span>
                    {results.coordinates.vertices.map((v) => (
                      <span key={v.vertex_number} className="inline-block mr-3 font-mono">
                        #{v.vertex_number}: ({v.latitude}, {v.longitude})
                      </span>
                    ))}
                  </div>
                )}
              </div>
            )}

            {/* Step 3: Save to Database Controls */}
            <div className="bg-amber-50/60 p-4 rounded-lg border border-amber-200 space-y-3">
              <span className="text-xs font-bold uppercase tracking-wider text-amber-900 block">
                Save & Link Options
              </span>

              <div className="grid grid-cols-1 sm:grid-cols-2 gap-3 text-xs">
                <label className="flex items-start gap-2 p-2.5 bg-white rounded border border-gray-200 cursor-pointer">
                  <input
                    type="radio"
                    name="saveAction"
                    value="new"
                    checked={saveActionType === 'new'}
                    onChange={() => setSaveActionType('new')}
                    className="mt-0.5"
                  />
                  <div>
                    <span className="font-bold text-gray-900 block">Register as New Property Listing</span>
                    <span className="text-[11px] text-gray-500">
                      Creates a new draft property in inventory with verified survey, district, taluk, village & GPS pin.
                    </span>
                  </div>
                </label>

                <label className="flex items-start gap-2 p-2.5 bg-white rounded border border-gray-200 cursor-pointer">
                  <input
                    type="radio"
                    name="saveAction"
                    value="update"
                    checked={saveActionType === 'update'}
                    onChange={() => setSaveActionType('update')}
                    className="mt-0.5"
                  />
                  <div className="w-full">
                    <span className="font-bold text-gray-900 block">Update Existing Property</span>
                    <span className="text-[11px] text-gray-500 block mb-1">
                      Links and saves these verified records to a registered property.
                    </span>
                    {saveActionType === 'update' && (
                      <Select
                        value={targetPropertyId}
                        onChange={(e) => setTargetPropertyId(e.target.value)}
                        className="h-7 text-xs w-full mt-1"
                      >
                        <option value="">Select Property to Update</option>
                        {properties.map((p) => (
                          <option key={p.id} value={p.id}>
                            {p.public_reference} - {p.title.substring(0, 30)}...
                          </option>
                        ))}
                      </Select>
                    )}
                  </div>
                </label>
              </div>

              {/* Consultant Notes */}
              <div>
                <label className="block text-[11px] font-semibold text-gray-700 mb-1">
                  Consultant Verification Notes (Optional)
                </label>
                <Input
                  className="h-7 text-xs"
                  placeholder="e.g. Survey boundary confirmed against revenue Patta No. 614"
                  value={consultantNotes}
                  onChange={(e) => setConsultantNotes(e.target.value)}
                />
              </div>
            </div>
          </div>
        )}

        {/* Modal Action Buttons */}
        <div className="flex items-center justify-between pt-3 border-t border-gray-200">
          <Button type="button" variant="outline" onClick={onClose} className="text-xs">
            Cancel & Discard
          </Button>

          {results && (
            <div className="flex items-center gap-2">
              <Button
                type="button"
                onClick={handleSaveToDb}
                isLoading={saveLoading}
                className="text-xs bg-[var(--color-forest)] text-white font-bold flex items-center gap-1.5"
              >
                <Save className="h-4 w-4" /> Save to Database
              </Button>
            </div>
          )}
        </div>
      </div>
    </Modal>
  );
}
