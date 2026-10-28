import { createFileRoute, Link, notFound } from "@tanstack/react-router";
import { useState } from "react";
import { AlertTriangle, ArrowLeft, ChevronDown } from "lucide-react";
import { ScoreRing, SkillRow } from "@/components/radix/ui";
import { ACTION_LABELS, CATEGORY_LABELS, type SkillCategory } from "@/lib/radix/contracts";
import { getLatestLiveAssessment, getSavedAssessments } from "@/lib/radix/session";
import type { AssessmentRecord } from "@/lib/radix/contracts";

export const Route = createFileRoute("/app/assessments/$assessmentId")({
  loader: ({ params }): AssessmentRecord => {
    const list = getSavedAssessments();
    const found = list.find((x) => x.id === params.assessmentId);
    if (found) return found;
    const latest = getLatestLiveAssessment();
    if (latest && params.assessmentId === latest.id) {
      return latest;
    }
    throw notFound();
  },
  head: ({ loaderData }) => ({
    meta: [
      { title: loaderData ? `${loaderData.role} at ${loaderData.company} — RADIX` : "Assessment — RADIX" },
      { name: "description", content: "Skill-match estimate, gaps and improvement plan." },
      { property: "og:title", content: loaderData ? `${loaderData.role} — skill match` : "Assessment" },
      { property: "og:description", content: "Skill-match estimate and improvement plan." },
    ],
  }),
  notFoundComponent: () => (
    <div className="py-24 text-center">
      <h1 className="font-display text-3xl">Assessment not found</h1>
      <Link to="/app/assessments" className="mt-4 inline-block text-primary">Back to assessments</Link>
    </div>
  ),
  component: Results,
});

function Section({
  title,
  count,
  children,
  defaultOpen = true,
}: {
  title: string;
  count: number;
  children: React.ReactNode;
  defaultOpen?: boolean;
}) {
  const [open, setOpen] = useState(defaultOpen);
  return (
    <section className="surface px-8 py-6">
      <button
        onClick={() => setOpen(!open)}
        aria-expanded={open}
        className="flex w-full items-center justify-between"
      >
        <h2 className="font-display text-xl">
          {title} <span className="ml-2 text-base text-muted-foreground">{count}</span>
        </h2>
        <ChevronDown className={`h-5 w-5 text-muted-foreground transition-transform ${open ? "rotate-180" : ""}`} />
      </button>
      {open && <div className="mt-2">{children}</div>}
    </section>
  );
}

