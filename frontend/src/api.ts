export interface EvidenceSource {
    section: "experience" | "education" | "projects" | "summary";
    verbatim: string;
    inferred_dates?: string[];
    context_level?: "practitioner" | "expert" | "learner" | "unknown";
}

export interface ComputedStats {
    months_experience: number;
    recency_decay: number;
    evidence_confidence: number;
}

export interface CandidateSkill {
    skill_id: string;
    evidence_sources: {
        section: "experience" | "education" | "projects" | "summary";
        verbatim: string;
        inferred_dates?: string[];
        context_level?: "practitioner" | "expert" | "learner" | "unknown";
    }[];
    computed_stats: ComputedStats;
}

export interface CandidateMetadata {
    name?: string;
    location?: string;
    links?: string[];
}

export interface ComputedCandidateStats {
    total_yoe: number;
    avg_tenure_months: number;
    management_experience_years: number;
}

export interface TimelineEntry {
    company?: string;
    title_raw?: string;
    title_norm?: string;
    start_date?: string;
    end_date?: string;
    domain_tags?: string[];
    extracted_skills?: { skill_id: string; context: string }[];
}

export interface EducationEntry {
    degree?: string;
    field?: string;
    institution?: string;
    year?: number;
}

export interface SkillProfileEntry {
    skill_slug: string;
    total_months: number;
    last_used?: string;
    competency_level?: string;
    sources: string[];
}

export interface CandidateProfile {
    id: string;
    candidate_metadata?: CandidateMetadata;
    computed_stats?: ComputedCandidateStats;
    timeline?: TimelineEntry[];
    skill_profile?: SkillProfileEntry[]; // Changed to Array
    education?: EducationEntry[];
    skills: CandidateSkill[]; // Keep for compatibility if needed
    competencies?: string[];
}

export interface JobMetadata {
    title?: string;
    location?: string;
    clearance?: string;
}

export interface GatingRules {
    visa_sponsorship?: boolean;
    education_min?: string;
    education_strict?: boolean; // New
    security_clearance?: string;
    location_strict?: boolean; // New
}

export interface SenioritySignals {
    target_level?: string;
    keywords_found: string[];
}

export interface Requirement {
    req_id: string;
    skill_id?: string;
    priority: "must_have" | "nice_to_have";
    min_years: number;
    context?: string;
    logic?: "one_of";
    options?: string[];
    // Manual Configuration
    level?: "junior" | "mid" | "senior";
    is_hard_filter?: boolean;
}

export interface Competency {
    name: string;
    description?: string;
    priority: "must_have" | "nice_to_have";
}

export interface JobDescription {
    id: string;
    job_metadata: JobMetadata;
    gating_rules: GatingRules;
    requirements: Requirement[];
    competencies?: Competency[];
    seniority_signals: SenioritySignals;
}

export interface TraceItem {
    skill_slug: string;
    status: "matched" | "missing" | "partial";
    score: number;
    seniority_level?: string;
    sources?: string[];
    priority?: "required" | "preferred";
}

export interface AnalysisSection {
    title: string;
    status: "met" | "not_met" | "review_needed" | "exceeds";
    summary: string;
    details: string[];
}

export interface TribunalVerdict {
    skeptic_summary: string;
    advocate_summary: string;
    consensus_flags: any[];
    consensus_strengths: any[];
    trajectory_analysis: {
        direction: string;
        reasoning: string;
    };
    narrative_tag: string;
}

export interface MatchResult {
    score: number;
    analysis: AnalysisSection[];
    technical_trace: TraceItem[];
    tribunal_verdict?: TribunalVerdict;
}

const API_URL = "http://localhost:8000";

// Returns the current user name for tracking who uploaded/ran analysis.
// Defaults to "default_user" if not set. Override via localStorage.
export function getUserName(): string {
    return localStorage.getItem("app_user_name") || "default_user";
}

export async function calculateMatch(candidate: CandidateProfile, jd: JobDescription): Promise<MatchResult> {
    const response = await fetch(`${API_URL}/match`, {
        method: "POST",
        headers: {
            "Content-Type": "application/json",
            "X-User-Name": getUserName(),
        },
        body: JSON.stringify({
            candidate: candidate,
            job_description: jd,
        }),
    });

    if (!response.ok) {
        throw new Error(`API Error: ${response.statusText}`);
    }

    return response.json();
}

export async function extractResume(text: string, apiKey: string): Promise<CandidateProfile> {
    const response = await fetch(`${API_URL}/extract/resume`, {
        method: "POST",
        headers: { "Content-Type": "application/json", "X-User-Name": getUserName() },
        body: JSON.stringify({ text, api_key: apiKey }),
    });
    if (!response.ok) throw new Error(`Extraction Failed: ${response.statusText}`);
    return response.json();
}

