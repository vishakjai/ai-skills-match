import React, { useState } from 'react';
import { calculateMatch, extractResume, extractJD, extractResumeFile, extractJDFile } from './api';
import type { CandidateProfile, JobDescription, MatchResult } from './api';
import { SkillRow } from './components/SkillRow';
import { AnalysisCard } from './components/AnalysisCard';
import { BatchDashboard } from './BatchDashboard';
import { JDConfigurationView } from './JDConfigurationView';
import { HistoryDashboard } from './HistoryDashboard';

// Default Data for easy testing
const DEFAULT_CANDIDATE_JSON = `{"id":"jane-doe","candidate_metadata":{"name":"Jane Doe","location":"Remote","links":["github.com/jane"]},"computed_stats":{"total_yoe":6.0,"avg_tenure_months":24,"management_experience_years":1},"timeline":[{"company":"TechCorp","title_raw":"Senior Engineer","start_date":"2021-01","end_date":"Present","extracted_skills":[{"skill_id":"java","context":"Backend API"},{"skill_id":"html5","context":"Frontend"},{"skill_id":"javascript","context":"Frontend"},{"skill_id":"git","context":"Version Control"}]}],"skills":[],"competencies":["Problem Solving","Communication"]}`;

const DEFAULT_JD_JSON = `{"id":"senior-engineer-real","job_metadata":{"title":"Senior Java Engineer","location":"New York (Hybrid)","clearance":"None"},"gating_rules":{"visa_sponsorship":true,"education_min":"Bachelors"},"requirements":[{"req_id":"r1","skill_id":"java","priority":"must_have","min_years":4},{"req_id":"r2","skill_id":"sql_server","priority":"must_have","min_years":3},{"req_id":"r3","skill_id":"database_design","priority":"must_have","min_years":3},{"req_id":"r4","skill_id":"html5","priority":"must_have","min_years":2},{"req_id":"r5","skill_id":"css3","priority":"must_have","min_years":2},{"req_id":"r6","skill_id":"javascript","priority":"must_have","min_years":2},{"req_id":"r7","skill_id":"git","priority":"must_have","min_years":3},{"req_id":"r8","skill_id":"rest_api","priority":"must_have","min_years":3},{"req_id":"r9","skill_id":"http","priority":"must_have","min_years":2}],"seniority_signals":{"target_level":"Senior","keywords_found":["Lead","Mentor"]},"competencies":[{"name":"Problem Solving","priority":"must_have"},{"name":"Code Quality","priority":"must_have"},{"name":"Communication","priority":"must_have"}]}`;

