import type { AssessmentRecord, CandidateProfile } from "./contracts";
import { saveProfileToSupabase, saveAssessmentToSupabase } from "../supabase";

// ── Keys ──────────────────────────────────────────────────────────────────────
const PROFILE_ID_KEY = "radix_profile_id";
const PROFILE_DATA_KEY = "radix_profile_data";
const ASSESSMENT_KEY = "radix_latest_assessment";
const ASSESSMENTS_LIST_KEY = "radix_assessments_list";

export function getSavedProfileId(): string | null {
  if (typeof window === "undefined") return null;
  return sessionStorage.getItem(PROFILE_ID_KEY);
}

export function setSavedProfileId(id: string | null) {
  if (typeof window === "undefined") return;
  if (id) sessionStorage.setItem(PROFILE_ID_KEY, id);
  else sessionStorage.removeItem(PROFILE_ID_KEY);
}

// ── Full profile data ──────────────────────────────────────────────────────────

export function getSavedProfile(): CandidateProfile | null {
  if (typeof window === "undefined") return null;
  try {
    const raw = sessionStorage.getItem(PROFILE_DATA_KEY);
    if (raw) {
      const value = JSON.parse(raw) as Partial<CandidateProfile> & {
        projects?: Array<{ title?: string; summary?: string; description?: string }>;
        experience?: Array<{ company?: string; title?: string; role?: string; period?: string; duration?: string }>;
      };
      if (!value || typeof value !== "object") return null;
      return {
        profile_id: value.profile_id ?? `candidate-${Date.now()}`,
        full_name: value.full_name ?? "Candidate",
        headline: value.headline ?? "",
        location: value.location,
        education: Array.isArray(value.education) ? value.education : [],
        skills: Array.isArray(value.skills) ? value.skills : [],
        projects: Array.isArray(value.projects)
          ? value.projects.map((project) => ({
              title: project.title ?? "",
              summary: project.summary ?? project.description ?? "",
            }))
          : [],
        experience: Array.isArray(value.experience)
          ? value.experience.map((experience) => ({
              company: experience.company ?? "",
              title: experience.title ?? experience.role ?? "",
              period: experience.period ?? experience.duration ?? "",
            }))
          : [],
        certifications: Array.isArray(value.certifications) ? value.certifications : [],
        preferred_roles: Array.isArray(value.preferred_roles) ? value.preferred_roles : [],
        created_at: value.created_at ?? new Date().toISOString().slice(0, 10),
      };
    }
  } catch {
    // fall through
  }
  return null;
}

export function setSavedProfile(profile: CandidateProfile) {
  if (typeof window === "undefined") return;
  sessionStorage.setItem(PROFILE_DATA_KEY, JSON.stringify(profile));
  setSavedProfileId(profile.profile_id);
  // Asynchronously sync to Supabase if configured
  void saveProfileToSupabase(profile);
}

export function hasSavedProfile(): boolean {
  if (typeof window === "undefined") return false;
  return !!sessionStorage.getItem(PROFILE_DATA_KEY);
}

// ── Assessments ───────────────────────────────────────────────────────────────

export function getLatestLiveAssessment(): AssessmentRecord | null {
  if (typeof window === "undefined") return null;
  try {
    const raw = sessionStorage.getItem(ASSESSMENT_KEY);
    return raw ? (JSON.parse(raw) as AssessmentRecord) : null;
  } catch {
    return null;
  }
}

export function setLatestLiveAssessment(record: AssessmentRecord | null) {
  if (typeof window === "undefined") return;
  if (record) {
    sessionStorage.setItem(ASSESSMENT_KEY, JSON.stringify(record));
    saveAssessmentRecord(record);
  } else {
    sessionStorage.removeItem(ASSESSMENT_KEY);
  }
}

export function getSavedAssessments(): AssessmentRecord[] {
  if (typeof window === "undefined") return [];
  try {
    const raw = sessionStorage.getItem(ASSESSMENTS_LIST_KEY);
    if (raw) {
      const list = JSON.parse(raw) as AssessmentRecord[];
      if (Array.isArray(list) && list.length > 0) return list;
    }
  } catch {}
  const latest = getLatestLiveAssessment();
  return latest ? [latest] : [];
}

/** Start a clean assessment session when the active resume changes. */
export function clearAssessmentHistory() {
  if (typeof window === "undefined") return;
  sessionStorage.removeItem(ASSESSMENT_KEY);
  sessionStorage.removeItem(ASSESSMENTS_LIST_KEY);
}

export function saveAssessmentRecord(record: AssessmentRecord) {
  if (typeof window === "undefined") return;
  try {
    const list = getSavedAssessments();
    const withoutCurrent = list.filter((a) => a.id !== record.id);
    const updated = [record, ...withoutCurrent];
    sessionStorage.setItem(ASSESSMENTS_LIST_KEY, JSON.stringify(updated));
    // Asynchronously sync to Supabase if configured
    void saveAssessmentToSupabase(record);
  } catch {}
}
