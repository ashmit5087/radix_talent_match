import { createFileRoute, Link } from "@tanstack/react-router";
import { useState, useEffect } from "react";
import { ArrowRight, ArrowUpRight, FileUp } from "lucide-react";
import { Button } from "@/components/ui/button";
import { LevelBar } from "@/components/radix/ui";
import { getSavedProfile, getLatestLiveAssessment, hasSavedProfile, getSavedAssessments } from "@/lib/radix/session";
import type { CandidateProfile, AssessmentRecord } from "@/lib/radix/contracts";

export const Route = createFileRoute("/app/")({
  head: () => ({
    meta: [
      { title: "Home — RADIX workspace" },
      { name: "description", content: "Pick up where you left off and take the next useful step." },
      { property: "og:title", content: "Home — RADIX workspace" },
      { property: "og:description", content: "Your candidate workspace home." },
    ],
  }),
  component: HomePage,
});

function HomePage() {
  const [profile, setProfile] = useState<CandidateProfile | null>(getSavedProfile());
  const [liveAssessment, setLiveAssessment] = useState<AssessmentRecord | null>(getLatestLiveAssessment());
  const [allAssessments, setAllAssessments] = useState<AssessmentRecord[]>(getSavedAssessments());

  useEffect(() => {
    setProfile(getSavedProfile());
    setLiveAssessment(getLatestLiveAssessment());
    setAllAssessments(getSavedAssessments());
  }, []);

  if (!profile) {
    return (
      <div className="py-12 animate-page">
        <div className="surface max-w-xl mx-auto p-10 text-center rounded-2xl border border-border">
          <div className="mx-auto flex h-14 w-14 items-center justify-center rounded-full bg-primary/10 text-primary">
            <FileUp className="h-7 w-7" />
          </div>
          <h2 className="font-display mt-6 text-2xl font-semibold">Welcome to your RADIX workspace</h2>
          <p className="mt-2 text-sm text-muted-foreground leading-relaxed">
            No profile created yet. Drop your resume to automatically extract your skills, project experience, and run live job matching.
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

  const latest = liveAssessment ?? (allAssessments.length > 0 ? allAssessments[0] : null);
  const firstName = profile.full_name.split(" ")[0] || "there";
  const isCustomProfile = hasSavedProfile() && !!profile;
  const completenessPercent = isCustomProfile && profile
    ? Math.round(([
        Boolean(profile.full_name.trim() && profile.headline.trim() && profile.location?.trim()),
        profile.education.some((entry) => (entry.institution ?? "").trim() || (entry.degree ?? "").trim()),
        profile.skills.length > 0,
        profile.projects.some((entry) => (entry.title ?? "").trim() || (entry.summary ?? "").trim()),
        profile.experience.some((entry) => (entry.company ?? "").trim() || (entry.title ?? "").trim()),
        profile.certifications.some((entry) => entry.trim()),
        profile.preferred_roles.some((entry) => entry.trim()),
      ].filter(Boolean).length / 7) * 100)
    : 0;

  return (
    <div>
      <div className="mb-10">
        <p className="text-sm text-muted-foreground">Good evening, {firstName}</p>
        <h1 className="mt-2 text-3xl font-semibold tracking-tight md:text-[34px]">
          Build the next version of <span className="font-[Instrument_Serif] font-normal italic">you.</span>
        </h1>
        <p className="mt-3 max-w-xl text-muted-foreground">
          One place to see your skills, compare them with real roles, and choose what to work on next.
        </p>
      </div>

      {latest ? (
        <div className="grid gap-10 lg:grid-cols-[1.7fr_1fr]">
          <Link to="/app/assessments/$assessmentId" params={{ assessmentId: latest.id }} className="surface group p-6 transition-shadow hover:shadow-md md:p-8">
            <div className="flex items-center justify-between">
              <p className="text-[13px] font-medium text-muted-foreground">
                Your latest assessment
              </p>
            </div>
            <div className="mt-6 flex flex-col sm:flex-row sm:items-center gap-6 rounded-2xl bg-muted/40 border border-border/60 p-6">
              <div className="flex items-baseline gap-1 tabular-nums shrink-0">
                <span className="font-display text-4xl md:text-5xl font-semibold tracking-tight text-foreground">
                  {latest.match.match_score}
                </span>
                <span className="text-sm font-medium text-muted-foreground">/100</span>
              </div>
              <div className="border-t sm:border-t-0 sm:border-l border-border/60 pt-4 sm:pt-0 sm:pl-6">
                <h2 className="text-xl font-semibold">{latest.role}</h2>
                <p className="text-sm text-muted-foreground">{latest.company}</p>
                <p className="mt-2 max-w-sm text-sm leading-relaxed text-muted-foreground">{latest.match.summary}</p>
                <span className="mt-4 inline-flex items-center gap-2 text-sm font-medium text-foreground">
                  View assessment details <ArrowRight className="h-4 w-4 transition-transform group-hover:translate-x-1" />
                </span>
              </div>
            </div>
          </Link>

          <div className="flex flex-col border-l-2 border-gold pl-6">
            <p className="text-[13px] font-medium text-muted-foreground">Recommended next step</p>
            <h3 className="mt-2 text-lg font-semibold">
              {latest.plan?.actions?.[0] ? `Level up ${latest.plan.actions[0].skill}` : "Close your critical gap"}
            </h3>
            <p className="mt-2 text-sm leading-relaxed text-muted-foreground">
              {latest.plan?.actions?.[0]?.why ?? `Focus on requirements for ${latest.company} to raise your match estimate.`}
            </p>
            <div className="mt-6 flex flex-wrap gap-2">
              <Button asChild><Link to="/app/skill-growth">View improvement plan</Link></Button>
              <Button asChild variant="outline"><Link to="/app/assessments/new"><FileUp /> Analyze a JD</Link></Button>
            </div>
          </div>
        </div>
      ) : (
        <div className="grid gap-10 lg:grid-cols-[1.7fr_1fr]">
          <div className="surface p-8 md:p-10 rounded-2xl border border-border flex flex-col justify-between">
            <div>
              <span className="rounded-full bg-primary/10 px-3 py-1 text-xs font-medium text-primary">
                Step 2: Match against a role
              </span>
              <h3 className="font-display mt-4 text-2xl md:text-3xl font-semibold">Ready to test your skills?</h3>
              <p className="mt-3 text-sm md:text-base text-muted-foreground leading-relaxed max-w-xl">
                Your profile is active with {profile.skills.length} verified skills. Upload a target job description to run a real-time match, benchmark against company standards, and generate your learning roadmap.
              </p>
            </div>
            <div className="mt-8 flex flex-wrap gap-3">
              <Button asChild size="lg">
                <Link to="/app/assessments/new"><FileUp className="mr-2 h-4 w-4" /> Run first assessment</Link>
              </Button>
              <Button asChild variant="outline" size="lg">
                <Link to="/app/profile">Review your skills</Link>
              </Button>
            </div>
          </div>

          <div className="surface p-8 rounded-2xl border border-border flex flex-col justify-between">
            <div>
              <div className="flex items-baseline justify-between">
                <h4 className="text-base font-semibold">Active Profile</h4>
                <span className="text-sm font-semibold tabular-nums text-primary">{completenessPercent}% complete</span>
              </div>
              <div className="mt-3"><LevelBar value={completenessPercent} max={100} /></div>
              <p className="mt-3 text-xs text-muted-foreground">
                {profile.skills.length} skills recorded in your active profile.
              </p>
              <div className="mt-5 flex flex-wrap gap-1.5">
                {profile.skills.slice(0, 8).map((s, i) => (
                  <span key={i} className="inline-flex items-center rounded-md border border-border bg-secondary/50 px-2 py-0.5 text-xs text-foreground">
                    {s.name}
                  </span>
                ))}
                {profile.skills.length > 8 && (
                  <span className="inline-flex items-center rounded-md px-1.5 py-0.5 text-xs text-muted-foreground">
                    +{profile.skills.length - 8} more
                  </span>
                )}
              </div>
            </div>
            <Link to="/app/profile" className="mt-6 inline-flex items-center gap-1 text-sm font-medium text-primary hover:underline">
              View full profile <ArrowUpRight className="h-4 w-4" />
            </Link>
          </div>
        </div>
      )}

      <div className="mt-14 grid gap-10 lg:grid-cols-[1.7fr_1fr]">
        <section>
          <div className="mb-3 flex items-center justify-between">
            <h3 className="text-lg font-semibold">Recent assessments</h3>
            {allAssessments.length > 0 && (
              <Link to="/app/assessments" className="text-sm text-muted-foreground hover:text-foreground">See all</Link>
            )}
          </div>
          {allAssessments.length === 0 ? (
            <div className="rounded-2xl border border-dashed border-border/80 bg-card/40 p-6 text-sm">
              <p className="font-medium text-foreground">Your assessment history will appear here.</p>
              <p className="mt-1 text-xs text-muted-foreground leading-relaxed">
                Every time you compare your skills against a job description, your match score, verified overlaps, and gap breakdown will be logged here for quick review.
              </p>
            </div>
          ) : (
            allAssessments.slice(0, 4).map((a) => (
              <Link key={a.id} to="/app/assessments/$assessmentId" params={{ assessmentId: a.id }}
                className="flex items-center justify-between border-t border-border py-3.5 transition-colors hover:bg-secondary/40">
                <div>
                  <p className="text-[15px] font-medium">{a.role}</p>
                  <p className="text-sm text-muted-foreground">{a.company} · {a.updated_at}</p>
                </div>
                <span className="text-lg font-semibold tabular-nums">
                  {a.match.match_score}<span className="text-xs font-normal text-muted-foreground">/100</span>
                </span>
              </Link>
            ))
          )}
        </section>
        <section className="flex flex-col justify-between border-l-2 border-border/60 pl-6">
          <div>
            <h3 className="text-lg font-semibold">How it works</h3>
            <ol className="mt-4 space-y-3 text-xs text-muted-foreground">
              <li className="flex items-start gap-2">
                <span className="flex h-5 w-5 shrink-0 items-center justify-center rounded-full bg-success/20 text-success text-[10px] font-bold">✓</span>
                <span><strong className="text-foreground">Step 1:</strong> Profile built and verified from your resume.</span>
              </li>
              <li className="flex items-start gap-2">
                <span className="flex h-5 w-5 shrink-0 items-center justify-center rounded-full bg-primary/20 text-primary text-[10px] font-bold">2</span>
                <span><strong className="text-foreground">Step 2:</strong> Upload a Job Description to extract requirements.</span>
              </li>
              <li className="flex items-start gap-2">
                <span className="flex h-5 w-5 shrink-0 items-center justify-center rounded-full bg-muted text-muted-foreground text-[10px] font-bold">3</span>
                <span><strong className="text-foreground">Step 3:</strong> Get your match score and personalized skill growth plan.</span>
              </li>
            </ol>
          </div>
          <Link to="/app/skill-growth" className="mt-6 block border-t border-border pt-4 text-sm text-muted-foreground hover:text-foreground">
            Skill Growth — small steps, stronger evidence →
          </Link>
        </section>
      </div>
    </div>
  );
}
