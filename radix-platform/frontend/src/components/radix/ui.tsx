import { useEffect, useState, type ReactNode } from "react";
import { AlertTriangle, CheckCircle2, ChevronDown, CircleDashed, HelpCircle, XCircle } from "lucide-react";
import { CATEGORY_LABELS, type MatchStatus, type SkillCategory, type SkillMatchItem } from "@/lib/radix/contracts";
import { cn } from "@/lib/utils";

export function Wordmark({ className }: { className?: string }) {
  return (
    <span className={cn("inline-flex items-center gap-2", className)}>
      <svg viewBox="0 0 24 24" className="h-5 w-5 text-primary" aria-hidden>
        <circle cx="12" cy="12" r="2.4" fill="currentColor" />
        <path d="M12 2v5M12 17v5M2 12h5M17 12h5M5 5l3 3M16 16l3 3M19 5l-3 3M8 16l-3 3" stroke="currentColor" strokeWidth="1.2" strokeLinecap="round" />
      </svg>
      <span className="font-display text-2xl tracking-wide">RADIX</span>
    </span>
  );
}

export function PageHeader({ eyebrow, title, children }: { eyebrow?: string; title: ReactNode; children?: ReactNode }) {
  return (
    <header className="mb-8 flex flex-col gap-5 md:flex-row md:items-end md:justify-between">
      <div>
        {eyebrow && <p className="mb-2 text-[13px] font-medium text-muted-foreground">{eyebrow}</p>}
        <h1 className="font-display text-3xl leading-tight md:text-[34px]">{title}</h1>
      </div>
      {children && <div className="flex flex-wrap gap-3">{children}</div>}
    </header>
  );
}

export function DemoTag({ children = "Demo data" }: { children?: ReactNode }) {
  return (
    <span className="inline-flex items-center gap-1.5 rounded-full border border-border px-2.5 py-0.5 text-xs text-muted-foreground">
      <CircleDashed className="h-3 w-3" /> {children}
    </span>
  );
}

const STATUS = {
  matched: { label: "Matched", icon: CheckCircle2, cls: "text-success bg-success/10 border-success/25" },
  partial: { label: "Partial", icon: AlertTriangle, cls: "text-warning bg-warning/10 border-warning/25" },
  review_required: { label: "Review required", icon: HelpCircle, cls: "text-review bg-review/10 border-review/25" },
  missing: { label: "Missing", icon: XCircle, cls: "text-destructive bg-destructive/10 border-destructive/25" },
} as const;

export function StatusBadge({ status }: { status: MatchStatus }) {
  const s = STATUS[status];
  const Icon = s.icon;
  return (
    <span className={cn("inline-flex items-center gap-1.5 rounded-full border px-2.5 py-0.5 text-xs font-medium", s.cls)}>
      <Icon className="h-3.5 w-3.5" /> {s.label}
    </span>
  );
}

export function CategoryBadge({ category }: { category: SkillCategory }) {
  return <span className="text-xs text-muted-foreground">{CATEGORY_LABELS[category]}</span>;
}

/** Display-only — the score always comes from the API. Animates once per score. */
export function ScoreRing({ score, size = 168 }: { score: number; size?: number }) {
  const r = 72;
  const c = 2 * Math.PI * r;
  const [shown, setShown] = useState(0);
  useEffect(() => {
    const id = requestAnimationFrame(() => setShown(score));
    return () => cancelAnimationFrame(id);
  }, [score]);
  return (
    <div className="relative shrink-0" style={{ width: size, height: size }} role="img" aria-label={`Skill-match estimate ${score} out of 100`}>
      <svg viewBox="0 0 160 160" className="h-full w-full -rotate-90">
        <circle cx="80" cy="80" r={r} fill="none" stroke="var(--border)" strokeWidth="3" />
        <circle
          cx="80" cy="80" r={r} fill="none" stroke="var(--gold)" strokeWidth="3" strokeLinecap="round"
          strokeDasharray={c} strokeDashoffset={c * (1 - shown / 100)}
          style={{ transition: "stroke-dashoffset 900ms cubic-bezier(.16,1,.3,1)" }}
        />
      </svg>
      <div className="absolute inset-0 flex flex-col items-center justify-center tabular-nums">
        <span className="leading-none" style={{ fontSize: size * 0.26, fontWeight: 600, letterSpacing: "-0.03em" }}>
          {score}<span className="text-muted-foreground" style={{ fontSize: size * 0.09, fontWeight: 500 }}>/100</span>
        </span>
        <span className="mt-1.5 text-[11px] text-muted-foreground">Skill-match estimate</span>
      </div>
    </div>
  );
}

export function LevelBar({ value, max = 5, tone = "primary" }: { value: number; max?: number; tone?: "primary" | "sky" }) {
  return (
    <div className="h-1.5 w-full overflow-hidden rounded-full bg-muted">
      <div className={cn("h-full animate-fill rounded-full", tone === "primary" ? "bg-gold" : "bg-sky")} style={{ width: `${(value / max) * 100}%` }} />
    </div>
  );
}

export function SkillRow({ item }: { item: SkillMatchItem }) {
  const [open, setOpen] = useState(false);
  return (
    <div className="border-b border-border last:border-0">
      <button onClick={() => setOpen(!open)} aria-expanded={open} className="flex w-full items-center gap-4 py-4 text-left">
        <div className="min-w-0 flex-1">
          <div className="flex flex-wrap items-center gap-2">
            <span className="font-medium">{item.skill}</span>
            {item.critical_gap && (
              <span className="rounded-full bg-destructive px-2 py-0.5 text-[11px] font-semibold uppercase tracking-wide text-destructive-foreground">Critical</span>
            )}
          </div>
          <CategoryBadge category={item.category} />
        </div>
        <StatusBadge status={item.status} />
        <ChevronDown className={cn("h-4 w-4 text-muted-foreground transition-transform", open && "rotate-180")} />
      </button>
      {open && (
        <div className="grid gap-4 pb-5 text-sm md:grid-cols-3 animate-page">
          <Field label="Why">{item.rationale}</Field>
          <Field label="From the job description">{item.jd_evidence ?? "—"}</Field>
          <Field label="Your evidence">{item.candidate_evidence ?? <span className="italic text-muted-foreground">No evidence provided</span>}</Field>
          {item.required_level != null && (
            <div className="md:col-span-3 grid gap-2 md:grid-cols-2">
              <div><p className="mb-1 text-xs text-muted-foreground">Required level {item.required_level}/10</p><LevelBar value={item.required_level} max={10} tone="sky" /></div>
              <div><p className="mb-1 text-xs text-muted-foreground">Your level {item.candidate_level ?? "—"}/10</p><LevelBar value={item.candidate_level ?? 0} max={10} /></div>
            </div>
          )}
        </div>
      )}
    </div>
  );
}

function Field({ label, children }: { label: string; children: ReactNode }) {
  return (
    <div>
      <p className="mb-1 text-xs text-muted-foreground">{label}</p>
      <p className="leading-relaxed">{children}</p>
    </div>
  );
}

export function EmptyState({ title, body, action }: { title: string; body: string; action?: ReactNode }) {
  return (
    <div className="surface flex flex-col items-center px-8 py-16 text-center">
      <div className="mb-5 h-10 w-10 rounded-full bg-gold-soft" />
      <h3 className="text-lg font-semibold">{title}</h3>
      <p className="mt-2 max-w-md text-sm text-muted-foreground">{body}</p>
      {action && <div className="mt-6">{action}</div>}
    </div>
  );
}