function Results() {
  const a = Route.useLoaderData();
  const m = a.match;
  const isLive = a.id.startsWith("live-");
  const gaps = [...m.missing_skills].sort((x, y) => Number(!!y.critical_gap) - Number(!!x.critical_gap));
  const criticalMatched = m.matched_skills.filter((skill) => skill.critical_gap);
  const matched = m.matched_skills.filter((skill) => !skill.critical_gap);

  return (
    <div className="space-y-6">
      <Link
        to="/app/assessments"
        className="inline-flex items-center gap-2 text-sm text-muted-foreground hover:text-foreground"
      >
        <ArrowLeft className="h-4 w-4" /> Assessments
      </Link>

      <div className="surface relative overflow-hidden p-8 md:p-10">
        <div className="relative flex flex-col gap-10 md:flex-row md:items-center">
          <ScoreRing score={m.match_score} />
          <div className="flex-1">
            <div className="flex flex-wrap items-center gap-2 text-sm text-muted-foreground">
              <span>{m.jd_source_file}</span>
              <span>·</span>
              <span>{a.role} Candidate</span>
                            {isLive && (
                <span className="rounded-full bg-success/15 px-2 py-0.5 text-xs font-medium text-success">
                  Live result
                </span>
              )}
            </div>
            <h1 className="font-display mt-3 text-3xl md:text-[34px] leading-tight">{m.role}</h1>
            <p className="text-lg text-muted-foreground">{m.company}</p>
            <p className="mt-5 max-w-2xl leading-relaxed">{m.summary}</p>
          </div>
        </div>
      </div>

      {m.warnings.length > 0 && (
        <div className="rounded-2xl border border-warning/30 bg-warning/10 p-5 text-sm">
          {m.warnings.map((w) => (
            <p key={w} className="flex items-start gap-2 text-warning">
              <AlertTriangle className="mt-0.5 h-4 w-4 shrink-0" />
              {w}
            </p>
          ))}
        </div>
      )}

      <Section title="Gaps to close" count={gaps.length}>
        {gaps.map((s) => <SkillRow key={s.skill} item={s} />)}
      </Section>

      <Section
        title="Needs attention"
        count={m.partial_matches.length + m.review_required.length}
      >
        {[...m.partial_matches, ...m.review_required].map((s) => (
          <SkillRow key={s.skill} item={s} />
        ))}
      </Section>

      <Section title="Matched but needs stronger proficiency" count={criticalMatched.length}>
        {criticalMatched.map((s) => <SkillRow key={s.skill} item={s} />)}
      </Section>

      <Section title="What you have" count={matched.length} defaultOpen={false}>
        {matched.map((s) => <SkillRow key={s.skill} item={s} />)}
      </Section>

      <section className="surface p-8">
        <div className="flex flex-wrap items-baseline justify-between gap-4">
          <h2 className="font-display text-xl">Improvement plan</h2>
          <p className="text-sm text-muted-foreground">
            {a.plan.current_score} → up to {a.plan.projected_score_if_all_closed} (estimate)
          </p>
        </div>
        <ol className="mt-6 space-y-4">
          {a.plan.actions.map((x, i) => (
            <li key={x.skill} className="flex gap-5 rounded-2xl border border-border p-5">
              <span className="font-display text-lg tabular-nums text-muted-foreground">{i + 1}</span>
              <div className="flex-1">
                <div className="flex flex-wrap items-center gap-3">
                  <span className="font-medium">{x.skill}</span>
                  <span className="rounded-full bg-accent px-2.5 py-0.5 text-xs text-accent-foreground">
                    {ACTION_LABELS[x.action_type]}
                  </span>
                  <span className="ml-auto text-sm text-success">+{x.score_gain} → {x.projected_score_after}</span>
                </div>
                <p className="mt-2 text-sm text-muted-foreground">{x.why}</p>
                <ul className="mt-3 space-y-1">
                  {x.steps.map((s) => (
                    <li key={s} className="flex gap-2 text-sm text-muted-foreground">
                      <span className="mt-2 h-1 w-1 shrink-0 rounded-full bg-gold" />
                      {s}
                    </li>
                  ))}
                </ul>
              </div>
            </li>
          ))}
        </ol>
        <p className="mt-5 text-xs text-muted-foreground">{a.plan.disclaimer}</p>
      </section>

      <details className="surface group p-8">
        <summary className="font-display cursor-pointer list-none text-lg">How is this calculated?</summary>
        {m.score_breakdown?.formula && (
          <code className="mt-5 block rounded-xl bg-muted p-4 text-sm">{m.score_breakdown.formula}</code>
        )}
        {m.score_breakdown?.weights && Object.keys(m.score_breakdown.weights).length > 0 && (
          <div className="mt-4 grid gap-2 sm:grid-cols-2">
            {Object.entries(m.score_breakdown.weights).map(([k, v]) => (
              <div key={k} className="flex justify-between text-sm">
                <span className="text-muted-foreground">{CATEGORY_LABELS[k as SkillCategory] ?? k}</span>
                <span>{v}</span>
              </div>
            ))}
          </div>
        )}
        {m.talent_check_context && (
          <div className="mt-4 text-sm space-y-1">
            <p>
              Talent Check: <strong>{m.talent_check_context.readiness_score != null ? `${m.talent_check_context.readiness_score}% readiness` : "Evaluated"}</strong>
            </p>
            {m.talent_check_context.handling && (
              <p className="text-xs text-muted-foreground leading-relaxed">{m.talent_check_context.handling}</p>
            )}
          </div>
        )}
        <p className="mt-3 text-xs text-muted-foreground">Algorithm {m.algorithm_version}</p>
      </details>

      <p className="border-t border-border pt-6 text-sm text-muted-foreground">{m.disclaimer}</p>
    </div>
  );
}
