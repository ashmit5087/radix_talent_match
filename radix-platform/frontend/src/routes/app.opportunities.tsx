import { createFileRoute } from "@tanstack/react-router";
import { useState } from "react";
import { Bookmark, MapPin, Search } from "lucide-react";
import { Button } from "@/components/ui/button";
import { PageHeader } from "@/components/radix/ui";
import { demoOpportunities } from "@/lib/radix/mock";
import { cn } from "@/lib/utils";

export const Route = createFileRoute("/app/opportunities")({
  head: () => ({
    meta: [
      { title: "Opportunities — RADIX" },
      { name: "description", content: "Find roles that match your potential." },
      { property: "og:title", content: "Opportunities — RADIX" },
      { property: "og:description", content: "Explore roles and compare your skills." },
    ],
  }),
  component: Opportunities,
});

const FILTERS = ["All", "Internship", "Full-time", "Remote", "On-site"] as const;

function Opportunities() {
  const [f, setF] = useState<(typeof FILTERS)[number]>("All");
  const [q, setQ] = useState("");
  const [saved, setSaved] = useState<string[]>([]);
  const list = demoOpportunities.filter((o) =>
    (f === "All" || o.type === f || o.mode === f) &&
    `${o.title} ${o.company} ${o.skills.join(" ")}`.toLowerCase().includes(q.toLowerCase()));
  return (
    <div>
      <PageHeader eyebrow="Opportunities" title={<>Find roles that match <em className="text-amber-gradient">your potential.</em></>} />
      <p className="mb-6 text-sm text-muted-foreground">Opportunity discovery is a demo view. Connect a provider to load live roles.</p>
      <div className="relative mb-4">
        <Search className="absolute left-4 top-1/2 h-4 w-4 -translate-y-1/2 text-muted-foreground" />
        <input value={q} onChange={(e) => setQ(e.target.value)} placeholder="Search role, company or skill"
          className="h-11 w-full rounded-xl border border-input bg-card pl-11 pr-4 text-sm outline-none focus:ring-2 focus:ring-ring" />
      </div>
      <div className="mb-8 flex flex-wrap gap-2">
        {FILTERS.map((x) => (
          <button key={x} onClick={() => setF(x)} className={cn("rounded-full border px-4 py-1.5 text-sm transition-colors", f === x ? "border-gold bg-gold-soft text-foreground" : "border-border bg-card text-muted-foreground hover:text-foreground")}>{x}</button>
        ))}
      </div>
      <div className="surface divide-y divide-border overflow-hidden">
        {list.length === 0 && <p className="p-8 text-center text-sm text-muted-foreground">No roles match this search.</p>}
        {list.map((o) => (
          <article key={o.id} className={cn("flex flex-col gap-4 p-5 transition-colors hover:bg-secondary/50 md:flex-row md:items-center md:p-6", saved.includes(o.id) && "bg-gold-soft/40")}>
            <div className="min-w-0 flex-1">
              <h3 className="text-base font-semibold">{o.title}</h3>
              <p className="mt-0.5 flex flex-wrap items-center gap-x-1.5 text-sm text-muted-foreground">{o.company} <span>·</span> <MapPin className="h-3.5 w-3.5" />{o.location} · {o.mode} · {o.type}</p>
              <div className="mt-3 flex flex-wrap gap-1.5">{o.skills.slice(0, 4).map((s) => <span key={s} className="rounded-md bg-secondary px-2 py-0.5 text-xs text-secondary-foreground">{s}</span>)}</div>
            </div>
            <div className="flex items-center gap-2">
              <Button size="sm" variant="outline">View role</Button><Button size="sm" variant="ghost">Compare skills</Button>
              <button className="rounded-lg p-2 hover:bg-secondary" aria-label={saved.includes(o.id) ? "Unsave" : "Save"} onClick={() => setSaved((s) => s.includes(o.id) ? s.filter((i) => i !== o.id) : [...s, o.id])}>
                <Bookmark className={cn("h-5 w-5", saved.includes(o.id) ? "fill-gold text-gold" : "text-muted-foreground")} />
              </button>
            </div>
          </article>
        ))}
      </div>
    </div>
  );
}
