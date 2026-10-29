// ─── RADIX API Services — all 5 role endpoints ────────────────────────────────
// Base URLs come from Vite env vars. Any service with a null URL shows
// "not configured" in the UI and throws a clear error on action.
// Nothing in this file fakes success.

import type {
  AssessmentRecord,
  CandidateProfile,
  Completeness,
  ImprovementPlan,
  MatchResult,
  SkillMatchItem,
} from "./contracts";

// ─── Service registry ─────────────────────────────────────────────────────────

export interface ServiceDef {
  key: string;
  name: string;
  role: string;
  baseUrl: string | null;
  healthPath: string | null;
  note?: string;
}

const env = import.meta.env as Record<string, string | undefined>;

export const SERVICES: ServiceDef[] = [
  {
    key: "jd",
    name: "JD Analytics",
    role: "Role 1",
    baseUrl: env["VITE_JD_API_URL"] ?? null,
    healthPath: "/health",
    note: "No scanned / image-only PDFs",
  },
  {
    key: "resume",
    name: "Resume Parsing",
    role: "Role 2",
    baseUrl: env["VITE_RESUME_API_URL"] ?? null,
    healthPath: "/health",
    note: "FastAPI adapter wrapping Groq pipeline",
  },
  {
    key: "profile",
    name: "Profile Builder",
    role: "Role 3",
    baseUrl: env["VITE_PROFILE_API_URL"] ?? null,
    healthPath: "/health",
  },
  {
    key: "talent",
    name: "Talent Check",
    role: "Role 4",
    baseUrl: env["VITE_TALENT_API_URL"] ?? null,
    healthPath: "/api/health",
  },
  {
    key: "match",
    name: "Skill Matching",
    role: "Role 5",
    baseUrl: env["VITE_MATCH_API_URL"] ?? null,
    healthPath: "/health",
  },
];

// ─── Health ───────────────────────────────────────────────────────────────────

export type HealthState = "online" | "offline" | "not_configured" | "unknown";

export async function checkHealth(s: ServiceDef): Promise<HealthState> {
  if (!s.baseUrl) return "not_configured";
  if (!s.healthPath) return "unknown";
  try {
    const ctrl = new AbortController();
    const t = setTimeout(() => ctrl.abort(), 4000);
    const r = await fetch(s.baseUrl + s.healthPath, { signal: ctrl.signal });
    clearTimeout(t);
    return r.ok ? "online" : "offline";
  } catch {
    return "offline";
  }
}

// ─── Helpers ──────────────────────────────────────────────────────────────────

function base(key: string): string {
  const svc = SERVICES.find((s) => s.key === key);
  if (!svc?.baseUrl)
    throw new Error(
      `${svc?.name ?? key} is not connected. Set VITE_${key.toUpperCase()}_API_URL in your .env file.`
    );
  return svc.baseUrl;
}

async function api<T>(url: string, init?: RequestInit): Promise<T> {
  const r = await fetch(url, init);
  if (!r.ok) {
    const msg = await r.text().catch(() => r.statusText);
    throw new Error(`${r.status} — ${msg}`);
  }
  return r.json() as Promise<T>;
}

// ─── Role 1: JD Analytics (port 8001) ────────────────────────────────────────

export interface JDAnalysis {
  jd_id: string;
  source_type: string;
  source_file: string;
  company?: string | null;
  role?: string | null;
  skills: {
    skill_name: string;
    category_code: string;
    evidence: string;
    confidence: "high" | "medium" | "low";
  }[];
}

/** POST /api/v1/jds/analyze — upload a PDF/DOCX job description */
export async function analyzeJD(
  file: File
): Promise<{ data: JDAnalysis; indexingStatus: string | null }> {
  const fd = new FormData();
  fd.append("file", file);
  const r = await fetch(`${base("jd")}/api/v1/jds/analyze`, {
    method: "POST",
    body: fd,
  });
  if (!r.ok) {
    const msg = await r.text().catch(() => r.statusText);
    throw new Error(`The job description could not be analysed. ${msg}`);
  }
  return { data: (await r.json()) as JDAnalysis, indexingStatus: r.headers.get("X-Indexing-Status") };
}

/** GET /api/v1/jds — list all analyzed JDs */
export async function listJDs(): Promise<JDAnalysis[]> {
  return api<JDAnalysis[]>(`${base("jd")}/api/v1/jds`);
}

/** GET /api/v1/jds/:id */
export async function getJD(jdId: string): Promise<JDAnalysis> {
  return api<JDAnalysis>(`${base("jd")}/api/v1/jds/${jdId}`);
}