function App() {
  const [viewMode, setViewMode] = useState<'single' | 'batch' | 'history'>('single');
  const [candidateStr, setCandidateStr] = useState(DEFAULT_CANDIDATE_JSON);
  const [jdStr, setJdStr] = useState(DEFAULT_JD_JSON);

  // Magic Extract State
  const [showExtractResume, setShowExtractResume] = useState(false);
  const [resumeText, setResumeText] = useState("");
  const [showExtractJD, setShowExtractJD] = useState(false);
  const [jdText, setJdText] = useState("");
  const [isConfiguring, setIsConfiguring] = useState(false);

  console.log("🚀 App Component Rendering...");

  const [matchResult, setMatchResult] = useState<MatchResult | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const handleMatch = async () => {
    setLoading(true);
    setError(null);
    setMatchResult(null);

    try {
      const candidate: CandidateProfile = JSON.parse(candidateStr);
      const jd: JobDescription = JSON.parse(jdStr);
      const result = await calculateMatch(candidate, jd);
      console.log("🔥 MATCH RESULT RECEIVED:", result);
      console.log("🔥 TECHNICAL TRACE:", result.technical_trace);
      console.log("🔥 TRIBUNAL VERDICT:", result.tribunal_verdict);
      setMatchResult(result);
    } catch (e: any) {
      setError(e.message || "Invalid JSON or API Error");
    } finally {
      setLoading(false);
    }
  };

  const handleExtractResume = async () => {
    setLoading(true);
    setError(null);
    try {
      const result = await extractResume(resumeText, "");
      setCandidateStr(JSON.stringify(result, null, 2));
      setShowExtractResume(false);
    } catch (e: any) {
      setError(e.message);
    } finally {
      setLoading(false);
    }
  }

  const handleExtractJD = async () => {
    setLoading(true);
    setError(null);
    try {
      const result = await extractJD(jdText, "");
      setJdStr(JSON.stringify(result, null, 2));
      setShowExtractJD(false);
      setIsConfiguring(true); // Open config immediately
    } catch (e: any) {
      setError(e.message);
    } finally {
      setLoading(false);
    }
  }

  const handleFileUpload = async (e: React.ChangeEvent<HTMLInputElement>, type: 'resume' | 'jd') => {
    const file = e.target.files?.[0];
    if (!file) return;

    setLoading(true);
    setError(null);
    try {
      let result;
      if (type === 'resume') {
        result = await extractResumeFile(file);
        setCandidateStr(JSON.stringify(result, null, 2));
        setShowExtractResume(false);
      } else {
        console.log("📂 Uploading JD File...");
        result = await extractJDFile(file);
        console.log("✅ JD Extracted Result:", result);
        setJdStr(JSON.stringify(result, null, 2));
        setShowExtractJD(false);
      }
    } catch (err: any) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  };



  return (
    <div className="min-h-screen bg-slate-950 text-slate-100 p-6 md:p-12 font-sans selection:bg-purple-500/30">
      <header className="mb-12 flex flex-col md:flex-row justify-between items-end gap-6 border-b border-white/10 pb-6">
        <div>
          <h1 className="text-4xl md:text-5xl font-black bg-clip-text text-transparent bg-gradient-to-r from-emerald-400 via-cyan-400 to-blue-500 tracking-tighter">
            Talience Core
          </h1>
          <p className="text-slate-400 mt-2 text-lg font-medium">Deterministic Skills Intelligence Engine</p>
        </div>

        <div className="flex gap-3 items-center">
          {/* View Switcher */}
          <div className="bg-slate-900 p-1 rounded-lg border border-white/10 flex">
            <button
              onClick={() => setViewMode('single')}
              className={"px-4 py-2 rounded-md text-sm font-bold transition-all " + (viewMode === 'single' ? "bg-slate-700 text-white shadow" : "text-slate-500 hover:text-slate-300")}
            >
              Single Match
            </button>
            <button
              onClick={() => setViewMode('batch')}
              className={"px-4 py-2 rounded-md text-sm font-bold transition-all " + (viewMode === 'batch' ? "bg-blue-600 text-white shadow" : "text-slate-500 hover:text-slate-300")}
            >
              Batch Platform
            </button>
            <button
              onClick={() => setViewMode('history')}
              className={"px-4 py-2 rounded-md text-sm font-bold transition-all " + (viewMode === 'history' ? "bg-purple-600 text-white shadow" : "text-slate-500 hover:text-slate-300")}
            >
              History
            </button>
          </div>

          <div className="bg-slate-900/50 border border-emerald-500/30 rounded-lg px-4 py-2 text-sm text-emerald-400 font-mono flex items-center gap-2">
            <span className="w-2 h-2 bg-emerald-500 rounded-full animate-pulse"></span>
            Engine Active
          </div>
        </div>
      </header>

      {viewMode === 'history' ? (
        <HistoryDashboard />
      ) : viewMode === 'batch' ? (
        <BatchDashboard />
      ) : (
        <main className="grid grid-cols-1 lg:grid-cols-2 gap-10 animate-fade-in">
          {/* INPUT COLUMN */}
          <div className="space-y-8">

            {/* CANDIDATE CARD */}
            <div className="group bg-slate-900/40 backdrop-blur-xl p-1 rounded-2xl border border-white/10 hover:border-blue-500/30 transition-all shadow-2xl">
              <div className="bg-slate-900/90 rounded-xl p-6 h-full">
                <div className="flex justify-between items-center mb-6">
                  <h2 className="text-xl font-bold text-blue-300 flex items-center gap-2">
                    <span className="w-2 h-8 bg-blue-500 rounded-full"></span>
                    Candidate Profile
                  </h2>
                  <button
                    onClick={() => setShowExtractResume(!showExtractResume)}
                    className={"text-xs px-4 py-2 rounded-full font-bold uppercase tracking-wider transition-all border " + (showExtractResume ? 'bg-red-500/10 text-red-400 border-red-500/20 hover:bg-red-500/20' : 'bg-blue-500/10 text-blue-400 border-blue-500/20 hover:bg-blue-500/20')}
                  >
                    {showExtractResume ? "✕ Cancel" : "✨ Extract"}
                  </button>
                </div>

                {showExtractResume ? (
                  <div className="space-y-6 animate-fade-in">
                    <div className="border-2 border-dashed border-slate-700 rounded-xl p-8 text-center hover:bg-slate-800/50 hover:border-blue-500/50 transition-all cursor-pointer group/upload">
                      <label className="cursor-pointer block w-full h-full">
                        <div className="text-4xl mb-3 group-hover/upload:scale-110 transition-transform">📄</div>
                        <span className="text-sm text-blue-300 font-bold block mb-1">Upload Resume (PDF/Text)</span>
                        <span className="text-xs text-slate-500">Auto-extracts using Hybrid engine</span>
                        <input type="file" className="hidden" accept=".pdf,.txt" onChange={(e) => handleFileUpload(e, 'resume')} />
                      </label>
                    </div>

                    <div className="relative">
                      <div className="absolute inset-0 flex items-center"><div className="w-full border-t border-slate-800"></div></div>
                      <div className="relative flex justify-center text-xs text-slate-500 font-bold uppercase tracking-widest"><span className="bg-slate-900 px-2">OR PASTE TEXT</span></div>
                    </div>

                    <textarea
                      className="w-full h-40 bg-slate-950/50 border border-slate-700/50 rounded-xl p-4 font-sans text-sm focus:ring-2 focus:ring-blue-500/50 outline-none placeholder-slate-700 resize-none transition-all"
                      placeholder="Paste raw resume text here..."
                      value={resumeText}
                      onChange={(e) => setResumeText(e.target.value)}
                    />
                    <button
                      onClick={handleExtractResume}
                      disabled={loading}
                      className="w-full py-3 bg-gradient-to-r from-blue-600 to-blue-500 hover:from-blue-500 hover:to-blue-400 rounded-xl font-bold text-white shadow-lg shadow-blue-900/20 transition-all transform active:scale-95"
                    >
                      Run Extractor
                    </button>
                  </div>
                ) : (
                  <textarea
                    className="w-full h-96 bg-slate-950/50 border border-slate-700/50 rounded-xl p-4 font-mono text-xs leading-relaxed text-blue-100 focus:ring-2 focus:ring-blue-500/50 outline-none resize-none"
                    value={candidateStr}
                    onChange={(e) => setCandidateStr(e.target.value)}
                  />
                )}
              </div>
            </div>

            {/* JD CARD */}
            <div className="group bg-slate-900/40 backdrop-blur-xl p-1 rounded-2xl border border-white/10 hover:border-emerald-500/30 transition-all shadow-2xl">
              <div className="bg-slate-900/90 rounded-xl p-6 h-full">

                {/* Header */}
                <div className="flex justify-between items-center mb-6">
                  <h2 className="text-xl font-bold text-emerald-300 flex items-center gap-2">
                    <span className="w-2 h-8 bg-emerald-500 rounded-full"></span>
                    Job Description
                  </h2>
                  <div className="flex gap-2">
                    {!showExtractJD && !isConfiguring && (
                      <button
                        onClick={() => setIsConfiguring(true)}
                        className="text-xs px-3 py-1 rounded-full font-bold uppercase tracking-wider bg-slate-800 text-slate-400 hover:text-white transition-colors"
                      >
                        ⚙️ Configure
                      </button>
                    )}
                    <button
                      onClick={() => {
                        setShowExtractJD(!showExtractJD);
                        setIsConfiguring(false);
                      }}
                      className={"text-xs px-4 py-2 rounded-full font-bold uppercase tracking-wider transition-all border " + (showExtractJD ? 'bg-red-500/10 text-red-400 border-red-500/20 hover:bg-red-500/20' : 'bg-emerald-500/10 text-emerald-400 border-emerald-500/20 hover:bg-emerald-500/20')}
                    >
                      {showExtractJD ? "✕ Cancel" : "✨ Extract"}
                    </button>
                  </div>
                </div>

                {/* MODE: Extracting */}
                {showExtractJD ? (
                  <div className="space-y-6 animate-fade-in">
                    <div className="border-2 border-dashed border-slate-700 rounded-xl p-8 text-center hover:bg-slate-800/50 hover:border-emerald-500/50 transition-all cursor-pointer group/upload">
                      <label className="cursor-pointer block w-full h-full">
                        <div className="text-4xl mb-3 group-hover/upload:scale-110 transition-transform">💼</div>
                        <span className="text-sm text-emerald-300 font-bold block mb-1">Upload JD (PDF/Text)</span>
                        <span className="text-xs text-slate-500">Auto-extracts using Hybrid engine</span>
                        <input type="file" className="hidden" accept=".pdf,.txt" onChange={(e) => handleFileUpload(e, 'jd')} />
                      </label>
                    </div>

                    <div className="relative">
                      <div className="absolute inset-0 flex items-center"><div className="w-full border-t border-slate-800"></div></div>
                      <div className="relative flex justify-center text-xs text-slate-500 font-bold uppercase tracking-widest"><span className="bg-slate-900 px-2">OR PASTE TEXT</span></div>
                    </div>

                    <textarea
                      className="w-full h-40 bg-slate-950/50 border border-slate-700/50 rounded-xl p-4 font-sans text-sm focus:ring-2 focus:ring-emerald-500/50 outline-none placeholder-slate-700 resize-none transition-all"
                      placeholder="Paste Job Description text here..."
                      value={jdText}
                      onChange={(e) => setJdText(e.target.value)}
                    />
                    <button
                      onClick={handleExtractJD}
                      disabled={loading}
                      className="w-full py-3 bg-gradient-to-r from-emerald-600 to-emerald-500 hover:from-emerald-500 hover:to-emerald-400 rounded-xl font-bold text-white shadow-lg shadow-emerald-900/20 transition-all transform active:scale-95"
                    >
                      Run Extractor
                    </button>
                  </div>
                ) : isConfiguring ? (
                  /* MODE: Configuring */
                  <div className="animate-fade-in text-slate-800">
                    <JDConfigurationView
                      jd={JSON.parse(jdStr)}
                      onConfirm={(newJD) => {
                        setJdStr(JSON.stringify(newJD, null, 2));
                        setIsConfiguring(false);
                      }}
                      onCancel={() => setIsConfiguring(false)}
                    />
                  </div>
                ) : (
                  /* MODE: View JSON */
                  <div className="space-y-4">
                    {/* Metadata Badges */}
                    <div className="flex flex-wrap gap-2 animate-fade-in">
                      {(() => {
                        try {
                          const jd = JSON.parse(jdStr);
                          const meta = [];
                          if (jd.location) meta.push(<span key="loc" className="bg-emerald-900/40 text-emerald-400 px-2 py-1 rounded text-xs border border-emerald-500/20">📍 {jd.location}</span>);
                          if (jd.min_experience_months > 0) meta.push(<span key="exp" className="bg-emerald-900/40 text-emerald-400 px-2 py-1 rounded text-xs border border-emerald-500/20">⏳ {jd.min_experience_months}+ Months</span>);
                          if (jd.domain_expertise?.length) meta.push(<span key="dom" className="bg-emerald-900/40 text-emerald-400 px-2 py-1 rounded text-xs border border-emerald-500/20">🏢 {jd.domain_expertise.join(", ")}</span>);
                          return meta;
                        } catch (e) { return null; }
                      })()}
                    </div>
                    <textarea
                      className="w-full h-80 bg-slate-950/50 border border-slate-700/50 rounded-xl p-4 font-mono text-xs leading-relaxed text-emerald-100 focus:ring-2 focus:ring-emerald-500/50 outline-none resize-none"
                      value={jdStr}
                      onChange={(e) => setJdStr(e.target.value)}
                    />
                  </div>
                )}
              </div>
            </div>

            <button
              onClick={handleMatch}
              disabled={loading}
              className={"w-full py-5 rounded-2xl font-black text-xl shadow-2xl transition-all transform active:scale-95 border border-white/10 " + (loading ? "bg-slate-800 text-slate-500 cursor-not-allowed" : "bg-gradient-to-r from-blue-600 via-purple-600 to-emerald-600 hover:from-blue-500 hover:via-purple-500 hover:to-emerald-500 text-white")}
            >
              {loading ? (
                <span className="flex items-center justify-center gap-2">
                  <svg className="animate-spin h-5 w-5 text-white" xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24">
                    <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4"></circle>
                    <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path>
                  </svg>
                  Analyzing Match...
                </span>
              ) : "ANALYZE MATCH"}
            </button>

            {error && (
              <div className="p-4 bg-red-950/50 border border-red-500/50 rounded-lg text-red-200 text-sm font-mono animate-shake">
                ⚠️ {error}
              </div>
            )}
          </div>

          {/* RESULTS COLUMN */}
          <div className="space-y-6">
            {matchResult && (
              <div className="bg-slate-900/80 backdrop-blur-xl p-8 rounded-2xl border border-white/10 shadow-2xl sticky top-8 animate-fade-in-up">

                {/* 1. Score & Tribunal Header */}
                <div className="flex flex-col items-center justify-center mb-8">
                  <div className="relative mb-4">
                    <svg className="w-48 h-48 transform -rotate-90">
                      <circle cx="96" cy="96" r="88" stroke="currentColor" strokeWidth="12" fill="transparent" className="text-slate-800" />
                      <circle cx="96" cy="96" r="88" stroke="currentColor" strokeWidth="12" fill="transparent"
                        strokeDasharray={2 * Math.PI * 88}
                        strokeDashoffset={2 * Math.PI * 88 * (1 - matchResult.score / 100)}
                        className={"transition-all duration-1000 ease-out " + (matchResult.score > 80 ? 'text-emerald-500' : matchResult.score > 60 ? 'text-purple-500' : 'text-blue-500')}
                      />
                    </svg>
                    <div className="absolute top-1/2 left-1/2 transform -translate-x-1/2 -translate-y-1/2 text-center">
                      <span className="text-5xl font-black text-white">{matchResult.score.toFixed(0)}</span>
                      <span className="block text-xs text-slate-400 font-bold uppercase tracking-widest mt-1">Match Score</span>
                    </div>
                  </div>

                  {/* Tribunal Verdict Tag */}
                  {matchResult.tribunal_verdict && (
                    <div className={"px-4 py-2 rounded-full border text-sm font-mono uppercase tracking-wider flex items-center gap-2 " +
                      (matchResult.tribunal_verdict.narrative_tag.includes("risk") || matchResult.tribunal_verdict.narrative_tag.includes("mismatch") ? "bg-red-500/10 border-red-500/30 text-red-300" :
                        matchResult.tribunal_verdict.narrative_tag.includes("top") ? "bg-emerald-500/10 border-emerald-500/30 text-emerald-300" :
                          "bg-blue-500/10 border-blue-500/30 text-blue-300")
                    }>
                      <span>⚖️ Tribunal:</span>
                      <span className="font-bold">{matchResult.tribunal_verdict.narrative_tag.replace(/_/g, " ")}</span>
                    </div>
                  )}
                </div>

                {/* 2. Narrative Analysis (Tribunal) */}
                {matchResult.tribunal_verdict && (
                  <div className="mb-8 bg-white/5 p-4 rounded-xl border border-indigo-500/30">
                    <div className="grid grid-cols-1 md:grid-cols-2 gap-4 mb-4">
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

                <div className="border-t border-white/5 my-6"></div>

                {/* 3. Deep Analysis (Education, Experience, Competencies) */}
                <div className="space-y-4 mb-8">
                  <h3 className="text-xs font-bold uppercase tracking-widest text-slate-500 mb-2">Deep Analysis</h3>
                  <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                    {matchResult.analysis.map((section, i) => (
                      <AnalysisCard key={i} section={section} />
                    ))}
                  </div>
                </div>

                <div className="space-y-6">
                  {/* Required Skills */}
                  <div>
                    <h3 className="text-xs font-bold uppercase tracking-widest text-emerald-500 mb-4 flex items-center gap-2">
                      <span className="w-2 h-2 rounded-full bg-emerald-500"></span>
                      Required Skills
                    </h3>
                    <div className="space-y-2 font-mono text-sm">
                      {(matchResult.technical_trace || [])
                        .filter(i => i.priority === 'required' || !i.priority) // Fallback for legacy
                        .map((item) => (
                          <SkillRow key={item.skill_slug} item={item} />
                        ))}
                      {(matchResult.technical_trace || []).filter(i => i.priority === 'required').length === 0 && (
                        <div className="p-3 bg-white/5 rounded-lg text-center text-xs opacity-50">No required skills found.</div>
                      )}
                    </div>
                  </div>

                  {/* Preferred Skills */}
                  {(matchResult.technical_trace || []).filter(i => i.priority === 'preferred').length > 0 && (
                    <div>
                      <h3 className="text-xs font-bold uppercase tracking-widest text-blue-500 mb-4 flex items-center gap-2">
                        <span className="w-2 h-2 rounded-full bg-blue-500"></span>
                        Preferred Skills
                      </h3>
                      <div className="space-y-2 font-mono text-sm">
                        {(matchResult.technical_trace || [])
                          .filter(i => i.priority === 'preferred')
                          .map((item) => (
                            <SkillRow key={item.skill_slug} item={item} />
                          ))}
                      </div>
                    </div>
                  )}
                </div>
              </div>
            )}

            {!matchResult && !loading && (
              <div className="h-full flex flex-col items-center justify-center text-slate-700 border-2 border-dashed border-slate-800 rounded-3xl p-12 min-h-[400px]">
                <div className="text-6xl mb-4 opacity-50">🤖</div>
                <p className="font-medium text-lg">Detailed analysis will appear here</p>
                <p className="text-sm mt-2 opacity-50">Upload a resume and JD to get started</p>
              </div>
            )}
          </div>
        </main>
      )}
    </div>
  );
}

export default App;
