import { useState, useEffect, useRef } from 'react';
import {
  fetchJDs, fetchCVsForJD, fetchReportsForJD, fetchReportDetail, fetchJDDetail,
  reanalyse, renameJD, deleteJD, deleteCV, uploadCVsForJD, extractJD, extractJDFile,
  updateJDExtracted, fetchJDCVCount,
} from './api';
import type {
  JDSummary, CVForJD, ReportSummary, ReportDetail, JDDetail,
  JobDescription, AnalysisSection, TraceItem,
} from './api';
import { SkillRow } from './components/SkillRow';
import { AnalysisCard } from './components/AnalysisCard';
import { JDConfigurationView } from './JDConfigurationView';

// ─── Helpers ────────────────────────────────────────────────────────────────

function fmtDate(iso: string) {
  try {
    return new Date(iso).toLocaleString();
  } catch {
    return iso;
  }
}

function ScoreBadge({ score }: { score: number }) {
  const color =
    score >= 80 ? 'text-emerald-400 border-emerald-500/30 bg-emerald-500/10' :
    score >= 60 ? 'text-blue-400 border-blue-500/30 bg-blue-500/10' :
    score >= 40 ? 'text-amber-400 border-amber-500/30 bg-amber-500/10' :
                  'text-red-400 border-red-500/30 bg-red-500/10';
  return (
    <span className={`px-3 py-1 rounded-full text-sm font-bold border ${color}`}>
      {score.toFixed(0)}%
    </span>
  );
}

function BackButton({ onClick, label }: { onClick: () => void; label: string }) {
  return (
    <button
      onClick={onClick}
      className="text-sm text-slate-400 hover:text-white flex items-center gap-1 mb-4 transition-colors"
    >
      <span>←</span> {label}
    </button>
  );
}

// ─── Views ──────────────────────────────────────────────────────────────────

type View =
  | { kind: 'jd_list' }
  | { kind: 'jd_detail'; jdId: string }
  | { kind: 'report_detail'; reportId: string; jdId: string };

export function HistoryDashboard() {
  const [view, setView] = useState<View>({ kind: 'jd_list' });

  return (
    <div className="animate-fade-in">
      {view.kind === 'jd_list' && (
        <JDListView onSelectJD={(id) => setView({ kind: 'jd_detail', jdId: id })} />
      )}
      {view.kind === 'jd_detail' && (
        <JDDetailView
          jdId={view.jdId}
          onBack={() => setView({ kind: 'jd_list' })}
          onSelectReport={(reportId) => setView({ kind: 'report_detail', reportId, jdId: view.jdId })}
        />
      )}
      {view.kind === 'report_detail' && (
        <ReportDetailView
          reportId={view.reportId}
          onBack={() => setView({ kind: 'jd_detail', jdId: view.jdId })}
        />
      )}
    </div>
  );
}

// ─── JD List ────────────────────────────────────────────────────────────────