/** POST /api/v1/jds/search */
export async function searchJDs(query: string, topK = 5): Promise<JDAnalysis[]> {
  return api<JDAnalysis[]>(`${base("jd")}/api/v1/jds/search`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ query, top_k: topK }),
  });
}

// ─── Role 2: Resume Parsing (port 8002) ───────────────────────────────────────

export interface ResumeExtract {
  source_type: "resume";
  source_file: string;
  skills: JDAnalysis["skills"];
  education: string | null;
  projects: string[];
  experience: string[];
  certifications: string[];
}

/** POST /api/v1/resumes/parse — upload a PDF/DOCX resume */
export async function parseResume(file: File): Promise<ResumeExtract> {
  const fd = new FormData();
  fd.append("file", file);
  const r = await fetch(`${base("resume")}/api/v1/resumes/parse`, {
    method: "POST",
    body: fd,
  });
  if (!r.ok) {
    const msg = await r.text().catch(() => r.statusText);
    throw new Error(`Resume could not be parsed. ${msg}`);
  }
  return r.json() as Promise<ResumeExtract>;
}

// ─── Role 3: Profile Builder (port 8003) ──────────────────────────────────────

export interface ProfileCreate {
  personal_info: {
    full_name: string;
    email: string;
    location?: string | null;
    summary?: string | null;
  };
  skills: {
    skill_name: string;
    category_code: string;
    evidence: string;
    confidence: "high" | "medium" | "low";
    source: "extracted" | "manual";
  }[];
}

export interface ProfileResponse {
  profile_id: string;
  personal_info: ProfileCreate["personal_info"];
  skills: ProfileCreate["skills"];
  created_at: string;
}

/** POST /api/v1/profiles — create a new profile */
export async function createProfile(data: ProfileCreate): Promise<ProfileResponse> {
  return api<ProfileResponse>(`${base("profile")}/api/v1/profiles`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(data),
  });
}

/** GET /api/v1/profiles/:id */
export async function getProfile(id: string): Promise<ProfileResponse> {
  return api<ProfileResponse>(`${base("profile")}/api/v1/profiles/${id}`);
}

/** GET /api/v1/profiles/:id/completeness */
export async function getCompleteness(id: string): Promise<Completeness> {
  return api<Completeness>(`${base("profile")}/api/v1/profiles/${id}/completeness`);
}

/** POST /api/v1/profiles/:id/cv — upload a CV file */
export async function uploadCV(id: string, file: File): Promise<{ message: string }> {
  const fd = new FormData();
  fd.append("file", file);
  return api<{ message: string }>(`${base("profile")}/api/v1/profiles/${id}/cv`, {
    method: "POST",
    body: fd,
  });
}

// ─── Role 2→3 Adapter ─────────────────────────────────────────────────────────

/** Convert a parsed resume into a ProfileCreate payload */
export function resumeToProfile(
  resume: ResumeExtract,
  personalInfo: ProfileCreate["personal_info"]
): ProfileCreate {
  return {
    personal_info: personalInfo,
    skills: resume.skills.map((s) => ({
      skill_name: s.skill_name,
      category_code: s.category_code,
      evidence: s.evidence || "Extracted from resume",
      confidence: s.confidence,
      source: "extracted" as const,
    })),
  };
}

// ─── Role 4: Talent Check (port 8004) ─────────────────────────────────────────

export interface Company {
  id: number;
  name: string;
  description?: string;
  industry?: string;
  skills?: Record<string, number>;
}

export interface WebAuditResult {
  enabled: boolean;
  github_handle?: string | null;
  leetcode_handle?: string | null;
  composite_reality_score: number;
  candidate_level: number;
  level_designation: string;
  level_explanation: string;
  sub_scores?: {
    github_authenticity?: number;
    leetcode_problem_solving?: number;
    skills_corroboration?: number;
    project_authenticity?: number;
  };
  skills_breakdown?: {
    total_claimed: number;
    total_verified: number;
    verified_skills: string[];
    unverified_skills: string[];
    bonus_discovered_skills: string[];
  };
  github_summary?: {
    exists: boolean;
    original_repos: number;
    forked_repos: number;
    stars: number;
    recent_active_repos: number;
  };
  leetcode_summary?: {
    exists: boolean;
    total_solved: number;
    easy: number;
    medium: number;
    hard: number;
    contest_rating?: number | null;
  };
}

