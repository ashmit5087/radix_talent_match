import { createFileRoute } from "@tanstack/react-router";
import { useEffect, useMemo, useState } from "react";
import {
  AlertTriangle,
  Building2,
  Check,
  CheckCircle2,
  ChevronRight,
  Code2,
  Github,
  Loader2,
  RefreshCw,
  Search,
  ShieldCheck,
  Sparkles,
  Target,
  TrendingUp,
  X,
} from "lucide-react";
import { Button } from "@/components/ui/button";
import { PageHeader, ScoreRing } from "@/components/radix/ui";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
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
  const [searchQuery, setSearchQuery] = useState("");
  const [verdictFilter, setVerdictFilter] = useState<string>("all");

  // Beta Web Footprint Scraper State
  const [betaEnabled, setBetaEnabled] = useState(false);
  const [githubHandle, setGithubHandle] = useState("");
  const [leetcodeHandle, setLeetcodeHandle] = useState("");

  // Detailed Modal State
  const [activeCompany, setActiveCompany] = useState<Company | null>(null);
  const [activeResult, setActiveResult] = useState<TalentCheckResult | undefined>(undefined);
  const [activeLoading, setActiveLoading] = useState(false);

  const talentReady = !!SERVICES.find((service) => service.key === "talent")?.baseUrl;

  async function loadCompanies() {
    setLoading(true);
    setError("");
    try {
      // Fetch up to 200 to ensure all companies from staging_company_skill_levels are included
      const found = await searchCompanies("", 200);
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

    const auditOptions = betaEnabled
      ? {
          enable_web_audit: true,
          github_handle: githubHandle.trim() || undefined,
          leetcode_handle: leetcodeHandle.trim() || undefined,
        }
      : undefined;

    // Process in batches of 15 for optimal UI responsiveness
    const chunkSize = 15;
    const allResults: CompanyResult[] = [];
    try {
      for (let i = 0; i < companies.length; i += chunkSize) {
        const chunk = companies.slice(i, i + chunkSize);
        const chunkResults = await Promise.all(
          chunk.map(async (company): Promise<CompanyResult> => {
            try {
              return { company, result: await runTalentCheck(company.id, profile, auditOptions) };
            } catch (e) {
              return { company, error: (e as Error).message };
            }
          }),
        );
        allResults.push(...chunkResults);
        setResults([...allResults]);
      }
    } catch (e) {
      setError((e as Error).message);
    } finally {
      setLoading(false);
      if (allResults.length > 0 && allResults.every((item) => item.error)) {
        setError("Talent Check could not evaluate any listed company.");
      }
    }
  }

  async function handleOpenDetail(company: Company, existingResult?: TalentCheckResult) {
    setActiveCompany(company);

    // If an existing result exists and matches our current beta audit preference, use it
    if (existingResult && (!betaEnabled || existingResult.web_audit)) {
      setActiveResult(existingResult);
      return;
    }

    // Evaluate on-the-fly for this specific company
    if (profile) {
      setActiveLoading(true);
      setActiveResult(undefined);
      try {
        const auditOptions = betaEnabled
          ? {
              enable_web_audit: true,
              github_handle: githubHandle.trim() || undefined,
              leetcode_handle: leetcodeHandle.trim() || undefined,
            }
          : undefined;

        const res = await runTalentCheck(company.id, profile, auditOptions);
        setActiveResult(res);
        setResults((prev) => {
          const filtered = prev.filter((p) => p.company.id !== company.id);
          return [...filtered, { company, result: res }];
        });
      } catch (e) {
        console.error("Failed to evaluate company:", e);
      } finally {
        setActiveLoading(false);
      }
    }
  }

  const resultsMap = useMemo(() => {
    const map = new Map<number, CompanyResult>();
    for (const r of results) {
      map.set(r.company.id, r);
    }
    return map;
  }, [results]);

  const displayedItems = useMemo(() => {
    const query = searchQuery.toLowerCase().trim();
    return companies
      .filter((company) => {
        if (query && !company.name.toLowerCase().includes(query)) return false;
        if (verdictFilter !== "all") {
          const item = resultsMap.get(company.id);
          if (!item?.result) return false;
          if (item.result.verdict !== verdictFilter) return false;
        }
        return true;
      })
      .map((company) => {
        const item = resultsMap.get(company.id);
        return {
          company,
          result: item?.result,
          error: item?.error,
        };
      });
  }, [companies, resultsMap, searchQuery, verdictFilter]);

  const successful = results.filter((item) => item.result);
  const average = successful.length
    ? Math.round(
        successful.reduce((sum, item) => sum + (item.result?.readiness_score ?? 0), 0) /
          successful.length,
      )
    : 0;
  const strongest = useMemo(
    () =>
      [...successful].sort(
        (a, b) => (b.result?.readiness_score ?? 0) - (a.result?.readiness_score ?? 0),
      )[0],
    [results],
  );

  if (!profile) return null;

  return (
    <div>
      <PageHeader
        eyebrow="Role 4 · Company benchmarks"
        title={
          <>
            Know where you stand. <em className="text-amber-gradient">Before you apply.</em>
          </>
        }
      >
        <div className="flex flex-wrap items-center gap-3">
          {/* Beta Feature Toggle alongside Refresh */}
          <label
            className={cn(
              "flex items-center gap-2 rounded-xl border px-3 py-2 text-xs font-medium cursor-pointer transition-all select-none",
              betaEnabled
                ? "border-primary/50 bg-primary/10 text-primary shadow-sm"
                : "border-border bg-card/80 text-muted-foreground hover:bg-secondary hover:text-foreground"
            )}
            title="Enable public code proof audit via GitHub and LeetCode"
          >
            <input
              type="checkbox"
              checked={betaEnabled}
              onChange={(e) => setBetaEnabled(e.target.checked)}
              className="h-4 w-4 rounded border-border accent-primary text-primary focus:ring-primary/40 cursor-pointer"
            />
            <Sparkles className="h-3.5 w-3.5 text-primary" />
            <span>Web Footprint</span>
            <span className="rounded bg-primary/20 text-primary px-1.5 py-0.2 text-[10px] font-bold uppercase tracking-wider">
              Beta
            </span>
          </label>

          <Button onClick={() => void runChecks()} disabled={loading || !companies.length} className="gap-2">
            {loading ? <Loader2 className="h-4 w-4 animate-spin" /> : <RefreshCw className="h-4 w-4" />}
            {results.length ? "Refresh checks" : `Run Talent Check (${companies.length})`}
          </Button>
        </div>
      </PageHeader>

      {/* Beta Footprint Input Panel */}
      {betaEnabled && (
        <div className="mb-6 rounded-2xl border border-primary/30 bg-gradient-to-r from-primary/10 via-card to-primary/5 p-5 animate-in fade-in slide-in-from-top-2 duration-300">
          <div className="flex flex-col md:flex-row md:items-center md:justify-between gap-4">
            <div className="space-y-1">
              <div className="flex items-center gap-2 text-sm font-semibold text-primary">
                <Sparkles className="h-4 w-4" />
                <span>Web Footprint Corroboration Engine</span>
                <span className="rounded-full bg-primary/20 px-2 py-0.5 text-[10px] font-bold uppercase tracking-wider">
                  Active
                </span>
              </div>
              <p className="text-xs text-muted-foreground max-w-xl leading-relaxed">
                Provide public profile URLs or handles. Talent Check scrapes repositories, commit recency, and LeetCode contest metrics to augment candidate evidence points across <strong>COD</strong>, <strong>SWE</strong>, <strong>DSA</strong>, and <strong>APTI</strong> before scoring company benchmarks.
              </p>
            </div>
            <div className="grid grid-cols-1 sm:grid-cols-2 gap-3 w-full md:max-w-lg">
              <div className="relative">
                <Github className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-muted-foreground" />
                <input
                  type="text"
                  value={githubHandle}
                  onChange={(e) => setGithubHandle(e.target.value)}
                  placeholder="GitHub URL or username (e.g. torvalds)"
                  className="w-full rounded-xl border border-border bg-background pl-9 pr-3 py-2 text-xs outline-none focus:border-primary focus:ring-1 focus:ring-primary placeholder:text-muted-foreground"
                />
              </div>
              <div className="relative">
                <Code2 className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-amber-500" />
                <input
                  type="text"
                  value={leetcodeHandle}
                  onChange={(e) => setLeetcodeHandle(e.target.value)}
                  placeholder="LeetCode URL or username (e.g. tourist)"
                  className="w-full rounded-xl border border-border bg-background pl-9 pr-3 py-2 text-xs outline-none focus:border-primary focus:ring-1 focus:ring-primary placeholder:text-muted-foreground"
                />
              </div>
            </div>
          </div>
        </div>
      )}

      <section className="relative overflow-hidden rounded-3xl border border-primary/20 bg-gradient-to-br from-primary/15 via-card to-gold-soft/40 p-6 md:p-8">
        <div className="pointer-events-none absolute -right-20 -top-20 h-56 w-56 rounded-full bg-primary/10 blur-3xl" />
        <div className="relative grid gap-8 lg:grid-cols-[1.4fr_1fr] lg:items-center">
          <div>
            <div className="flex items-center gap-2 text-sm font-medium text-primary">
              <ShieldCheck className="h-4 w-4" /> Preliminary readiness benchmark
            </div>
            <h2 className="mt-3 font-display text-3xl md:text-4xl">
              Your profile, measured against real hiring bars.
            </h2>
            <p className="mt-3 max-w-2xl text-sm leading-relaxed text-muted-foreground">
              Role 4 evaluates evidence across coding, systems, communication, cloud and other competency categories.
              Click any company card to inspect the full 12-skillset benchmark duel view.
            </p>
            <div className="mt-6 flex flex-wrap gap-3 text-xs text-muted-foreground">
              <span className="rounded-full border border-border bg-card/70 px-3 py-1.5">
                {profile.skills.length} profile skills
              </span>
              <span className="rounded-full border border-border bg-card/70 px-3 py-1.5 font-medium text-foreground">
                {companies.length} total companies loaded
              </span>
              {successful.length > 0 && (
                <span className="rounded-full border border-border bg-card/70 px-3 py-1.5 font-medium text-primary">
                  {successful.length} checks completed
                </span>
              )}
              {betaEnabled && (
                <span className="rounded-full border border-primary/40 bg-primary/10 px-3 py-1.5 font-medium text-primary inline-flex items-center gap-1.5">
                  <Sparkles className="h-3 w-3" /> Web Footprint Active
                </span>
              )}
            </div>
          </div>
          <div className="flex items-center justify-center gap-6 rounded-2xl border border-border/70 bg-card/70 p-6">
            <ScoreRing score={average} size={132} />
            <div>
              <p className="text-sm font-semibold">Average readiness</p>
              <p className="mt-1 text-xs leading-relaxed text-muted-foreground">
                {strongest
                  ? `Strongest current benchmark: ${strongest.company.name}.`
                  : "Run the check or click a company to evaluate."}
              </p>
            </div>
          </div>
        </div>
      </section>

      {error && (
        <div className="mt-5 rounded-xl border border-destructive/30 bg-destructive/10 p-4 text-sm text-destructive">
          {error}
        </div>
      )}
      {!talentReady && (
        <div className="mt-5 rounded-xl border border-border bg-secondary p-4 text-sm">
          Role 4 is not connected. Start the service on port 8004 to enable company benchmarks.
        </div>
      )}

      <section className="mt-10">
        <div className="mb-6 flex flex-col gap-4 sm:flex-row sm:items-end sm:justify-between">
          <div>
            <p className="text-xs font-semibold uppercase tracking-wider text-muted-foreground">
              Company landscape
            </p>
            <h2 className="mt-1 text-2xl font-semibold">Where do you currently fit?</h2>
            <p className="mt-1 text-xs text-muted-foreground">
              Click any company card to open the interactive 12-skillset breakdown modal.
            </p>
          </div>

          {/* Search & Filter Bar */}
          <div className="flex flex-col sm:flex-row items-stretch sm:items-center gap-3">
            <div className="relative min-w-[260px]">
              <Search className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-muted-foreground" />
              <input
                type="text"
                value={searchQuery}
                onChange={(e) => setSearchQuery(e.target.value)}
                placeholder="Search all 115+ companies…"
                className="w-full rounded-xl border border-input bg-card pl-9 pr-8 py-2 text-sm outline-none focus:border-primary focus:ring-1 focus:ring-primary placeholder:text-muted-foreground"
              />
              {searchQuery && (
                <button
                  onClick={() => setSearchQuery("")}
                  className="absolute right-2.5 top-1/2 -translate-y-1/2 text-muted-foreground hover:text-foreground"
                  aria-label="Clear search"
                >
                  <X className="h-3.5 w-3.5" />
                </button>
              )}
            </div>
            <span className="rounded-xl border border-border bg-card px-3 py-2 text-xs font-mono text-muted-foreground whitespace-nowrap text-center">
              {displayedItems.length} of {companies.length}
            </span>
          </div>
        </div>

        {/* Verdict Filter Pills if results exist */}
        {successful.length > 0 && (
          <div className="mb-6 flex flex-wrap gap-2">
            {[
              { id: "all", label: "All Companies" },
              { id: "Ready", label: "Ready" },
              { id: "Close", label: "Close" },
              { id: "Needs Work", label: "Needs Work" },
            ].map((tab) => (
              <button
                key={tab.id}
                onClick={() => setVerdictFilter(tab.id)}
                className={cn(
                  "rounded-lg px-3 py-1.5 text-xs font-medium transition-colors border",
                  verdictFilter === tab.id
                    ? "border-primary bg-primary text-primary-foreground"
                    : "border-border bg-card text-muted-foreground hover:bg-secondary",
                )}
              >
                {tab.label}
              </button>
            ))}
          </div>
        )}

        {loading && !results.length ? (
          <div className="flex items-center gap-2 rounded-2xl border border-dashed border-border p-8 text-sm text-muted-foreground">
            <Loader2 className="h-4 w-4 animate-spin" /> Loading all {companies.length || 115} company benchmarks…
          </div>
        ) : displayedItems.length === 0 ? (
          <div className="rounded-2xl border border-dashed border-border p-12 text-center text-sm text-muted-foreground">
            No companies matching "{searchQuery}".
          </div>
        ) : (
          <div className="grid gap-4 md:grid-cols-2 xl:grid-cols-3">
            {displayedItems.map(({ company, result, error: resultError }) => (
              <CompanyCard
                key={company.id}
                company={company}
                result={result}
                error={resultError}
                onClick={() => handleOpenDetail(company, result)}
              />
            ))}
          </div>
        )}
      </section>

      {successful.length > 0 && (
        <section className="mt-10 grid gap-4 md:grid-cols-3">
          <Metric icon={TrendingUp} label="Average readiness" value={`${average}%`} />
          <Metric icon={Target} label="Best current fit" value={strongest?.company.name ?? "—"} />
          <Metric
            icon={AlertTriangle}
            label="Critical gaps to address"
            value={String(
              successful.reduce((sum, item) => sum + (item.result?.critical_gaps.length ?? 0), 0),
            )}
          />
        </section>
      )}

      {/* Comprehensive Company Detail Modal */}
      <CompanyDetailModal
        company={activeCompany}
        result={activeResult}
        loading={activeLoading}
        betaActive={betaEnabled}
        onClose={() => setActiveCompany(null)}
        onRunCheck={() => {
          if (activeCompany) void handleOpenDetail(activeCompany);
        }}
      />
    </div>
  );
}

