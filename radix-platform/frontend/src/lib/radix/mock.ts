import type { AssessmentRecord, CandidateProfile, Completeness, Opportunity } from "./contracts";

// DEMO FIXTURES — clearly labelled as local/demo data in the UI.

export const demoProfile: CandidateProfile = {
  profile_id: "demo-profile",
  full_name: "Aarav Mehta",
  headline: "Final-year B.Tech, Computer Science · Aspiring backend engineer",
  location: "Pune, India",
  education: [{ institution: "College of Engineering, Pune", degree: "B.Tech Computer Science", year: "2027" }],
  skills: [
    { name: "Python", category: "COD", confidence: "high", evidence: "3 projects, 400+ commits", source: "extracted" },
    { name: "TypeScript", category: "COD", confidence: "medium", evidence: "Hackathon dashboard", source: "manual" },
    { name: "Graphs & DP", category: "DSA", confidence: "medium", evidence: "210 LeetCode problems", source: "manual" },
    { name: "PostgreSQL", category: "SQL", confidence: "medium", evidence: "Course project schema", source: "extracted" },
    { name: "Docker", category: "CLOUD", confidence: "low", evidence: null, source: "extracted" },
    { name: "Technical writing", category: "COMM", confidence: "medium", evidence: "Blog with 6 posts", source: "manual" },
  ],
  projects: [
    { title: "Campus Ride", summary: "FastAPI + Postgres ride-pooling service used by 300 students." },
    { title: "Lumen Notes", summary: "Offline-first markdown notes app with sync." },
  ],
  experience: [{ company: "Northwind Labs", title: "Backend Intern", period: "May – Jul 2026" }],
  certifications: [],
  preferred_roles: ["Backend Engineer", "Platform Engineer"],
  created_at: "2026-09-02",
};

export const demoCompleteness: Completeness = {
  percent: 72,
  sections: [
    { key: "personal", label: "Personal info", complete: true },
    { key: "education", label: "Education", complete: true },
    { key: "skills", label: "Skills", complete: true },
    { key: "projects", label: "Projects", complete: true },
    { key: "experience", label: "Experience", complete: true },
    { key: "certifications", label: "Certifications", complete: false },
    { key: "preferred", label: "Preferred roles", complete: false },
  ],
};

const DISCLAIMER =
  "This skill-match estimate is decision support only. It is not a hiring guarantee or a prediction of any employer's decision.";

export const demoAssessments: AssessmentRecord[] = [
  {
    id: "a-1042",
    role: "Backend Engineer I",
    company: "Halcyon Systems",
    jd_file: "halcyon_backend_eng.pdf",
    updated_at: "2026-10-24",
    status: "complete",
    match: {
      match_score: 74,
      summary:
        "Strong coding and SQL foundations align with the core of this role. System design depth and container tooling are the main gaps.",
      jd_source_file: "halcyon_backend_eng.pdf",
      company: "Halcyon Systems",
      role: "Backend Engineer I",
      matched_skills: [
        { skill: "Python", category: "COD", status: "matched", rationale: "JD requires production Python; candidate shows 3 substantial projects.", jd_evidence: "3+ years Python or equivalent project work", candidate_evidence: "3 projects, 400+ commits" },
        { skill: "PostgreSQL", category: "SQL", status: "matched", rationale: "Relational modelling experience meets the stated requirement.", jd_evidence: "Comfort with relational databases", candidate_evidence: "Course project schema" },
      ],
      partial_matches: [
        { skill: "Data structures", category: "DSA", status: "partial", rationale: "Solid practice volume; graph problems at medium level only.", jd_evidence: "Strong DSA fundamentals", candidate_evidence: "210 LeetCode problems", required_level: 4, candidate_level: 3 },
      ],
      review_required: [
        { skill: "Docker", category: "CLOUD", status: "review_required", rationale: "Skill listed on resume but no supporting evidence was found.", jd_evidence: "Containerised deployments", candidate_evidence: null },
      ],
      missing_skills: [
        { skill: "Distributed system design", category: "SYSD", status: "missing", critical_gap: true, rationale: "JD lists system design interviews; no matching evidence in profile.", jd_evidence: "Design scalable services", candidate_evidence: null, required_level: 3, candidate_level: null },
        { skill: "Networking basics", category: "NETW", status: "missing", critical_gap: false, rationale: "Nice-to-have requirement with no evidence.", jd_evidence: "Understanding of HTTP, TCP/IP", candidate_evidence: null },
      ],
      score_breakdown: {
        formula: "score = Σ(weight_c × coverage_c) − critical_penalty",
        weights: { COD: 0.3, DSA: 0.2, SQL: 0.15, SYSD: 0.2, CLOUD: 0.1, NETW: 0.05 },
      },
      talent_check_context: { verdict: "Close", readiness_score: 76 },
      warnings: ["Docker evidence could not be verified from the supplied profile."],
      disclaimer: DISCLAIMER,
      algorithm_version: "r5-1.3.0",
    },
    plan: {
      current_score: 74,
      projected_score_if_all_closed: 91,
      source: "role5/improvement-plan",
      warnings: [],
      disclaimer: "Projected scores are estimates against this job description only.",
      actions: [
        { skill: "Distributed system design", action_type: "learn_skill", score_gain: 9, projected_score_after: 83, level_needed: 3, why: "This is marked as a critical gap in the job description.", steps: ["Study load balancing, caching, and queues", "Write a design doc for Campus Ride at 10× scale", "Add the doc to your profile as evidence"] },
        { skill: "Docker", action_type: "verify_and_add_evidence", score_gain: 4, projected_score_after: 87, level_needed: null, why: "Listed but unverified — evidence would move it to matched.", steps: ["Containerise Campus Ride", "Publish the Dockerfile in the repo", "Link the repo in your profile"] },
        { skill: "Data structures", action_type: "raise_level", score_gain: 3, projected_score_after: 90, level_needed: 4, why: "Graph problems at hard level close the level gap.", steps: ["Solve 25 hard graph problems", "Record patterns in a notes repo"] },
        { skill: "Networking basics", action_type: "strengthen_evidence", score_gain: 1, projected_score_after: 91, level_needed: null, why: "A small, nice-to-have gain.", steps: ["Complete a short TCP/IP course", "Add the certificate"] },
      ],
    },
  },
];

export const demoOpportunities: Opportunity[] = [
  { id: "o1", title: "Backend Engineer I", company: "Halcyon Systems", location: "Bengaluru", mode: "Hybrid", type: "Full-time", skills: ["Python", "PostgreSQL", "System design"] },
  { id: "o2", title: "Platform Intern", company: "Tidewater Cloud", location: "Remote", mode: "Remote", type: "Internship", skills: ["Docker", "Linux", "Go"] },
  { id: "o3", title: "Data Engineer", company: "Orchid Analytics", location: "Hyderabad", mode: "On-site", type: "Full-time", skills: ["SQL", "Airflow", "Python"] },
  { id: "o4", title: "ML Engineering Intern", company: "Lantern AI", location: "Remote", mode: "Remote", type: "Internship", skills: ["PyTorch", "Python", "MLOps"] },
  { id: "o5", title: "Software Engineer, APIs", company: "Meridian Pay", location: "Pune", mode: "On-site", type: "Full-time", skills: ["TypeScript", "Node.js", "REST"] },
];