export interface TalentCheckResult {
  candidate_name?: string;
  candidate_headline?: string;
  company?: string;
  company_id?: number;
  readiness_score: number;
  baseline_score?: number;
  baseline_verdict?: string;
  baseline_levels?: Record<string, number>;
  score_delta?: number;
  levels_delta?: Record<string, number>;
  verdict: string;
  verdict_badge?: string;
  verdict_message?: string;
  critical_gaps: string[];
  focus_areas: string[];
  summary?: {
    total_categories: number;
    met_count: number;
    gap_count: number;
    critical_gap_count: number;
    critical_categories: string[];
  };
  candidate_levels?: Record<string, number>;
  evidence_points?: Record<string, number>;
  category_results?: Record<string, unknown>;
  skillset_gap?: Array<{
    category_code: string;
    category_name: string;
    required_level: number;
    required_tier: string;
    tier_name: string;
    candidate_level: number;
    gap: boolean;
    gap_size: number;
    ratio: number;
    evidence_points?: number;
  }>;
  web_audit?: WebAuditResult;
}

/** GET /api/companies?q=&limit= */
export async function searchCompanies(q = "", limit = 200): Promise<Company[]> {
  const url = new URL(`${base("talent")}/api/companies`);
  if (q) url.searchParams.set("q", q);
  url.searchParams.set("limit", String(limit));
  const raw = await api<any[]>(url.toString());
  return raw.map((company) => ({
    id: company.id,
    name: company.name ?? company.company ?? "Unknown company",
    description: company.description,
    industry: company.industry,
    skills: company.skills,
  }));
}

/** GET /api/companies/:id */
export async function getCompany(id: number): Promise<Company> {
  return api<Company>(`${base("talent")}/api/companies/${id}`);
}

function normalizeTalentCheck(raw: any): TalentCheckResult {
  const critical_gaps: string[] =
    Array.isArray(raw?.critical_gaps)
      ? raw.critical_gaps
      : Array.isArray(raw?.summary?.critical_categories)
      ? raw.summary.critical_categories
      : [];
  const focus_areas: string[] = Array.isArray(raw?.focus_areas)
    ? raw.focus_areas.map((f: any) => (typeof f === "string" ? f : f?.name ?? f?.code ?? ""))
    : [];

  const readiness_score = typeof raw?.readiness_score === "number" ? raw.readiness_score : 0;
  const baseline_score = typeof raw?.baseline_score === "number" ? raw.baseline_score : readiness_score;
  const score_delta = typeof raw?.score_delta === "number" ? raw.score_delta : (readiness_score - baseline_score);

  return {
    ...raw,
    critical_gaps,
    focus_areas,
    readiness_score,
    baseline_score,
    baseline_verdict: raw?.baseline_verdict ?? raw?.verdict ?? "Needs Work",
    baseline_levels: raw?.baseline_levels ?? raw?.candidate_levels ?? {},
    score_delta,
    levels_delta: raw?.levels_delta ?? {},
    verdict: raw?.verdict ?? "Needs Work",
    web_audit: raw?.web_audit,
  };
}

/** POST /api/talent-check — profile-based assessment with optional web audit (Beta) */
export async function runTalentCheck(
  companyId: number,
  profile: CandidateProfile,
  options?: {
    enable_web_audit?: boolean;
    github_handle?: string;
    leetcode_handle?: string;
  }
): Promise<TalentCheckResult> {
  const raw = await api<any>(`${base("talent")}/api/talent-check`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({
      company_id: companyId,
      candidate_profile: profile,
      enable_web_audit: options?.enable_web_audit ?? false,
      github_handle: options?.github_handle || undefined,
      leetcode_handle: options?.leetcode_handle || undefined,
    }),
  });
  return normalizeTalentCheck(raw);
}

/** POST /api/talent-check/direct — raw skill-levels assessment */
export async function runTalentCheckDirect(
  companyId: number,
  skillLevels: Record<string, number>
): Promise<TalentCheckResult> {
  const raw = await api<any>(`${base("talent")}/api/talent-check/direct`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ company_id: companyId, skill_levels: skillLevels }),
  });
  return normalizeTalentCheck(raw);
}

/** POST /api/audit/web-footprint — standalone web audit for candidate */
export async function auditWebFootprint(req: {
  github_handle?: string;
  leetcode_handle?: string;
  claimed_skills?: string[];
  claimed_projects?: any[];
}): Promise<any> {
  return api<any>(`${base("talent")}/api/audit/web-footprint`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(req),
  });
}

// ─── Role 5: Skill Matching (port 8005) ───────────────────────────────────────

export interface MatchRequest {
  candidate: { skills: JDAnalysis["skills"] };
  job_description: JDAnalysis;
  talent_check?: TalentCheckResult | null;
}

