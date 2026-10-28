import { createFileRoute, Link } from "@tanstack/react-router";
import { useState, useEffect } from "react";
import { Check, MapPin, Pencil, Plus, Save, Upload, UserRound } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { LevelBar } from "@/components/radix/ui";
import { CATEGORY_LABELS, type SkillCategory, type CandidateProfile } from "@/lib/radix/contracts";
import { getSavedProfile, hasSavedProfile, setSavedProfile } from "@/lib/radix/session";
import { cn } from "@/lib/utils";

export const Route = createFileRoute("/app/profile")({
  head: () => ({
    meta: [
      { title: "My Profile — RADIX" },
      { name: "description", content: "Your skills, projects and experience in one record." },
      { property: "og:title", content: "My Profile — RADIX" },
      { property: "og:description", content: "Candidate profile." },
    ],
  }),
  component: Profile,
});

const TABS = ["Skills", "About", "Projects & experience", "Education", "Certifications", "Preferences"] as const;

function Profile() {
  const [tab, setTab] = useState<(typeof TABS)[number]>("Skills");
  const [profile, setProfile] = useState<CandidateProfile | null>(getSavedProfile());
  const [manualSkill, setManualSkill] = useState("");
  const [manualSkillCategory, setManualSkillCategory] = useState<SkillCategory>("OTHER");
  const [manualProject, setManualProject] = useState("");
  const [manualExperience, setManualExperience] = useState("");
  const [manualEducation, setManualEducation] = useState("");
  const [manualCertification, setManualCertification] = useState("");
  const [manualRole, setManualRole] = useState("");
  const isCustom = hasSavedProfile() && !!profile;

  useEffect(() => {
    setProfile(getSavedProfile());
  }, []);

  if (!profile) {
    return (
      <div className="py-12 animate-page">
        <div className="surface max-w-xl mx-auto p-10 text-center rounded-2xl border border-border">
          <div className="mx-auto flex h-14 w-14 items-center justify-center rounded-full bg-primary/10 text-primary">
            <UserRound className="h-7 w-7" />
          </div>
          <h2 className="font-display mt-6 text-2xl font-semibold">No profile loaded</h2>
          <p className="mt-2 text-sm text-muted-foreground leading-relaxed">
            Please import your resume in onboarding to generate your profile with verified skills and experience.
          </p>
          <div className="mt-6 flex justify-center">
            <Button asChild>
              <Link to="/onboarding"><Upload className="mr-2 h-4 w-4" /> Import Resume</Link>
            </Button>
          </div>
        </div>
      </div>
    );
  }

  const p = profile;
  const groups = p.skills.reduce<Record<string, typeof p.skills>>((acc, s) => {
    (acc[s.category] ??= []).push(s);
    return acc;
  }, {});

  const sections = [
    { key: "personal", label: "Personal info", complete: Boolean(p.full_name.trim() && p.headline.trim() && p.location?.trim()) },
    { key: "education", label: "Education", complete: p.education.some((e) => (e.institution ?? "").trim() || (e.degree ?? "").trim()) },
    { key: "skills", label: "Skills", complete: p.skills.length > 0 },
    { key: "projects", label: "Projects", complete: p.projects.some((project) => (project.title ?? "").trim() || (project.summary ?? "").trim()) },
    { key: "experience", label: "Experience", complete: p.experience.some((experience) => (experience.company ?? "").trim() || (experience.title ?? "").trim()) },
    { key: "certifications", label: "Certifications", complete: p.certifications.some((certification) => certification.trim()) },
    { key: "preferred", label: "Preferred roles", complete: p.preferred_roles.some((role) => role.trim()) },
  ];
  const completenessPercent = isCustom
    ? Math.round((sections.filter((section) => section.complete).length / sections.length) * 100)
    : 0;

  function updateProfile(patch: Partial<CandidateProfile>) {
    if (!profile) return;
    const updated = { ...profile, ...patch };
    setProfile(updated);
    setSavedProfile(updated);
  }

  function addManualSkill() {
    const name = manualSkill.trim();
    if (!name || p.skills.some((skill) => skill.name.toLowerCase() === name.toLowerCase())) return;
    updateProfile({
      skills: [...p.skills, { name, category: manualSkillCategory, confidence: "medium", evidence: "Added manually", source: "manual" }],
    });
    setManualSkill("");
    setManualSkillCategory("OTHER");
  }

  function addManualEntry(kind: "project" | "experience" | "education" | "certification" | "role") {
    const value = ({
      project: manualProject,
      experience: manualExperience,
      education: manualEducation,
      certification: manualCertification,
      role: manualRole,
    } as const)[kind].trim();
    if (!value) return;
    if (kind === "project") updateProfile({ projects: [...p.projects, { title: value, summary: "Added manually" }] });
    if (kind === "experience") updateProfile({ experience: [...p.experience, { company: value, title: "Added manually", period: "" }] });
    if (kind === "education") updateProfile({ education: [...p.education, { institution: value, degree: "", year: "" }] });
    if (kind === "certification") updateProfile({ certifications: [...p.certifications, value] });
    if (kind === "role") updateProfile({ preferred_roles: [...p.preferred_roles, value] });
    ({ project: setManualProject, experience: setManualExperience, education: setManualEducation, certification: setManualCertification, role: setManualRole } as const)[kind]("");
  }

  return (
    <div>
      <div className="mb-10 flex flex-col gap-6 md:flex-row md:items-end md:justify-between">
        <div>
          <div className="flex items-center gap-3">
            <h1 className="font-display text-3xl md:text-[34px] leading-tight">{p.full_name}</h1>
            
            {isCustom && (
              <span className="rounded-full bg-success/15 px-3 py-1 text-xs text-success font-medium">
                Active profile ({p.skills.length} skills)
              </span>
            )}
          </div>
          <p className="mt-2 text-muted-foreground">{p.headline || "Candidate Profile"}</p>
          {p.location && (
            <p className="mt-1 flex items-center gap-1.5 text-sm text-muted-foreground">
              <MapPin className="h-3.5 w-3.5" />{p.location}
            </p>
          )}
        </div>
        <div className="flex gap-2">
          <Button asChild variant="outline">
            <Link to="/onboarding"><Pencil /> Upload new resume</Link>
          </Button>
        </div>
      </div>

      <div className="mb-8 rounded-xl bg-secondary/60 p-5">
        <div className="flex items-baseline justify-between">
          <p className="font-medium">Your profile is {completenessPercent}% complete</p>
          <p className="text-xs text-muted-foreground">Completeness tracks profile information, not your job-match score.</p>
        </div>
        <div className="mt-4"><LevelBar value={completenessPercent} max={100} /></div>
        <div className="mt-4 flex flex-wrap gap-x-5 gap-y-2 text-sm">
          {sections.map((s) => {
            const isSectionDone = s.complete;
            return (
              <span key={s.key} className={cn("flex items-center gap-1.5", isSectionDone ? "text-foreground" : "text-muted-foreground")}>
                {isSectionDone ? <Check className="h-3.5 w-3.5 text-success" /> : <span className="h-3.5 w-3.5 rounded-full border border-muted-foreground" />}
                {s.label}
              </span>
            );
          })}
        </div>
      </div>

      <section className="mb-8 rounded-xl border border-border bg-card p-5">
        <div className="flex items-start justify-between gap-4">
          <div>
            <h2 className="font-semibold">Complete missing details</h2>
            <p className="mt-1 text-sm text-muted-foreground">
              Anything added here is saved to your profile and included in future assessments.
            </p>
          </div>
          <Save className="h-4 w-4 text-muted-foreground" />
        </div>
        <div className="mt-5 grid gap-4 md:grid-cols-2">
          {(!p.location || !p.headline || p.headline === "Candidate Profile") && (
            <>
              <div className="space-y-2">
                <label className="text-xs font-semibold text-muted-foreground">Location</label>
                <Input
                  placeholder="City, country"
                  value={p.location ?? ""}
                  onChange={(event) => updateProfile({ location: event.target.value })}
                />
              </div>
              <div className="space-y-2">
                <label className="text-xs font-semibold text-muted-foreground">Headline or summary</label>
                <Input
                  placeholder="e.g. Data analyst with Python and SQL experience"
                  value={p.headline === "Candidate Profile" ? "" : p.headline}
                  onChange={(event) => updateProfile({ headline: event.target.value })}
                />
              </div>
            </>
          )}
          {[
            ["skill", "Skill not found by parser", manualSkill, setManualSkill, addManualSkill],
            ["project", "Project not found by parser", manualProject, setManualProject, () => addManualEntry("project")],
            ["experience", "Experience not found by parser", manualExperience, setManualExperience, () => addManualEntry("experience")],
            ["education", "Education not found by parser", manualEducation, setManualEducation, () => addManualEntry("education")],
            ["certification", "Certification", manualCertification, setManualCertification, () => addManualEntry("certification")],
            ["role", "Preferred role", manualRole, setManualRole, () => addManualEntry("role")],
          ].map(([key, placeholder, value, setter, submit]) => (
            <div key={key} className="flex items-end gap-2">
              <div className="flex-1 space-y-2">
                <label className="text-xs font-semibold text-muted-foreground">{placeholder}</label>
                <div className="flex gap-2">
                  <Input
                    placeholder={`Add ${placeholder.toLowerCase()}`}
                    value={value as string}
                    onChange={(event) => (setter as (value: string) => void)(event.target.value)}
                    onKeyDown={(event) => { if (event.key === "Enter") (submit as () => void)(); }}
                  />
                  {key === "skill" && (
                    <select
                      className="h-9 rounded-md border border-input bg-transparent px-2 text-sm"
                      value={manualSkillCategory}
                      aria-label="Skill category"
                      onChange={(event) => setManualSkillCategory(event.target.value as SkillCategory)}
                    >
                      {Object.entries(CATEGORY_LABELS).map(([category, label]) => (
                        <option key={category} value={category}>{label}</option>
                      ))}
                    </select>
                  )}
                </div>
              </div>
              <Button type="button" size="icon" variant="outline" aria-label={`Add ${placeholder}`} onClick={submit as () => void}>
                <Plus className="h-4 w-4" />
              </Button>
            </div>
          ))}
        </div>
      </section>

      <div className="mb-6 flex gap-1 overflow-x-auto border-b border-border">
        {TABS.map((t) => (
          <button
            key={t}
            onClick={() => setTab(t)}
            className={cn(
              "whitespace-nowrap border-b-2 px-4 py-3 text-sm transition-colors",
              tab === t ? "border-primary text-foreground" : "border-transparent text-muted-foreground hover:text-foreground"
            )}
          >
            {t} {t === "Skills" && `(${p.skills.length})`}
          </button>
        ))}
      </div>

      {tab === "Skills" && (
        <div className="divide-y divide-border">
          {Object.keys(groups).length === 0 ? (
            <p className="py-6 text-sm text-muted-foreground">No skills recorded yet. Import a resume from onboarding to populate skills.</p>
          ) : (
            Object.entries(groups).map(([cat, skills]) => (
              <div key={cat} className="py-6 first:pt-2">
                <h3 className="text-[17px] font-semibold">{CATEGORY_LABELS[cat as SkillCategory] ?? cat}</h3>
                {skills.map((s) => (
                  <div key={s.name} className="mt-4 border-t border-border pt-4">
                    <div className="flex items-center justify-between">
                      <span className="font-medium">{s.name}</span>
                      <span className="flex gap-1.5 text-xs">
                        <span className="rounded-md bg-gold-soft px-2 py-0.5">{s.confidence} confidence</span>
                        <span className="rounded-md bg-secondary px-2 py-0.5 text-muted-foreground">Source: {s.source ?? "extracted"}</span>
                      </span>
                    </div>
                    <p className="mt-1 text-sm text-muted-foreground">{s.evidence ?? <em>Extracted from resume</em>}</p>
                  </div>
                ))}
              </div>
            ))
          )}
        </div>
      )}

      {tab === "About" && (
        <div className="py-6 space-y-4">
          <div>
            <h3 className="text-sm font-semibold text-muted-foreground">Full Name</h3>
            <p className="mt-1 font-medium">{p.full_name}</p>
          </div>
          {p.location && (
            <div>
              <h3 className="text-sm font-semibold text-muted-foreground">Location</h3>
              <p className="mt-1">{p.location}</p>
            </div>
          )}
          {p.headline && (
            <div>
              <h3 className="text-sm font-semibold text-muted-foreground">Summary / Headline</h3>
              <p className="mt-1">{p.headline}</p>
            </div>
          )}
        </div>
      )}

      {tab === "Projects & experience" && (
        <div className="py-6 space-y-6">
          <section>
            <h3 className="text-lg font-semibold">Projects</h3>
            {p.projects.length === 0 ? (
              <p className="mt-2 text-sm text-muted-foreground">No projects listed yet.</p>
            ) : (
              p.projects.map((proj) => (
                <div key={proj.title} className="mt-3 rounded-lg border border-border p-4">
                  <h4 className="font-medium">{proj.title}</h4>
                  <p className="mt-1 text-sm text-muted-foreground">{proj.summary}</p>
                </div>
              ))
            )}
          </section>
          <section>
            <h3 className="text-lg font-semibold">Experience</h3>
            {p.experience.length === 0 ? (
              <p className="mt-2 text-sm text-muted-foreground">No experience entries listed yet.</p>
            ) : (
              p.experience.map((exp) => (
                <div key={exp.company} className="mt-3 rounded-lg border border-border p-4">
                  <h4 className="font-medium">{exp.title} · {exp.company}</h4>
                  <p className="mt-1 text-sm text-muted-foreground">{exp.period}</p>
                </div>
              ))
            )}
          </section>
        </div>
      )}

      {tab === "Education" && (
        <div className="py-6 space-y-3">
          {p.education.length === 0 ? (
            <p className="text-sm text-muted-foreground">No education entries listed yet.</p>
          ) : (
            p.education.map((edu) => (
              <div key={edu.institution} className="rounded-lg border border-border p-4">
                <h4 className="font-medium">{edu.degree}</h4>
                <p className="text-sm text-muted-foreground">{edu.institution} · {edu.year}</p>
              </div>
            ))
          )}
        </div>
      )}

      {tab === "Certifications" && (
        <div className="py-6">
          {p.certifications.length === 0 ? (
            <p className="text-sm text-muted-foreground">No certifications listed yet.</p>
          ) : (
            <ul className="list-disc pl-5 text-sm space-y-1">
              {p.certifications.map((c) => <li key={c}>{c}</li>)}
            </ul>
          )}
        </div>
      )}

      {tab === "Preferences" && (
        <div className="py-6">
          <h3 className="text-sm font-semibold text-muted-foreground">Preferred Roles</h3>
          {p.preferred_roles.length === 0 ? (
            <p className="mt-1 text-sm text-muted-foreground">No preferences specified.</p>
          ) : (
            <div className="mt-2 flex flex-wrap gap-2">
              {p.preferred_roles.map((r) => (
                <span key={r} className="rounded-full bg-secondary px-3 py-1 text-xs font-medium">{r}</span>
              ))}
            </div>
          )}
        </div>
      )}
    </div>
  );
}
