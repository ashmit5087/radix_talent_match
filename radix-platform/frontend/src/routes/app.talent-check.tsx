import { createFileRoute } from "@tanstack/react-router";
import { useEffect, useMemo, useState } from "react";
import {
  AlertTriangle,
  ArrowRight,
  Building2,
  Check,
  CheckCircle2,
  ChevronLeft,
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
import { PageHeader } from "@/components/radix/ui";
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

const PAGE_SIZE = 30;

function TalentCheckPage() {
  const [profile] = useState<CandidateProfile | null>(getSavedProfile());
  const [companies, setCompanies] = useState<Company[]>([]);
  const [results, setResults] = useState<CompanyResult[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");
  const [searchQuery, setSearchQuery] = useState("");
  const [verdictFilter, setVerdictFilter] = useState<string>("all");
  const [currentPage, setCurrentPage] = useState(1);

  // Reset pagination on search or filter change
  useEffect(() => {
    setCurrentPage(1);
  }, [searchQuery, verdictFilter]);

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

    // Process in batches of 15 for responsiveness
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

    if (existingResult && (!betaEnabled || existingResult.web_audit)) {
      setActiveResult(existingResult);
      return;
    }

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

  const totalItems = displayedItems.length;
  const totalPages = Math.max(1, Math.ceil(totalItems / PAGE_SIZE));
  const validPage = Math.min(currentPage, totalPages);
  const startIndex = (validPage - 1) * PAGE_SIZE;
  const paginatedItems = displayedItems.slice(startIndex, startIndex + PAGE_SIZE);

  const successful = results.filter((item) => item.result);
  const average = successful.length
    ? Math.round(
        successful.reduce((sum, item) => sum + (item.result?.readiness_score ?? 0), 0) /
          successful.length,
      )
    : 0;

  const baselineAverage = successful.length
    ? Math.round(
        successful.reduce(
          (sum, item) => sum + (item.result?.baseline_score ?? item.result?.readiness_score ?? 0),
          0,
        ) / successful.length,
      )
    : 0;

  const hasAuditedResults = successful.some((item) => !!item.result?.web_audit);
  const averageLift = hasAuditedResults ? average - baselineAverage : 0;

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
            Know where you stand. <span className="font-[Instrument_Serif] font-normal italic">Before you apply.</span>
          </>
        }
      >
        <div className="flex flex-wrap items-center gap-2.5">
          {/* Beta Web Footprint Toggle Button */}
          <button
            type="button"
            onClick={() => setBetaEnabled(!betaEnabled)}
            className={cn(
              "inline-flex items-center gap-2 rounded-full border px-4 py-2 text-xs font-medium transition-all select-none",
              betaEnabled
                ? "border-primary bg-primary text-primary-foreground shadow-sm"
                : "border-border bg-card text-muted-foreground hover:bg-muted hover:text-foreground",
            )}
          >
            <Sparkles className="h-3.5 w-3.5" />
            <span>Web Footprint</span>
            <span
              className={cn(
                "rounded-full px-2 py-0.5 text-[10px] font-semibold uppercase tracking-wider",
                betaEnabled ? "bg-white/20 text-white" : "bg-muted text-foreground",
              )}
            >
              Beta
            </span>
            {betaEnabled && <Check className="h-3.5 w-3.5 ml-0.5" />}
          </button>

          <Button onClick={() => void runChecks()} disabled={loading || !companies.length} className="gap-2">
            {loading ? <Loader2 className="h-4 w-4 animate-spin" /> : <RefreshCw className="h-4 w-4" />}
            {results.length ? "Refresh benchmarks" : `Run Talent Check (${companies.length})`}
          </Button>
        </div>
      </PageHeader>

      {/* Beta Configuration Panel */}
      {betaEnabled && (
        <section className="surface p-6 mb-8 animate-page">
          <div className="flex flex-col lg:flex-row lg:items-center lg:justify-between gap-6">
            <div className="max-w-xl">
              <div className="flex items-center gap-2 text-xs font-semibold text-primary mb-1">
                <Sparkles className="h-4 w-4 text-primary" />
                <span>Web Footprint Verification (Beta Active)</span>
              </div>
              <p className="text-sm text-muted-foreground leading-relaxed">
                Connect your public code presence. Talent Check will scrape your GitHub repositories, star ratings, and LeetCode problem solving metrics to augment candidate evidence points across <strong>COD</strong>, <strong>SWE</strong>, <strong>DSA</strong>, and <strong>APTI</strong> alongside your resume baseline.
              </p>
            </div>
            <div className="grid grid-cols-1 sm:grid-cols-2 gap-3 w-full lg:max-w-md">
              <div className="relative">
                <Github className="absolute left-4 top-1/2 -translate-y-1/2 h-4 w-4 text-muted-foreground" />
                <input
                  type="text"
                  value={githubHandle}
                  onChange={(e) => setGithubHandle(e.target.value)}
                  placeholder="github.com/user or handle"
                  className="h-10 w-full rounded-full border border-input bg-card pl-11 pr-4 text-xs outline-none focus:ring-2 focus:ring-ring"
                />
              </div>
              <div className="relative">
                <Code2 className="absolute left-4 top-1/2 -translate-y-1/2 h-4 w-4 text-muted-foreground" />
                <input
                  type="text"
                  value={leetcodeHandle}
                  onChange={(e) => setLeetcodeHandle(e.target.value)}
                  placeholder="leetcode.com/user or handle"
                  className="h-10 w-full rounded-full border border-input bg-card pl-11 pr-4 text-xs outline-none focus:ring-2 focus:ring-ring"
                />
              </div>
            </div>
          </div>
        </section>
      )}

      {/* Primary Workspace Overview Banner */}
      <section className="surface p-6 md:p-8 mb-8">
        <div className="flex flex-col md:flex-row md:items-center justify-between gap-8">
          <div className="max-w-xl">
            <div className="flex items-center gap-2 text-xs font-medium text-muted-foreground mb-2">
              <ShieldCheck className="h-4 w-4 text-primary" /> Preliminary readiness benchmark
            </div>
            <h2 className="text-xl md:text-2xl font-semibold">
              Your profile, measured against real hiring bars.
            </h2>
            <p className="mt-2 text-sm text-muted-foreground leading-relaxed">
              Role 4 evaluates evidence across 12 competency categories. Click any company card to inspect the full benchmark duel view.
            </p>
            <div className="mt-4 flex flex-wrap gap-2 text-xs text-muted-foreground">
              <span className="rounded-full border border-border bg-card px-3 py-1">
                {profile.skills.length} profile skills
              </span>
              <span className="rounded-full border border-border bg-card px-3 py-1 font-medium text-foreground">
                {companies.length} companies loaded
              </span>
              {successful.length > 0 && (
                <span className="rounded-full border border-border bg-card px-3 py-1 text-muted-foreground">
                  {successful.length} benchmarked
                </span>
              )}
              {hasAuditedResults && (
                <span className="rounded-full border border-primary/30 bg-primary/10 px-3 py-1 font-medium text-primary inline-flex items-center gap-1.5">
                  <Sparkles className="h-3 w-3" /> Web Footprint Active
                </span>
              )}
            </div>
          </div>

          <div className="flex items-center gap-5 rounded-2xl bg-muted/40 border border-border/60 p-5 shrink-0">
            <div className="flex items-baseline gap-1 tabular-nums">
              <span className="font-display text-4xl md:text-5xl font-semibold tracking-tight text-foreground">
                {average}
              </span>
              <span className="text-sm font-medium text-muted-foreground">/100</span>
            </div>
            <div className="border-l border-border/60 pl-5">
              <p className="text-sm font-semibold">Average readiness</p>
              <p className="mt-1 text-xs text-muted-foreground max-w-[200px]">
                {strongest
                  ? `Highest current fit: ${strongest.company.name} (${strongest.result?.readiness_score}%)`
                  : "Run benchmarks to evaluate readiness"}
              </p>
              {hasAuditedResults && averageLift > 0 && (
                <p className="mt-2 text-xs text-emerald-600 font-medium inline-flex items-center gap-1">
                  <TrendingUp className="h-3.5 w-3.5" /> +{averageLift}% avg. lift from web proof
                </p>
              )}
            </div>
          </div>
        </div>
      </section>

      {error && (
        <div className="mb-6 rounded-2xl border border-destructive/30 bg-destructive/10 p-4 text-sm text-destructive">
          {error}
        </div>
      )}
      {!talentReady && (
        <div className="mb-6 rounded-2xl border border-border bg-muted p-4 text-sm">
          Role 4 is not connected. Start the service on port 8004 to enable company benchmarks.
        </div>
      )}

      {/* Company Landscape Section */}
      <section className="mt-8">
        <div className="mb-6 flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
          <div>
            <h3 className="text-lg font-semibold">Hiring Landscape</h3>
            <p className="text-xs text-muted-foreground">Compare benchmarks across 115+ engineering organizations.</p>
          </div>

          <div className="flex items-center gap-3">
            <div className="relative min-w-[260px] flex-1">
              <Search className="absolute left-4 top-1/2 -translate-y-1/2 h-4 w-4 text-muted-foreground" />
              <input
                type="text"
                value={searchQuery}
                onChange={(e) => setSearchQuery(e.target.value)}
                placeholder="Search company or industry…"
                className="h-10 w-full rounded-full border border-input bg-card pl-11 pr-8 text-sm outline-none focus:ring-2 focus:ring-ring"
              />
              {searchQuery && (
                <button
                  onClick={() => setSearchQuery("")}
                  className="absolute right-3 top-1/2 -translate-y-1/2 text-muted-foreground hover:text-foreground"
                >
                  <X className="h-3.5 w-3.5" />
                </button>
              )}
            </div>
            <span className="rounded-full border border-border bg-card px-3.5 py-2 text-xs font-mono text-muted-foreground whitespace-nowrap">
              {totalItems === 0
                ? "0 of " + companies.length
                : `${startIndex + 1}–${Math.min(startIndex + PAGE_SIZE, totalItems)} of ${companies.length}`}
            </span>
          </div>
        </div>

        {/* Verdict Filter Tabs */}
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
                  "rounded-full px-3.5 py-1 text-xs font-medium transition-colors border",
                  verdictFilter === tab.id
                    ? "border-primary bg-primary text-primary-foreground"
                    : "border-border bg-card text-muted-foreground hover:bg-muted hover:text-foreground",
                )}
              >
                {tab.label}
              </button>
            ))}
          </div>
        )}

        {loading && !results.length ? (
          <div className="surface flex items-center justify-center gap-3 p-12 text-sm text-muted-foreground">
            <Loader2 className="h-4 w-4 animate-spin text-primary" /> Loading all {companies.length || 115} company benchmarks…
          </div>
        ) : displayedItems.length === 0 ? (
          <div className="surface p-12 text-center text-sm text-muted-foreground">
            No companies matching "{searchQuery}".
          </div>
        ) : (
          <>
            <div className="grid gap-5 md:grid-cols-2 xl:grid-cols-3">
              {paginatedItems.map(({ company, result, error: resultError }) => (
                <CompanyCard
                  key={company.id}
                  company={company}
                  result={result}
                  error={resultError}
                  onClick={() => handleOpenDetail(company, result)}
                />
              ))}
            </div>

            {/* Pagination Controls */}
            {totalPages > 1 && (
              <div className="mt-8 flex flex-col sm:flex-row items-center justify-between gap-4 surface p-4 rounded-2xl">
                <p className="text-xs text-muted-foreground">
                  Showing <strong className="text-foreground">{startIndex + 1}–{Math.min(startIndex + PAGE_SIZE, totalItems)}</strong> of{" "}
                  <strong className="text-foreground">{totalItems}</strong> companies (Page {validPage} of {totalPages})
                </p>

                <div className="flex items-center gap-1.5">
                  <Button
                    variant="outline"
                    size="sm"
                    onClick={() => {
                      setCurrentPage((p) => Math.max(1, p - 1));
                      window.scrollTo({ top: 350, behavior: "smooth" });
                    }}
                    disabled={validPage <= 1}
                    className="h-8 gap-1 rounded-full px-3 text-xs"
                  >
                    <ChevronLeft className="h-3.5 w-3.5" />
                    <span>Previous</span>
                  </Button>

                  <div className="flex items-center gap-1 px-1">
                    {Array.from({ length: totalPages }, (_, i) => i + 1).map((pageNum) => (
                      <button
                        key={pageNum}
                        onClick={() => {
                          setCurrentPage(pageNum);
                          window.scrollTo({ top: 350, behavior: "smooth" });
                        }}
                        className={cn(
                          "h-8 min-w-[32px] px-2 rounded-full text-xs font-medium transition-colors",
                          validPage === pageNum
                            ? "bg-primary text-primary-foreground font-semibold shadow-xs"
                            : "text-muted-foreground hover:bg-muted hover:text-foreground"
                        )}
                      >
                        {pageNum}
                      </button>
                    ))}
                  </div>

                  <Button
                    variant="outline"
                    size="sm"
                    onClick={() => {
                      setCurrentPage((p) => Math.min(totalPages, p + 1));
                      window.scrollTo({ top: 350, behavior: "smooth" });
                    }}
                    disabled={validPage >= totalPages}
                    className="h-8 gap-1 rounded-full px-3 text-xs"
                  >
                    <span>Next</span>
                    <ChevronRight className="h-3.5 w-3.5" />
                  </Button>
                </div>
              </div>
            )}
          </>
        )}
      </section>

      {/* Aggregate Stats Section */}
      {successful.length > 0 && (
        <section className="mt-10 grid gap-4 md:grid-cols-3">
          <Metric icon={TrendingUp} label="Average readiness" value={`${average}%`} />
          <Metric icon={Target} label="Best current fit" value={strongest?.company.name ?? "—"} />
          <Metric
            icon={AlertTriangle}
            label="Critical gaps identified"
            value={String(
              successful.reduce((sum, item) => sum + (item.result?.critical_gaps.length ?? 0), 0),
            )}
          />
        </section>
      )}

      {/* Company Detail Modal */}
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
  const baselineScore = result?.baseline_score ?? score;
  const scoreDelta = result?.score_delta ?? (score - baselineScore);
  const hasAudit = !!result?.web_audit;

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
      className="surface group p-6 transition-all hover:border-foreground/30 hover:shadow-md cursor-pointer flex flex-col justify-between"
    >
      <div>
        <div className="flex items-start justify-between gap-3">
          <div>
            <div className="flex items-center gap-2">
              <Building2 className="h-4 w-4 text-primary" />
              <h4 className="font-semibold transition-colors group-hover:text-primary">
                {company.name}
              </h4>
            </div>
            <p className="mt-1 text-xs text-muted-foreground line-clamp-1">
              {company.industry ?? company.description ?? "Engineering benchmark"}
            </p>
          </div>
          {result && (
            <div className="text-right">
              <span className="font-display text-2xl tabular-nums">{score}</span>
              <span className="text-xs text-muted-foreground">/100</span>
            </div>
          )}
        </div>

        {result ? (
          <>
            {/* Before vs After Score Delta Pill */}
            {hasAudit && (
              <div className="mt-4 flex items-center justify-between rounded-xl bg-muted/40 border border-border/70 px-3 py-2 text-xs">
                <span className="text-muted-foreground">
                  Baseline: <strong className="text-foreground">{baselineScore}%</strong>
                </span>
                <span className="inline-flex items-center gap-1 font-medium text-primary">
                  <Sparkles className="h-3 w-3" /> Web Proof: <strong>{score}%</strong>
                  {scoreDelta > 0 && (
                    <span className="rounded-full bg-emerald-500/15 text-emerald-600 px-1.5 py-0.2 text-[10px] font-bold">
                      +{scoreDelta}%
                    </span>
                  )}
                </span>
              </div>
            )}

            {/* Duel Readiness Bar */}
            <div className="mt-4 h-1.5 overflow-hidden rounded-full bg-muted">
              <div
                className="h-full rounded-full bg-gold transition-all duration-500"
                style={{ width: `${score}%` }}
              />
            </div>

            <div className="mt-3 flex items-center justify-between text-xs">
              <p className="font-medium">{result.verdict}</p>
              <span className="text-muted-foreground">Click to inspect</span>
            </div>

            <div className="mt-4 grid grid-cols-3 gap-2 text-center text-xs">
              <div className="rounded-lg bg-muted/40 p-2">
                <p className="text-[10px] text-muted-foreground">Met</p>
                <p className="mt-0.5 font-semibold text-emerald-600">{result.summary?.met_count ?? 0}</p>
              </div>
              <div className="rounded-lg bg-muted/40 p-2">
                <p className="text-[10px] text-muted-foreground">Gaps</p>
                <p className="mt-0.5 font-semibold text-amber-600">{result.summary?.gap_count ?? result.skillset_gap?.length ?? 0}</p>
              </div>
              <div className="rounded-lg bg-muted/40 p-2">
                <p className="text-[10px] text-muted-foreground">Critical</p>
                <p className="mt-0.5 font-semibold text-rose-600">{result.summary?.critical_gap_count ?? result.critical_gaps.length}</p>
              </div>
            </div>

            {result.focus_areas && result.focus_areas.length > 0 && (
              <p className="mt-3 text-xs text-muted-foreground line-clamp-1">
                Focus: {result.focus_areas.slice(0, 3).map((f: any) => typeof f === 'string' ? f : f?.name ?? f?.code).join(", ")}
              </p>
            )}
          </>
        ) : (
          <div className="mt-6 text-xs text-muted-foreground">
            {error ?? "Click to calculate readiness against this benchmark."}
          </div>
        )}
      </div>

      <div className="mt-5 pt-3 border-t border-border flex items-center justify-between text-xs font-medium text-foreground">
        <span>View 12-skill breakdown</span>
        <ArrowRight className="h-3.5 w-3.5 transition-transform group-hover:translate-x-1" />
      </div>
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
  const baselineScore = result?.baseline_score ?? score;
  const scoreDelta = result?.score_delta ?? (score - baselineScore);
  const verdict = result?.verdict ?? "Pending";
  const baselineVerdict = result?.baseline_verdict ?? verdict;
  const isReady = verdict === "Ready";
  const isClose = verdict === "Close";

  return (
    <Dialog open={!!company} onOpenChange={(open) => { if (!open) onClose(); }}>
      <DialogContent className="max-w-3xl max-h-[88vh] overflow-y-auto border-border bg-card p-6 sm:p-8">
        <DialogHeader className="space-y-3">
          <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4 border-b border-border pb-5">
            <div className="flex items-start gap-3">
              <div className="rounded-xl border border-border bg-muted/40 p-3 mt-1 shrink-0">
                <Building2 className="h-6 w-6 text-primary" />
              </div>
              <div>
                <DialogTitle className="text-xl sm:text-2xl font-semibold tracking-tight">
                  {company.name}
                </DialogTitle>
                <DialogDescription className="text-xs sm:text-sm text-muted-foreground mt-0.5">
                  Hiring Benchmark · ID #{company.id}
                </DialogDescription>
                {result && (
                  <div className="mt-2.5 flex flex-wrap items-center gap-2">
                    <span
                      className={cn(
                        "rounded-full px-2.5 py-0.5 text-xs font-semibold uppercase tracking-wider",
                        isReady && "bg-emerald-500/15 text-emerald-600 border border-emerald-500/30",
                        isClose && "bg-amber-500/15 text-amber-600 border border-amber-500/30",
                        !isReady && !isClose && "bg-rose-500/15 text-rose-600 border border-rose-500/30",
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
              <div className="flex items-baseline gap-1 tabular-nums rounded-xl bg-muted/40 border border-border/60 px-4 py-2 shrink-0 self-start sm:self-center">
                <span className="font-display text-2xl sm:text-3xl font-semibold text-foreground">{score}</span>
                <span className="text-xs font-medium text-muted-foreground">/100</span>
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
            {/* Quick Metrics Bar */}
            <div className="grid grid-cols-2 sm:grid-cols-4 gap-3 text-center">
              <div className="surface p-3">
                <p className="text-[11px] text-muted-foreground uppercase font-medium">Readiness</p>
                <p className="mt-1 text-2xl font-semibold tabular-nums text-primary">{score}%</p>
              </div>
              <div className="surface p-3">
                <p className="text-[11px] text-muted-foreground uppercase font-medium">Met Bar</p>
                <p className="mt-1 text-2xl font-semibold tabular-nums text-emerald-600">{result.summary?.met_count ?? 0} / 12</p>
              </div>
              <div className="surface p-3">
                <p className="text-[11px] text-muted-foreground uppercase font-medium">Skill Gaps</p>
                <p className="mt-1 text-2xl font-semibold tabular-nums text-amber-600">{result.summary?.gap_count ?? 0} / 12</p>
              </div>
              <div className="surface p-3">
                <p className="text-[11px] text-muted-foreground uppercase font-medium">Critical Gaps</p>
                <p className="mt-1 text-2xl font-semibold tabular-nums text-rose-600">{result.summary?.critical_gap_count ?? result.critical_gaps.length}</p>
              </div>
            </div>

            {/* Before vs After Score Report */}
            {result.web_audit && (
              <div className="surface p-5 space-y-4">
                <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-3 border-b border-border pb-3">
                  <div>
                    <span className="text-xs font-semibold uppercase tracking-wider text-muted-foreground">Score Lift Report</span>
                    <h4 className="text-base font-semibold mt-0.5">Resume Baseline vs. Web Footprint</h4>
                  </div>
                  <div className="inline-flex items-center gap-2 rounded-full border border-border bg-muted/40 px-3.5 py-1 text-xs">
                    <span className="text-muted-foreground">Reality Corroboration:</span>
                    <strong className="text-foreground">{result.web_audit.composite_reality_score}%</strong>
                  </div>
                </div>

                {/* Score Comparison Grid */}
                <div className="grid grid-cols-1 sm:grid-cols-3 gap-3 text-center">
                  <div className="p-3.5 rounded-xl border border-border bg-muted/20">
                    <p className="text-[11px] font-medium text-muted-foreground uppercase">1. Before (Resume Only)</p>
                    <p className="text-2xl font-semibold mt-1 tabular-nums text-foreground">{baselineScore}%</p>
                    <p className="text-xs text-muted-foreground mt-0.5">{baselineVerdict}</p>
                  </div>
                  <div className="p-3.5 rounded-xl border border-border bg-muted/20">
                    <p className="text-[11px] font-medium text-muted-foreground uppercase">2. After (Code Verified)</p>
                    <p className="text-2xl font-semibold mt-1 tabular-nums text-primary">{score}%</p>
                    <p className="text-xs text-muted-foreground mt-0.5">{verdict}</p>
                  </div>
                  <div className="p-3.5 rounded-xl border border-primary/30 bg-primary/5">
                    <p className="text-[11px] font-medium text-primary uppercase">Readiness Lift</p>
                    <p className="text-2xl font-semibold mt-1 tabular-nums text-primary">
                      {scoreDelta >= 0 ? `+${scoreDelta}` : scoreDelta}%
                    </p>
                    <p className="text-xs text-muted-foreground mt-0.5">
                      {scoreDelta > 0 ? "Evidence elevated" : "Baseline preserved"}
                    </p>
                  </div>
                </div>

                {/* Boosted Categories Chips */}
                {result.levels_delta && Object.entries(result.levels_delta).some(([_, delta]) => delta > 0) && (
                  <div className="pt-2 border-t border-border flex flex-wrap items-center gap-2">
                    <span className="text-xs text-muted-foreground">Skillsets boosted by live code proof:</span>
                    {Object.entries(result.levels_delta)
                      .filter(([_, delta]) => delta > 0)
                      .map(([cat, delta]) => (
                        <span key={cat} className="inline-flex items-center gap-1 rounded-full border border-border bg-card px-2.5 py-0.5 text-xs">
                          <strong>{cat}</strong> <span className="text-emerald-600 font-semibold">+{delta} levels</span>
                        </span>
                      ))}
                  </div>
                )}

                {/* Audited Designation & Explanation */}
                <div className="rounded-xl border border-border bg-muted/30 p-3.5 flex flex-col sm:flex-row sm:items-center justify-between gap-3 text-xs">
                  <div>
                    <p className="text-[10px] font-semibold text-muted-foreground uppercase">Audited Level</p>
                    <p className="text-sm font-semibold text-foreground mt-0.5">
                      {result.web_audit.level_designation} <span className="font-mono text-xs text-muted-foreground">({result.web_audit.candidate_level.toFixed(1)} / 10.0)</span>
                    </p>
                  </div>
                  <p className="text-xs text-muted-foreground max-w-sm leading-relaxed">
                    {result.web_audit.level_explanation}
                  </p>
                </div>

                {/* Platform Footprints */}
                <div className="grid grid-cols-1 sm:grid-cols-2 gap-3 text-xs">
                  <div className="rounded-xl border border-border bg-card p-3 space-y-2">
                    <div className="flex items-center justify-between font-semibold">
                      <span className="flex items-center gap-1.5 text-foreground">
                        <Github className="h-4 w-4" /> GitHub Signal
                      </span>
                      {result.web_audit.github_handle && (
                        <span className="font-mono text-[11px] text-muted-foreground">
                          @{result.web_audit.github_handle}
                        </span>
                      )}
                    </div>
                    <div className="grid grid-cols-3 gap-2 text-center pt-1">
                      <div className="bg-muted/50 rounded p-1.5">
                        <p className="text-[10px] text-muted-foreground">Repos</p>
                        <p className="font-semibold text-foreground">{result.web_audit.github_summary?.original_repos ?? 0}</p>
                      </div>
                      <div className="bg-muted/50 rounded p-1.5">
                        <p className="text-[10px] text-muted-foreground">Stars</p>
                        <p className="font-semibold text-primary">{result.web_audit.github_summary?.stars ?? 0}</p>
                      </div>
                      <div className="bg-muted/50 rounded p-1.5">
                        <p className="text-[10px] text-muted-foreground">Active</p>
                        <p className="font-semibold text-emerald-600">{result.web_audit.github_summary?.recent_active_repos ?? 0}</p>
                      </div>
                    </div>
                  </div>

                  <div className="rounded-xl border border-border bg-card p-3 space-y-2">
                    <div className="flex items-center justify-between font-semibold">
                      <span className="flex items-center gap-1.5 text-foreground">
                        <Code2 className="h-4 w-4" /> LeetCode Signal
                      </span>
                      {result.web_audit.leetcode_handle && (
                        <span className="font-mono text-[11px] text-muted-foreground">
                          @{result.web_audit.leetcode_handle}
                        </span>
                      )}
                    </div>
                    <div className="grid grid-cols-3 gap-2 text-center pt-1">
                      <div className="bg-muted/50 rounded p-1.5">
                        <p className="text-[10px] text-muted-foreground">Solved</p>
                        <p className="font-semibold text-foreground">{result.web_audit.leetcode_summary?.total_solved ?? 0}</p>
                      </div>
                      <div className="bg-muted/50 rounded p-1.5">
                        <p className="text-[10px] text-muted-foreground">Med / Hard</p>
                        <p className="font-semibold text-amber-600">
                          {(result.web_audit.leetcode_summary?.medium ?? 0) + (result.web_audit.leetcode_summary?.hard ?? 0)}
                        </p>
                      </div>
                      <div className="bg-muted/50 rounded p-1.5">
                        <p className="text-[10px] text-muted-foreground">Contest</p>
                        <p className="font-semibold text-foreground">
                          {result.web_audit.leetcode_summary?.contest_rating ? Math.round(result.web_audit.leetcode_summary.contest_rating) : "—"}
                        </p>
                      </div>
                    </div>
                  </div>
                </div>

                {/* Verified vs Unverified Skills */}
                {result.web_audit.skills_breakdown && (
                  <div className="space-y-2 pt-1 text-xs">
                    {result.web_audit.skills_breakdown.verified_skills?.length > 0 && (
                      <div>
                        <p className="text-[11px] font-semibold text-emerald-600 mb-1 flex items-center gap-1">
                          <CheckCircle2 className="h-3.5 w-3.5" /> Skills Verified with Public Code Proof ({result.web_audit.skills_breakdown.verified_skills.length})
                        </p>
                        <div className="flex flex-wrap gap-1.5">
                          {result.web_audit.skills_breakdown.verified_skills.map((skill, idx) => (
                            <span key={idx} className="rounded-full border border-emerald-500/30 bg-emerald-500/10 px-2.5 py-0.5 text-[11px] text-emerald-700 font-medium">
                              ✓ {skill}
                            </span>
                          ))}
                        </div>
                      </div>
                    )}

                    {result.web_audit.skills_breakdown.bonus_discovered_skills?.length > 0 && (
                      <div className="pt-1">
                        <p className="text-[11px] font-semibold text-primary mb-1 flex items-center gap-1">
                          <Sparkles className="h-3.5 w-3.5" /> Bonus Unclaimed Skills in Public Code
                        </p>
                        <div className="flex flex-wrap gap-1.5">
                          {result.web_audit.skills_breakdown.bonus_discovered_skills.map((skill, idx) => (
                            <span key={idx} className="rounded-full border border-border bg-card px-2.5 py-0.5 text-[11px] text-foreground font-medium">
                              + {skill}
                            </span>
                          ))}
                        </div>
                      </div>
                    )}
                  </div>
                )}
              </div>
            )}

            {/* Targeted Remediation Notice */}
            {result.focus_areas && result.focus_areas.length > 0 && (
              <div className="surface p-4">
                <div className="flex items-center gap-2 text-xs font-semibold text-amber-600">
                  <AlertTriangle className="h-4 w-4 shrink-0" />
                  <span>Targeted Remediation Focus Areas</span>
                </div>
                <div className="mt-2 flex flex-wrap gap-1.5">
                  {result.focus_areas.map((fa: any, idx: number) => {
                    const label = typeof fa === "string" ? fa : `${fa.name || fa.code} (Gap: +${fa.gap}, Target: ${fa.target_tier || 'Level ' + fa.required})`;
                    return (
                      <span key={idx} className="rounded-full border border-border bg-muted/40 px-3 py-1 text-xs text-foreground font-medium">
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
                  All 12 Competency Benchmarks
                </h4>
                <span className="text-[11px] text-muted-foreground">White marker = company requirement</span>
              </div>

              <div className="surface divide-y divide-border overflow-hidden">
                {result.skillset_gap?.map((item) => {
                  const isCritical = item.gap && item.gap_size >= 4;
                  const reqPct = Math.min(100, (item.required_level / 10) * 100);
                  const candPct = Math.min(100, (item.candidate_level / 10) * 100);
                  const baseLevel = result.baseline_levels?.[item.category_code] ?? item.candidate_level;
                  const levelLift = item.candidate_level - baseLevel;

                  return (
                    <div key={item.category_code} className="p-4 hover:bg-muted/30 transition-colors">
                      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-2 mb-2">
                        <div className="flex items-center gap-2">
                          <span className="rounded bg-muted px-2 py-0.5 font-mono text-[11px] font-semibold text-foreground">
                            {item.category_code}
                          </span>
                          <span className="text-sm font-medium">{item.category_name}</span>
                        </div>
                        <div className="flex items-center gap-2 text-xs">
                          <span className="text-muted-foreground">
                            Required: <strong className="text-foreground">Lvl {item.required_level}</strong> ({item.required_tier})
                          </span>
                          <span className="text-muted-foreground">·</span>
                          <span className="text-muted-foreground">
                            Candidate: <strong className={item.gap ? "text-amber-600 font-semibold" : "text-emerald-600 font-semibold"}>
                              Lvl {item.candidate_level}
                            </strong>
                            {levelLift > 0 && (
                              <span className="ml-1 text-emerald-600 font-bold">
                                (was {baseLevel}, +{levelLift})
                              </span>
                            )}
                          </span>
                          <span className="ml-2">
                            {!item.gap ? (
                              <span className="rounded-full border border-emerald-500/30 bg-emerald-500/10 px-2.5 py-0.5 text-[11px] font-semibold text-emerald-700 inline-flex items-center gap-1">
                                <Check className="h-3 w-3" /> Met
                              </span>
                            ) : isCritical ? (
                              <span className="rounded-full border border-rose-500/30 bg-rose-500/10 px-2.5 py-0.5 text-[11px] font-semibold text-rose-700 inline-flex items-center gap-1">
                                <AlertTriangle className="h-3 w-3" /> Critical (-{item.gap_size})
                              </span>
                            ) : (
                              <span className="rounded-full border border-amber-500/30 bg-amber-500/10 px-2.5 py-0.5 text-[11px] font-semibold text-amber-700">
                                Gap (-{item.gap_size})
                              </span>
                            )}
                          </span>
                        </div>
                      </div>

                      {/* Duel Progress Bar */}
                      <div className="relative mt-2 h-1.5 w-full rounded-full bg-muted overflow-hidden">
                        <div
                          className={cn(
                            "h-full rounded-full transition-all duration-500",
                            !item.gap ? "bg-emerald-600" : isCritical ? "bg-rose-500" : "bg-gold",
                          )}
                          style={{ width: `${candPct}%` }}
                        />
                        <div
                          className="absolute top-0 bottom-0 w-1 bg-foreground z-10 -ml-0.5"
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
        ) : (
          <div className="surface p-12 text-center space-y-4">
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
    <div className="surface flex items-center gap-4 p-6">
      <div className="rounded-full bg-muted p-3 text-primary">
        <Icon className="h-5 w-5" />
      </div>
      <div>
        <p className="text-xs text-muted-foreground">{label}</p>
        <p className="mt-1 font-semibold text-lg">{value}</p>
      </div>
    </div>
  );
}