function normalizeSkillResult(s: any): SkillMatchItem {
  return {
    skill: s.skill ?? s.skill_name ?? "Unknown skill",
    category: s.category ?? s.category_code ?? "OTHER",
    status: s.status ?? "missing",
    critical_gap: !!s.critical_gap,
    rationale: s.rationale ?? "",
    jd_evidence: s.jd_evidence ?? null,
    candidate_evidence: s.candidate_evidence ?? null,
    required_level: s.required_level ?? s.category_required_level ?? null,
    candidate_level: s.candidate_level ?? s.category_candidate_level ?? null,
  };
}

function normalizeMatchResult(raw: any): MatchResult {
  return {
    ...raw,
    match_score: typeof raw.match_score === "number" ? raw.match_score : (raw.overall_score ?? 0),
    summary: raw.summary ?? "",
    jd_source_file: raw.jd_source_file ?? "",
    company: raw.company ?? "",
    role: raw.role ?? "",
    matched_skills: (raw.matched_skills ?? []).map(normalizeSkillResult),
    partial_matches: (raw.partial_matches ?? []).map(normalizeSkillResult),
    review_required: (raw.review_required ?? []).map(normalizeSkillResult),
    missing_skills: (raw.missing_skills ?? []).map(normalizeSkillResult),
    score_breakdown: {
      formula: raw.score_breakdown?.formula ?? "",
      weights: raw.score_breakdown?.weights ?? {},
      ...raw.score_breakdown,
    },
    warnings: raw.warnings ?? [],
    disclaimer: raw.disclaimer ?? "",
    algorithm_version: raw.algorithm_version ?? "1.0.0",
  };
}

/** POST /api/v1/matches (or /api/v1/matches/with-talent-check if talent_check is provided) */
export async function runMatch(req: MatchRequest): Promise<MatchResult> {
  const endpoint = req.talent_check
    ? `${base("match")}/api/v1/matches/with-talent-check`
    : `${base("match")}/api/v1/matches`;
  const raw = await api<any>(endpoint, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(req),
  });
  return normalizeMatchResult(raw);
}

/** POST /api/v1/matches/preview — lightweight match without persistence */
export async function previewMatch(req: MatchRequest): Promise<MatchResult> {
  const raw = await api<any>(`${base("match")}/api/v1/matches/preview`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(req),
  });
  return normalizeMatchResult(raw);
}

/** POST /api/v1/improvement-plan */
export async function getImprovementPlan(req: MatchRequest): Promise<ImprovementPlan> {
  const raw = await api<any>(`${base("match")}/api/v1/improvement-plan`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(req),
  });
  const actions = (raw.actions ?? []).map((a: any) => ({
    ...a,
    skill: a.skill ?? a.skill_name ?? "Skill",
    action_type: a.action_type ?? "learn_skill",
    score_gain: typeof a.score_gain === "number" ? a.score_gain : 0,
    projected_score_after: typeof a.projected_score_after === "number" ? a.projected_score_after : 0,
    steps: Array.isArray(a.steps) ? a.steps : [],
    why: a.why ?? "",
    level_needed: a.level_needed ?? null,
  }));
  return {
    ...raw,
    actions,
    current_score: typeof raw.current_score === "number" ? raw.current_score : 0,
    projected_score_if_all_closed: typeof raw.projected_score_if_all_closed === "number" ? raw.projected_score_if_all_closed : 0,
    source: raw.source ?? "offline_deterministic",
    warnings: Array.isArray(raw.warnings) ? raw.warnings : [],
    disclaimer: raw.disclaimer ?? "",
  };
}

// ─── Convenience: full assessment flow ────────────────────────────────────────

/**
 * Runs the complete assessment pipeline:
 *   1. Run skill match (Role 5)
 *   2. Fetch improvement plan (Role 5)
 * Returns a partial AssessmentRecord (without id/timestamps — caller adds those).
 */
export async function runFullAssessment(
  profile: CandidateProfile,
  jd: JDAnalysis,
  talentResult?: TalentCheckResult | null
): Promise<Pick<AssessmentRecord, "match" | "plan">> {
  const candidateSkills = profile.skills.map((s) => ({
    skill_name: s.name,
    category_code: s.category,
    evidence: s.evidence ?? "",
    confidence: s.confidence,
  }));

  const req: MatchRequest = {
    candidate: { skills: candidateSkills },
    job_description: jd,
    talent_check: talentResult ?? null,
  };

  const [match, plan] = await Promise.all([runMatch(req), getImprovementPlan(req)]);
  return { match, plan };
}
