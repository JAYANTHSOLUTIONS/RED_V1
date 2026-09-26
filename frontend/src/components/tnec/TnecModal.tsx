import React, { useState, useEffect, useRef, useCallback, useMemo } from 'react';
import {
  X,
  FileText,
  Search,
  Plus,
  Trash2,
  CheckCircle,
  AlertCircle,
  Clock,
  Download,
  Shield,
  Loader2,
  RefreshCw,
  Layers,
  Calendar,
  Building,
  MapPin,
  FileCheck,
  Sparkles,
  ArrowRight,
  Database,
} from 'lucide-react';
import {
  tnecApi,
  HierarchyItem,
  SurveySubdivisionItem,
  TnecJobStatus,
} from '../../api/tnec';

interface TnecModalProps {
  isOpen: boolean;
  onClose: () => void;
  propertyId?: string;
  initialSurveyNo?: string;
  initialSubdivision?: string;
  initialDistrict?: string;
  initialTaluk?: string;
  initialVillage?: string;
  onDocumentAttached?: () => void;
}

export const TnecModal: React.FC<TnecModalProps> = ({
  isOpen,
  onClose,
  propertyId,
  initialSurveyNo = '',
  initialSubdivision = '',
  initialDistrict = '',
  initialTaluk = '',
  initialVillage = '',
  onDocumentAttached,
}) => {
  // Access Mode: 'auto' (Auto detail fetch from property) or 'manual' (Manual dropdown explore)
  const [accessMode, setAccessMode] = useState<'auto' | 'manual'>('auto');

  // Cascading Dropdown States
  const [zones, setZones] = useState<HierarchyItem[]>([]);
  const [districts, setDistricts] = useState<HierarchyItem[]>([]);
  const [sros, setSros] = useState<HierarchyItem[]>([]);
  const [villages, setVillages] = useState<HierarchyItem[]>([]);

  const [selectedZone, setSelectedZone] = useState<string>('');
  const [selectedDistrict, setSelectedDistrict] = useState<string>('');
  const [selectedSro, setSelectedSro] = useState<string>('');
  const [selectedVillage, setSelectedVillage] = useState<string>('');

  const [loadingDistricts, setLoadingDistricts] = useState(false);
  const [loadingSros, setLoadingSros] = useState(false);
  const [loadingVillages, setLoadingVillages] = useState(false);

  // Auto-match state
  const [matchingLocation, setMatchingLocation] = useState(false);
  const [autoMatchSuccess, setAutoMatchSuccess] = useState<{
    zone_name: string;
    district_name: string;
    sro_name: string;
    village_name: string;
    confidence: string;
  } | null>(null);
  const [alternateVillages, setAlternateVillages] = useState<{ id: string; name: string }[]>([]);
  const [showWorkflow, setShowWorkflow] = useState(true);

  // Date Picker States (Default: 01-01-1975 to today - 1 day)
  const getYesterdayIso = () => {
    const d = new Date();
    d.setDate(d.getDate() - 1);
    const yyyy = d.getFullYear();
    const mm = String(d.getMonth() + 1).padStart(2, '0');
    const dd = String(d.getDate()).padStart(2, '0');
    return `${yyyy}-${mm}-${dd}`;
  };

  const [startDateIso, setStartDateIso] = useState('1975-01-01');
  const [endDateIso, setEndDateIso] = useState(getYesterdayIso());

  // Converts YYYY-MM-DD to DD/MM/YYYY for TNREGINET
  const toTnDate = (isoStr: string) => {
    if (!isoStr || !isoStr.includes('-')) return isoStr;
    const [yyyy, mm, dd] = isoStr.split('-');
    return `${dd}/${mm}/${yyyy}`;
  };

  // Multi-Survey Builder
  const [curSurveyNo, setCurSurveyNo] = useState(initialSurveyNo);
  const [curSubdivision, setCurSubdivision] = useState(initialSubdivision);
  const [surveyList, setSurveyList] = useState<SurveySubdivisionItem[]>(() => {
    if (initialSurveyNo) {
      return [{ survey_no: initialSurveyNo, sub_division_no: initialSubdivision }];
    }
    return [];
  });

  // Dynamically synchronize survey, subdivision, and locations when modal opens or initial props change
  useEffect(() => {
    if (isOpen) {
      setCurSurveyNo(initialSurveyNo || '');
      setCurSubdivision(initialSubdivision || '');
      if (initialSurveyNo) {
        setSurveyList([{ survey_no: initialSurveyNo, sub_division_no: initialSubdivision || '' }]);
      } else {
        setSurveyList([]);
      }
      setSelectedZone('');
      setSelectedDistrict('');
      setSelectedSro('');
      setSelectedVillage('');
      setAutoMatchSuccess(null);
      setAlternateVillages([]);
      setJobStatus(null);
      setActiveJobId(null);
      setErrorMsg(null);
    }
  }, [isOpen, propertyId, initialSurveyNo, initialSubdivision]);

  // Execution & Tracking States
  const [isScraping, setIsScraping] = useState(false);
  const [activeJobId, setActiveJobId] = useState<string | null>(null);
  const [jobStatus, setJobStatus] = useState<TnecJobStatus | null>(null);
  const [errorMsg, setErrorMsg] = useState<string | null>(null);

  // Captcha Fallback Input
  const [captchaInput, setCaptchaInput] = useState('');
  const [submittingCaptcha, setSubmittingCaptcha] = useState(false);
  const [isDownloading, setIsDownloading] = useState(false);

  const handleDownloadPdf = async () => {
    if (!jobStatus?.job_id || !jobStatus.pdf_filename) return;
    setIsDownloading(true);
    try {
      await tnecApi.downloadPdf(jobStatus.job_id, jobStatus.pdf_filename);
    } catch (err: any) {
      alert(err.message || 'Download failed');
    } finally {
      setIsDownloading(false);
    }
  };

  const pollIntervalRef = useRef<NodeJS.Timeout | null>(null);


  // Load Zones on Mount
  useEffect(() => {
    if (!isOpen) return;
    tnecApi
      .getZones()
      .then((res: any) => {
        const zList: HierarchyItem[] = Array.isArray(res) ? res : res?.data || [];
        setZones(zList);
      })
      .catch((err) => {
        console.error('Failed to load zones:', err);
      });
  }, [isOpen]);

  // Load Districts when Zone changes
  useEffect(() => {
    if (!selectedZone) {
      setDistricts([]);
      return;
    }
    setLoadingDistricts(true);
    tnecApi
      .getDistricts(selectedZone)
      .then((res: any) => {
        const dList: HierarchyItem[] = Array.isArray(res) ? res : res?.data || [];
        setDistricts(dList);
        setLoadingDistricts(false);
      })
      .catch(() => setLoadingDistricts(false));
  }, [selectedZone]);

  // Load SROs when District changes
  useEffect(() => {
    if (!selectedDistrict) {
      setSros([]);
      return;
    }
    setLoadingSros(true);
    tnecApi
      .getSros(selectedDistrict, selectedZone)
      .then((res: any) => {
        const sList: HierarchyItem[] = Array.isArray(res) ? res : res?.data || [];
        setSros(sList);
        setLoadingSros(false);
      })
      .catch(() => setLoadingSros(false));
  }, [selectedDistrict, selectedZone]);

  // Load Villages when SRO changes
  useEffect(() => {
    if (!selectedSro) {
      setVillages([]);
      return;
    }
    setLoadingVillages(true);
    tnecApi
      .getVillages(selectedSro)
      .then((res: any) => {
        const vList: HierarchyItem[] = Array.isArray(res) ? res : res?.data || [];
        setVillages(vList);
        setLoadingVillages(false);
      })
      .catch(() => setLoadingVillages(false));
  }, [selectedSro]);

  // Access Method 1: Auto-Detect & Fill from Property Details
  const handleAutoFillFromProperty = useCallback(async () => {
    setMatchingLocation(true);
    setErrorMsg(null);
    try {
      const matchRes = await tnecApi.matchLocation({
        district: initialDistrict,
        taluk: initialTaluk,
        village: initialVillage,
      });

      const match = (matchRes as any)?.data || matchRes;
      if (match && match.zone_id) {
        // Set values
        setSelectedZone(match.zone_id);

        // Fetch and select District
        const dList = await tnecApi.getDistricts(match.zone_id);
        const dists = Array.isArray(dList) ? dList : (dList as any)?.data || [];
        setDistricts(dists);
        setSelectedDistrict(match.district_id);

        // Fetch and select SRO
        const sList = await tnecApi.getSros(match.district_id, match.zone_id);
        const srosArr = Array.isArray(sList) ? sList : (sList as any)?.data || [];
        setSros(srosArr);
        setSelectedSro(match.sro_id);

        // Fetch and select Village
        const vList = await tnecApi.getVillages(match.sro_id);
        const vilsArr = Array.isArray(vList) ? vList : (vList as any)?.data || [];
        setVillages(vilsArr);
        setSelectedVillage(match.village_id);

        if (match.alternate_villages) {
          setAlternateVillages(match.alternate_villages);
        } else {
          setAlternateVillages([]);
        }

        // Auto-add property survey number if available
        if (initialSurveyNo) {
          setCurSurveyNo(initialSurveyNo);
          setCurSubdivision(initialSubdivision || '');
          setSurveyList([{ survey_no: initialSurveyNo, sub_division_no: initialSubdivision || '' }]);
        }

        setAutoMatchSuccess({
          zone_name: match.zone_name,
          district_name: match.district_name,
          sro_name: match.sro_name,
          village_name: match.village_name,
          confidence: match.match_confidence,
        });
      } else {
        setErrorMsg('Could not find direct match in master records. Please select manually below.');
      }
    } catch (err: any) {
      console.error('Auto match failed:', err);
      setErrorMsg('Auto-match failed. Please select your jurisdiction manually.');
    } finally {
      setMatchingLocation(false);
    }
  }, [initialDistrict, initialTaluk, initialVillage, initialSurveyNo, initialSubdivision]);

  // Trigger auto-match on open if in auto mode
  useEffect(() => {
    if (isOpen && accessMode === 'auto' && !selectedVillage && initialDistrict) {
      handleAutoFillFromProperty();
    }
  }, [isOpen, accessMode, selectedVillage, initialDistrict, handleAutoFillFromProperty]);

  // Add Survey handler
  const handleAddSurvey = () => {
    const sNo = curSurveyNo.trim();
    const sSub = curSubdivision.trim();
    if (!sNo) return;

    const exists = surveyList.some(
      (item) =>
        item.survey_no.toLowerCase() === sNo.toLowerCase() &&
        (item.sub_division_no || '').toLowerCase() === sSub.toLowerCase()
    );

    if (!exists) {
      setSurveyList([...surveyList, { survey_no: sNo, sub_division_no: sSub }]);
    }
    setCurSurveyNo('');
    setCurSubdivision('');
  };

  const handleRemoveSurvey = (idx: number) => {
    setSurveyList(surveyList.filter((_, i) => i !== idx));
  };

  // Start Scraper
  const handleStartScrape = async () => {
    if (!selectedZone || !selectedDistrict || !selectedSro || !selectedVillage) {
      setErrorMsg('Please select Zone, District, SRO, and Village.');
      return;
    }

    let surveysToSearch = [...surveyList];
    if (surveysToSearch.length === 0 && curSurveyNo.trim()) {
      surveysToSearch = [
        { survey_no: curSurveyNo.trim(), sub_division_no: curSubdivision.trim() },
      ];
      setSurveyList(surveysToSearch);
    }

    if (surveysToSearch.length === 0) {
      setErrorMsg('Please add at least one Survey Number.');
      return;
    }

    setErrorMsg(null);
    setIsScraping(true);
    setJobStatus(null);
    setCaptchaInput('');

    try {
      const startRes = await tnecApi.startScrape({
        property_id: propertyId,
        zone_id: selectedZone,
        district_id: selectedDistrict,
        sro_id: selectedSro,
        village_id: selectedVillage,
        start_date: toTnDate(startDateIso),
        end_date: toTnDate(endDateIso),
        surveys: surveysToSearch,
      });

      const resData = (startRes as any)?.data || startRes;
      setActiveJobId(resData.job_id);
    } catch (err: any) {
      setErrorMsg(err.message || 'Failed to start TNEC scraper.');
      setIsScraping(false);
    }
  };

  // Polling Job Status
  const pollStatus = useCallback(async () => {
    if (!activeJobId) return;
    try {
      const statusRes = await tnecApi.getStatus(activeJobId);
      const resData = (statusRes as any)?.data || statusRes;
      setJobStatus(resData);

      if (resData.status === 'completed') {
        setIsScraping(false);
        if (pollIntervalRef.current) clearInterval(pollIntervalRef.current);
        if (onDocumentAttached) {
          onDocumentAttached();
        }
      } else if (resData.status === 'failed') {
        setIsScraping(false);
        setErrorMsg(resData.error || resData.message || 'Scraper encountered an error.');
        if (pollIntervalRef.current) clearInterval(pollIntervalRef.current);
      }
    } catch (err: any) {
      console.error('Error polling status:', err);
    }
  }, [activeJobId, onDocumentAttached]);

  useEffect(() => {
    if (activeJobId && isScraping) {
      pollIntervalRef.current = setInterval(pollStatus, 1500);
      pollStatus();
    }
    return () => {
      if (pollIntervalRef.current) clearInterval(pollIntervalRef.current);
    };
  }, [activeJobId, isScraping, pollStatus]);

  // Submit Captcha Override
  const handleSubmitCaptcha = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!activeJobId || !captchaInput.trim()) return;

    setSubmittingCaptcha(true);
    try {
      await tnecApi.submitCaptcha(activeJobId, captchaInput.trim());
      setCaptchaInput('');
    } catch (err: any) {
      setErrorMsg('Failed to submit CAPTCHA.');
    } finally {
      setSubmittingCaptcha(false);
    }
  };

  if (!isOpen) return null;

  const currentStep = jobStatus ? jobStatus.current_step : 1;

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/60 backdrop-blur-sm animate-fadeIn">
      <div className="relative w-full max-w-3xl max-h-[92vh] flex flex-col bg-white dark:bg-gray-900 rounded-2xl shadow-2xl border border-gray-100 dark:border-gray-800 overflow-hidden">
        {/* MODAL HEADER */}
        <div className="px-6 py-4 flex items-center justify-between border-b border-gray-100 dark:border-gray-800 bg-gradient-to-r from-blue-600 via-indigo-600 to-purple-600 text-white">
          <div className="flex items-center space-x-3">
            <div className="p-2.5 bg-white/10 rounded-xl backdrop-blur-md">
              <FileText className="h-6 w-6 text-white" />
            </div>
            <div>
              <h2 className="text-lg font-bold tracking-tight">
                TNREGINET Encumbrance Certificate (EC) Search
              </h2>
              <p className="text-xs text-blue-100 font-medium">
                Inspector General of Registration (IGR) Tamil Nadu • Automated Form 15/16 Downloader
              </p>
            </div>
          </div>
          <button
            onClick={onClose}
            className="p-1.5 rounded-lg text-white/80 hover:text-white hover:bg-white/10 transition-colors"
          >
            <X className="h-5 w-5" />
          </button>
        </div>

        {/* ACCESS METHOD SELECTOR TABS */}
        <div className="px-6 pt-4 pb-2 bg-gray-50 dark:bg-gray-850 border-b border-gray-200 dark:border-gray-800">
          <div className="flex items-center p-1 bg-gray-200/70 dark:bg-gray-800 rounded-xl max-w-md">
            <button
              type="button"
              onClick={() => {
                setAccessMode('auto');
                if (!selectedVillage) handleAutoFillFromProperty();
              }}
              className={`flex-1 py-1.5 px-3 rounded-lg text-xs font-bold transition-all flex items-center justify-center gap-1.5 ${
                accessMode === 'auto'
                  ? 'bg-white dark:bg-gray-700 text-blue-700 dark:text-blue-300 shadow-sm'
                  : 'text-gray-600 dark:text-gray-400 hover:text-gray-900'
              }`}
            >
              <Sparkles className="h-3.5 w-3.5 text-blue-600" />
              <span>1. Auto Detail Fetch</span>
            </button>
            <button
              type="button"
              onClick={() => setAccessMode('manual')}
              className={`flex-1 py-1.5 px-3 rounded-lg text-xs font-bold transition-all flex items-center justify-center gap-1.5 ${
                accessMode === 'manual'
                  ? 'bg-white dark:bg-gray-700 text-purple-700 dark:text-purple-300 shadow-sm'
                  : 'text-gray-600 dark:text-gray-400 hover:text-gray-900'
              }`}
            >
              <Search className="h-3.5 w-3.5 text-purple-600" />
              <span>2. Manual Custom Search</span>
            </button>
          </div>
        </div>

        {/* MODAL BODY */}
        <div className="p-6 overflow-y-auto flex-1 space-y-6">
          {errorMsg && (
            <div className="p-3.5 bg-rose-50 dark:bg-rose-950/40 border border-rose-200 dark:border-rose-900/60 rounded-xl flex items-start space-x-3 text-rose-700 dark:text-rose-300 text-xs">
              <AlertCircle className="h-4 w-4 shrink-0 mt-0.5 text-rose-600" />
              <div className="flex-1">
                <span className="font-semibold">Notice: </span>
                {errorMsg}
              </div>
            </div>
          )}

          {/* ACCESS MODE 1: AUTO DETAIL FETCH CONTEXT CARD */}
          {accessMode === 'auto' && (
            <div className="p-4 bg-gradient-to-r from-blue-50 via-indigo-50 to-purple-50 dark:from-blue-950/30 dark:via-indigo-950/20 dark:to-purple-950/30 border border-blue-200/80 dark:border-blue-900/60 rounded-xl space-y-3">
              <div className="flex items-center justify-between">
                <div className="flex items-center gap-2">
                  <Database className="h-4 w-4 text-blue-600" />
                  <span className="text-xs font-bold text-gray-900 dark:text-gray-100">
                    Property Location & Survey Metadata
                  </span>
                </div>
                <button
                  type="button"
                  onClick={handleAutoFillFromProperty}
                  disabled={matchingLocation || isScraping}
                  className="px-3 py-1 bg-white dark:bg-gray-800 hover:bg-blue-50 text-blue-700 dark:text-blue-300 border border-blue-200 dark:border-blue-800 rounded-lg text-xs font-semibold flex items-center gap-1.5 shadow-2xs transition-all"
                >
                  {matchingLocation ? (
                    <>
                      <Loader2 className="h-3 w-3 animate-spin text-blue-600" />
                      <span>Matching Master Records...</span>
                    </>
                  ) : (
                    <>
                      <Sparkles className="h-3 w-3 text-blue-600" />
                      <span>⚡ Auto-Fill from Property</span>
                    </>
                  )}
                </button>
              </div>

              <div className="grid grid-cols-2 sm:grid-cols-4 gap-2 text-xs">
                <div className="p-2 bg-white/80 dark:bg-gray-800/80 rounded-lg border border-blue-100 dark:border-gray-700">
                  <div className="text-[10px] text-gray-500 font-medium">District</div>
                  <div className="font-bold text-gray-800 dark:text-gray-200 truncate">
                    {initialDistrict || '—'}
                  </div>
                </div>
                <div className="p-2 bg-white/80 dark:bg-gray-800/80 rounded-lg border border-blue-100 dark:border-gray-700">
                  <div className="text-[10px] text-gray-500 font-medium">Taluk</div>
                  <div className="font-bold text-gray-800 dark:text-gray-200 truncate">
                    {initialTaluk || '—'}
                  </div>
                </div>
                <div className="p-2 bg-white/80 dark:bg-gray-800/80 rounded-lg border border-blue-100 dark:border-gray-700">
                  <div className="text-[10px] text-gray-500 font-medium">Village / Locality</div>
                  <div className="font-bold text-gray-800 dark:text-gray-200 truncate">
                    {initialVillage || '—'}
                  </div>
                </div>
                <div className="p-2 bg-white/80 dark:bg-gray-800/80 rounded-lg border border-blue-100 dark:border-gray-700">
                  <div className="text-[10px] text-gray-500 font-medium">Survey / Subdiv</div>
                  <div className="font-bold text-gray-800 dark:text-gray-200 truncate">
                    {initialSurveyNo ? `${initialSurveyNo}/${initialSubdivision || '—'}` : '—'}
                  </div>
                </div>
              </div>

              {autoMatchSuccess && (
                <div className="p-2.5 bg-emerald-50/90 dark:bg-emerald-950/40 border border-emerald-200 dark:border-emerald-800/60 rounded-lg text-xs text-emerald-800 dark:text-emerald-300 flex items-center gap-2">
                  <CheckCircle className="h-4 w-4 text-emerald-600 shrink-0" />
                  <div className="truncate">
                    <span className="font-bold">Auto-Matched:</span> Zone:{' '}
                    <span className="font-semibold">{autoMatchSuccess.zone_name}</span> • District:{' '}
                    <span className="font-semibold">{autoMatchSuccess.district_name}</span> • SRO:{' '}
                    <span className="font-semibold">{autoMatchSuccess.sro_name}</span> • Village:{' '}
                    <span className="font-semibold">{autoMatchSuccess.village_name}</span>
                  </div>
                </div>
              )}

              {/* SIBLING VILLAGE ALTERNATE SELECTOR */}
              {alternateVillages && alternateVillages.length > 0 && (
                <div className="p-2.5 bg-amber-50 dark:bg-amber-950/40 border border-amber-200 dark:border-amber-800/60 rounded-lg text-xs text-amber-900 dark:text-amber-200 flex flex-col sm:flex-row sm:items-center sm:justify-between gap-2">
                  <div className="flex items-center gap-1.5">
                    <AlertCircle className="h-4 w-4 text-amber-600 shrink-0" />
                    <span>
                      <strong>Sibling Village detected in this SRO:</strong> Documents might be registered under {alternateVillages.map((v) => v.name).join(', ')}.
                    </span>
                  </div>
                  <div className="flex items-center gap-1.5 shrink-0">
                    {alternateVillages.map((alt) => (
                      <button
                        key={alt.id}
                        type="button"
                        onClick={() => setSelectedVillage(alt.id)}
                        className={`px-2.5 py-1 rounded-md text-[11px] font-bold transition-all ${
                          selectedVillage === alt.id
                            ? 'bg-amber-600 text-white shadow-xs'
                            : 'bg-white dark:bg-gray-800 text-amber-800 dark:text-amber-300 border border-amber-300 dark:border-amber-700 hover:bg-amber-100'
                        }`}
                      >
                        {selectedVillage === alt.id ? `✓ Active: ${alt.name}` : `Switch to ${alt.name}`}
                      </button>
                    ))}
                  </div>
                </div>
              )}

              {/* EXPLICIT WORKFLOW PIPELINE ACCORDION */}
              <div className="border border-indigo-100 dark:border-indigo-900/60 rounded-xl overflow-hidden shadow-xs">
                <div
                  onClick={() => setShowWorkflow(!showWorkflow)}
                  className="px-4 py-2.5 bg-gradient-to-r from-indigo-50 to-blue-50 dark:from-indigo-950/40 dark:to-blue-950/30 flex items-center justify-between cursor-pointer select-none"
                >
                  <div className="flex items-center gap-2">
                    <Layers className="h-4 w-4 text-indigo-600" />
                    <span className="text-xs font-bold text-indigo-950 dark:text-indigo-200 uppercase tracking-wider">
                      EC Extraction Workflow & Live Query Pipeline
                    </span>
                  </div>
                  <span className="text-[11px] text-indigo-600 dark:text-indigo-400 font-semibold">
                    {showWorkflow ? 'Hide Workflow Details ▲' : 'Show Full Workflow Steps ▼'}
                  </span>
                </div>

                {showWorkflow && (
                  <div className="p-4 bg-white dark:bg-gray-850 space-y-3 text-xs border-t border-indigo-100 dark:border-indigo-900/40">
                    <div className="grid grid-cols-1 md:grid-cols-3 gap-3">
                      {/* Step 1: Extracted Property Identification */}
                      <div className="p-3 rounded-lg bg-gray-50 dark:bg-gray-800/60 border border-gray-200 dark:border-gray-700">
                        <div className="flex items-center justify-between mb-1.5">
                          <span className="font-bold text-gray-800 dark:text-gray-200 flex items-center gap-1">
                            <span className="w-4 h-4 rounded-full bg-blue-600 text-white text-[10px] flex items-center justify-center font-bold">1</span>
                            Extracted Credentials
                          </span>
                          <span className="text-[10px] text-emerald-600 font-semibold bg-emerald-50 px-1.5 py-0.5 rounded border border-emerald-200">
                            Auto-Parsed
                          </span>
                        </div>
                        <ul className="space-y-1 text-[11px] text-gray-600 dark:text-gray-300">
                          <li><strong>Survey:</strong> <span className="font-mono font-bold text-blue-700 dark:text-blue-300">{curSurveyNo || initialSurveyNo || 'Not specified'}</span></li>
                          <li><strong>Subdivision:</strong> <span className="font-mono font-bold text-purple-700 dark:text-purple-300">{curSubdivision || initialSubdivision || 'Undivided (--)'}</span></li>
                          <li><strong>Village:</strong> {initialVillage || '—'}</li>
                        </ul>
                      </div>

                      {/* Step 2: Jurisdiction & SRO Match */}
                      <div className="p-3 rounded-lg bg-gray-50 dark:bg-gray-800/60 border border-gray-200 dark:border-gray-700">
                        <div className="flex items-center justify-between mb-1.5">
                          <span className="font-bold text-gray-800 dark:text-gray-200 flex items-center gap-1">
                            <span className="w-4 h-4 rounded-full bg-purple-600 text-white text-[10px] flex items-center justify-center font-bold">2</span>
                            TNREGINET Cascade
                          </span>
                          <span className="text-[10px] text-indigo-600 font-semibold bg-indigo-50 px-1.5 py-0.5 rounded border border-indigo-200">
                            {autoMatchSuccess?.confidence || 'Mapped'}
                          </span>
                        </div>
                        <ul className="space-y-1 text-[11px] text-gray-600 dark:text-gray-300">
                          <li><strong>Zone:</strong> {autoMatchSuccess?.zone_name || zones.find((z) => z.id === selectedZone)?.name || '—'}</li>
                          <li><strong>SRO:</strong> {autoMatchSuccess?.sro_name || sros.find((s) => s.id === selectedSro)?.name || '—'}</li>
                          <li><strong>Village:</strong> {selectedVillage ? villages.find((v) => v.id === selectedVillage)?.name : '—'}</li>
                        </ul>
                      </div>

                      {/* Step 3: Query Execution Scope */}
                      <div className="p-3 rounded-lg bg-gray-50 dark:bg-gray-800/60 border border-gray-200 dark:border-gray-700">
                        <div className="flex items-center justify-between mb-1.5">
                          <span className="font-bold text-gray-800 dark:text-gray-200 flex items-center gap-1">
                            <span className="w-4 h-4 rounded-full bg-emerald-600 text-white text-[10px] flex items-center justify-center font-bold">3</span>
                            Search Target
                          </span>
                          <span className="text-[10px] text-purple-600 font-semibold bg-purple-50 px-1.5 py-0.5 rounded border border-purple-200">
                            {toTnDate(startDateIso)} → {toTnDate(endDateIso)}
                          </span>
                        </div>
                        <p className="text-[11px] text-gray-500 dark:text-gray-400 leading-relaxed">
                          Querying {surveyList.length} parcel(s). TNREGINET matches exact subdivision. If searching with blank subdivision returns &quot;No records found&quot;, enter subdivision number or toggle sibling village.
                        </p>
                      </div>
                    </div>
                  </div>
                )}
              </div>
            </div>
          )}

          {/* LIVE FLIPKART TRACKING STEPPER */}
          {isScraping && (
            <div className="p-5 bg-gradient-to-b from-blue-50/50 to-indigo-50/30 dark:from-gray-800/60 dark:to-gray-850 border border-blue-100 dark:border-gray-700 rounded-xl shadow-sm space-y-4">
              <div className="flex items-center justify-between">
                <span className="text-xs font-bold text-blue-800 dark:text-blue-300 uppercase tracking-wider flex items-center gap-1.5">
                  <RefreshCw className="h-3.5 w-3.5 animate-spin text-blue-600" />
                  Live Extraction Tracker
                </span>
                <span className="text-[11px] font-semibold text-gray-500 bg-white dark:bg-gray-800 px-2.5 py-1 rounded-full border border-gray-200 dark:border-gray-700">
                  Job #{activeJobId}
                </span>
              </div>

              {/* Progress Milestones */}
              <div className="space-y-3 pt-2">
                {[
                  {
                    step: 1,
                    title: 'Background Engine & Portal Authentication',
                    desc: 'Headless Chrome started silently, dismissed app modal, locale set to English',
                  },
                  {
                    step: 2,
                    title: 'Jurisdiction & Multi-Survey Injection',
                    desc: `Setting ${selectedDistrict ? 'District/SRO/Village' : 'location'} and adding ${surveyList.length || 1} survey parcel(s)`,
                  },
                  {
                    step: 3,
                    title: 'Security CAPTCHA Recognition',
                    desc:
                      jobStatus?.status === 'waiting_for_captcha'
                        ? 'Awaiting user CAPTCHA confirmation below'
                        : 'OCR preprocessing grid lines and extracting 5-character token',
                  },
                  {
                    step: 4,
                    title: 'Query Execution & Confirmation Dialogs',
                    desc: 'Submitting search, handling portal alert dialogues',
                  },
                  {
                    step: 5,
                    title: 'EC Statement Generation & Vault Download',
                    desc: 'Retrieving official signed EC PDF and attaching to Property Vault',
                  },
                ].map((m) => {
                  const isDone = currentStep > m.step || jobStatus?.status === 'completed';
                  const isCurrent = currentStep === m.step && jobStatus?.status !== 'completed';

                  return (
                    <div key={m.step} className="flex items-start space-x-3 text-xs">
                      <div className="relative mt-0.5">
                        {isDone ? (
                          <div className="w-5 h-5 rounded-full bg-emerald-500 text-white flex items-center justify-center text-[10px] font-bold">
                            ✓
                          </div>
                        ) : isCurrent ? (
                          <div className="w-5 h-5 rounded-full bg-blue-600 text-white flex items-center justify-center text-[10px] font-bold ring-4 ring-blue-100 dark:ring-blue-900/50 animate-pulse">
                            {m.step}
                          </div>
                        ) : (
                          <div className="w-5 h-5 rounded-full bg-gray-200 dark:bg-gray-700 text-gray-500 flex items-center justify-center text-[10px] font-bold">
                            {m.step}
                          </div>
                        )}
                      </div>
                      <div className="flex-1">
                        <div
                          className={`font-semibold ${
                            isCurrent
                              ? 'text-blue-700 dark:text-blue-400'
                              : isDone
                              ? 'text-emerald-700 dark:text-emerald-400'
                              : 'text-gray-500'
                          }`}
                        >
                          {m.title}
                        </div>
                        <div className="text-[11px] text-gray-500 dark:text-gray-400">
                          {m.desc}
                        </div>
                      </div>
                    </div>
                  );
                })}
              </div>

              {/* IN-MODAL SECURITY CAPTCHA ENTRY CHALLENGE */}
              {jobStatus?.status === 'waiting_for_captcha' && jobStatus.captcha_image && (
                <div className="mt-4 p-5 bg-gradient-to-br from-amber-50 via-orange-50/40 to-yellow-50/50 dark:from-amber-950/60 dark:via-orange-950/30 dark:to-yellow-950/40 border-2 border-amber-400 dark:border-amber-600 rounded-2xl shadow-xl ring-4 ring-amber-400/20 space-y-4 animate-in fade-in zoom-in-95 duration-200">
                  <div className="flex items-center justify-between">
                    <div className="flex items-center space-x-2 text-amber-950 dark:text-amber-100 text-sm font-bold">
                      <Shield className="h-5 w-5 text-amber-600 animate-pulse" />
                      <span>Security CAPTCHA Verification</span>
                    </div>
                    <span className="px-2.5 py-0.5 rounded-full text-[11px] font-bold bg-amber-200/80 dark:bg-amber-800 text-amber-900 dark:text-amber-100">
                      Step 3 of 5
                    </span>
                  </div>

                  <p className="text-xs text-amber-900/90 dark:text-amber-200/90 font-medium">
                    The official TNREGINET portal requires human security verification to retrieve this document. Please enter the 5 characters shown below:
                  </p>

                  <div className="flex flex-col sm:flex-row items-center gap-4 bg-white/90 dark:bg-gray-850 p-4 rounded-xl border border-amber-200/80 dark:border-amber-800/80 shadow-inner">
                    {/* Captcha Image zoomed and centered */}
                    <div className="p-2 bg-white dark:bg-gray-900 rounded-xl border-2 border-amber-300 dark:border-amber-700 shadow-sm flex items-center justify-center shrink-0">
                      <img
                        src={jobStatus.captcha_image}
                        alt="Security CAPTCHA"
                        className="h-12 w-auto max-w-[180px] rounded object-contain select-none"
                      />
                    </div>

                    {/* Entry Form */}
                    <form onSubmit={handleSubmitCaptcha} className="flex flex-col sm:flex-row items-center gap-3 flex-1 w-full">
                      <div className="relative flex-1 w-full">
                        <input
                          type="text"
                          maxLength={5}
                          value={captchaInput}
                          onChange={(e) => setCaptchaInput(e.target.value.toUpperCase())}
                          placeholder="ENTER 5 CHARS"
                          className="w-full px-4 py-3 text-base font-mono font-bold tracking-[0.25em] uppercase rounded-xl border-2 border-amber-300 dark:border-amber-700 bg-white dark:bg-gray-800 text-gray-900 dark:text-gray-100 focus:ring-4 focus:ring-amber-400/40 focus:border-amber-500 outline-none text-center shadow-xs placeholder:tracking-normal placeholder:text-xs"
                          autoFocus
                        />
                      </div>
                      <button
                        type="submit"
                        disabled={submittingCaptcha || captchaInput.trim().length < 4}
                        className="w-full sm:w-auto px-6 py-3 text-xs font-bold text-white bg-gradient-to-r from-amber-600 to-orange-600 hover:from-amber-700 hover:to-orange-700 disabled:opacity-50 rounded-xl transition-all shadow-md hover:shadow-lg flex items-center justify-center space-x-2 shrink-0 cursor-pointer"
                      >
                        {submittingCaptcha ? (
                          <>
                            <Loader2 className="h-4 w-4 animate-spin" />
                            <span>Verifying...</span>
                          </>
                        ) : (
                          <>
                            <CheckCircle className="h-4 w-4" />
                            <span>Confirm & Search</span>
                          </>
                        )}
                      </button>
                    </form>
                  </div>
                  <div className="text-[11px] text-gray-500 dark:text-gray-400 text-center">
                    💡 Tip: Letters and numbers are automatically capitalized. Press <kbd className="px-1.5 py-0.5 bg-gray-200 dark:bg-gray-700 rounded text-[10px] font-mono">Enter</kbd> to submit immediately.
                  </div>
                </div>
              )}
            </div>
          )}

          {/* COMPLETED SUCCESS STATE */}
          {jobStatus?.status === 'completed' && (
            <div className="p-5 bg-emerald-50 dark:bg-emerald-950/30 border border-emerald-200 dark:border-emerald-800 rounded-xl space-y-4">
              <div className="flex items-center space-x-3">
                <div className="p-2 bg-emerald-100 dark:bg-emerald-900 rounded-full text-emerald-700 dark:text-emerald-300">
                  <CheckCircle className="h-6 w-6" />
                </div>
                <div>
                  <h3 className="text-sm font-bold text-emerald-900 dark:text-emerald-200">
                    {jobStatus.is_nil_encumbrance
                      ? 'Nil Encumbrance Verified (Form 16)'
                      : 'Encumbrance Certificate (EC) Ready!'}
                  </h3>
                  <p className="text-xs text-emerald-700 dark:text-emerald-400">
                    {jobStatus.message || 'Document downloaded and attached to Property Vault.'}
                  </p>
                </div>
              </div>

              {/* NIL ENCUMBRANCE DIAGNOSTICS & HELP */}
              {jobStatus.is_nil_encumbrance && (
                <div className="p-4 bg-amber-50 dark:bg-amber-950/40 border border-amber-200 dark:border-amber-800 rounded-xl space-y-2 text-xs text-amber-900 dark:text-amber-200">
                  <div className="font-bold flex items-center gap-1.5 text-amber-800 dark:text-amber-300">
                    <AlertCircle className="h-4 w-4 text-amber-600" />
                    Document exists but TNREGINET returned &quot;No Records Found&quot;? Check these factors:
                  </div>
                  <ul className="list-disc pl-5 space-y-1.5 text-[11px] text-amber-800/90 dark:text-amber-300/90">
                    <li>
                      <strong>Subdivision Match:</strong> TNREGINET treats an empty subdivision as an undivided parcel (<code>--</code>). If the document was registered under a subdivision like <code>4</code>, <code>1</code>, or <code>1B2</code>, searching without a subdivision will return Nil EC.
                    </li>
                    {alternateVillages.length > 0 && (
                      <li>
                        <strong>Sibling Village:</strong> In this SRO, revenue records are divided between multiple village registers (e.g. <code>{alternateVillages[0].name}</code>).
                        <button
                          type="button"
                          onClick={() => {
                            const other = alternateVillages[0];
                            if (other) {
                              setSelectedVillage(other.id);
                              setJobStatus(null);
                            }
                          }}
                          className="ml-2 px-2 py-0.5 bg-amber-200 hover:bg-amber-300 rounded text-amber-900 font-bold underline"
                        >
                          Switch to {alternateVillages[0].name} & Retry
                        </button>
                      </li>
                    )}
                    <li>
                      <strong>Search Period:</strong> Verify the start date covers the year the deed was executed (default begins 01/01/1975).
                    </li>
                  </ul>
                </div>
              )}

              {jobStatus.pdf_filename && (
                <div className="flex items-center justify-between p-3 bg-white dark:bg-gray-800 rounded-lg border border-emerald-100 dark:border-emerald-900/50">
                  <div className="flex items-center space-x-2.5">
                    <FileCheck className="h-5 w-5 text-emerald-600" />
                    <div>
                      <div className="text-xs font-bold text-gray-800 dark:text-gray-200">
                        {jobStatus.pdf_filename}
                      </div>
                      <div className="text-[10px] text-gray-500">Official TNREGINET Signed PDF</div>
                    </div>
                  </div>
                  <button
                    type="button"
                    onClick={handleDownloadPdf}
                    disabled={isDownloading}
                    className="px-3.5 py-1.5 bg-emerald-600 hover:bg-emerald-700 disabled:opacity-50 text-white rounded-lg text-xs font-semibold flex items-center space-x-1.5 transition-colors shadow-sm"
                  >
                    {isDownloading ? (
                      <>
                        <Loader2 className="h-3.5 w-3.5 animate-spin" />
                        <span>Downloading...</span>
                      </>
                    ) : (
                      <>
                        <Download className="h-3.5 w-3.5" />
                        <span>Download PDF</span>
                      </>
                    )}
                  </button>
                </div>
              )}
            </div>
          )}


          {/* FORM: CASCASED DROPDOWNS & SURVEYS */}
          <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
            {/* Zone */}
            <div>
              <label className="block text-xs font-bold text-gray-700 dark:text-gray-300 mb-1.5 flex items-center gap-1">
                <Building className="h-3.5 w-3.5 text-blue-600" />
                Registration Zone
              </label>
              <select
                value={selectedZone}
                onChange={(e) => {
                  setSelectedZone(e.target.value);
                  setSelectedDistrict('');
                  setSelectedSro('');
                  setSelectedVillage('');
                }}
                disabled={isScraping}
                className="w-full px-3 py-2 text-xs rounded-xl border border-gray-200 dark:border-gray-700 bg-white dark:bg-gray-800 text-gray-800 dark:text-gray-200 focus:ring-2 focus:ring-blue-500 outline-none"
              >
                <option value="">-- Select Registration Zone --</option>
                {zones.map((z) => (
                  <option key={z.id} value={z.id}>
                    {z.name}
                  </option>
                ))}
              </select>
            </div>

            {/* District */}
            <div>
              <label className="block text-xs font-bold text-gray-700 dark:text-gray-300 mb-1.5 flex items-center gap-1">
                <MapPin className="h-3.5 w-3.5 text-indigo-600" />
                Registration District {loadingDistricts && <Loader2 className="h-3 w-3 animate-spin inline ml-1" />}
              </label>
              <select
                value={selectedDistrict}
                onChange={(e) => {
                  setSelectedDistrict(e.target.value);
                  setSelectedSro('');
                  setSelectedVillage('');
                }}
                disabled={isScraping || loadingDistricts}
                className="w-full px-3 py-2 text-xs rounded-xl border border-gray-200 dark:border-gray-700 bg-white dark:bg-gray-800 text-gray-800 dark:text-gray-200 focus:ring-2 focus:ring-blue-500 outline-none"
              >
                <option value="">{loadingDistricts ? 'Loading districts...' : '-- Select Registration District --'}</option>
                {districts.map((d) => (
                  <option key={d.id} value={d.id}>
                    {d.name}
                  </option>
                ))}
              </select>
            </div>

            {/* SRO */}
            <div>
              <label className="block text-xs font-bold text-gray-700 dark:text-gray-300 mb-1.5 flex items-center gap-1">
                <Layers className="h-3.5 w-3.5 text-purple-600" />
                Sub-Registrar Office (SRO) {loadingSros && <Loader2 className="h-3 w-3 animate-spin inline ml-1" />}
              </label>
              <select
                value={selectedSro}
                onChange={(e) => {
                  setSelectedSro(e.target.value);
                  setSelectedVillage('');
                }}
                disabled={isScraping || loadingSros}
                className="w-full px-3 py-2 text-xs rounded-xl border border-gray-200 dark:border-gray-700 bg-white dark:bg-gray-800 text-gray-800 dark:text-gray-200 focus:ring-2 focus:ring-blue-500 outline-none"
              >
                <option value="">{loadingSros ? 'Loading SROs...' : '-- Select Sub-Registrar Office (SRO) --'}</option>
                {sros.map((s) => (
                  <option key={s.id} value={s.id}>
                    {s.name}
                  </option>
                ))}
              </select>
            </div>

            {/* Village */}
            <div>
              <label className="block text-xs font-bold text-gray-700 dark:text-gray-300 mb-1.5 flex items-center gap-1">
                <MapPin className="h-3.5 w-3.5 text-emerald-600" />
                Revenue Village {loadingVillages && <Loader2 className="h-3 w-3 animate-spin inline ml-1" />}
              </label>
              <select
                value={selectedVillage}
                onChange={(e) => setSelectedVillage(e.target.value)}
                disabled={isScraping || loadingVillages}
                className="w-full px-3 py-2 text-xs rounded-xl border border-gray-200 dark:border-gray-700 bg-white dark:bg-gray-800 text-gray-800 dark:text-gray-200 focus:ring-2 focus:ring-blue-500 outline-none"
              >
                <option value="">{loadingVillages ? 'Loading villages...' : '-- Select Revenue Village --'}</option>
                {villages.map((v) => (
                  <option key={v.id} value={v.id}>
                    {v.name}
                  </option>
                ))}
              </select>
            </div>
          </div>

          {/* DATE RANGE / PERIOD (DATE PICKER NOT TYPING) */}
          <div className="grid grid-cols-1 sm:grid-cols-2 gap-4 p-4 bg-gray-50 dark:bg-gray-800/40 border border-gray-100 dark:border-gray-800 rounded-xl">
            <div>
              <label className="block text-xs font-bold text-gray-700 dark:text-gray-300 mb-1 flex items-center justify-between">
                <span className="flex items-center gap-1">
                  <Calendar className="h-3.5 w-3.5 text-blue-600" />
                  Period Start Date (Calendar Picker)
                </span>
                <span className="text-[10px] text-gray-400 font-normal">Default: 01-01-1975</span>
              </label>
              <input
                type="date"
                value={startDateIso}
                min="1950-01-01"
                max={endDateIso}
                onChange={(e) => setStartDateIso(e.target.value)}
                disabled={isScraping}
                className="w-full px-3 py-2 text-xs rounded-lg border border-gray-200 dark:border-gray-700 bg-white dark:bg-gray-800 text-gray-800 dark:text-gray-200 focus:ring-2 focus:ring-blue-500 outline-none cursor-pointer"
              />
              <div className="text-[10px] text-gray-400 mt-0.5">
                Formatted for TNREGINET: <span className="font-mono text-gray-600 dark:text-gray-300">{toTnDate(startDateIso)}</span>
              </div>
            </div>
            <div>
              <label className="block text-xs font-bold text-gray-700 dark:text-gray-300 mb-1 flex items-center justify-between">
                <span className="flex items-center gap-1">
                  <Clock className="h-3.5 w-3.5 text-purple-600" />
                  Period End Date (Calendar Picker)
                </span>
                <span className="text-[10px] text-gray-400 font-normal">Default: Yesterday (Today - 1)</span>
              </label>
              <input
                type="date"
                value={endDateIso}
                min={startDateIso}
                max={getYesterdayIso()}
                onChange={(e) => setEndDateIso(e.target.value)}
                disabled={isScraping}
                className="w-full px-3 py-2 text-xs rounded-lg border border-gray-200 dark:border-gray-700 bg-white dark:bg-gray-800 text-gray-800 dark:text-gray-200 focus:ring-2 focus:ring-blue-500 outline-none cursor-pointer"
              />
              <div className="text-[10px] text-gray-400 mt-0.5">
                Formatted for TNREGINET: <span className="font-mono text-gray-600 dark:text-gray-300">{toTnDate(endDateIso)}</span>
              </div>
            </div>
          </div>

          {/* MULTI-SURVEY BUILDER */}
          <div className="p-4 bg-gradient-to-br from-indigo-50/40 via-purple-50/20 to-blue-50/30 dark:from-gray-800/60 dark:to-gray-850 border border-indigo-100 dark:border-gray-700 rounded-xl space-y-3">
            <div className="flex items-center justify-between">
              <span className="text-xs font-bold text-indigo-900 dark:text-indigo-300 flex items-center gap-1.5">
                <Layers className="h-3.5 w-3.5 text-indigo-600" />
                Survey & Subdivision Numbers to Search
              </span>
              <span className="text-[11px] text-gray-500 font-medium">
                {surveyList.length} parcel(s) in query
              </span>
            </div>

            <div className="flex items-center space-x-2">
              <div className="flex-1">
                <input
                  type="text"
                  placeholder="Survey No (e.g. 217)"
                  value={curSurveyNo}
                  onChange={(e) => setCurSurveyNo(e.target.value)}
                  disabled={isScraping}
                  className="w-full px-3 py-2 text-xs rounded-lg border border-gray-200 dark:border-gray-700 bg-white dark:bg-gray-800 text-gray-800 dark:text-gray-200 focus:ring-2 focus:ring-indigo-500 outline-none"
                />
              </div>
              <div className="w-32">
                <input
                  type="text"
                  placeholder="Subdivision (e.g. 6)"
                  value={curSubdivision}
                  onChange={(e) => setCurSubdivision(e.target.value)}
                  disabled={isScraping}
                  className="w-full px-3 py-2 text-xs rounded-lg border border-gray-200 dark:border-gray-700 bg-white dark:bg-gray-800 text-gray-800 dark:text-gray-200 focus:ring-2 focus:ring-indigo-500 outline-none"
                />
              </div>
              <button
                type="button"
                onClick={handleAddSurvey}
                disabled={isScraping || !curSurveyNo.trim()}
                className="px-3.5 py-2 text-xs font-semibold text-white bg-indigo-600 hover:bg-indigo-700 disabled:opacity-40 rounded-lg transition-colors flex items-center space-x-1 shadow-sm shrink-0"
              >
                <Plus className="h-3.5 w-3.5" />
                <span>Add Survey</span>
              </button>
            </div>

            {/* Added Survey Chips */}
            {surveyList.length > 0 ? (
              <div className="flex flex-wrap gap-2 pt-1">
                {surveyList.map((item, idx) => (
                  <span
                    key={idx}
                    className="inline-flex items-center space-x-1.5 px-2.5 py-1 rounded-full text-xs font-semibold bg-white dark:bg-gray-800 border border-indigo-200 dark:border-indigo-800 text-indigo-800 dark:text-indigo-300 shadow-2xs"
                  >
                    <span>
                      Survey {item.survey_no}
                      {item.sub_division_no ? `/${item.sub_division_no}` : ''}
                    </span>
                    {!isScraping && (
                      <button
                        type="button"
                        onClick={() => handleRemoveSurvey(idx)}
                        className="text-gray-400 hover:text-rose-600 transition-colors"
                      >
                        <Trash2 className="h-3 w-3" />
                      </button>
                    )}
                  </span>
                ))}
              </div>
            ) : (
              <p className="text-[11px] text-gray-400 italic">
                No survey added yet. Enter survey number above and click &quot;Add Survey&quot; to include it in the EC query.
              </p>
            )}
          </div>
        </div>

        {/* MODAL FOOTER */}
        <div className="px-6 py-4 border-t border-gray-100 dark:border-gray-800 bg-gray-50/70 dark:bg-gray-850 flex items-center justify-between">
          <button
            type="button"
            onClick={onClose}
            className="px-4 py-2 text-xs font-semibold text-gray-600 dark:text-gray-300 hover:bg-gray-200/60 dark:hover:bg-gray-800 rounded-xl transition-colors"
          >
            {jobStatus?.status === 'completed' ? 'Close' : 'Cancel'}
          </button>

          <div className="flex items-center space-x-3">
            {jobStatus?.status === 'completed' ? (
              <button
                type="button"
                onClick={() => {
                  setJobStatus(null);
                  setActiveJobId(null);
                }}
                className="px-4 py-2 text-xs font-semibold text-blue-600 dark:text-blue-400 hover:bg-blue-50 dark:hover:bg-blue-900/30 rounded-xl transition-colors"
              >
                Search Another EC
              </button>
            ) : (
              <button
                type="button"
                onClick={handleStartScrape}
                disabled={isScraping}
                className="px-5 py-2.5 bg-gradient-to-r from-blue-600 via-indigo-600 to-purple-600 hover:from-blue-700 hover:to-purple-700 disabled:opacity-50 text-white rounded-xl text-xs font-bold shadow-md hover:shadow-lg transition-all flex items-center space-x-2"
              >
                {isScraping ? (
                  <>
                    <Loader2 className="h-4 w-4 animate-spin" />
                    <span>Extracting from TNREGINET...</span>
                  </>
                ) : (
                  <>
                    <Search className="h-4 w-4" />
                    <span>Fetch & Download EC</span>
                  </>
                )}
              </button>
            )}
          </div>
        </div>
      </div>
    </div>
  );
};
