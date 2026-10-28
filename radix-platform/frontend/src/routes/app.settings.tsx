import { createFileRoute } from "@tanstack/react-router";
import { useEffect, useState } from "react";
import { RefreshCw } from "lucide-react";
import { Button } from "@/components/ui/button";
import { PageHeader } from "@/components/radix/ui";
import { checkHealth, SERVICES, type HealthState } from "@/lib/radix/services";
import { cn } from "@/lib/utils";

export const Route = createFileRoute("/app/settings")({
  head: () => ({
    meta: [
      { title: "Settings — RADIX" },
      { name: "description", content: "Service connections, motion and privacy." },
      { property: "og:title", content: "Settings — RADIX" },
      { property: "og:description", content: "Workspace settings." },
    ],
  }),
  component: Settings,
});

const LABEL: Record<HealthState, string> = { online: "Online", offline: "Offline", not_configured: "Not connected yet", unknown: "Configured" };

function Settings() {
  const [h, setH] = useState<Record<string, HealthState>>({});
  const run = () => SERVICES.forEach((s) => checkHealth(s).then((r) => setH((p) => ({ ...p, [s.key]: r }))));
  useEffect(run, []);
  return (
    <div className="space-y-6">
      <PageHeader eyebrow="Settings" title="Quiet controls.">
        <Button variant="outline" onClick={run}><RefreshCw /> Retry health check</Button>
      </PageHeader>
      <section className="surface p-6 md:p-8">
        <h2 className="font-display text-xl">Service connections</h2>
        <div className="mt-4 divide-y divide-border">
          {SERVICES.map((s) => {
            const st = h[s.key] ?? "unknown";
            return (
              <div key={s.key} className="flex items-center justify-between py-4">
                <div><p className="font-medium">{s.name} <span className="text-sm text-muted-foreground">· {s.role}</span></p>{s.note && <p className="text-xs text-muted-foreground">{s.note}</p>}</div>
                <span className="flex items-center gap-2 text-sm">
                  <span className={cn("h-2 w-2 rounded-full", st === "online" ? "bg-success" : st === "offline" ? "bg-destructive" : "bg-muted-foreground")} />{LABEL[st]}
                </span>
              </div>
            );
          })}
        </div>
      </section>
      <section className="border-t border-border pt-6">
        <h2 className="font-display text-lg">Motion</h2>
        <p className="mt-2 text-sm text-muted-foreground">RADIX follows your device's reduced-motion setting automatically.</p>
      </section>
      <section className="border-t border-border pt-6">
        <h2 className="font-display text-lg">Privacy</h2>
        <p className="mt-2 text-sm text-muted-foreground">Your email is never sent to skill matching. Scores are decision support, not a hiring guarantee.</p>
        <p className="mt-4 text-xs text-muted-foreground">RADIX Talent Match · frontend v0.1</p>
      </section>
    </div>
  );
}