export async function extractJD(text: string, apiKey: string): Promise<JobDescription> {
    const response = await fetch(`${API_URL}/extract/jd`, {
        method: "POST",
        headers: { "Content-Type": "application/json", "X-User-Name": getUserName() },
        body: JSON.stringify({ text, api_key: apiKey }),
    });
    if (!response.ok) throw new Error(`Extraction Failed: ${response.statusText}`);
    return response.json();
}

export async function extractResumeFile(file: File): Promise<CandidateProfile> {
    const formData = new FormData();
    formData.append("file", file);

    const response = await fetch(`${API_URL}/extract/resume/file`, {
        method: "POST",
        headers: { "X-User-Name": getUserName() },
        body: formData,
    });
    if (!response.ok) {
        const err = await response.json().catch(() => ({ detail: response.statusText }));
        throw new Error(err.detail || response.statusText);
    }
    return response.json();
}

export async function extractJDFile(file: File): Promise<JobDescription> {
    const formData = new FormData();
    formData.append("file", file);

    const response = await fetch(`${API_URL}/extract/jd/file`, {
        method: "POST",
        headers: { "X-User-Name": getUserName() },
        body: formData,
    });
    if (!response.ok) {
        const err = await response.json().catch(() => ({ detail: response.statusText }));
        throw new Error(err.detail || response.statusText);
    }
    return response.json();
}

// --- BATCH API ---

export interface CandidateMatchSummary {
    candidate_id: string;
    name: string;
    total_score: number;
    education_status: "met" | "not_met" | "review_needed";
    experience_status: "met" | "not_met" | "review_needed";
    tribunal_status: "Green" | "Yellow" | "Red" | null;
    top_skills_found: string[];
    missing_critical_skills: string[];
    details?: MatchResult;
}

export interface BatchJobResult {
    job_id: string;
    status: {
        status: "pending" | "processing" | "completed" | "failed";
        total_files: number;
        processed_count: number;
        progress_percent: number;
    };
    candidates: CandidateMatchSummary[];
    average_score: number;
    best_candidate_name?: string;
}

export async function submitBatch(jdInput: string | JobDescription, files: File[]): Promise<{ batch_id: string }> {
    const formData = new FormData();
    if (typeof jdInput === 'string') {
        formData.append("jd", jdInput);
    } else {
        formData.append("jd_json", JSON.stringify(jdInput));
    }
    files.forEach(f => formData.append("files", f));

    const response = await fetch(`${API_URL}/batch/upload`, {
        method: "POST",
        body: formData,
    });

    if (!response.ok) {
        throw new Error(`Batch Submit Failed: ${response.statusText}`);
    }
    return response.json();
}

export async function getBatchStatus(batchId: string): Promise<BatchJobResult> {
    const response = await fetch(`${API_URL}/batch/${batchId}`);
    if (!response.ok) {
        throw new Error(`Batch Poll Failed: ${response.statusText}`);
    }
    return response.json();
}

export async function parseDocument(file: File): Promise<{ text: string; filename: string }> {
    const formData = new FormData();
    formData.append("file", file);

    const response = await fetch(`${API_URL}/utils/parse_doc`, {
        method: "POST",
        body: formData,
    });

    if (!response.ok) {
        throw new Error(`Document Parsing Failed: ${response.statusText}`);
    }
    return response.json();
}

// --- HISTORY / BROWSE API ---

export interface JDSummary {
    id: string;
    filename: string | null;
    model_used: string | null;
    is_valid: boolean;
    created_at: string;
    job_title: string | null;
    job_location: string | null;
    uploaded_by_name: string | null;
    report_count: number;
}

export interface CVForJD {
    cv_id: string;
    filename: string | null;
    candidate_name: string | null;
    candidate_location: string | null;
    model_used: string | null;
    is_valid: boolean;
    cv_uploaded_at: string;
    report_id: string;
    score: number;
    analysis_date: string;
    uploaded_by_name: string | null;
}

export interface ReportSummary {
    report_id: string;
    score: number;
    analysis_date: string;
    analysis_json: MatchResult;
    cv_id: string;
    cv_filename: string | null;
    candidate_name: string | null;
    run_by_name: string | null;
}

export interface ReportDetail {
    id: string;
    jd_id: string;
    cv_id: string;
    score: number;
    analysis_json: MatchResult;
    created_at: string;
    cv_filename: string | null;
    candidate_name: string | null;
    job_title: string | null;
    jd_filename: string | null;
    run_by_name: string | null;
}

export interface JDDetail {
    id: string;
    uploaded_by: string | null;
    raw_text: string;
    filename: string | null;
    extracted_json: JobDescription;
    model_used: string | null;
    is_valid: boolean;
    created_at: string;
    uploaded_by_name: string | null;
}