function JDListView({ onSelectJD }: { onSelectJD: (id: string) => void }) {
  const [jds, setJds] = useState<JDSummary[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [showAddJD, setShowAddJD] = useState(false);
  const [jdText, setJdText] = useState('');
  const [addingJD, setAddingJD] = useState(false);
  const [deletingId, setDeletingId] = useState<string | null>(null);
  const [confirmDelete, setConfirmDelete] = useState<{ jdId: string; cvCount: number; loading: boolean } | null>(null);
  const fileInputRef = useRef<HTMLInputElement>(null);

  const loadJDs = () => {
    setLoading(true);
    fetchJDs()
      .then((data) => { setJds(data.jds); setError(null); })
      .catch((e) => setError(e.message))
      .finally(() => setLoading(false));
  };

  useEffect(() => { loadJDs(); }, []);

  const handleAddJDText = async () => {
    if (!jdText.trim()) return;
    setAddingJD(true);
    setError(null);
    try {
      await extractJD(jdText, '');
      setJdText('');
      setShowAddJD(false);
      loadJDs();
    } catch (e: any) {
      setError(`Add JD failed: ${e.message}`);
    } finally {
      setAddingJD(false);
    }
  };

  const handleAddJDFile = async (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (!file) return;
    setAddingJD(true);
    setError(null);
    try {
      await extractJDFile(file);
      setShowAddJD(false);
      loadJDs();
    } catch (err: any) {
      setError(`Add JD failed: ${err.message}`);
    } finally {
      setAddingJD(false);
      if (fileInputRef.current) fileInputRef.current.value = '';
    }
  };

  const handleDeleteClick = async (jdId: string) => {
    setError(null);
    setConfirmDelete({ jdId, cvCount: 0, loading: true });
    try {
      const { cv_count } = await fetchJDCVCount(jdId);
      setConfirmDelete({ jdId, cvCount: cv_count, loading: false });
    } catch (e: any) {
      setError(`Failed to check CVs: ${e.message}`);
      setConfirmDelete(null);
    }
  };

  const handleDeleteConfirm = async () => {
    if (!confirmDelete) return;
    const { jdId } = confirmDelete;
    setDeletingId(jdId);
    setError(null);
    try {
      await deleteJD(jdId);
      setConfirmDelete(null);
      loadJDs();
    } catch (e: any) {
      setError(`Delete failed: ${e.message}`);
    } finally {
      setDeletingId(null);
    }
  };

  if (loading && jds.length === 0) return <LoadingSpinner label="Loading Job Descriptions..." />;

  return (
    <div>
      <div className="flex justify-between items-center mb-6">
        <h2 className="text-2xl font-bold text-white flex items-center gap-3">
          <span className="w-2 h-8 bg-emerald-500 rounded-full"></span>
          Uploaded Job Descriptions
        </h2>
        <button
          onClick={() => setShowAddJD(!showAddJD)}
          className={`text-sm px-4 py-2 rounded-lg font-bold transition-all border ${showAddJD ? 'bg-red-500/10 text-red-400 border-red-500/20 hover:bg-red-500/20' : 'bg-emerald-500/10 text-emerald-400 border-emerald-500/20 hover:bg-emerald-500/20'}`}
        >
          {showAddJD ? '✕ Cancel' : '+ Add JD'}
        </button>
      </div>

      {error && <div className="mb-4"><ErrorBanner message={error} /></div>}

      {/* Add JD Panel */}
      {showAddJD && (
        <div className="bg-slate-900/60 border border-emerald-500/20 rounded-xl p-6 mb-6 animate-fade-in">
          <h3 className="text-sm font-bold text-emerald-300 uppercase tracking-wider mb-4">Add New Job Description</h3>

          <div className="border-2 border-dashed border-slate-700 rounded-xl p-6 text-center hover:bg-slate-800/50 hover:border-emerald-500/50 transition-all cursor-pointer mb-4">
            <label className="cursor-pointer block w-full h-full">
              <div className="text-3xl mb-2">💼</div>
              <span className="text-sm text-emerald-300 font-bold block mb-1">Upload JD File (PDF/Text)</span>
              <span className="text-xs text-slate-500">Auto-extracts using Hybrid engine</span>
              <input ref={fileInputRef} type="file" className="hidden" accept=".pdf,.txt,.docx" onChange={handleAddJDFile} disabled={addingJD} />
            </label>
          </div>

          <div className="relative mb-4">
            <div className="absolute inset-0 flex items-center"><div className="w-full border-t border-slate-800"></div></div>
            <div className="relative flex justify-center text-xs text-slate-500 font-bold uppercase tracking-widest"><span className="bg-slate-900 px-2">OR PASTE TEXT</span></div>
          </div>

          <textarea
            className="w-full h-32 bg-slate-950/50 border border-slate-700/50 rounded-xl p-4 font-sans text-sm focus:ring-2 focus:ring-emerald-500/50 outline-none placeholder-slate-700 resize-none transition-all text-slate-200 mb-3"
            placeholder="Paste Job Description text here..."
            value={jdText}
            onChange={(e) => setJdText(e.target.value)}
          />
          <button
            onClick={handleAddJDText}
            disabled={addingJD || !jdText.trim()}
            className="w-full py-3 bg-gradient-to-r from-emerald-600 to-emerald-500 hover:from-emerald-500 hover:to-emerald-400 rounded-xl font-bold text-white shadow-lg shadow-emerald-900/20 transition-all transform active:scale-95 disabled:opacity-50 disabled:cursor-not-allowed"
          >
            {addingJD ? '⏳ Extracting...' : 'Extract & Add JD'}
          </button>
        </div>
      )}

      {jds.length === 0 && !showAddJD ? (
        <EmptyState message="No JDs uploaded yet. Click '+ Add JD' to get started." />
      ) : (
        <div className="space-y-3">
          {jds.map((jd) => (
            <div
              key={jd.id}
              className="bg-slate-900/60 border border-white/10 hover:border-emerald-500/30 rounded-xl p-5 transition-all group"
            >
              <div className="flex justify-between items-start">
                <button onClick={() => onSelectJD(jd.id)} className="flex-1 min-w-0 text-left">
                  <div className="flex items-center gap-3 mb-2">
                    <span className="text-lg font-bold text-white group-hover:text-emerald-300 transition-colors truncate">
                      {jd.job_title || jd.filename || 'Untitled JD'}
                    </span>
                    {jd.is_valid && (
                      <span className="text-[10px] px-2 py-0.5 bg-emerald-500/10 text-emerald-400 border border-emerald-500/20 rounded-full font-bold uppercase">Valid</span>
                    )}
                  </div>
                  <div className="flex flex-wrap gap-3 text-xs text-slate-400">
                    {jd.job_location && <span>📍 {jd.job_location}</span>}
                    {jd.uploaded_by_name && <span>👤 {jd.uploaded_by_name}</span>}
                    <span>🕐 {fmtDate(jd.created_at)}</span>
                    {jd.model_used && <span className="text-slate-500">via {jd.model_used}</span>}
                  </div>
                </button>
                <div className="flex items-center gap-3 ml-4 shrink-0">
                  <div className="text-right mr-2">
                    <div className="text-2xl font-black text-white">{jd.report_count}</div>
                    <div className="text-[10px] text-slate-500 uppercase font-bold">Reports</div>
                  </div>
                  <button
                    onClick={(e) => { e.stopPropagation(); handleDeleteClick(jd.id); }}
                    className="text-xs px-2 py-1.5 rounded-lg text-slate-600 hover:text-red-400 hover:bg-red-500/10 transition-all border border-transparent hover:border-red-500/20"
                    title="Delete JD"
                  >
                    🗑️
                  </button>
                  <button onClick={() => onSelectJD(jd.id)} className="text-slate-600 group-hover:text-emerald-400 transition-colors text-xl">→</button>
                </div>
              </div>
            </div>
          ))}
        </div>
      )}

      {/* Delete Confirmation Modal */}
      {confirmDelete && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/60 backdrop-blur-sm animate-fade-in">
          <div className="bg-slate-900 border border-red-500/30 rounded-2xl p-6 max-w-md w-full mx-4 shadow-2xl shadow-red-900/20">
            {confirmDelete.loading ? (
              <div className="text-center py-4">
                <div className="text-2xl mb-2 animate-spin inline-block">⏳</div>
                <p className="text-slate-400 text-sm">Checking associated CVs...</p>
              </div>
            ) : (
              <>
                <div className="flex items-center gap-3 mb-4">
                  <span className="text-3xl">⚠️</span>
                  <h3 className="text-lg font-bold text-white">Delete Job Description?</h3>
                </div>
                {confirmDelete.cvCount > 0 ? (
                  <p className="text-slate-300 text-sm mb-5 leading-relaxed">
                    This JD has <span className="font-bold text-red-400">{confirmDelete.cvCount} CV{confirmDelete.cvCount > 1 ? 's' : ''}</span> uploaded against it.
                    Deleting this JD will also <span className="font-bold text-red-400">permanently remove</span> all associated CVs and their analysis reports.
                  </p>
                ) : (
                  <p className="text-slate-300 text-sm mb-5 leading-relaxed">
                    This JD has no CVs uploaded against it. Are you sure you want to delete it?
                  </p>
                )}
                <div className="flex gap-3 justify-end">
                  <button
                    onClick={() => setConfirmDelete(null)}
                    disabled={deletingId !== null}
                    className="px-4 py-2 rounded-lg text-sm font-bold text-slate-400 hover:text-white border border-slate-700 hover:border-slate-500 transition-all"
                  >
                    Cancel
                  </button>
                  <button
                    onClick={handleDeleteConfirm}
                    disabled={deletingId !== null}
                    className="px-4 py-2 rounded-lg text-sm font-bold bg-red-600/20 text-red-400 border border-red-500/30 hover:bg-red-600/40 transition-all disabled:opacity-50"
                  >
                    {deletingId ? '⏳ Deleting...' : confirmDelete.cvCount > 0 ? `Yes, Delete JD & ${confirmDelete.cvCount} CV${confirmDelete.cvCount > 1 ? 's' : ''}` : 'Yes, Delete'}
                  </button>
                </div>
              </>
            )}
          </div>
        </div>
      )}
    </div>
  );
}

