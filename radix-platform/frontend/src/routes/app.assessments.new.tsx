import { createFileRoute, Link, useNavigate } from "@tanstack/react-router";
import { useRef, useState, useEffect } from "react";
import { Check, FileText, Loader2, UploadCloud, UserCheck, ArrowRight, FileUp } from "lucide-react";
import { Button } from "@/components/ui/button";
import { PageHeader } from "@/components/radix/ui";
import { getSavedProfile, hasSavedProfile, setLatestLiveAssessment } from "@/lib/radix/session";
import {
  analyzeJD,
  runMatch,
  getImprovementPlan,
  SERVICES,
  type JDAnalysis,
  type MatchRequest,
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

  // Run match
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
        talent_check: null,
      };
      const [match, plan] = await Promise.all([
        runMatch(req),
        getImprovementPlan(req),
      ]);
      const record: AssessmentRecord = {
        id: `live-${Date.now()}`,
        role: jdResult.role ?? "Unknown role",
        company: jdResult.company ?? "Unknown company",
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
                  <span className="inline-flex items-center gap-1 rounded-full bg-primary/15 px-2 py-0.5 text-xs font-medium text-primary">
                    <UserCheck className="h-3 w-3" /> Custom
                  </span>
                )}
              </div>
              <p className="text-xs text-muted-foreground">
                {activeProfile.headline || "Verified resume candidate profile"}
              </p>
              <div className="mt-3 flex flex-wrap gap-1">
                {activeProfile.skills.slice(0, 4).map((s) => (
                  <span key={s.name} className="rounded bg-secondary px-2 py-0.5 text-xs">
                    {s.name}
                  </span>
                ))}
                {activeProfile.skills.length > 4 && (
                  <span className="text-xs text-muted-foreground">
                    +{activeProfile.skills.length - 4} more
                  </span>
                )}
              </div>
            </div>
            <div
              className={cn(
                "flex h-6 w-6 items-center justify-center rounded-full border",
                profileSelected ? "border-primary bg-primary text-primary-foreground" : "border-muted"
              )}
            >
              {profileSelected && <Check className="h-3.5 w-3.5" />}
            </div>
          </button>
        </section>

        {/* Step 2 — JD */}
        <section className="surface p-8">
          <p className="text-sm text-muted-foreground">Step 2</p>
          <h2 className="font-display mt-1 text-xl">Job description</h2>
          <button
            onClick={() => fileInput.current?.click()}
            disabled={!jdServiceReady || uploadState === "uploading"}
            className={cn(
              "mt-6 flex w-full flex-col items-center justify-center rounded-2xl border border-dashed p-8 text-center transition-colors",
              uploadState === "done"
                ? "border-primary bg-primary/10"
                : "border-border hover:bg-accent/40",
              !jdServiceReady && "opacity-50 cursor-not-allowed"
            )}
          >
            <div className="flex h-12 w-12 items-center justify-center rounded-full bg-secondary">
              {uploadState === "uploading" ? (
                <Loader2 className="h-6 w-6 animate-spin text-muted-foreground" />
              ) : uploadState === "done" ? (
                <FileText className="h-6 w-6 text-primary" />
              ) : (
                <UploadCloud className="h-6 w-6 text-muted-foreground" />
              )}
            </div>
            <p className="mt-4 font-medium">
              {file ? file.name : "Upload JD (PDF or DOCX)"}
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

      {/* Action Section */}
      <div className="surface mt-6 p-8">
        <div className="flex flex-col gap-4 sm:flex-row sm:items-center sm:justify-between">
          <div>
            <h3 className="text-base font-semibold">Ready to evaluate</h3>
            <p className="mt-1 text-xs text-muted-foreground">
              {ready
                ? "Profile and job description ready for deterministic skill match."
                : `To continue, ${missing}.`}
            </p>
            {runState === "error" && (
              <p className="mt-2 text-xs text-destructive">{runErr}</p>
            )}
          </div>

          <Button
            size="lg"
            disabled={!ready || runState === "running"}
            onClick={() => void runAssessment()}
          >
            {runState === "running" && <Loader2 className="mr-2 h-4 w-4 animate-spin" />}
            {runState === "running" ? "Running…" : "Run skill match"}
          </Button>
        </div>
      </div>
    </div>
  );
}
