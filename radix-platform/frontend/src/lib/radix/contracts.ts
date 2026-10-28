// Typed contracts mirroring the role documents. Backend is source of truth.

export type SkillCategory =
  | "COD" | "DSA" | "OOD" | "APTI" | "COMM" | "AI" | "CLOUD"
  | "SQL" | "SWE" | "SYSD" | "NETW" | "OS" | "OTHER";

export const CATEGORY_LABELS: Record<SkillCategory, string> = {
  COD: "Coding",
  DSA: "Data Structures & Algorithms",
  OOD: "Object-Oriented Design",
  APTI: "Aptitude",
  COMM: "Communication",
  AI: "Artificial Intelligence",
  CLOUD: "Cloud",
  SQL: "SQL",
  SWE: "Software Engineering",
  SYSD: "System Design",
  NETW: "Networking",
  OS: "Operating Systems",
  OTHER: "Other",
};

export type Confidence = "high" | "medium" | "low";

export interface ProfileSkill {
  name: string;
  category: SkillCategory;
  confidence: Confidence;
  evidence?: string | null;
  source?: "extracted" | "manual";
}

export interface CandidateProfile {
  profile_id: string;
  full_name: string;
  headline: string;
  location?: string;
  education: { institution: string; degree: string; year: string }[];
  skills: ProfileSkill[];
  projects: { title: string; summary: string }[];
  experience: { company: string; title: string; period: string }[];
  certifications: string[];
  preferred_roles: string[];
  created_at: string;
}

export interface Completeness {
  percent: number;
  sections: { key: string; label: string; complete: boolean }[];
}

export type MatchStatus = "matched" | "partial" | "review_required" | "missing";

export interface SkillMatchItem {
  skill: string;
  category: SkillCategory;
  status: MatchStatus;
  critical_gap?: boolean;
  rationale: string;
  jd_evidence?: string | null;
  candidate_evidence?: string | null;
  required_level?: number | null;
  candidate_level?: number | null;
}

export interface MatchResult {
  match_score: number;
  summary: string;
  jd_source_file: string;
  company: string;
  role: string;
  matched_skills: SkillMatchItem[];
  partial_matches: SkillMatchItem[];
  review_required: SkillMatchItem[];
  missing_skills: SkillMatchItem[];
  score_breakdown: { formula: string; weights?: Record<string, number> };
  talent_check_context?: { verdict?: string; readiness_score?: number; handling?: string; critical_categories?: string[] } | null;
  warnings: string[];
  disclaimer: string;
  algorithm_version: string;
}

export type ActionType = "learn_skill" | "strengthen_evidence" | "verify_and_add_evidence" | "raise_level";

export const ACTION_LABELS: Record<ActionType, string> = {
  learn_skill: "Learn",
  strengthen_evidence: "Add stronger evidence",
  verify_and_add_evidence: "Verify & document",
  raise_level: "Level up",
};

export interface ImprovementAction {
  skill: string;
  action_type: ActionType;
  score_gain: number;
  projected_score_after: number;
  steps: string[];
  why: string;
  level_needed?: number | null;
}

export interface ImprovementPlan {
  actions: ImprovementAction[];
  current_score: number;
  projected_score_if_all_closed: number;
  source: string;
  warnings: string[];
  disclaimer: string;
}

export interface AssessmentRecord {
  id: string;
  role: string;
  company: string;
  jd_file: string;
  updated_at: string;
  status: "complete" | "draft";
  match: MatchResult;
  plan: ImprovementPlan;
}

export interface Opportunity {
  id: string;
  title: string;
  company: string;
  location: string;
  mode: "Remote" | "On-site" | "Hybrid";
  type: "Internship" | "Full-time";
  skills: string[];
}