function CompanyCard({
  company,
  result,
  error,
  onClick,
}: CompanyResult & { onClick: () => void }) {
  const score = result?.readiness_score ?? 0;
  return (
    <article
      onClick={onClick}
      role="button"
      tabIndex={0}
      onKeyDown={(e) => {
        if (e.key === "Enter" || e.key === " ") {
          e.preventDefault();
          onClick();
        }
      }}
      className="group cursor-pointer rounded-2xl border border-border bg-card p-5 transition-all hover:-translate-y-0.5 hover:border-primary/60 hover:shadow-lg focus:outline-none focus:ring-2 focus:ring-primary/40"
    >
      <div className="flex items-start justify-between gap-3">
        <div>
          <div className="flex items-center gap-2">
            <Building2 className="h-4 w-4 text-primary transition-transform group-hover:scale-110" />
            <h3 className="font-semibold transition-colors group-hover:text-primary">
              {company.name}
            </h3>
          </div>
          <p className="mt-1 text-xs text-muted-foreground line-clamp-1">
            {company.industry ?? company.description ?? "Enterprise benchmark"}
          </p>
        </div>
        {result && (
          <span className="text-2xl font-semibold tabular-nums text-primary">{score}</span>
        )}
      </div>

      {result ? (
        <>
          <div className="mt-5 h-2 overflow-hidden rounded-full bg-secondary">
            <div
              className="h-full rounded-full bg-gradient-to-r from-primary to-gold transition-all duration-500"
              style={{ width: `${score}%` }}
            />
          </div>
          <div className="mt-3 flex items-center justify-between">
            <p className="text-sm font-medium">{result.verdict}</p>
            <span className="text-xs text-muted-foreground">Click for details</span>
          </div>

          {/* Web Audit Mini-Banner if available */}
          {result.web_audit && (
            <div className="mt-3 flex items-center justify-between text-[11px] rounded-lg border border-primary/30 bg-primary/10 px-2.5 py-1 text-primary">
              <span className="flex items-center gap-1 font-semibold">
                <Sparkles className="h-3 w-3" /> Audited Level
              </span>
              <span className="font-mono font-medium text-foreground">
                Lvl {result.web_audit.candidate_level.toFixed(1)} · {result.web_audit.composite_reality_score}% reality
              </span>
            </div>
          )}

          <div className="mt-4 grid grid-cols-3 gap-2 text-center text-xs">
            <MiniStat label="Met" value={result.summary?.met_count ?? 0} tone="success" />
            <MiniStat
              label="Gaps"
              value={result.summary?.gap_count ?? result.skillset_gap?.length ?? 0}
              tone="warning"
            />
            <MiniStat
              label="Critical"
              value={result.summary?.critical_gap_count ?? result.critical_gaps.length}
              tone="danger"
            />
          </div>
          {result.focus_areas && result.focus_areas.length > 0 && (
            <p className="mt-4 text-xs text-muted-foreground line-clamp-1">
              Focus: {result.focus_areas.slice(0, 3).map((f: any) => typeof f === 'string' ? f : f?.name ?? f?.code).join(", ")}
            </p>
          )}
          <div className="mt-4 pt-3 border-t border-border/50 flex items-center justify-between text-xs text-primary font-medium group-hover:translate-x-0.5 transition-transform">
            <span>View 12-skill breakdown</span>
            <ChevronRight className="h-3.5 w-3.5" />
          </div>
        </>
      ) : (
        <div className="mt-5">
          <p className={cn("text-xs", error ? "text-destructive" : "text-muted-foreground")}>
            {error ?? "Click to view benchmark & evaluate."}
          </p>
          <div className="mt-4 pt-3 border-t border-border/50 flex items-center justify-between text-xs text-primary font-medium group-hover:translate-x-0.5 transition-transform">
            <span>Open benchmark profile</span>
            <ChevronRight className="h-3.5 w-3.5" />
          </div>
        </div>
      )}
    </article>
  );
}

