import { createClient, SupabaseClient } from "@supabase/supabase-js";
import type { CandidateProfile, AssessmentRecord } from "./contracts";

const supabaseUrl = import.meta.env.VITE_SUPABASE_URL;
const supabaseAnonKey = import.meta.env.VITE_SUPABASE_ANON_KEY;

export const isSupabaseConfigured = Boolean(
  supabaseUrl &&
  supabaseAnonKey &&
  !supabaseUrl.includes("your-project") &&
  !supabaseAnonKey.includes("your-anon-key")
);

export const supabase: SupabaseClient | null = isSupabaseConfigured
  ? createClient(supabaseUrl, supabaseAnonKey)
  : null;

// ── Profile helpers ──────────────────────────────────────────────────────────

export async function saveProfileToSupabase(profile: CandidateProfile): Promise<boolean> {
  if (!supabase) return false;
  try {
    const { error: profileError } = await supabase.from("profiles").upsert({
      profile_id: profile.profile_id,
      full_name: profile.full_name,
      email: `${profile.full_name.toLowerCase().replace(/\s+/g, ".")}@candidate.radix`,
      headline: profile.headline,
      location: profile.location,
      profile_data: profile,
      updated_at: new Date().toISOString(),
    });
    if (profileError) {
      console.warn("Supabase profile upsert error:", profileError.message);
      return false;
    }

    if (profile.skills.length > 0) {
      const rows = profile.skills.map((s) => ({
        profile_id: profile.profile_id,
        skill_name: s.name,
        category_code: s.category,
        evidence: s.evidence || "",
        confidence: s.confidence,
        source: s.source || "extracted",
      }));
      await supabase.from("profile_skills").delete().eq("profile_id", profile.profile_id);
      await supabase.from("profile_skills").insert(rows);
    }
    return true;
  } catch (err) {
    console.warn("Supabase profile save exception:", err);
    return false;
  }
}

export async function loadProfileFromSupabase(profileId: string): Promise<CandidateProfile | null> {
  if (!supabase) return null;
  try {
    const { data, error } = await supabase
      .from("profiles")
      .select("profile_data")
      .eq("profile_id", profileId)
      .single();
    if (error || !data) return null;
    return data.profile_data as CandidateProfile;
  } catch {
    return null;
  }
}

// ── Assessments helpers ──────────────────────────────────────────────────────

export async function saveAssessmentToSupabase(record: AssessmentRecord): Promise<boolean> {
  if (!supabase) return false;
  try {
    const { error } = await supabase.from("assessments").upsert({
      id: record.id,
      profile_id: record.profile_id,
      role: record.role,
      company: record.company,
      jd_file: record.jd_file,
      match_score: record.match.match_score,
      matched_skills: record.match.matched_skills,
      missing_skills: record.match.missing_skills,
      partial_skills: record.match.partial_skills,
      improvement_plan: record.plan,
      talent_check: record.talent_check,
      summary: record.match.summary,
      updated_at: new Date().toISOString(),
    });
    if (error) {
      console.warn("Supabase assessment upsert error:", error.message);
      return false;
    }
    return true;
  } catch (err) {
    console.warn("Supabase assessment save exception:", err);
    return false;
  }
}

export async function loadAssessmentsFromSupabase(): Promise<AssessmentRecord[]> {
  if (!supabase) return [];
  try {
    const { data, error } = await supabase
      .from("assessments")
      .select("*")
      .order("created_at", { ascending: false });
    if (error || !data) return [];
    return data.map((d) => ({
      id: d.id,
      profile_id: d.profile_id,
      role: d.role,
      company: d.company,
      jd_file: d.jd_file,
      match: {
        match_score: d.match_score,
        matched_skills: d.matched_skills || [],
        missing_skills: d.missing_skills || [],
        partial_skills: d.partial_skills || [],
        summary: d.summary || "",
      },
      plan: d.improvement_plan,
      talent_check: d.talent_check,
      created_at: d.created_at,
      updated_at: d.updated_at,
    }));
  } catch {
    return [];
  }
}
