/**
 * FmbGeneratorPanel
 *
 * Renders inside the existing FMB vault section on PropertyDetailPage.
 * Handles the full Generate → Preview → Download / Save-to-Vault lifecycle.
 *
 * Responsibilities:
 * - Survey / subdivision inputs
 * - Calling fmbApi.generate (backend → CollabLand, never direct)
 * - Inline PDF preview (base64 blob URL in an <iframe>)
 * - Download action (fmbApi.downloadBase64Pdf)
 * - Save-to-Vault action with duplicate handling
 *
 * Does NOT:
 * - Call CollabLand directly
 * - Expose GIS codes, government endpoints, or raw API errors
 */
import React, { useState, useEffect, useRef, useCallback } from 'react';
import {
  Map,
  FileText,
  Download,
  Save,
  Loader2,
  AlertCircle,
  CheckCircle2,
  RefreshCw,
  Eye,
  X,
} from 'lucide-react';
import { fmbApi, FmbGenerateResponse } from '../../api/fmb';

interface FmbGeneratorPanelProps {
  propertyId: string;
  initialSurveyNo?: string;
  initialSubdivision?: string;
  /** Called after a successful Save-to-Vault so parent can refresh the document list */
  onDocumentSaved?: () => void;
}

type PanelState =
  | 'idle'
  | 'generating'
  | 'generated'
  | 'saving'
  | 'saved'
  | 'error';

