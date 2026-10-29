import { createFileRoute, Link } from "@tanstack/react-router";
import { useState } from "react";
import { Plus, Search } from "lucide-react";
import { Button } from "@/components/ui/button";
import { EmptyState, PageHeader } from "@/components/radix/ui";
import { getSavedAssessments } from "@/lib/radix/session";

export const Route = createFileRoute("/app/assessments/")({
  head: () => ({
    meta: [
      { title: "Assessments — RADIX" },
      { name: "description", content: "Browse your skill-match assessments and start new ones." },
      { property: "og:title", content: "Assessments — RADIX" },
      { property: "og:description", content: "Your skill-match assessments." },
    ],
  }),
  component: AssessmentsPage,
});

function AssessmentsPage() {
  const [q, setQ] = useState("");
  const rows = getSavedAssessments().filter((a) => `${a.role} ${a.company}`.toLowerCase().includes(q.toLowerCase()));
  return (
    <div>
      <PageHeader eyebrow="Assessments" title="Every role you've measured against.">
        <Button asChild><Link to="/app/assessments/new"><Plus /> New assessment</Link></Button>
      </PageHeader>
      <div className="mb-6 flex items-center gap-3">
        <div className="relative flex-1">
          <Search className="absolute left-4 top-1/2 h-4 w-4 -translate-y-1/2 text-muted-foreground" />
          <input value={q} onChange={(e) => setQ(e.target.value)} placeholder="Search role or company"
            className="h-11 w-full rounded-full border border-input bg-card pl-11 pr-4 text-sm outline-none focus:ring-2 focus:ring-ring" />
        </div>
        
      </div>
      {rows.length === 0 ? (
        <EmptyState title="No assessments yet" body="Pick a profile and a job description to see how your skills line up."
          action={<Button asChild><Link to="/app/assessments/new">New assessment</Link></Button>} />
      ) : (
        <div className="surface divide-y divide-border">
          {rows.map((a) => (
            <Link key={a.id} to="/app/assessments/$assessmentId" params={{ assessmentId: a.id }}
              className="grid grid-cols-[1fr_auto] items-center gap-4 p-6 transition-colors hover:bg-accent/40 md:grid-cols-[2fr_1.5fr_1fr_auto]">
              <div><p className="font-medium">{a.role}</p><p className="text-sm text-muted-foreground">{a.company}</p></div>
              <p className="hidden truncate text-sm text-muted-foreground md:block">{a.jd_file}</p>
              <p className="hidden text-sm text-muted-foreground md:block">{a.updated_at}</p>
              <div className="text-right">
                <span className="font-display text-2xl tabular-nums">{a.match.match_score}</span>
                <span className="text-xs text-muted-foreground">/100</span>
              </div>
            </Link>
          ))}
        </div>
      )}
    </div>
  );
}
