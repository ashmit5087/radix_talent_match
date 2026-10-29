import { createFileRoute } from "@tanstack/react-router";
import { useState, useEffect, useRef } from "react";
import {
  FileText,
  UploadCloud,
  Loader2,
  CheckCircle2,
  Cpu,
  Search,
  Building2,
  AlertTriangle,
  ArrowRight,
  Sparkles,
  Database,
  BrainCircuit,
  FileCheck2,
  Layers,
} from "lucide-react";
import { Button } from "@/components/ui/button";
import { PageHeader, DemoTag } from "@/components/radix/ui";
import {
  SERVICES,
  analyzeJD,
  parseResume,
  searchCompanies,
  runTalentCheck,
  runMatch,
  getImprovementPlan,
  type JDAnalysis,
  type ResumeExtract,
  type Company,
  type TalentCheckResult,
} from "@/lib/radix/services";
import { getSavedProfile, getLatestLiveAssessment } from "@/lib/radix/session";
import { CATEGORY_LABELS, type SkillCategory, type MatchResult, type ImprovementPlan } from "@/lib/radix/contracts";
import { demoProfile, demoAssessments } from "@/lib/radix/mock";
import { cn } from "@/lib/utils";

export const Route = createFileRoute("/app/showcase")({
  head: () => ({
    meta: [
      { title: "Role Showcase — RADIX" },
      { name: "description", content: "Inspect and test each of the 5 AI microservices independently." },
    ],
  }),
  component: RoleShowcase,
});

type TabKey = "role1" | "role2" | "role3" | "role4" | "role5";

const TABS = [
  { key: "role1", label: "Role 1: JD Analytics", port: "8001", icon: FileText, tag: "Gemini + ChromaDB" },
  { key: "role2", label: "Role 2: Resume Parsing", port: "8002", icon: FileCheck2, tag: "Groq LLM" },
  { key: "role3", label: "Role 3: Profile Builder", port: "8003", icon: Database, tag: "Schema & DB" },
  { key: "role4", label: "Role 4: Talent Check", port: "8004", icon: Building2, tag: "Company Benchmarks" },
  { key: "role5", label: "Role 5: Skill Matching", port: "8005", icon: BrainCircuit, tag: "Scoring & Planning" },
] as const;

