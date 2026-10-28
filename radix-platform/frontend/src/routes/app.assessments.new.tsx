import { createFileRoute, Link, useNavigate } from "@tanstack/react-router";
import { useRef, useState, useEffect, useCallback } from "react";
import { Check, FileText, Loader2, UploadCloud, Building2, Search, X, UserCheck } from "lucide-react";
import { Button } from "@/components/ui/button";
import { PageHeader } from "@/components/radix/ui";
import { getSavedProfile, hasSavedProfile, setLatestLiveAssessment } from "@/lib/radix/session";
import {
  analyzeJD,
  runMatch,
  getImprovementPlan,
  searchCompanies,
  runTalentCheck,
  SERVICES,
  type JDAnalysis,
  type MatchRequest,
  type Company,
  type TalentCheckResult,
} from "@/lib/radix/services";
import type { AssessmentRecord, CandidateProfile } from "@/lib/radix/contracts";
import { cn } from "@/lib/utils";

export const Route = createFileRoute("/app/assessments/new")({
  head: () => ({
    meta: [
      { title: "New assessment — RADIX" },
      { name: "description", content: "Compare a candidate profile with a job description." },
      { property: "og:title", content: "New assessment — RADIX" },
      { property: "og:description", content: "Run a new skill match." },
    ],
  }),
  component: NewAssessment,
});

type UploadState = "idle" | "uploading" | "done" | "error";
type RunState = "idle" | "running" | "done" | "error";

// ─── Company Picker Component ──────────────────────────────────────────────────
function CompanyPicker({
  selected,
  onSelect,
}: {
  selected: Company | null;
  onSelect: (c: Company | null) => void;
}) {
  const [query, setQuery] = useState("");
  const [results, setResults] = useState<Company[]>([]);
  const [loading, setLoading] = useState(false);
  const [open, setOpen] = useState(false);
  const debounceRef = useRef<ReturnType<typeof setTimeout> | null>(null);
  const talentServiceReady = !!SERVICES.find((s) => s.key === "talent")?.baseUrl;

  const doSearch = useCallback(async (q: string) => {
    if (!talentServiceReady) return;
    setLoading(true);
    try {
      const data = await searchCompanies(q, 12);
      setResults(
        data.map((c: any) => ({
          id: c.id,
          name: c.company ?? c.name,
          industry: c.industry,
          description: c.description,
        }))
      );
    } catch {
      setResults([]);
    } finally {
      setLoading(false);
    }
  }, [talentServiceReady]);

  useEffect(() => {
    if (!open) return;
    if (debounceRef.current) clearTimeout(debounceRef.current);
    debounceRef.current = setTimeout(() => void doSearch(query), 300);
    return () => { if (debounceRef.current) clearTimeout(debounceRef.current); };
  }, [query, open, doSearch]);

  useEffect(() => {
    if (open) void doSearch(query);
  }, [open, doSearch]);

  if (!talentServiceReady) {
    return (
      <p className="mt-3 text-xs text-muted-foreground">
        Set <code>VITE_TALENT_API_URL</code> in <code>.env</code> to enable company search.
      </p>
    );
  }

  if (selected) {
    return (
      <div className="mt-3 flex items-center justify-between rounded-xl border border-primary/40 bg-primary/10 px-4 py-3">
        <div className="flex items-center gap-3">
          <Building2 className="h-4 w-4 text-primary" />
          <span className="text-sm font-medium">{selected.name}</span>
        </div>
        <button
          onClick={() => onSelect(null)}
          className="rounded p-1 text-muted-foreground hover:text-foreground"
          aria-label="Clear company"
        >
          <X className="h-4 w-4" />
        </button>
      </div>
    );
  }

  return (
    <div className="relative mt-3">
      <button
        onClick={() => setOpen((v) => !v)}
        className="flex w-full items-center gap-2 rounded-xl border border-input bg-background px-4 py-3 text-left text-sm transition-colors hover:border-primary hover:bg-primary/5"
      >
        <Search className="h-4 w-4 text-muted-foreground" />
        <span className="text-muted-foreground">Search company…</span>
      </button>

      {open && (
        <div className="absolute z-50 mt-1 w-full rounded-xl border border-border bg-popover shadow-lg">
          <div className="flex items-center gap-2 border-b border-border px-3 py-2">
            <Search className="h-4 w-4 shrink-0 text-muted-foreground" />
            <input
              autoFocus
              value={query}
              onChange={(e) => setQuery(e.target.value)}
              placeholder="Type to filter…"
              className="w-full bg-transparent text-sm outline-none placeholder:text-muted-foreground"
            />
            {loading && <Loader2 className="h-4 w-4 animate-spin text-muted-foreground" />}
          </div>
          <ul className="max-h-52 overflow-y-auto py-1">
            {results.length === 0 && !loading && (
              <li className="px-4 py-3 text-sm text-muted-foreground">No companies found.</li>
            )}
            {results.map((c) => (
              <li key={c.id}>
                <button
                  className="flex w-full items-center gap-3 px-4 py-2.5 text-left text-sm hover:bg-accent"
                  onClick={() => {
                    onSelect(c);
                    setOpen(false);
                    setQuery("");
                  }}
                >
                  <Building2 className="h-4 w-4 shrink-0 text-muted-foreground" />
                  <span className="font-medium">{c.name}</span>
                  {c.industry && (
                    <span className="ml-auto text-xs text-muted-foreground">{c.industry}</span>
                  )}
                </button>
              </li>
            ))}
          </ul>
          <div className="border-t border-border px-3 py-2 text-right">
            <button
              onClick={() => setOpen(false)}
              className="text-xs text-muted-foreground hover:text-foreground"
            >
              Close
            </button>
          </div>
        </div>
      )}
    </div>
  );
}