function CompanyDetailModal({
  company,
  result,
  loading,
  betaActive,
  onClose,
  onRunCheck,
}: {
  company: Company | null;
  result?: TalentCheckResult;
  loading: boolean;
  betaActive: boolean;
  onClose: () => void;
  onRunCheck: () => void;
}) {
  if (!company) return null;
  const score = result?.readiness_score ?? 0;
  const verdict = result?.verdict ?? "Pending";
  const isReady = verdict === "Ready";
  const isClose = verdict === "Close";

  return (
    <Dialog open={!!company} onOpenChange={(open) => { if (!open) onClose(); }}>
      <DialogContent className="max-w-3xl max-h-[88vh] overflow-y-auto border-border bg-card p-6 sm:p-8">
        <DialogHeader className="space-y-3">
          <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4 border-b border-border/60 pb-5">
            <div className="flex items-start gap-3">
              <div className="rounded-xl border border-primary/30 bg-primary/10 p-3 text-primary mt-1 shrink-0">
                <Building2 className="h-6 w-6" />
              </div>
              <div>
                <DialogTitle className="text-xl sm:text-2xl font-bold font-display">
                  {company.name}
                </DialogTitle>
                <DialogDescription className="text-xs sm:text-sm text-muted-foreground mt-0.5">
                  Enterprise Hiring Benchmark · Benchmark ID #{company.id}
                </DialogDescription>
                {result && (
                  <div className="mt-2.5 flex flex-wrap items-center gap-2">
                    <span
                      className={cn(
                        "rounded-full px-2.5 py-0.5 text-xs font-semibold uppercase tracking-wider",
                        isReady && "bg-emerald-500/15 text-emerald-500 border border-emerald-500/30",
                        isClose && "bg-amber-500/15 text-amber-500 border border-amber-500/30",
                        !isReady && !isClose && "bg-rose-500/15 text-rose-500 border border-rose-500/30",
                      )}
                    >
                      {verdict}
                    </span>
                    <span className="text-xs text-muted-foreground">
                      {result.verdict_message}
                    </span>
                  </div>
                )}
              </div>
            </div>
            {result && (
              <div className="flex items-center gap-3 shrink-0 self-start sm:self-center">
                <ScoreRing score={score} size={84} />
              </div>
            )}
          </div>
        </DialogHeader>

        {loading ? (
          <div className="py-16 text-center">
            <Loader2 className="h-8 w-8 animate-spin text-primary mx-auto mb-3" />
            <p className="text-sm font-medium">Evaluating profile against {company.name} hiring bar…</p>
            <p className="text-xs text-muted-foreground mt-1">
              {betaActive
                ? "Scraping GitHub & LeetCode footprints and fusing evidence across 12 skillsets…"
                : "Scoring 12 skill categories via Role 4 deterministic engine"}
            </p>
          </div>
        ) : result ? (
          <div className="space-y-6 pt-2">
            {/* Quick Metrics */}
            <div className="grid grid-cols-2 sm:grid-cols-4 gap-3 text-center">
              <div className="rounded-xl border border-border/70 bg-secondary/50 p-3">
                <p className="text-[11px] text-muted-foreground font-medium uppercase tracking-wider">Readiness</p>
                <p className="mt-1 text-2xl font-bold tabular-nums text-primary">{score}%</p>
              </div>
              <div className="rounded-xl border border-border/70 bg-secondary/50 p-3">
                <p className="text-[11px] text-muted-foreground font-medium uppercase tracking-wider">Met Bar</p>
                <p className="mt-1 text-2xl font-bold tabular-nums text-emerald-500">{result.summary?.met_count ?? 0} / 12</p>
              </div>
              <div className="rounded-xl border border-border/70 bg-secondary/50 p-3">
                <p className="text-[11px] text-muted-foreground font-medium uppercase tracking-wider">Skill Gaps</p>
                <p className="mt-1 text-2xl font-bold tabular-nums text-amber-500">{result.summary?.gap_count ?? 0} / 12</p>
              </div>
              <div className="rounded-xl border border-border/70 bg-secondary/50 p-3">
                <p className="text-[11px] text-muted-foreground font-medium uppercase tracking-wider">Critical Gaps</p>
                <p className="mt-1 text-2xl font-bold tabular-nums text-rose-500">{result.summary?.critical_gap_count ?? result.critical_gaps.length}</p>
              </div>
            </div>

            {/* Beta Web Footprint Detailed Breakdown Section */}
            {result.web_audit && (
              <div className="rounded-2xl border border-primary/30 bg-gradient-to-br from-primary/10 via-card to-background p-5 space-y-4">
                <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-3 border-b border-border/50 pb-3">
                  <div className="flex items-center gap-2">
                    <Sparkles className="h-4 w-4 text-primary" />
                    <h4 className="text-sm font-bold text-foreground">Web Footprint Corroboration (Beta)</h4>
                    <span className="rounded bg-primary/20 text-primary px-1.5 py-0.5 text-[10px] font-bold uppercase tracking-wider">
                      Verified Proof
                    </span>
                  </div>
                  <div className="flex items-center gap-2 text-xs">
                    <span className="text-muted-foreground">Composite Reality Score:</span>
                    <span className="font-bold text-primary font-mono text-sm">
                      {result.web_audit.composite_reality_score}%
                    </span>
                  </div>
                </div>

                {/* Audited Designation & Explanation */}
                <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3 bg-secondary/40 rounded-xl p-3.5 border border-border/50">
                  <div>
                    <p className="text-[11px] font-semibold text-muted-foreground uppercase tracking-wider">
                      Audited Engineering Level
                    </p>
                    <p className="text-base font-bold text-foreground mt-0.5">
                      {result.web_audit.level_designation} <span className="text-xs font-mono font-medium text-primary">({result.web_audit.candidate_level.toFixed(1)} / 10.0)</span>
                    </p>
                  </div>
                  <p className="text-xs text-muted-foreground max-w-sm leading-relaxed">
                    {result.web_audit.level_explanation}
                  </p>
                </div>

                {/* Platform Footprints */}
                <div className="grid grid-cols-1 sm:grid-cols-2 gap-3 text-xs">
                  {/* GitHub Signal */}
                  <div className="rounded-xl border border-border/70 bg-card p-3 space-y-2">
                    <div className="flex items-center justify-between font-semibold">
                      <span className="flex items-center gap-1.5 text-foreground">
                        <Github className="h-4 w-4 text-foreground" /> GitHub Signal
                      </span>
                      {result.web_audit.github_handle && (
                        <span className="font-mono text-[11px] text-muted-foreground">
                          @{result.web_audit.github_handle}
                        </span>
                      )}
                    </div>
                    <div className="grid grid-cols-3 gap-2 text-center pt-1">
                      <div className="bg-secondary/60 rounded p-1.5">
                        <p className="text-[10px] text-muted-foreground">Original Repos</p>
                        <p className="font-bold text-foreground">{result.web_audit.github_summary?.original_repos ?? 0}</p>
                      </div>
                      <div className="bg-secondary/60 rounded p-1.5">
                        <p className="text-[10px] text-muted-foreground">Total Stars</p>
                        <p className="font-bold text-primary">{result.web_audit.github_summary?.stars ?? 0}</p>
                      </div>
                      <div className="bg-secondary/60 rounded p-1.5">
                        <p className="text-[10px] text-muted-foreground">Active Recency</p>
                        <p className="font-bold text-emerald-500">{result.web_audit.github_summary?.recent_active_repos ?? 0}</p>
                      </div>
                    </div>
                  </div>

                  {/* LeetCode Signal */}
                  <div className="rounded-xl border border-border/70 bg-card p-3 space-y-2">
                    <div className="flex items-center justify-between font-semibold">
                      <span className="flex items-center gap-1.5 text-foreground">
                        <Code2 className="h-4 w-4 text-amber-500" /> LeetCode Signal
                      </span>
                      {result.web_audit.leetcode_handle && (
                        <span className="font-mono text-[11px] text-muted-foreground">
                          @{result.web_audit.leetcode_handle}
                        </span>
                      )}
                    </div>
                    <div className="grid grid-cols-3 gap-2 text-center pt-1">
                      <div className="bg-secondary/60 rounded p-1.5">
                        <p className="text-[10px] text-muted-foreground">Total Solved</p>
                        <p className="font-bold text-foreground">{result.web_audit.leetcode_summary?.total_solved ?? 0}</p>
                      </div>
                      <div className="bg-secondary/60 rounded p-1.5">
                        <p className="text-[10px] text-muted-foreground">Med / Hard</p>
                        <p className="font-bold text-amber-500">
                          {(result.web_audit.leetcode_summary?.medium ?? 0) + (result.web_audit.leetcode_summary?.hard ?? 0)}
                        </p>
                      </div>
                      <div className="bg-secondary/60 rounded p-1.5">
                        <p className="text-[10px] text-muted-foreground">Contest Rating</p>
                        <p className="font-bold text-foreground">
                          {result.web_audit.leetcode_summary?.contest_rating ? Math.round(result.web_audit.leetcode_summary.contest_rating) : "—"}
                        </p>
                      </div>
                    </div>
                  </div>
                </div>

                {/* Skills Verification Breakdown */}
                {result.web_audit.skills_breakdown && (
                  <div className="space-y-2.5 pt-1 text-xs">
                    {result.web_audit.skills_breakdown.verified_skills?.length > 0 && (
                      <div>
                        <p className="text-[11px] font-semibold text-emerald-500 mb-1.5 flex items-center gap-1">
                          <CheckCircle2 className="h-3.5 w-3.5" /> Skills Verified with Public Code Proof ({result.web_audit.skills_breakdown.verified_skills.length})
                        </p>
                        <div className="flex flex-wrap gap-1.5">
                          {result.web_audit.skills_breakdown.verified_skills.map((skill, idx) => (
                            <span key={idx} className="rounded-md border border-emerald-500/30 bg-emerald-500/10 px-2.5 py-0.5 text-[11px] text-emerald-400 font-medium">
                              ✓ {skill}
                            </span>
                          ))}
                        </div>
                      </div>
                    )}

                    {result.web_audit.skills_breakdown.bonus_discovered_skills?.length > 0 && (
                      <div className="pt-1">
                        <p className="text-[11px] font-semibold text-primary mb-1.5 flex items-center gap-1">
                          <Sparkles className="h-3.5 w-3.5" /> Bonus Unclaimed Skills Found in Public Repositories
                        </p>
                        <div className="flex flex-wrap gap-1.5">
                          {result.web_audit.skills_breakdown.bonus_discovered_skills.map((skill, idx) => (
                            <span key={idx} className="rounded-md border border-primary/30 bg-primary/10 px-2.5 py-0.5 text-[11px] text-primary font-medium">
                              + {skill}
                            </span>
                          ))}
                        </div>
                      </div>
                    )}

                    {result.web_audit.skills_breakdown.unverified_skills?.length > 0 && (
                      <div className="pt-1">
                        <p className="text-[11px] font-semibold text-muted-foreground mb-1.5 flex items-center gap-1">
                          <AlertTriangle className="h-3.5 w-3.5 text-amber-500" /> Resume Claims Lacking Public Web Evidence
                        </p>
                        <div className="flex flex-wrap gap-1.5">
                          {result.web_audit.skills_breakdown.unverified_skills.slice(0, 10).map((skill, idx) => (
                            <span key={idx} className="rounded-md border border-border bg-secondary/50 px-2 py-0.5 text-[11px] text-muted-foreground">
                              {skill}
                            </span>
                          ))}
                          {result.web_audit.skills_breakdown.unverified_skills.length > 10 && (
                            <span className="text-[11px] text-muted-foreground self-center">
                              +{result.web_audit.skills_breakdown.unverified_skills.length - 10} more
                            </span>
                          )}
                        </div>
                      </div>
                    )}
                  </div>
                )}

                <p className="text-[11px] text-muted-foreground/80 italic border-t border-border/40 pt-2">
                  * All 12 competency benchmarks below reflect augmented candidate levels derived from both resume evidence and verified public coding proofs.
                </p>
              </div>
            )}

            {/* Focus Areas Notice */}
            {result.focus_areas && result.focus_areas.length > 0 && (
              <div className="rounded-xl border border-amber-500/30 bg-amber-500/10 p-4">
                <div className="flex items-center gap-2 text-xs font-semibold text-amber-500">
                  <AlertTriangle className="h-4 w-4 shrink-0" />
                  <span>Targeted Remediation Focus Areas</span>
                </div>
                <div className="mt-2.5 flex flex-wrap gap-2">
                  {result.focus_areas.map((fa: any, idx: number) => {
                    const label = typeof fa === "string" ? fa : `${fa.name || fa.code} (Gap: +${fa.gap}, Target: ${fa.target_tier || 'Level ' + fa.required})`;
                    return (
                      <span key={idx} className="rounded-lg border border-amber-500/30 bg-background/80 px-2.5 py-1 text-xs text-foreground font-medium">
                        {label}
                      </span>
                    );
                  })}
                </div>
              </div>
            )}

            {/* 12 Skillset Breakdown Table */}
            <div>
              <div className="flex items-center justify-between mb-3">
                <h4 className="text-sm font-semibold flex items-center gap-2">
                  <ShieldCheck className="h-4 w-4 text-primary" />
                  All 12 RADIX Competency Benchmarks
                </h4>
                <span className="text-[11px] text-muted-foreground">White marker = company requirement</span>
              </div>

              <div className="rounded-xl border border-border overflow-hidden">
                <div className="divide-y divide-border/60">
                  {result.skillset_gap?.map((item) => {
                    const isCritical = item.gap && item.gap_size >= 4;
                    const reqPct = Math.min(100, (item.required_level / 10) * 100);
                    const candPct = Math.min(100, (item.candidate_level / 10) * 100);

                    return (
                      <div key={item.category_code} className="p-3.5 hover:bg-secondary/30 transition-colors">
                        <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-2 mb-2">
                          <div className="flex items-center gap-2">
                            <span className="rounded bg-primary/10 border border-primary/20 px-1.5 py-0.5 font-mono text-[11px] font-semibold text-primary">
                              {item.category_code}
                            </span>
                            <span className="text-sm font-medium">{item.category_name}</span>
                          </div>
                          <div className="flex items-center gap-2 text-xs">
                            <span className="text-muted-foreground">
                              Req: <strong className="text-foreground">Lvl {item.required_level}</strong> ({item.required_tier})
                            </span>
                            <span className="text-muted-foreground">·</span>
                            <span className="text-muted-foreground">
                              Candidate: <strong className={item.gap ? "text-amber-500 font-semibold" : "text-emerald-500 font-semibold"}>Lvl {item.candidate_level}</strong>
                              {item.evidence_points !== undefined && ` (${item.evidence_points} pts)`}
                            </span>
                            <span className="ml-2">
                              {!item.gap ? (
                                <span className="rounded-md border border-emerald-500/30 bg-emerald-500/10 px-2 py-0.5 text-[11px] font-semibold text-emerald-500 inline-flex items-center gap-1">
                                  <Check className="h-3 w-3" /> Met
                                </span>
                              ) : isCritical ? (
                                <span className="rounded-md border border-rose-500/30 bg-rose-500/10 px-2 py-0.5 text-[11px] font-semibold text-rose-500 inline-flex items-center gap-1">
                                  <AlertTriangle className="h-3 w-3" /> Critical (-{item.gap_size})
                                </span>
                              ) : (
                                <span className="rounded-md border border-amber-500/30 bg-amber-500/10 px-2 py-0.5 text-[11px] font-semibold text-amber-500">
                                  Gap (-{item.gap_size})
                                </span>
                              )}
                            </span>
                          </div>
                        </div>

                        {/* Duel Progress Bar */}
                        <div className="relative mt-1.5 h-2 w-full rounded-full bg-secondary/80 overflow-hidden">
                          <div
                            className={cn(
                              "h-full rounded-full transition-all duration-500",
                              !item.gap ? "bg-emerald-500" : isCritical ? "bg-rose-500" : "bg-amber-500"
                            )}
                            style={{ width: `${candPct}%` }}
                          />
                          {/* Required level indicator */}
                          <div
                            className="absolute top-0 bottom-0 w-1 bg-foreground/90 shadow-sm z-10 -ml-0.5"
                            style={{ left: `${reqPct}%` }}
                            title={`Required Level: ${item.required_level}/10`}
                          />
                        </div>
                      </div>
                    );
                  })}
                </div>
              </div>
            </div>
          </div>
        ) : (
          <div className="py-12 text-center space-y-4">
            <p className="text-sm text-muted-foreground">This company has not been evaluated against your profile yet.</p>
            <Button onClick={onRunCheck} className="gap-2">
              <RefreshCw className="h-4 w-4" /> Run Benchmark Now
            </Button>
          </div>
        )}
      </DialogContent>
    </Dialog>
  );
}

function MiniStat({
  label,
  value,
  tone,
}: {
  label: string;
  value: number;
  tone: "success" | "warning" | "danger";
}) {
  return (
    <div className="rounded-lg bg-secondary/70 p-2">
      <p className="text-[10px] text-muted-foreground">{label}</p>
      <p
        className={cn(
          "mt-1 font-semibold",
          tone === "success" && "text-emerald-500",
          tone === "warning" && "text-amber-500",
          tone === "danger" && "text-rose-500",
        )}
      >
        {value}
      </p>
    </div>
  );
}

function Metric({
  icon: Icon,
  label,
  value,
}: {
  icon: typeof TrendingUp;
  label: string;
  value: string;
}) {
  return (
    <div className="flex items-center gap-3 rounded-2xl border border-border bg-card p-5">
      <Icon className="h-5 w-5 text-primary" />
      <div>
        <p className="text-xs text-muted-foreground">{label}</p>
        <p className="mt-1 font-semibold">{value}</p>
      </div>
    </div>
  );
}