export const FmbGeneratorPanel: React.FC<FmbGeneratorPanelProps> = ({
  propertyId,
  initialSurveyNo = '',
  initialSubdivision = '',
  onDocumentSaved,
}) => {
  const [surveyNo, setSurveyNo] = useState(initialSurveyNo);
  const [subdivision, setSubdivision] = useState(initialSubdivision);
  const [state, setState] = useState<PanelState>('idle');
  const [errorMsg, setErrorMsg] = useState<string | null>(null);
  const [successMsg, setSuccessMsg] = useState<string | null>(null);
  const [generated, setGenerated] = useState<FmbGenerateResponse | null>(null);
  const [pdfObjectUrl, setPdfObjectUrl] = useState<string | null>(null);
  const [duplicateWarning, setDuplicateWarning] = useState(false);
  const [previewOpen, setPreviewOpen] = useState(false);
  const prevObjectUrl = useRef<string | null>(null);

  // Revoke old object URL on new generation to prevent memory leaks
  useEffect(() => {
    return () => {
      if (prevObjectUrl.current) {
        URL.revokeObjectURL(prevObjectUrl.current);
      }
    };
  }, []);

  const makePdfObjectUrl = useCallback((base64: string): string => {
    if (prevObjectUrl.current) URL.revokeObjectURL(prevObjectUrl.current);
    const byteChars = atob(base64);
    const byteArray = new Uint8Array(byteChars.length);
    for (let i = 0; i < byteChars.length; i++) {
      byteArray[i] = byteChars.charCodeAt(i);
    }
    const blob = new Blob([byteArray], { type: 'application/pdf' });
    const url = URL.createObjectURL(blob);
    prevObjectUrl.current = url;
    return url;
  }, []);

  const handleGenerate = async () => {
    const sNo = surveyNo.trim();
    if (!sNo) {
      setErrorMsg('Please enter a Survey Number to generate the FMB map.');
      return;
    }

    setState('generating');
    setErrorMsg(null);
    setSuccessMsg(null);
    setGenerated(null);
    setPdfObjectUrl(null);
    setDuplicateWarning(false);
    setPreviewOpen(false);

    try {
      const result = await fmbApi.generate(propertyId, {
        survey_number: sNo,
        subdivision_number: subdivision.trim() || undefined,
      });

      // result is already the inner data (apiClient unwraps the envelope)
      const data = (result as any)?.data ?? result;
      setGenerated(data);
      const objUrl = makePdfObjectUrl(data.pdf_base64);
      setPdfObjectUrl(objUrl);
      setState('generated');
    } catch (err: any) {
      const msg =
        err?.message ||
        err?.error?.message ||
        'FMB map could not be generated. Please verify the property\'s survey and location details.';
      setErrorMsg(msg);
      setState('error');
    }
  };

  const handleDownload = () => {
    if (!generated) return;
    fmbApi.downloadBase64Pdf(generated.pdf_base64, generated.filename);
  };

  const handleSave = async (force = false) => {
    if (!generated) return;

    setState('saving');
    setErrorMsg(null);
    setDuplicateWarning(false);

    try {
      await fmbApi.saveToVault(propertyId, {
        survey_number: generated.survey_number,
        subdivision_number: generated.subdivision_number ?? undefined,
        pdf_base64: generated.pdf_base64,
        filename: generated.filename,
        force_duplicate: force,
      });

      setState('saved');
      setSuccessMsg('FMB map saved to Document Vault successfully.');
      if (onDocumentSaved) onDocumentSaved();
    } catch (err: any) {
      // 409 → duplicate
      const errMsg: string = err?.message || err?.error?.message || '';
      if (errMsg.toLowerCase().includes('already exists') || err?.status === 409) {
        setState('generated'); // stay on generated state
        setDuplicateWarning(true);
        return;
      }
      setErrorMsg(
        errMsg || 'FMB map could not be saved. Please try again.'
      );
      setState('error');
    }
  };

  const handleReset = () => {
    setState('idle');
    setErrorMsg(null);
    setSuccessMsg(null);
    setGenerated(null);
    setDuplicateWarning(false);
    setPreviewOpen(false);
    if (prevObjectUrl.current) {
      URL.revokeObjectURL(prevObjectUrl.current);
      prevObjectUrl.current = null;
    }
    setPdfObjectUrl(null);
  };

  const isWorking = state === 'generating' || state === 'saving';

  return (
    <div className="mx-4 mb-4 mt-2 rounded-xl border border-amber-200 bg-gradient-to-r from-amber-50 to-yellow-50 dark:from-amber-950/30 dark:to-yellow-950/20 dark:border-amber-800/50 overflow-hidden">
      {/* Panel header */}
      <div className="flex items-center justify-between px-4 py-2.5 border-b border-amber-200/70 dark:border-amber-800/40">
        <div className="flex items-center gap-2">
          <div className="p-1.5 bg-amber-100 dark:bg-amber-900/50 rounded-lg">
            <Map className="h-3.5 w-3.5 text-amber-700 dark:text-amber-400" />
          </div>
          <div>
            <p className="text-xs font-bold text-amber-900 dark:text-amber-200">
              Generate FMB Map
            </p>
            <p className="text-[10px] text-amber-700/80 dark:text-amber-400/70">
              Official Field Measurement Book sketch via CollabLand (TN Govt.)
            </p>
          </div>
        </div>
        {(state === 'generated' || state === 'saved' || state === 'error') && (
          <button
            onClick={handleReset}
            className="text-amber-600 hover:text-amber-800 dark:text-amber-400 dark:hover:text-amber-200 transition-colors"
            title="Reset"
          >
            <RefreshCw className="h-3.5 w-3.5" />
          </button>
        )}
      </div>

      <div className="px-4 py-3 space-y-3">
        {/* Error message */}
        {errorMsg && (
          <div className="p-3 bg-rose-50 dark:bg-rose-950/40 border border-rose-200 dark:border-rose-800/60 rounded-lg flex items-start gap-2 text-[11px] text-rose-700 dark:text-rose-300">
            <AlertCircle className="h-3.5 w-3.5 shrink-0 mt-0.5" />
            <span>{errorMsg}</span>
          </div>
        )}

        {/* Success message */}
        {successMsg && (
          <div className="p-3 bg-emerald-50 dark:bg-emerald-950/40 border border-emerald-200 dark:border-emerald-800/60 rounded-lg flex items-start gap-2 text-[11px] text-emerald-700 dark:text-emerald-300">
            <CheckCircle2 className="h-3.5 w-3.5 shrink-0 mt-0.5" />
            <span>{successMsg}</span>
          </div>
        )}

        {/* Duplicate warning */}
        {duplicateWarning && (
          <div className="p-3 bg-amber-50 dark:bg-amber-950/40 border border-amber-300 dark:border-amber-700/60 rounded-lg text-[11px] text-amber-800 dark:text-amber-300 space-y-2">
            <div className="flex items-start gap-2">
              <AlertCircle className="h-3.5 w-3.5 shrink-0 mt-0.5 text-amber-600" />
              <span>
                An FMB map already exists in the vault for this survey number. Save a new copy?
              </span>
            </div>
            <div className="flex items-center gap-2">
              <button
                onClick={() => handleSave(true)}
                className="px-3 py-1.5 bg-amber-600 hover:bg-amber-700 text-white text-xs font-semibold rounded-lg transition-colors"
              >
                Save New Copy
              </button>
              <button
                onClick={() => setDuplicateWarning(false)}
                className="px-3 py-1.5 text-amber-700 dark:text-amber-300 text-xs font-semibold hover:underline"
              >
                Cancel
              </button>
            </div>
          </div>
        )}

        {/* Inputs (shown in idle/error states) */}
        {(state === 'idle' || state === 'error') && (
          <div className="flex flex-col sm:flex-row items-end gap-2">
            <div className="flex-1">
              <label className="block text-[10px] font-bold text-amber-800 dark:text-amber-300 mb-1 uppercase tracking-wider">
                Survey Number <span className="text-rose-500">*</span>
              </label>
              <input
                type="text"
                value={surveyNo}
                onChange={(e) => setSurveyNo(e.target.value)}
                placeholder="e.g. 123 or 123/2A"
                disabled={isWorking}
                className="w-full px-3 py-1.5 text-xs rounded-lg border border-amber-300 dark:border-amber-700 bg-white dark:bg-gray-800 text-gray-800 dark:text-gray-200 placeholder-gray-400 focus:outline-none focus:ring-2 focus:ring-amber-400 dark:focus:ring-amber-600"
              />
            </div>
            <div className="flex-1">
              <label className="block text-[10px] font-bold text-amber-800 dark:text-amber-300 mb-1 uppercase tracking-wider">
                Sub-Division / Plot No.{' '}
                <span className="text-[9px] font-normal text-amber-600">(optional)</span>
              </label>
              <input
                type="text"
                value={subdivision}
                onChange={(e) => setSubdivision(e.target.value)}
                placeholder="e.g. 1 or 2B"
                disabled={isWorking}
                className="w-full px-3 py-1.5 text-xs rounded-lg border border-amber-300 dark:border-amber-700 bg-white dark:bg-gray-800 text-gray-800 dark:text-gray-200 placeholder-gray-400 focus:outline-none focus:ring-2 focus:ring-amber-400 dark:focus:ring-amber-600"
              />
            </div>
            <button
              onClick={handleGenerate}
              disabled={isWorking}
              className="flex items-center gap-1.5 px-4 py-1.5 bg-amber-600 hover:bg-amber-700 disabled:opacity-50 text-white text-xs font-bold rounded-lg transition-colors shadow-sm whitespace-nowrap"
            >
              {state === 'generating' ? (
                <>
                  <Loader2 className="h-3.5 w-3.5 animate-spin" />
                  Generating...
                </>
              ) : (
                <>
                  <Map className="h-3.5 w-3.5" />
                  Generate FMB Map
                </>
              )}
            </button>
          </div>
        )}

        {/* Generated result */}
        {(state === 'generated' || state === 'saving' || state === 'saved') && generated && (
          <div className="space-y-3">
            {/* File info card */}
            <div className="flex items-center justify-between p-3 bg-white dark:bg-gray-800 rounded-lg border border-amber-200 dark:border-amber-800/50">
              <div className="flex items-center gap-2.5">
                <div className="p-2 bg-amber-100 dark:bg-amber-900/50 rounded-lg">
                  <FileText className="h-4 w-4 text-amber-700 dark:text-amber-400" />
                </div>
                <div>
                  <p className="text-xs font-bold text-gray-900 dark:text-gray-100">
                    {generated.filename}
                  </p>
                  <div className="flex flex-wrap items-center gap-2 text-[10px] text-gray-500 mt-0.5">
                    <span className="px-1.5 py-0.5 bg-amber-100 dark:bg-amber-900/50 text-amber-800 dark:text-amber-300 rounded font-mono font-bold">
                      FMB
                    </span>
                    <span>{(generated.file_size / 1024).toFixed(1)} KB</span>
                    {generated.district && <span>• {generated.district}</span>}
                    {generated.survey_number && (
                      <span>• Survey {generated.survey_number}</span>
                    )}
                    {generated.subdivision_number && (
                      <span>/ {generated.subdivision_number}</span>
                    )}
                    <span className="text-amber-600 dark:text-amber-400">• CollabLand</span>
                  </div>
                </div>
              </div>
              {state === 'saved' && (
                <CheckCircle2 className="h-4 w-4 text-emerald-500 shrink-0" />
              )}
            </div>

            {/* PDF inline preview */}
            {previewOpen && pdfObjectUrl && (
              <div className="relative rounded-lg overflow-hidden border border-amber-200 dark:border-amber-800/50 bg-gray-100 dark:bg-gray-900">
                <button
                  onClick={() => setPreviewOpen(false)}
                  className="absolute top-2 right-2 z-10 p-1 bg-white dark:bg-gray-800 rounded-full shadow text-gray-500 hover:text-gray-700 dark:hover:text-gray-300"
                >
                  <X className="h-3.5 w-3.5" />
                </button>
                <iframe
                  src={pdfObjectUrl}
                  title="FMB Map Preview"
                  className="w-full h-96 border-0"
                />
              </div>
            )}

            {/* Actions */}
            <div className="flex flex-wrap items-center gap-2">
              {!previewOpen && (
                <button
                  onClick={() => setPreviewOpen(true)}
                  className="flex items-center gap-1.5 px-3 py-1.5 text-xs font-semibold text-amber-800 dark:text-amber-300 bg-white dark:bg-gray-800 border border-amber-300 dark:border-amber-700 rounded-lg hover:bg-amber-50 dark:hover:bg-amber-900/30 transition-colors"
                >
                  <Eye className="h-3.5 w-3.5" />
                  View
                </button>
              )}

              <button
                onClick={handleDownload}
                className="flex items-center gap-1.5 px-3 py-1.5 text-xs font-semibold text-amber-800 dark:text-amber-300 bg-white dark:bg-gray-800 border border-amber-300 dark:border-amber-700 rounded-lg hover:bg-amber-50 dark:hover:bg-amber-900/30 transition-colors"
              >
                <Download className="h-3.5 w-3.5" />
                Download
              </button>

              {state !== 'saved' && !duplicateWarning && (
                <button
                  onClick={() => handleSave(false)}
                  disabled={state === 'saving'}
                  className="flex items-center gap-1.5 px-3 py-1.5 text-xs font-bold text-white bg-amber-700 hover:bg-amber-800 disabled:opacity-50 rounded-lg transition-colors shadow-sm"
                >
                  {state === 'saving' ? (
                    <>
                      <Loader2 className="h-3.5 w-3.5 animate-spin" />
                      Saving...
                    </>
                  ) : (
                    <>
                      <Save className="h-3.5 w-3.5" />
                      Save to Vault
                    </>
                  )}
                </button>
              )}

              {state === 'saved' && (
                <span className="flex items-center gap-1.5 px-3 py-1.5 text-xs font-semibold text-emerald-700 dark:text-emerald-400">
                  <CheckCircle2 className="h-3.5 w-3.5" />
                  Saved to Vault
                </span>
              )}

              <button
                onClick={handleReset}
                className="flex items-center gap-1.5 px-3 py-1.5 text-xs font-medium text-gray-500 dark:text-gray-400 hover:text-gray-700 dark:hover:text-gray-200 transition-colors"
              >
                <RefreshCw className="h-3 w-3" />
                New Search
              </button>
            </div>
          </div>
        )}

        {/* Generating spinner */}
        {state === 'generating' && (
          <div className="flex items-center gap-2 text-xs text-amber-700 dark:text-amber-400">
            <Loader2 className="h-4 w-4 animate-spin" />
            <span>
              Fetching official FMB map from CollabLand (Tamil Nadu GIS)...
            </span>
          </div>
        )}
      </div>
    </div>
  );
};

export default FmbGeneratorPanel;