// ─── JD Detail (CVs + Reports) ─────────────────────────────────────────────

function JDDetailView({
  jdId,
  onBack,
  onSelectReport,
}: {
  jdId: string;
  onBack: () => void;
  onSelectReport: (reportId: string) => void;
}) {
  const [jdDetail, setJdDetail] = useState<JDDetail | null>(null);
  const [cvs, setCvs] = useState<CVForJD[]>([]);
  const [reports, setReports] = useState<ReportSummary[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [reanalysingCvId, setReanalysingCvId] = useState<string | null>(null);
  const [tab, setTab] = useState<'cvs' | 'reports'>('cvs');

  // Rename state
  const [isRenaming, setIsRenaming] = useState(false);
  const [renameValue, setRenameValue] = useState('');
  const [renameSaving, setRenameSaving] = useState(false);

  // Upload CVs state
  const [showUploadCVs, setShowUploadCVs] = useState(false);
  const [uploadingCVs, setUploadingCVs] = useState(false);
  const [uploadResults, setUploadResults] = useState<any[] | null>(null);
  const cvFileInputRef = useRef<HTMLInputElement>(null);

  // Delete CV state
  const [confirmDeleteCvId, setConfirmDeleteCvId] = useState<string | null>(null);
  const [deletingCvId, setDeletingCvId] = useState<string | null>(null);

  // Edit JD state
  const [isEditingJD, setIsEditingJD] = useState(false);
  const [editSaving, setEditSaving] = useState(false);

  const loadData = () => {
    setLoading(true);
    Promise.all([
      fetchJDDetail(jdId),
      fetchCVsForJD(jdId),
      fetchReportsForJD(jdId),
    ])
      .then(([jd, cvData, repData]) => {
        setJdDetail(jd);
        setCvs(cvData.cvs);
        setReports(repData.reports);
        setError(null);
      })
      .catch((e) => setError(e.message))
      .finally(() => setLoading(false));
  };

  useEffect(() => { loadData(); }, [jdId]);

  const handleReanalyse = async (cv: CVForJD) => {
    if (!jdDetail) return;
    setReanalysingCvId(cv.cv_id);
    try {
      await reanalyse(jdId, cv.cv_id);
      loadData();
    } catch (e: any) {
      setError(`Re-analysis failed: ${e.message}`);
    } finally {
      setReanalysingCvId(null);
    }
  };

  const handleRename = async () => {
    if (!renameValue.trim()) return;
    setRenameSaving(true);
    try {
      await renameJD(jdId, renameValue.trim());
      setIsRenaming(false);
      loadData();
    } catch (e: any) {
      setError(`Rename failed: ${e.message}`);
    } finally {
      setRenameSaving(false);
    }
  };

  const handleUploadCVs = async (e: React.ChangeEvent<HTMLInputElement>) => {
    const fileList = e.target.files;
    if (!fileList || fileList.length === 0) return;
    setUploadingCVs(true);
    setUploadResults(null);
    setError(null);
    try {
      const files = Array.from(fileList);
      const result = await uploadCVsForJD(jdId, files);
      setUploadResults(result.results);
      loadData();
    } catch (err: any) {
      setError(`Upload failed: ${err.message}`);
    } finally {
      setUploadingCVs(false);
      if (cvFileInputRef.current) cvFileInputRef.current.value = '';
    }
  };

  const handleDeleteCV = async (cvId: string) => {
    setDeletingCvId(cvId);
    try {
      await deleteCV(cvId);
      setConfirmDeleteCvId(null);
      loadData();
    } catch (e: any) {
      setError(`Delete CV failed: ${e.message}`);
    } finally {
      setDeletingCvId(null);
    }
  };

  const handleEditJDSave = async (updatedJD: JobDescription) => {
    setEditSaving(true);
    setError(null);
    try {
      await updateJDExtracted(jdId, updatedJD);
      setIsEditingJD(false);
      loadData();
    } catch (e: any) {
      setError(`Save JD failed: ${e.message}`);
    } finally {
      setEditSaving(false);
    }
  };

  if (loading && !jdDetail) return <><BackButton onClick={onBack} label="All JDs" /><LoadingSpinner label="Loading JD details..." /></>;
  if (error && !jdDetail) return <><BackButton onClick={onBack} label="All JDs" /><ErrorBanner message={error} /></>;
  if (!jdDetail) return <><BackButton onClick={onBack} label="All JDs" /><ErrorBanner message="JD not found" /></>;

  const jdMeta = jdDetail.extracted_json?.job_metadata;
  const displayTitle = jdMeta?.title || jdDetail.filename || 'Untitled JD';

  return (
    <div>
      <BackButton onClick={onBack} label="All JDs" />

      {error && <div className="mb-4"><ErrorBanner message={error} /></div>}

      {/* JD Header */}
      <div className="bg-slate-900/60 border border-white/10 rounded-xl p-6 mb-6">
        <div className="flex justify-between items-start">
          <div className="flex-1 min-w-0">
            {isRenaming ? (
              <div className="flex items-center gap-2 mb-2">
                <input
                  type="text"
                  value={renameValue}
                  onChange={(e) => setRenameValue(e.target.value)}
                  onKeyDown={(e) => { if (e.key === 'Enter') handleRename(); if (e.key === 'Escape') setIsRenaming(false); }}
                  className="bg-slate-800 border border-emerald-500/30 rounded-lg px-3 py-1.5 text-white text-lg font-bold outline-none focus:ring-2 focus:ring-emerald-500/50 flex-1"
                  autoFocus
                />
                <button onClick={handleRename} disabled={renameSaving} className="text-xs px-3 py-1.5 rounded-lg font-bold bg-emerald-600/20 text-emerald-400 border border-emerald-500/30 hover:bg-emerald-600/40 transition-all disabled:opacity-50">
                  {renameSaving ? '...' : 'Save'}
                </button>
                <button onClick={() => setIsRenaming(false)} className="text-xs px-2 py-1.5 text-slate-400 hover:text-white">✕</button>
              </div>
            ) : (
              <div className="flex items-center gap-3 mb-2">
                <h2 className="text-2xl font-bold text-white truncate">{displayTitle}</h2>
                <button
                  onClick={() => { setRenameValue(displayTitle); setIsRenaming(true); }}
                  className="text-xs px-2 py-1 rounded text-slate-500 hover:text-emerald-400 hover:bg-emerald-500/10 transition-all"
                  title="Rename JD"
                >
                  ✏️
                </button>
              </div>
            )}
            <div className="flex flex-wrap gap-3 text-sm text-slate-400">
              {jdMeta?.location && <span className="bg-slate-800 px-2 py-1 rounded text-xs">📍 {jdMeta.location}</span>}
              {jdDetail.uploaded_by_name && <span className="bg-slate-800 px-2 py-1 rounded text-xs">👤 {jdDetail.uploaded_by_name}</span>}
              <span className="bg-slate-800 px-2 py-1 rounded text-xs">🕐 {fmtDate(jdDetail.created_at)}</span>
            </div>
          </div>
          <div className="text-right">
            <div className="text-3xl font-black text-emerald-400">{reports.length}</div>
            <div className="text-[10px] text-slate-500 uppercase font-bold">Analysis Reports</div>
          </div>
        </div>
      </div>

      {/* Action Buttons */}
      <div className="mb-6">
        <div className="flex items-center gap-3 mb-3">
          <button
            onClick={() => { setShowUploadCVs(!showUploadCVs); setUploadResults(null); setIsEditingJD(false); }}
            className={`text-sm px-4 py-2 rounded-lg font-bold transition-all border ${showUploadCVs ? 'bg-red-500/10 text-red-400 border-red-500/20 hover:bg-red-500/20' : 'bg-blue-500/10 text-blue-400 border-blue-500/20 hover:bg-blue-500/20'}`}
          >
            {showUploadCVs ? '✕ Cancel' : '📄 Upload CVs'}
          </button>
          <button
            onClick={() => { setIsEditingJD(!isEditingJD); setShowUploadCVs(false); }}
            className={`text-sm px-4 py-2 rounded-lg font-bold transition-all border ${isEditingJD ? 'bg-red-500/10 text-red-400 border-red-500/20 hover:bg-red-500/20' : 'bg-purple-500/10 text-purple-400 border-purple-500/20 hover:bg-purple-500/20'}`}
          >
            {isEditingJD ? '✕ Cancel Edit' : '⚙️ Edit JD'}
          </button>
        </div>

        {showUploadCVs && (
          <div className="bg-slate-900/60 border border-blue-500/20 rounded-xl p-6 animate-fade-in">
            <h3 className="text-sm font-bold text-blue-300 uppercase tracking-wider mb-4">Upload Resumes Against This JD</h3>
            <p className="text-xs text-slate-400 mb-4">Each CV will be extracted, matched against the JD, and a report will be generated automatically.</p>

            <div className="border-2 border-dashed border-slate-700 rounded-xl p-6 text-center hover:bg-slate-800/50 hover:border-blue-500/50 transition-all cursor-pointer mb-4">
              <label className="cursor-pointer block w-full h-full">
                <div className="text-3xl mb-2">📄</div>
                <span className="text-sm text-blue-300 font-bold block mb-1">Select CV Files (PDF/Text)</span>
                <span className="text-xs text-slate-500">You can select multiple files at once</span>
                <input
                  ref={cvFileInputRef}
                  type="file"
                  className="hidden"
                  accept=".pdf,.txt,.docx"
                  multiple
                  onChange={handleUploadCVs}
                  disabled={uploadingCVs}
                />
              </label>
            </div>

            {uploadingCVs && <LoadingSpinner label="Extracting and analysing CVs... This may take a moment." />}

            {uploadResults && (
              <div className="space-y-2 mt-4">
                <h4 className="text-xs font-bold text-slate-400 uppercase tracking-wider">Upload Results</h4>
                {uploadResults.map((r, i) => (
                  <div key={i} className={`flex items-center justify-between p-3 rounded-lg border text-sm ${r.status === 'success' ? 'bg-emerald-500/5 border-emerald-500/20' : 'bg-red-500/5 border-red-500/20'}`}>
                    <div className="flex items-center gap-3">
                      <span className={r.status === 'success' ? 'text-emerald-400' : 'text-red-400'}>{r.status === 'success' ? '✅' : '❌'}</span>
                      <span className="text-white font-medium">{r.candidate_name || r.filename}</span>
                    </div>
                    {r.score != null ? <ScoreBadge score={r.score} /> : <span className="text-xs text-red-400">{r.error}</span>}
                  </div>
                ))}
              </div>
            )}
          </div>
        )}

        {isEditingJD && jdDetail.extracted_json && (
          <div className="animate-fade-in">
            {editSaving && <LoadingSpinner label="Saving JD changes..." />}
            <JDConfigurationView
              jd={jdDetail.extracted_json}
              onConfirm={handleEditJDSave}
              onCancel={() => setIsEditingJD(false)}
            />
          </div>
        )}
      </div>

      {/* Tab Switcher */}
      <div className="bg-slate-900 p-1 rounded-lg border border-white/10 flex mb-6 w-fit">
        <button
          onClick={() => setTab('cvs')}
          className={`px-4 py-2 rounded-md text-sm font-bold transition-all ${tab === 'cvs' ? 'bg-slate-700 text-white shadow' : 'text-slate-500 hover:text-slate-300'}`}
        >
          CVs ({cvs.length})
        </button>
        <button
          onClick={() => setTab('reports')}
          className={`px-4 py-2 rounded-md text-sm font-bold transition-all ${tab === 'reports' ? 'bg-blue-600 text-white shadow' : 'text-slate-500 hover:text-slate-300'}`}
        >
          Reports ({reports.length})
        </button>
      </div>

      {/* CVs Tab */}
      {tab === 'cvs' && (
        <div>
          {cvs.length === 0 ? (
            <EmptyState message="No CVs have been analysed against this JD yet. Click 'Upload CVs' above to get started." />
          ) : (
            <div className="space-y-3">
              {cvs.map((cv) => (
                <div
                  key={cv.cv_id}
                  className="bg-slate-900/60 border border-white/10 rounded-xl p-5 flex justify-between items-center hover:border-blue-500/30 transition-all"
                >
                  <div className="flex-1 min-w-0">
                    <div className="flex items-center gap-3 mb-1">
                      <span className="text-base font-bold text-white truncate">
                        {cv.candidate_name || cv.filename || 'Unknown Candidate'}
                      </span>
                      <ScoreBadge score={cv.score} />
                    </div>
                    <div className="flex flex-wrap gap-3 text-xs text-slate-400">
                      {cv.candidate_location && <span>📍 {cv.candidate_location}</span>}
                      {cv.uploaded_by_name && <span>👤 {cv.uploaded_by_name}</span>}
                      <span>🕐 {fmtDate(cv.analysis_date)}</span>
                    </div>
                  </div>
                  <div className="flex items-center gap-2 ml-4 shrink-0">
                    <button
                      onClick={() => onSelectReport(cv.report_id)}
                      className="text-xs px-3 py-2 rounded-lg font-bold bg-slate-800 text-slate-300 hover:bg-slate-700 hover:text-white transition-all border border-white/10"
                    >
                      View Report
                    </button>
                    <button
                      onClick={() => handleReanalyse(cv)}
                      disabled={reanalysingCvId === cv.cv_id}
                      className="text-xs px-3 py-2 rounded-lg font-bold bg-blue-600/20 text-blue-300 hover:bg-blue-600/40 transition-all border border-blue-500/30 disabled:opacity-50"
                    >
                      {reanalysingCvId === cv.cv_id ? '⏳ Running...' : '🔄 Re-Analyse'}
                    </button>
                    {confirmDeleteCvId === cv.cv_id ? (
                      <div className="flex items-center gap-1">
                        <button
                          onClick={() => handleDeleteCV(cv.cv_id)}
                          disabled={deletingCvId === cv.cv_id}
                          className="text-xs px-3 py-1.5 rounded-lg font-bold bg-red-600/20 text-red-400 border border-red-500/30 hover:bg-red-600/40 transition-all disabled:opacity-50"
                        >
                          {deletingCvId === cv.cv_id ? '...' : 'Confirm'}
                        </button>
                        <button onClick={() => setConfirmDeleteCvId(null)} className="text-xs px-2 py-1.5 text-slate-400 hover:text-white">✕</button>
                      </div>
                    ) : (
                      <button
                        onClick={() => setConfirmDeleteCvId(cv.cv_id)}
                        className="text-xs px-2 py-1.5 rounded-lg text-slate-600 hover:text-red-400 hover:bg-red-500/10 transition-all border border-transparent hover:border-red-500/20"
                        title="Delete CV"
                      >
                        🗑️
                      </button>
                    )}
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>
      )}

      {/* Reports Tab */}
      {tab === 'reports' && (
        <div>
          {reports.length === 0 ? (
            <EmptyState message="No analysis reports yet." />
          ) : (
            <div className="space-y-3">
              {reports.map((r) => (
                <button
                  key={r.report_id}
                  onClick={() => onSelectReport(r.report_id)}
                  className="w-full text-left bg-slate-900/60 hover:bg-slate-800/80 border border-white/10 hover:border-purple-500/30 rounded-xl p-5 transition-all group"
                >
                  <div className="flex justify-between items-center">
                    <div className="flex items-center gap-4">
                      <ScoreBadge score={r.score} />
                      <div>
                        <span className="text-base font-bold text-white group-hover:text-purple-300 transition-colors">
                          {r.candidate_name || r.cv_filename || 'Unknown Candidate'}
                        </span>
                        <div className="flex gap-3 text-xs text-slate-400 mt-1">
                          {r.run_by_name && <span>👤 {r.run_by_name}</span>}
                          <span>🕐 {fmtDate(r.analysis_date)}</span>
                        </div>
                      </div>
                    </div>
                    <span className="text-slate-600 group-hover:text-purple-400 transition-colors text-xl">→</span>
                  </div>
                </button>
              ))}
            </div>
          )}
        </div>
      )}
    </div>
  );
}

// ─── Report Detail ──────────────────────────────────────────────────────────

function ReportDetailView({ reportId, onBack }: { reportId: string; onBack: () => void }) {
  const [report, setReport] = useState<ReportDetail | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    setLoading(true);
    fetchReportDetail(reportId)
      .then((data) => { setReport(data); setError(null); })
      .catch((e) => setError(e.message))
      .finally(() => setLoading(false));
  }, [reportId]);

  if (loading) return <><BackButton onClick={onBack} label="Back" /><LoadingSpinner label="Loading report..." /></>;
  if (error) return <><BackButton onClick={onBack} label="Back" /><ErrorBanner message={error} /></>;
  if (!report) return <><BackButton onClick={onBack} label="Back" /><ErrorBanner message="Report not found" /></>;

  const matchResult = report.analysis_json;

  return (
    <div>
      <BackButton onClick={onBack} label="Back to JD" />

      {/* Report Header */}
      <div className="bg-slate-900/60 border border-white/10 rounded-xl p-6 mb-6">
        <div className="flex justify-between items-start">
          <div>
            <h2 className="text-xl font-bold text-white mb-1">
              {report.candidate_name || report.cv_filename || 'Unknown Candidate'}
            </h2>
            <p className="text-sm text-slate-400 mb-2">
              vs <span className="text-emerald-400 font-medium">{report.job_title || report.jd_filename || 'Untitled JD'}</span>
            </p>
            <div className="flex flex-wrap gap-3 text-xs text-slate-500">
              {report.run_by_name && <span>👤 Analysed by {report.run_by_name}</span>}
              <span>🕐 {fmtDate(report.created_at)}</span>
            </div>
          </div>
          <div className="text-right">
            <div className={`text-5xl font-black ${matchResult.score >= 80 ? 'text-emerald-400' : matchResult.score >= 60 ? 'text-blue-400' : 'text-amber-400'}`}>
              {matchResult.score.toFixed(0)}
            </div>
            <div className="text-[10px] text-slate-500 uppercase font-bold">Match Score</div>
          </div>
        </div>
      </div>

      {/* Tribunal Verdict */}
      {matchResult.tribunal_verdict && (
        <div className="mb-6 bg-slate-900/60 border border-indigo-500/20 rounded-xl p-5">
          <div className="flex items-center gap-2 mb-4">
            <span className="text-sm font-bold text-indigo-300">⚖️ Tribunal Verdict:</span>
            <span className={`px-3 py-1 rounded-full text-xs font-bold uppercase border ${
              matchResult.tribunal_verdict.narrative_tag.includes('risk') || matchResult.tribunal_verdict.narrative_tag.includes('mismatch')
                ? 'bg-red-500/10 border-red-500/30 text-red-300'
                : matchResult.tribunal_verdict.narrative_tag.includes('top')
                ? 'bg-emerald-500/10 border-emerald-500/30 text-emerald-300'
                : 'bg-blue-500/10 border-blue-500/30 text-blue-300'
            }`}>
              {matchResult.tribunal_verdict.narrative_tag.replace(/_/g, ' ')}
            </span>
          </div>
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4 mb-3">
            <div className="bg-black/20 p-3 rounded-lg border border-white/5">
              <div className="text-[10px] text-red-400 font-bold uppercase mb-1">The Skeptic</div>
              <p className="text-sm italic opacity-80">"{matchResult.tribunal_verdict.skeptic_summary}"</p>
            </div>
            <div className="bg-black/20 p-3 rounded-lg border border-white/5">
              <div className="text-[10px] text-emerald-400 font-bold uppercase mb-1">The Advocate</div>
              <p className="text-sm italic opacity-80">"{matchResult.tribunal_verdict.advocate_summary}"</p>
            </div>
          </div>
          <div className="flex items-center justify-between text-xs opacity-70 border-t border-white/5 pt-2">
            <span>Trajectory: <span className="font-bold text-white uppercase">{matchResult.tribunal_verdict.trajectory_analysis.direction}</span></span>
            <span className="italic opacity-80">{matchResult.tribunal_verdict.trajectory_analysis.reasoning}</span>
          </div>
        </div>
      )}

      {/* Deep Analysis */}
      {matchResult.analysis && matchResult.analysis.length > 0 && (
        <div className="mb-6">
          <h3 className="text-xs font-bold uppercase tracking-widest text-slate-500 mb-3">Deep Analysis</h3>
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            {matchResult.analysis.map((section: AnalysisSection, i: number) => (
              <AnalysisCard key={i} section={section} />
            ))}
          </div>
        </div>
      )}

      {/* Technical Trace */}
      {matchResult.technical_trace && matchResult.technical_trace.length > 0 && (
        <div className="bg-slate-900/60 border border-white/10 rounded-xl p-5">
          <div className="mb-4">
            <h3 className="text-xs font-bold uppercase tracking-widest text-emerald-500 mb-3 flex items-center gap-2">
              <span className="w-2 h-2 rounded-full bg-emerald-500"></span>
              Required Skills
            </h3>
            <div className="space-y-2 font-mono text-sm">
              {matchResult.technical_trace
                .filter((i: TraceItem) => i.priority === 'required' || !i.priority)
                .map((item: TraceItem) => (
                  <SkillRow key={item.skill_slug} item={item} />
                ))}
            </div>
          </div>

          {matchResult.technical_trace.filter((i: TraceItem) => i.priority === 'preferred').length > 0 && (
            <div className="mt-4 pt-4 border-t border-white/5">
              <h3 className="text-xs font-bold uppercase tracking-widest text-blue-500 mb-3 flex items-center gap-2">
                <span className="w-2 h-2 rounded-full bg-blue-500"></span>
                Preferred Skills
              </h3>
              <div className="space-y-2 font-mono text-sm">
                {matchResult.technical_trace
                  .filter((i: TraceItem) => i.priority === 'preferred')
                  .map((item: TraceItem) => (
                    <SkillRow key={item.skill_slug} item={item} />
                  ))}
              </div>
            </div>
          )}
        </div>
      )}
    </div>
  );
}

// ─── Shared UI Atoms ────────────────────────────────────────────────────────

function LoadingSpinner({ label }: { label: string }) {
  return (
    <div className="flex flex-col items-center justify-center py-20 text-slate-500">
      <svg className="animate-spin h-8 w-8 mb-3" xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24">
        <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4"></circle>
        <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path>
      </svg>
      <span className="text-sm font-medium">{label}</span>
    </div>
  );
}

function ErrorBanner({ message }: { message: string }) {
  return (
    <div className="p-4 bg-red-950/50 border border-red-500/50 rounded-lg text-red-200 text-sm font-mono">
      ⚠️ {message}
    </div>
  );
}

function EmptyState({ message }: { message: string }) {
  return (
    <div className="flex flex-col items-center justify-center py-16 text-slate-600 border-2 border-dashed border-slate-800 rounded-2xl">
      <div className="text-5xl mb-3 opacity-50">📋</div>
      <p className="text-sm font-medium">{message}</p>
    </div>
  );
}