// ─── Main Page ─────────────────────────────────────────────────────────────────

function NewAssessment() {
  const navigate = useNavigate();

  // Active profile
  const [activeProfile, setActiveProfile] = useState<CandidateProfile | null>(getSavedProfile());

  // Step 1 — Profile Selection (default to true if profile is loaded)
  const [profileSelected, setProfileSelected] = useState(true);

  // Step 2 — JD
  const [file, setFile] = useState<File | null>(null);
  const [jdResult, setJdResult] = useState<JDAnalysis | null>(null);
  const [uploadState, setUploadState] = useState<UploadState>("idle");
  const [uploadErr, setUploadErr] = useState("");
  const fileInput = useRef<HTMLInputElement>(null);

  // Step 3 — Talent Check options
  const [includeTalentCheck, setIncludeTalentCheck] = useState(false);
  const [selectedCompany, setSelectedCompany] = useState<Company | null>(null);
  const [talentResult, setTalentResult] = useState<TalentCheckResult | null>(null);
  const [talentState, setTalentState] = useState<"idle" | "running" | "done" | "error">("idle");
  const [talentErr, setTalentErr] = useState("");

  const talentServiceReady = !!SERVICES.find((s) => s.key === "talent")?.baseUrl;

  // Step 4 — Run match
  const [runState, setRunState] = useState<RunState>("idle");
  const [runErr, setRunErr] = useState("");

  const jdServiceReady = !!SERVICES.find((s) => s.key === "jd")?.baseUrl;
  const matchServiceReady = !!SERVICES.find((s) => s.key === "match")?.baseUrl;

  useEffect(() => {
    setActiveProfile(getSavedProfile());
  }, []);

  if (!activeProfile) {
    return (
      <div className="py-12 animate-page">
        <div className="surface max-w-xl mx-auto p-10 text-center rounded-2xl border border-border">
          <div className="mx-auto flex h-14 w-14 items-center justify-center rounded-full bg-primary/10 text-primary">
            <FileUp className="h-7 w-7" />
          </div>
          <h2 className="font-display mt-6 text-2xl font-semibold">Resume required</h2>
          <p className="mt-2 text-sm text-muted-foreground leading-relaxed">
            Please import your resume first before creating an assessment so your skills can be matched.
          </p>
          <div className="mt-8 flex justify-center">
            <Button asChild size="lg">
              <Link to="/onboarding">Import your resume <ArrowRight className="ml-2 h-4 w-4" /></Link>
            </Button>
          </div>
        </div>
      </div>
    );
  }
  const isCustomProfile = hasSavedProfile();

  async function pickFile(f: File | undefined) {
    if (!f) return;
    if (!/\.(pdf|docx)$/i.test(f.name)) {
      setUploadErr("Please choose a PDF or DOCX file.");
      setUploadState("error");
      return;
    }
    setFile(f);
    setUploadState("uploading");
    setUploadErr("");
    setJdResult(null);
    try {
      const { data } = await analyzeJD(f);
      setJdResult(data);
      setUploadState("done");
    } catch (e) {
      setUploadErr((e as Error).message);
      setUploadState("error");
    }
  }

  // Run talent check against active candidate profile
  async function fetchTalentCheck(company: Company) {
    if (!talentServiceReady) return;
    setTalentState("running");
    setTalentErr("");
    try {
      const result = await runTalentCheck(company.id, {
        full_name: activeProfile.full_name,
        name: activeProfile.full_name,
        skills: activeProfile.skills.map((s) => ({
          name: s.name,
          skill_name: s.name,
          category: s.category,
          category_code: s.category,
          confidence: s.confidence,
          evidence: s.evidence ?? "",
        })),
        // Role 4 also scores these (projects +1, experience/internships +1.5, certifications +1 evidence points).
        // Sending only skills understated readiness by ~10-19 points.
        projects: activeProfile?.projects ?? [],
        experience: activeProfile?.experience ?? [],
        certifications: activeProfile?.certifications ?? [],
      } as any);
      setTalentResult(result);
      setTalentState("done");
    } catch (e) {
      setTalentErr((e as Error).message);
      setTalentState("error");
      setTalentResult(null);
    }
  }

  function handleCompanySelect(company: Company | null) {
    setSelectedCompany(company);
    setTalentResult(null);
    setTalentState("idle");
    setTalentErr("");
    if (company && includeTalentCheck) void fetchTalentCheck(company);
  }

  function handleToggleTalentCheck(checked: boolean) {
    setIncludeTalentCheck(checked);
    if (!checked) {
      setSelectedCompany(null);
      setTalentResult(null);
      setTalentState("idle");
    } else if (selectedCompany) {
      void fetchTalentCheck(selectedCompany);
    }
  }

  async function runAssessment() {
    if (!jdResult || !profileSelected) return;
    setRunState("running");
    setRunErr("");
    try {
      const candidateSkills = activeProfile.skills.map((s) => ({
        skill_name: s.name,
        category_code: s.category,
        evidence: s.evidence ?? "",
        confidence: s.confidence,
      }));
      const req: MatchRequest = {
        candidate: { skills: candidateSkills },
        job_description: jdResult,
        talent_check: includeTalentCheck ? (talentResult ?? null) : null,
      };
      const [match, plan] = await Promise.all([
        runMatch(req),
        getImprovementPlan(req),
      ]);
      const record: AssessmentRecord = {
        id: `live-${Date.now()}`,
        role: jdResult.role ?? "Unknown role",
        company: selectedCompany?.name ?? jdResult.company ?? "Unknown company",
        jd_file: jdResult.source_file,
        updated_at: new Date().toISOString().slice(0, 10),
        status: "complete",
        match,
        plan,
      };
      setLatestLiveAssessment(record);
      setRunState("done");
      await navigate({ to: "/app/assessments/$assessmentId", params: { assessmentId: record.id } });
    } catch (e) {
      setRunErr((e as Error).message);
      setRunState("error");
    }
  }

  const ready = profileSelected && uploadState === "done" && matchServiceReady;
  const missing = [
    !profileSelected && "choose a profile",
    uploadState !== "done" && "analyse a job description",
    !matchServiceReady && "configure VITE_MATCH_API_URL",
  ].filter(Boolean).join(", ");

  return (
    <div>
      <PageHeader eyebrow="New assessment" title="Two inputs. One clear picture." />

      {/* Service warnings */}
      {!jdServiceReady && (
        <div className="mb-6 rounded-2xl border border-warning/30 bg-warning/10 p-4 text-sm text-warning">
          JD Analytics (Role 1) is not configured — set <code>VITE_JD_API_URL</code> in{" "}
          <code>.env</code>.
        </div>
      )}
      {!matchServiceReady && (
        <div className="mb-6 rounded-2xl border border-warning/30 bg-warning/10 p-4 text-sm text-warning">
          Skill Matching (Role 5) is not configured — set <code>VITE_MATCH_API_URL</code> in{" "}
          <code>.env</code>.
        </div>
      )}

      <div className="grid gap-6 md:grid-cols-2">
        {/* Step 1 — Profile */}
        <section className="surface p-8">
          <p className="text-sm text-muted-foreground">Step 1</p>
          <h2 className="font-display mt-1 text-xl">Candidate profile</h2>
          <button
            onClick={() => setProfileSelected((v) => !v)}
            className={cn(
              "mt-6 flex w-full items-center justify-between rounded-2xl border p-5 text-left transition-colors",
              profileSelected ? "border-primary bg-primary/10" : "border-border hover:bg-accent/40"
            )}
          >
            <div>
              <div className="flex items-center gap-2">
                <p className="font-medium">{activeProfile.full_name}</p>
                {isCustomProfile && (
                  <span className="rounded-full bg-success/20 px-2 py-0.5 text-xs text-success font-medium">
                    From resume
                  </span>
                )}
              </div>
              <p className="text-sm text-muted-foreground mt-0.5">
                {activeProfile.skills.length} skills · {isCustomProfile ? "active profile" : "demo profile"}
              </p>
            </div>
            {profileSelected && <Check className="h-5 w-5 text-primary" />}
          </button>

          {/* Candidate skill preview chips */}
          {activeProfile.skills.length > 0 && (
            <div className="mt-3 flex flex-wrap gap-1.5 max-h-36 overflow-y-auto rounded-xl border border-border/60 bg-secondary/30 p-2.5">
              {activeProfile.skills.map((s, i) => (
                <span
                  key={`${s.name}-${i}`}
                  className="inline-flex items-center gap-1 rounded-md border border-border bg-card px-2 py-0.5 text-xs text-foreground"
                >
                  {s.name}
                  <span className="rounded bg-secondary px-1 text-[9px] font-semibold text-muted-foreground">
                    {s.category}
                  </span>
                </span>
              ))}
            </div>
          )}
          <div className="mt-4 flex items-center justify-between text-sm">
            <Link to="/onboarding" className="text-primary hover:underline">
              Import a different resume
            </Link>

          </div>
          <p className="mt-6 text-xs text-muted-foreground">
            Your email is never sent to the matching service.
          </p>
        </section>

        {/* Step 2 — JD upload */}
        <section className="surface p-8">
          <p className="text-sm text-muted-foreground">Step 2</p>
          <h2 className="font-display mt-1 text-xl">Job description</h2>
          <button
            onClick={() => fileInput.current?.click()}
            onDragOver={(e) => e.preventDefault()}
            onDrop={(e) => { e.preventDefault(); void pickFile(e.dataTransfer.files[0]); }}
            className="mt-6 flex w-full flex-col items-center rounded-2xl border border-dashed border-input p-8 text-center transition-colors hover:border-primary hover:bg-primary/5"
          >
            {uploadState === "uploading"
              ? <Loader2 className="h-8 w-8 animate-spin text-primary" />
              : uploadState === "done"
              ? <FileText className="h-8 w-8 text-primary" />
              : <UploadCloud className="h-8 w-8 text-primary" />}
            <p className="mt-3 font-medium">
              {file ? file.name : "Drop a PDF or DOCX"}
            </p>
            <p className="mt-1 text-xs text-muted-foreground">
              {uploadState === "uploading"
                ? "Uploading → Role 1 extracting requirements with Gemini…"
                : "Scanned image-only PDFs aren't supported."}
            </p>
          </button>
          <input
            ref={fileInput}
            type="file"
            accept=".pdf,.docx"
            className="hidden"
            onChange={(e) => void pickFile(e.target.files?.[0])}
          />
          {uploadState === "done" && jdResult && (
            <div className="mt-4 rounded-xl border border-success/30 bg-success/10 p-4 text-sm">
              <div className="flex items-center justify-between">
                <p className="font-semibold text-success">
                  Extracted {jdResult.skills.length} skills from JD
                </p>
                {jdResult.role && (
                  <span className="rounded-md bg-secondary/80 px-2 py-0.5 text-xs font-medium text-foreground">
                    {jdResult.role} {jdResult.company ? `· ${jdResult.company}` : ""}
                  </span>
                )}
              </div>
              <div className="mt-3 flex flex-wrap gap-1.5 max-h-36 overflow-y-auto pt-1">
                {jdResult.skills.map((s, i) => (
                  <span
                    key={`${s.skill_name}-${i}`}
                    className="inline-flex items-center gap-1.5 rounded-lg border border-border bg-card px-2.5 py-1 text-xs font-medium"
                  >
                    <span>{s.skill_name}</span>
                    <span className="rounded bg-secondary px-1 text-[10px] text-muted-foreground font-semibold">
                      {s.category_code}
                    </span>
                  </span>
                ))}
              </div>
            </div>
          )}
          {uploadState === "error" && (
            <p className="mt-4 rounded-xl border border-destructive/30 bg-destructive/10 p-3 text-sm text-destructive">
              {uploadErr}
            </p>
          )}
        </section>
      </div>

      {/* Step 3 — Talent Check Options */}
      <div className="surface mt-6 p-8">
        <div className="flex flex-col gap-5 md:flex-row md:items-start md:justify-between">
          <div className="flex-1">
            <label className="flex cursor-pointer items-center gap-3 text-sm font-medium">
              <input
                type="checkbox"
                checked={includeTalentCheck}
                onChange={(e) => handleToggleTalentCheck(e.target.checked)}
                disabled={!talentServiceReady}
                className="h-4 w-4 accent-primary"
              />
              <Building2 className="h-4 w-4 text-primary" />
              Include Talent Check context
              {!talentServiceReady && (
                <span className="text-muted-foreground font-normal">
                  (set <code className="text-xs">VITE_TALENT_API_URL</code> to enable)
                </span>
              )}
            </label>

            {/* Company Picker — shown when toggle is ON */}
            {includeTalentCheck && (
              <div className="mt-4 pl-7">
                <p className="text-xs text-muted-foreground mb-1">
                  Select a company to run a readiness check against its skill benchmarks.
                </p>
                <CompanyPicker
                  selected={selectedCompany}
                  onSelect={handleCompanySelect}
                />

                {/* Talent check status */}
                {selectedCompany && talentState === "running" && (
                  <div className="mt-3 flex items-center gap-2 text-xs text-muted-foreground">
                    <Loader2 className="h-3 w-3 animate-spin" />
                    Running talent check against {selectedCompany.name}…
                  </div>
                )}
                {selectedCompany && talentState === "done" && talentResult && (
                  <div className="mt-3 rounded-xl border border-success/30 bg-success/10 p-3 text-sm">
                    <p className="font-medium text-success">
                      Readiness score: {talentResult.readiness_score}% — {talentResult.verdict}
                    </p>
                    {Array.isArray(talentResult.critical_gaps) && talentResult.critical_gaps.length > 0 && (
                      <p className="mt-1 text-xs text-muted-foreground">
                        Critical gaps: {talentResult.critical_gaps.slice(0, 3).join(", ")}
                        {talentResult.critical_gaps.length > 3 && ` +${talentResult.critical_gaps.length - 3} more`}
                      </p>
                    )}
                    {Array.isArray(talentResult.focus_areas) && talentResult.focus_areas.length > 0 && (
                      <p className="mt-1 text-xs text-muted-foreground">
                        Focus areas: {talentResult.focus_areas.slice(0, 3).join(", ")}
                      </p>
                    )}
                  </div>
                )}
                {talentState === "error" && (
                  <p className="mt-3 rounded-xl border border-destructive/30 bg-destructive/10 p-3 text-xs text-destructive">
                    Talent check failed: {talentErr}
                  </p>
                )}
              </div>
            )}
          </div>

          {/* Run button */}
          <div className="flex flex-col items-start gap-2 md:items-end">
            {runState === "error" && (
              <p className="text-xs text-destructive max-w-xs text-right">{runErr}</p>
            )}
            <Button
              size="lg"
              disabled={!ready || runState === "running"}
              onClick={() => void runAssessment()}
            >
              {runState === "running" && <Loader2 className="mr-2 h-4 w-4 animate-spin" />}
              {runState === "running" ? "Running…" : "Run skill match"}
            </Button>
            {!ready && runState !== "running" && (
              <p className="text-xs text-muted-foreground">To continue, {missing}.</p>
            )}
          </div>
        </div>
      </div>
    </div>
  );
}