function RoleShowcase() {
  const [activeTab, setActiveTab] = useState<TabKey>("role1");
  const profile = getSavedProfile();

  // ── Role 1 State ──
  const [jdFile, setJdFile] = useState<File | null>(null);
  const [jdAnalysis, setJdAnalysis] = useState<JDAnalysis | null>(null);
  const [jdLoading, setJdLoading] = useState(false);
  const [jdError, setJdError] = useState("");
  const jdInputRef = useRef<HTMLInputElement>(null);

  // ── Role 2 State ──
  const [resumeFile, setResumeFile] = useState<File | null>(null);
  const [resumeExtract, setResumeExtract] = useState<ResumeExtract | null>(null);
  const [resumeLoading, setResumeLoading] = useState(false);
  const [resumeError, setResumeError] = useState("");
  const resumeInputRef = useRef<HTMLInputElement>(null);

  // ── Role 4 State ──
  const [companyQuery, setCompanyQuery] = useState("");
  const [companies, setCompanies] = useState<Company[]>([]);
  const [selectedCompany, setSelectedCompany] = useState<Company | null>(null);
  const [talentResult, setTalentResult] = useState<TalentCheckResult | null>(null);
  const [talentLoading, setTalentLoading] = useState(false);
  const [talentError, setTalentError] = useState("");

  // ── Role 5 State ──
  const [matchResult, setMatchResult] = useState<MatchResult | null>(null);
  const [matchPlan, setMatchPlan] = useState<ImprovementPlan | null>(null);
  const [matchLoading, setMatchLoading] = useState(false);
  const [matchError, setMatchError] = useState("");

  // Service readiness
  const isReady = (key: string) => !!SERVICES.find((s) => s.key === key)?.baseUrl;

  // Role 1 Run
  async function handleAnalyzeJD(f: File | undefined) {
    if (!f) return;
    setJdFile(f);
    setJdLoading(true);
    setJdError("");
    try {
      const { data } = await analyzeJD(f);
      setJdAnalysis(data);
    } catch (e) {
      setJdError((e as Error).message);
    } finally {
      setJdLoading(false);
    }
  }

  // Role 2 Run
  async function handleParseResume(f: File | undefined) {
    if (!f) return;
    setResumeFile(f);
    setResumeLoading(true);
    setResumeError("");
    try {
      const data = await parseResume(f);
      setResumeExtract(data);
    } catch (e) {
      setResumeError((e as Error).message);
    } finally {
      setResumeLoading(false);
    }
  }

  // Role 4 Search & Run
  async function handleSearchCompanies(q: string) {
    setCompanyQuery(q);
    if (!q.trim()) return;
    try {
      const res = await searchCompanies(q, 8);
      setCompanies(res.map((c: any) => ({
        id: c.id,
        name: c.company ?? c.name,
        industry: c.industry,
        description: c.description,
      })));
    } catch {
      setCompanies([]);
    }
  }

  async function handleRunTalentCheck(company: Company) {
    setSelectedCompany(company);
    setTalentLoading(true);
    setTalentError("");
    try {
      const candidatePayload = {
        full_name: profile.full_name,
        skills: profile.skills.map((s) => ({
          name: s.name,
          category: s.category,
          confidence: s.confidence,
          evidence: s.evidence ?? "",
        })),
      };
      const res = await runTalentCheck(company.id, candidatePayload as any);
      setTalentResult(res);
    } catch (e) {
      setTalentError((e as Error).message);
    } finally {
      setTalentLoading(false);
    }
  }

  // Role 5 Run
  async function handleRunMatch() {
    setMatchLoading(true);
    setMatchError("");
    try {
      const targetJD: JDAnalysis = jdAnalysis ?? {
        source_type: "jd",
        source_file: "demo_software_engineer.pdf",
        company: "Acme Cloud Corp",
        role: "Senior Backend Engineer",
        skills: [
          { skill_name: "Python", category_code: "COD", evidence: "5+ years backend Python development", confidence: "high" },
          { skill_name: "Docker", category_code: "CLOUD", evidence: "Containerization with Docker", confidence: "high" },
          { skill_name: "PostgreSQL", category_code: "SQL", evidence: "Relational database tuning & queries", confidence: "high" },
          { skill_name: "FastAPI", category_code: "SWE", evidence: "High performance REST API construction", confidence: "high" },
          { skill_name: "Kubernetes", category_code: "CLOUD", evidence: "Cluster orchestration and deployments", confidence: "medium" },
          { skill_name: "System Design", category_code: "SYSD", evidence: "Architecting high availability distributed systems", confidence: "high" },
        ],
      };

      const candidateSkills = profile.skills.map((s) => ({
        skill_name: s.name,
        category_code: s.category,
        evidence: s.evidence ?? "",
        confidence: s.confidence,
      }));

      const req = {
        candidate: { skills: candidateSkills },
        job_description: targetJD,
        talent_check: talentResult ?? null,
      };

      const [resMatch, resPlan] = await Promise.all([
        runMatch(req),
        getImprovementPlan(req),
      ]);
      setMatchResult(resMatch);
      setMatchPlan(resPlan);
    } catch (e) {
      setMatchError((e as Error).message);
    } finally {
      setMatchLoading(false);
    }
  }

  return (
    <div className="space-y-8 animate-page">
      <PageHeader
        eyebrow="Architecture & Microservices"
        title="Role Showcase & Services Lab"
      >
        <DemoTag>Live Microservice Inspection</DemoTag>
      </PageHeader>

      <p className="max-w-2xl text-sm text-muted-foreground -mt-4 leading-relaxed">
        Test and verify each of the 5 AI microservices independently. Inspect raw inputs,
        categorized skill extractions, vector indices, and match computations.
      </p>

      {/* Tabs */}
      <div className="flex flex-wrap gap-2 border-b border-border pb-4">
        {TABS.map((t) => {
          const Icon = t.icon;
          const active = activeTab === t.key;
          return (
            <button
              key={t.key}
              onClick={() => setActiveTab(t.key as TabKey)}
              className={cn(
                "flex items-center gap-2.5 rounded-xl border px-4 py-2.5 text-sm font-medium transition-all",
                active
                  ? "border-primary bg-primary text-primary-foreground shadow-sm"
                  : "border-border bg-card text-muted-foreground hover:bg-secondary hover:text-foreground"
              )}
            >
              <Icon className="h-4 w-4" />
              <span>{t.label}</span>
              <span className={cn("text-[11px] rounded-md px-1.5 py-0.5 font-semibold", active ? "bg-white/20 text-white" : "bg-secondary text-muted-foreground")}>
                {t.port}
              </span>
            </button>
          );
        })}
      </div>

      {/* ── TAB 1: Role 1 — JD Analytics ── */}
      {activeTab === "role1" && (
        <section className="surface p-8 space-y-6">
          <div className="flex flex-wrap items-center justify-between gap-4 border-b border-border pb-6">
            <div>
              <div className="flex items-center gap-2">
                <h2 className="text-xl font-semibold">Role 1: Job Description Analytics</h2>
                <span className="rounded-full bg-success/15 px-2.5 py-0.5 text-xs font-medium text-success">Port 8001</span>
              </div>
              <p className="mt-1 text-sm text-muted-foreground">
                Parses PDF/DOCX job postings with Gemini, categorizes required skills into 12 RADIX codes, and creates ChromaDB vector embeddings.
              </p>
            </div>
            <Button
              variant="outline"
              size="sm"
              onClick={() => jdInputRef.current?.click()}
              disabled={jdLoading}
            >
              {jdLoading ? <Loader2 className="h-4 w-4 animate-spin" /> : <UploadCloud className="h-4 w-4" />}
              {jdLoading ? "Analyzing with Gemini..." : "Upload JD (PDF/DOCX)"}
            </Button>
            <input
              ref={jdInputRef}
              type="file"
              accept=".pdf,.docx"
              className="hidden"
              onChange={(e) => void handleAnalyzeJD(e.target.files?.[0])}
            />
          </div>

          {jdError && (
            <div className="rounded-xl border border-destructive/30 bg-destructive/10 p-4 text-sm text-destructive">
              {jdError}
            </div>
          )}

          {jdAnalysis ? (
            <div className="space-y-6">
              <div className="flex flex-wrap items-center justify-between gap-3 rounded-xl bg-secondary/50 p-4">
                <div>
                  <h3 className="font-semibold text-lg">{jdAnalysis.role || "Role Extracted"}</h3>
                  <p className="text-sm text-muted-foreground">{jdAnalysis.company || "Company"} · Source: {jdAnalysis.source_file}</p>
                </div>
                <span className="rounded-full bg-primary/10 border border-primary/20 px-3 py-1 text-xs font-semibold text-primary">
                  {jdAnalysis.skills.length} Required Skills Extracted
                </span>
              </div>

              <div>
                <h4 className="text-xs font-semibold uppercase tracking-wider text-muted-foreground mb-3">Extracted Skill Requirements & Evidence</h4>
                <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-3">
                  {jdAnalysis.skills.map((s, idx) => (
                    <div key={`${s.skill_name}-${idx}`} className="rounded-xl border border-border bg-card p-3.5 space-y-2">
                      <div className="flex items-center justify-between">
                        <span className="font-semibold text-sm">{s.skill_name}</span>
                        <span className="rounded bg-secondary px-2 py-0.5 text-[10px] font-semibold text-muted-foreground">
                          {s.category_code}
                        </span>
                      </div>
                      <p className="text-xs text-muted-foreground italic line-clamp-2">
                        "{s.evidence || "No evidence quote"}"
                      </p>
                      <span className="inline-block text-[11px] font-medium text-primary">
                        {s.confidence} confidence
                      </span>
                    </div>
                  ))}
                </div>
              </div>
            </div>
          ) : (
            <div className="rounded-2xl border border-dashed border-border py-12 text-center">
              <FileText className="mx-auto h-10 w-10 text-muted-foreground/60" />
              <h3 className="mt-3 text-base font-semibold">Upload a Job Description to inspect Role 1</h3>
              <p className="mt-1 text-sm text-muted-foreground max-w-md mx-auto">
                Role 1 extracts skills, required proficiency levels, and evidence quotes from any PDF or DOCX file.
              </p>
              <Button className="mt-4" onClick={() => jdInputRef.current?.click()}>
                Choose JD File
              </Button>
            </div>
          )}
        </section>
      )}

      {/* ── TAB 2: Role 2 — Resume Parsing ── */}
      {activeTab === "role2" && (
        <section className="surface p-8 space-y-6">
          <div className="flex flex-wrap items-center justify-between gap-4 border-b border-border pb-6">
            <div>
              <div className="flex items-center gap-2">
                <h2 className="text-xl font-semibold">Role 2: Resume Parsing Service</h2>
                <span className="rounded-full bg-success/15 px-2.5 py-0.5 text-xs font-medium text-success">Port 8002</span>
              </div>
              <p className="mt-1 text-sm text-muted-foreground">
                Parses candidate resumes with Groq LLM and extracts verified technical skills, projects, and education.
              </p>
            </div>
            <Button
              variant="outline"
              size="sm"
              onClick={() => resumeInputRef.current?.click()}
              disabled={resumeLoading}
            >
              {resumeLoading ? <Loader2 className="h-4 w-4 animate-spin" /> : <UploadCloud className="h-4 w-4" />}
              {resumeLoading ? "Parsing with Groq..." : "Upload Resume (PDF/DOCX)"}
            </Button>
            <input
              ref={resumeInputRef}
              type="file"
              accept=".pdf,.docx"
              className="hidden"
              onChange={(e) => void handleParseResume(e.target.files?.[0])}
            />
          </div>

          {resumeError && (
            <div className="rounded-xl border border-destructive/30 bg-destructive/10 p-4 text-sm text-destructive">
              {resumeError}
            </div>
          )}

          {resumeExtract ? (
            <div className="space-y-6">
              <div className="rounded-xl bg-secondary/50 p-4 flex flex-wrap items-center justify-between">
                <div>
                  <h3 className="font-semibold">{resumeExtract.source_file}</h3>
                  <p className="text-xs text-muted-foreground">Parsed via Groq LLM · {resumeExtract.skills.length} skills identified</p>
                </div>
                {resumeExtract.education && (
                  <span className="text-xs rounded-md bg-card border border-border px-3 py-1 text-muted-foreground">
                    Education: <strong className="text-foreground">{resumeExtract.education}</strong>
                  </span>
                )}
              </div>

              <div>
                <h4 className="text-xs font-semibold uppercase tracking-wider text-muted-foreground mb-3">Extracted Skills Array</h4>
                <div className="flex flex-wrap gap-2">
                  {resumeExtract.skills.map((s, idx) => (
                    <div key={`${s.skill_name}-${idx}`} className="inline-flex items-center gap-2 rounded-xl border border-border bg-card px-3 py-1.5 text-sm">
                      <span className="font-medium">{s.skill_name}</span>
                      <span className="rounded bg-secondary px-1.5 py-0.5 text-[10px] font-semibold text-muted-foreground">
                        {CATEGORY_LABELS[s.category_code as SkillCategory] || s.category_code}
                      </span>
                    </div>
                  ))}
                </div>
              </div>

              {resumeExtract.projects.length > 0 && (
                <div>
                  <h4 className="text-xs font-semibold uppercase tracking-wider text-muted-foreground mb-3">Detected Projects</h4>
                  <ul className="space-y-1.5 text-sm text-muted-foreground">
                    {resumeExtract.projects.map((proj, idx) => (
                      <li key={idx} className="flex items-center gap-2">
                        <span className="h-1.5 w-1.5 rounded-full bg-primary" />
                        {proj}
                      </li>
                    ))}
                  </ul>
                </div>
              )}
            </div>
          ) : (
            <div className="rounded-2xl border border-dashed border-border py-12 text-center">
              <FileCheck2 className="mx-auto h-10 w-10 text-muted-foreground/60" />
              <h3 className="mt-3 text-base font-semibold">Upload a Resume to test Role 2</h3>
              <p className="mt-1 text-sm text-muted-foreground max-w-md mx-auto">
                Role 2 processes the document and converts candidate experience into normalized skill tokens.
              </p>
              <Button className="mt-4" onClick={() => resumeInputRef.current?.click()}>
                Choose Resume File
              </Button>
            </div>
          )}
        </section>
      )}

      {/* ── TAB 3: Role 3 — Profile Builder ── */}
      {activeTab === "role3" && (
        <section className="surface p-8 space-y-6">
          <div className="flex flex-wrap items-center justify-between gap-4 border-b border-border pb-6">
            <div>
              <div className="flex items-center gap-2">
                <h2 className="text-xl font-semibold">Role 3: Profile Builder Service</h2>
                <span className="rounded-full bg-success/15 px-2.5 py-0.5 text-xs font-medium text-success">Port 8003</span>
              </div>
              <p className="mt-1 text-sm text-muted-foreground">
                Maintains the canonical candidate profile, calculates completeness scoring, and manages data persistence.
              </p>
            </div>
          </div>

          <div className="grid gap-6 md:grid-cols-2">
            <div className="rounded-xl border border-border p-5 space-y-4">
              <h3 className="font-semibold text-base">Active Candidate Profile Record</h3>
              <div className="space-y-2 text-sm">
                <div className="flex justify-between py-1 border-b border-border">
                  <span className="text-muted-foreground">Full Name</span>
                  <span className="font-medium">{profile.full_name}</span>
                </div>
                <div className="flex justify-between py-1 border-b border-border">
                  <span className="text-muted-foreground">Profile ID</span>
                  <code className="text-xs">{profile.profile_id}</code>
                </div>
                <div className="flex justify-between py-1 border-b border-border">
                  <span className="text-muted-foreground">Total Skills Stored</span>
                  <span className="font-medium">{profile.skills.length} skills</span>
                </div>
                <div className="flex justify-between py-1 border-b border-border">
                  <span className="text-muted-foreground">Headline</span>
                  <span>{profile.headline || "Candidate Profile"}</span>
                </div>
              </div>
            </div>

            <div className="rounded-xl border border-border p-5 space-y-4">
              <h3 className="font-semibold text-base">Category Breakdown</h3>
              <div className="flex flex-wrap gap-2">
                {Object.entries(
                  profile.skills.reduce((acc, s) => {
                    acc[s.category] = (acc[s.category] || 0) + 1;
                    return acc;
                  }, {} as Record<string, number>)
                ).map(([cat, count]) => (
                  <span key={cat} className="inline-flex items-center gap-1.5 rounded-lg bg-secondary px-3 py-1.5 text-xs font-medium">
                    <span>{CATEGORY_LABELS[cat as SkillCategory] || cat}</span>
                    <span className="rounded-full bg-card px-1.5 py-0.5 text-[10px] font-bold text-foreground">
                      {count}
                    </span>
                  </span>
                ))}
              </div>
            </div>
          </div>
        </section>
      )}

      {/* ── TAB 4: Role 4 — Talent Check ── */}
      {activeTab === "role4" && (
        <section className="surface p-8 space-y-6">
          <div className="flex flex-wrap items-center justify-between gap-4 border-b border-border pb-6">
            <div>
              <div className="flex items-center gap-2">
                <h2 className="text-xl font-semibold">Role 4: Talent Check Benchmark Service</h2>
                <span className="rounded-full bg-success/15 px-2.5 py-0.5 text-xs font-medium text-success">Port 8004</span>
              </div>
              <p className="mt-1 text-sm text-muted-foreground">
                Evaluates candidate skill evidence against verified company hiring bars and cultural rubrics.
              </p>
            </div>
          </div>

          <div className="space-y-4">
            <label className="block text-sm font-medium">Search Company Database:</label>
            <div className="relative max-w-md">
              <Search className="absolute left-3.5 top-1/2 -translate-y-1/2 h-4 w-4 text-muted-foreground" />
              <input
                value={companyQuery}
                onChange={(e) => void handleSearchCompanies(e.target.value)}
                placeholder="Type 'Google', 'Amazon', 'Stripe', etc..."
                className="h-10 w-full rounded-xl border border-input bg-card pl-10 pr-4 text-sm outline-none focus:ring-2 focus:ring-ring"
              />
            </div>

            {companies.length > 0 && (
              <div className="grid gap-2 sm:grid-cols-2 md:grid-cols-3 max-w-2xl pt-2">
                {companies.map((c) => (
                  <button
                    key={c.id}
                    onClick={() => void handleRunTalentCheck(c)}
                    className={cn(
                      "flex items-center justify-between rounded-xl border p-3 text-left transition-colors",
                      selectedCompany?.id === c.id ? "border-primary bg-primary/10" : "border-border hover:bg-secondary"
                    )}
                  >
                    <div>
                      <p className="text-sm font-semibold">{c.name}</p>
                      <p className="text-xs text-muted-foreground">{c.industry || "Technology"}</p>
                    </div>
                    <ArrowRight className="h-4 w-4 text-muted-foreground" />
                  </button>
                ))}
              </div>
            )}

            {talentLoading && (
              <div className="flex items-center gap-2 py-6 text-sm text-muted-foreground">
                <Loader2 className="h-4 w-4 animate-spin text-primary" />
                Evaluating {profile.full_name} against {selectedCompany?.name}'s hiring bar...
              </div>
            )}

            {talentResult && selectedCompany && !talentLoading && (
              <div className="mt-6 rounded-2xl border border-success/30 bg-success/10 p-6 space-y-4">
                <div className="flex items-center justify-between">
                  <h3 className="font-semibold text-lg">{selectedCompany.name} Talent Check Result</h3>
                  <span className="rounded-full bg-success/20 px-3 py-1 text-xs font-semibold text-success">
                    Evaluated Successfully
                  </span>
                </div>
                <div className="grid gap-4 sm:grid-cols-3 text-sm">
                  <div className="rounded-xl bg-card/80 p-3">
                    <p className="text-xs text-muted-foreground">Assessment Status</p>
                    <p className="font-semibold text-foreground mt-1 capitalize">{talentResult.status || "Passed benchmark"}</p>
                  </div>
                  <div className="rounded-xl bg-card/80 p-3 sm:col-span-2">
                    <p className="text-xs text-muted-foreground">Readiness Assessment</p>
                    <p className="text-xs text-foreground mt-1 leading-relaxed">
                      Candidate skills demonstrate alignment with {selectedCompany.name}'s technical profile.
                    </p>
                  </div>
                </div>
              </div>
            )}
          </div>
        </section>
      )}

      {/* ── TAB 5: Role 5 — Skill Matching ── */}
      {activeTab === "role5" && (
        <section className="surface p-8 space-y-6">
          <div className="flex flex-wrap items-center justify-between gap-4 border-b border-border pb-6">
            <div>
              <div className="flex items-center gap-2">
                <h2 className="text-xl font-semibold">Role 5: Skill Matching & Improvement Planner</h2>
                <span className="rounded-full bg-success/15 px-2.5 py-0.5 text-xs font-medium text-success">Port 8005</span>
              </div>
              <p className="mt-1 text-sm text-muted-foreground">
                Compares Candidate Profile vs. Job Requirements, calculates gap matrices, and generates actionable learning steps.
              </p>
            </div>
            <Button
              onClick={() => void handleRunMatch()}
              disabled={matchLoading}
              className="gap-2"
            >
              {matchLoading ? <Loader2 className="h-4 w-4 animate-spin" /> : <BrainCircuit className="h-4 w-4" />}
              {matchLoading ? "Running Matching Engine..." : "Run Live Match"}
            </Button>
          </div>

          {matchError && (
            <div className="rounded-xl border border-destructive/30 bg-destructive/10 p-4 text-sm text-destructive">
              {matchError}
            </div>
          )}

          {matchResult ? (
            <div className="space-y-6">
              <div className="flex flex-col sm:flex-row sm:items-center gap-6 rounded-2xl bg-secondary/50 p-6">
                <div className="flex items-baseline gap-1 tabular-nums shrink-0">
                  <span className="font-display text-4xl md:text-5xl font-semibold tracking-tight text-foreground">
                    {matchResult.match_score}
                  </span>
                  <span className="text-sm font-medium text-muted-foreground">/100</span>
                </div>
                <div className="border-t sm:border-t-0 sm:border-l border-border/60 pt-4 sm:pt-0 sm:pl-6">
                  <h3 className="text-xl font-semibold">{matchResult.role || "Target Role"}</h3>
                  <p className="text-sm text-muted-foreground">{matchResult.company}</p>
                  <p className="mt-2 text-sm leading-relaxed max-w-lg text-muted-foreground">{matchResult.summary}</p>
                </div>
              </div>

              <div className="grid gap-6 md:grid-cols-2">
                <div className="rounded-xl border border-border p-4">
                  <h4 className="font-semibold text-sm text-success mb-3">Matched Skills ({matchResult.matched_skills.length})</h4>
                  <div className="flex flex-wrap gap-1.5">
                    {matchResult.matched_skills.map((s) => (
                      <span key={s.skill} className="rounded-md bg-success/10 border border-success/20 px-2.5 py-1 text-xs font-medium text-success">
                        ✓ {s.skill}
                      </span>
                    ))}
                  </div>
                </div>

                <div className="rounded-xl border border-border p-4">
                  <h4 className="font-semibold text-sm text-destructive mb-3">Missing Skills & Gaps ({matchResult.missing_skills.length})</h4>
                  <div className="flex flex-wrap gap-1.5">
                    {matchResult.missing_skills.map((s) => (
                      <span key={s.skill} className="rounded-md bg-destructive/10 border border-destructive/20 px-2.5 py-1 text-xs font-medium text-destructive">
                        ✕ {s.skill} {s.critical_gap && "(Critical)"}
                      </span>
                    ))}
                  </div>
                </div>
              </div>

              {matchPlan && matchPlan.actions && (
                <div className="rounded-xl border border-border p-5">
                  <h4 className="font-semibold text-sm mb-3">Prioritized Learning Action Plan (from Role 5)</h4>
                  <div className="space-y-3">
                    {matchPlan.actions.map((act, i) => (
                      <div key={i} className="flex items-start gap-3 rounded-lg bg-card p-3 border border-border/80 text-sm">
                        <span className="flex h-6 w-6 shrink-0 items-center justify-center rounded-full bg-primary/10 text-xs font-bold text-primary">
                          {i + 1}
                        </span>
                        <div>
                          <p className="font-semibold">{act.skill} · <span className="text-success">+{act.score_gain} score gain</span></p>
                          <p className="text-xs text-muted-foreground mt-0.5">{act.why}</p>
                        </div>
                      </div>
                    ))}
                  </div>
                </div>
              )}
            </div>
          ) : (
            <div className="rounded-2xl border border-dashed border-border py-12 text-center">
              <BrainCircuit className="mx-auto h-10 w-10 text-muted-foreground/60" />
              <h3 className="mt-3 text-base font-semibold">Ready to test Role 5</h3>
              <p className="mt-1 text-sm text-muted-foreground max-w-md mx-auto">
                Click "Run Live Match" above to execute the matching algorithm between the active candidate and target job description.
              </p>
            </div>
          )}
        </section>
      )}
    </div>
  );
}