export async function fetchJDs(limit = 50, offset = 0): Promise<{ jds: JDSummary[]; count: number }> {
    const response = await fetch(`${API_URL}/jds?limit=${limit}&offset=${offset}`);
    if (!response.ok) throw new Error(`Failed to fetch JDs: ${response.statusText}`);
    return response.json();
}

export async function fetchJDDetail(jdId: string): Promise<JDDetail> {
    const response = await fetch(`${API_URL}/jds/${jdId}`);
    if (!response.ok) throw new Error(`Failed to fetch JD: ${response.statusText}`);
    return response.json();
}

export async function fetchCVsForJD(jdId: string): Promise<{ jd_id: string; cvs: CVForJD[]; count: number }> {
    const response = await fetch(`${API_URL}/jds/${jdId}/cvs`);
    if (!response.ok) throw new Error(`Failed to fetch CVs: ${response.statusText}`);
    return response.json();
}

export async function fetchReportsForJD(jdId: string): Promise<{ jd_id: string; reports: ReportSummary[]; count: number }> {
    const response = await fetch(`${API_URL}/jds/${jdId}/reports`);
    if (!response.ok) throw new Error(`Failed to fetch reports: ${response.statusText}`);
    return response.json();
}

export async function fetchReportDetail(reportId: string): Promise<ReportDetail> {
    const response = await fetch(`${API_URL}/reports/${reportId}`);
    if (!response.ok) throw new Error(`Failed to fetch report: ${response.statusText}`);
    return response.json();
}

export async function updateJDExtracted(jdId: string, jd: JobDescription): Promise<{ status: string; jd_id: string }> {
    const response = await fetch(`${API_URL}/jds/${jdId}/extracted`, {
        method: "PUT",
        headers: { "Content-Type": "application/json", "X-User-Name": getUserName() },
        body: JSON.stringify(jd),
    });
    if (!response.ok) {
        const err = await response.json().catch(() => ({ detail: response.statusText }));
        throw new Error(err.detail || response.statusText);
    }
    return response.json();
}

export async function renameJD(jdId: string, title: string): Promise<{ status: string; jd_id: string; new_title: string }> {
    const response = await fetch(`${API_URL}/jds/${jdId}`, {
        method: "PATCH",
        headers: { "Content-Type": "application/json", "X-User-Name": getUserName() },
        body: JSON.stringify({ title }),
    });
    if (!response.ok) {
        const err = await response.json().catch(() => ({ detail: response.statusText }));
        throw new Error(err.detail || response.statusText);
    }
    return response.json();
}

export async function fetchJDCVCount(jdId: string): Promise<{ jd_id: string; cv_count: number }> {
    const response = await fetch(`${API_URL}/jds/${jdId}/cv-count`);
    if (!response.ok) {
        const err = await response.json().catch(() => ({ detail: response.statusText }));
        throw new Error(err.detail || response.statusText);
    }
    return response.json();
}

export async function deleteJD(jdId: string): Promise<{ status: string }> {
    const response = await fetch(`${API_URL}/jds/${jdId}`, {
        method: "DELETE",
        headers: { "X-User-Name": getUserName() },
    });
    if (!response.ok) {
        const err = await response.json().catch(() => ({ detail: response.statusText }));
        throw new Error(err.detail || response.statusText);
    }
    return response.json();
}

export async function deleteCV(cvId: string): Promise<{ status: string }> {
    const response = await fetch(`${API_URL}/cvs/${cvId}`, {
        method: "DELETE",
        headers: { "X-User-Name": getUserName() },
    });
    if (!response.ok) {
        const err = await response.json().catch(() => ({ detail: response.statusText }));
        throw new Error(err.detail || response.statusText);
    }
    return response.json();
}

export interface UploadCVResult {
    filename: string;
    status: string;
    score: number | null;
    cv_id: string | null;
    report_id: string | null;
    candidate_name: string | null;
    error: string | null;
}

export async function uploadCVsForJD(jdId: string, files: File[]): Promise<{ jd_id: string; processed: number; successful: number; results: UploadCVResult[] }> {
    const formData = new FormData();
    files.forEach(f => formData.append("files", f));

    const response = await fetch(`${API_URL}/jds/${jdId}/upload-cvs`, {
        method: "POST",
        headers: { "X-User-Name": getUserName() },
        body: formData,
    });
    if (!response.ok) {
        const err = await response.json().catch(() => ({ detail: response.statusText }));
        throw new Error(err.detail || response.statusText);
    }
    return response.json();
}

export async function reanalyse(jdId: string, cvId: string): Promise<MatchResult> {
    const response = await fetch(`${API_URL}/reanalyse`, {
        method: "POST",
        headers: { "Content-Type": "application/json", "X-User-Name": getUserName() },
        body: JSON.stringify({ jd_id: jdId, cv_id: cvId }),
    });
    if (!response.ok) {
        const err = await response.json().catch(() => ({ detail: response.statusText }));
        throw new Error(err.detail || response.statusText);
    }
    return response.json();
}
