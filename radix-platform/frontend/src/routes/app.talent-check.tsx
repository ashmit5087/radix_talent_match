import { createFileRoute } from "@tanstack/react-router";
import { useEffect, useMemo, useState } from "react";
import { AlertTriangle, Building2, CheckCircle2, Loader2, RefreshCw, ShieldCheck, Target, TrendingUp } from "lucide-react";
import { Button } from "@/components/ui/button";
import { PageHeader, ScoreRing } from "@/components/radix/ui";
import {
  SERVICES,
  runTalentCheck,
  searchCompanies,
  type Company,
  type TalentCheckResult,
} from "@/lib/radix/services";
import { getSavedProfile } from "@/lib/radix/session";
import type { CandidateProfile } from "@/lib/radix/contracts";
import { cn } from "@/lib/utils";

export const Route = createFileRoute("/app/talent-check")({
  head: () => ({
    meta: [
      { title: "Talent Check — RADIX" },
      { name: "description", content: "Benchmark your profile against company hiring standards." },
    ],
  }),
  component: TalentCheckPage,
});

type CompanyResult = { company: Company; result?: TalentCheckResult; error?: string };

function TalentCheckPage() {
  const [profile] = useState<CandidateProfile | null>(getSavedProfile());
  const [companies, setCompanies] = useState<Company[]>([]);
  const [results, setResults] = useState<CompanyResult[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");
  const talentReady = !!SERVICES.find((service) => service.key === "talent")?.baseUrl;

  async function loadCompanies() {
    setLoading(true);
    setError("");
    try {
      const found = await searchCompanies("", 20);
      setCompanies(found);
      setResults([]);
    } catch (e) {
      setError((e as Error).message);
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    if (talentReady) void loadCompanies();
  }, [talentReady]);

  async function runChecks() {
    if (!profile || companies.length === 0) return;
    setLoading(true);
    setError("");
    const settled = await Promise.all(
      companies.map(async (company): Promise<CompanyResult> => {
        try {
          return { company, result: await runTalentCheck(company.id, profile) };
        } catch (e) {
          return { company, error: (e as Error).message };
        }
      }),
    );
    setResults(settled);
    setLoading(false);
    if (settled.every((item) => item.error)) {
      setError("Talent Check could not evaluate any listed company.");
    }
  }

  const successful = results.filter((item) => item.result);
  const average = successful.length
    ? Math.round(successful.reduce((sum, item) => sum + (item.result?.readiness_score ?? 0), 0) / successful.length)
    : 0;
  const strongest = useMemo(
    () => [...successful].sort((a, b) => (b.result?.readiness_score ?? 0) - (a.result?.readiness_score ?? 0))[0],
    [results],
  );

  if (!profile) return null;

  return (
    <div>
      <PageHeader
        eyebrow="Role 4 · Company benchmarks"
        title={<>Know where you stand. <em className="text-amber-gradient">Before you apply.</em></>}
      >
        <Button onClick={() => void runChecks()} disabled={loading || !companies.length} className="gap-2">
          {loading ? <Loader2 className="h-4 w-4 animate-spin" /> : <RefreshCw className="h-4 w-4" />}
          {results.length ? "Refresh checks" : "Run Talent Check"}
        </Button>
      </PageHeader>

      <section className="relative overflow-hidden rounded-3xl border border-primary/20 bg-gradient-to-br from-primary/15 via-card to-gold-soft/40 p-6 md:p-8">
        <div className="pointer-events-none absolute -right-20 -top-20 h-56 w-56 rounded-full bg-primary/10 blur-3xl" />
        <div className="relative grid gap-8 lg:grid-cols-[1.4fr_1fr] lg:items-center">
          <div>
            <div className="flex items-center gap-2 text-sm font-medium text-primary">
              <ShieldCheck className="h-4 w-4" /> Preliminary readiness benchmark
            </div>
            <h2 className="mt-3 font-display text-3xl md:text-4xl">Your profile, measured against real hiring bars.</h2>
            <p className="mt-3 max-w-2xl text-sm leading-relaxed text-muted-foreground">
              Role 4 evaluates evidence across coding, systems, communication, cloud and other competency categories.
              It is a company-readiness signal, not a hiring decision or a job-match score.
            </p>
            <div className="mt-6 flex flex-wrap gap-3 text-xs text-muted-foreground">
              <span className="rounded-full border border-border bg-card/70 px-3 py-1.5">{profile.skills.length} profile skills</span>
              <span className="rounded-full border border-border bg-card/70 px-3 py-1.5">{companies.length} companies available</span>
              {successful.length > 0 && <span className="rounded-full border border-border bg-card/70 px-3 py-1.5">{successful.length} checks completed</span>}
            </div>
          </div>
          <div className="flex items-center justify-center gap-6 rounded-2xl border border-border/70 bg-card/70 p-6">
            <ScoreRing score={average} size={132} />
            <div>
              <p className="text-sm font-semibold">Average readiness</p>
              <p className="mt-1 text-xs leading-relaxed text-muted-foreground">
                {strongest ? `Strongest current benchmark: ${strongest.company.name}.` : "Run the check to compare your profile."}
              </p>
            </div>
          </div>
        </div>
      </section>

      {error && <div className="mt-5 rounded-xl border border-destructive/30 bg-destructive/10 p-4 text-sm text-destructive">{error}</div>}
      {!talentReady && <div className="mt-5 rounded-xl border border-border bg-secondary p-4 text-sm">Role 4 is not connected. Start the service on port 8004 to enable company benchmarks.</div>}

      <section className="mt-10">
        <div className="mb-4 flex items-end justify-between gap-4">
          <div>
            <p className="text-xs font-semibold uppercase tracking-wider text-muted-foreground">Company landscape</p>
            <h2 className="mt-1 text-2xl font-semibold">Where do you currently fit?</h2>
          </div>
          <p className="text-xs text-muted-foreground">Higher readiness means stronger evidence against the company baseline.</p>
        </div>
        {loading && !results.length ? (
          <div className="flex items-center gap-2 rounded-2xl border border-dashed border-border p-8 text-sm text-muted-foreground"><Loader2 className="h-4 w-4 animate-spin" /> Loading company benchmarks…</div>
        ) : (
          <div className="grid gap-4 md:grid-cols-2 xl:grid-cols-3">
            {results.map(({ company, result, error: resultError }) => (
              <CompanyCard key={company.id} company={company} result={result} error={resultError} />
            ))}
            {!results.length && companies.map((company) => (
              <div key={company.id} className="rounded-2xl border border-border bg-card p-5">
                <Building2 className="h-5 w-5 text-primary" />
                <h3 className="mt-4 font-semibold">{company.name}</h3>
                <p className="mt-1 text-xs text-muted-foreground">{company.industry ?? company.description ?? "Company benchmark"}</p>
                <p className="mt-5 text-xs text-muted-foreground">Ready to evaluate when you click Run Talent Check.</p>
              </div>
            ))}
          </div>
        )}
      </section>

      {successful.length > 0 && (
        <section className="mt-10 grid gap-4 md:grid-cols-3">
          <Metric icon={TrendingUp} label="Average readiness" value={`${average}%`} />
          <Metric icon={Target} label="Best current fit" value={strongest?.company.name ?? "—"} />
          <Metric icon={AlertTriangle} label="Critical gaps to address" value={String(successful.reduce((sum, item) => sum + (item.result?.critical_gaps.length ?? 0), 0))} />
        </section>
      )}
    </div>
  );
}

function CompanyCard({ company, result, error }: CompanyResult) {
  const score = result?.readiness_score ?? 0;
  return (
    <article className="group rounded-2xl border border-border bg-card p-5 transition-all hover:-translate-y-0.5 hover:border-primary/40 hover:shadow-md">
      <div className="flex items-start justify-between gap-3">
        <div>
          <div className="flex items-center gap-2"><Building2 className="h-4 w-4 text-primary" /><h3 className="font-semibold">{company.name}</h3></div>
          <p className="mt-1 text-xs text-muted-foreground">{company.industry ?? company.description ?? "Company benchmark"}</p>
        </div>
        {result && <span className="text-2xl font-semibold tabular-nums">{score}</span>}
      </div>
      {result ? (
        <>
          <div className="mt-5 h-2 overflow-hidden rounded-full bg-secondary"><div className="h-full rounded-full bg-gradient-to-r from-primary to-gold" style={{ width: `${score}%` }} /></div>
          <p className="mt-3 text-sm font-medium">{result.verdict}</p>
          <div className="mt-4 grid grid-cols-3 gap-2 text-center text-xs">
            <MiniStat label="Met" value={result.summary?.met_count ?? 0} tone="success" />
            <MiniStat label="Gaps" value={result.summary?.gap_count ?? result.skillset_gap?.length ?? 0} tone="warning" />
            <MiniStat label="Critical" value={result.summary?.critical_gap_count ?? result.critical_gaps.length} tone="danger" />
          </div>
          {result.focus_areas.length > 0 && <p className="mt-4 text-xs text-muted-foreground">Focus: {result.focus_areas.slice(0, 3).join(", ")}</p>}
        </>
      ) : (
        <p className={cn("mt-6 text-xs", error ? "text-destructive" : "text-muted-foreground")}>{error ?? "No result yet."}</p>
      )}
    </article>
  );
}

function MiniStat({ label, value, tone }: { label: string; value: number; tone: "success" | "warning" | "danger" }) {
  return <div className="rounded-lg bg-secondary/70 p-2"><p className="text-[10px] text-muted-foreground">{label}</p><p className={cn("mt-1 font-semibold", tone === "success" && "text-success", tone === "warning" && "text-amber-600", tone === "danger" && "text-destructive")}>{value}</p></div>;
}

function Metric({ icon: Icon, label, value }: { icon: typeof TrendingUp; label: string; value: string }) {
  return <div className="flex items-center gap-3 rounded-2xl border border-border bg-card p-5"><Icon className="h-5 w-5 text-primary" /><div><p className="text-xs text-muted-foreground">{label}</p><p className="mt-1 font-semibold">{value}</p></div></div>;
}
