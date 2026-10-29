import { createFileRoute, Link } from "@tanstack/react-router";
import { useEffect, useRef, useState, type ReactNode } from "react";
import heroVideo from "@/assets/hero-day.mp4.asset.json";
import { ArrowRight, FileSearch, Menu, Sparkles, Target, UserRound, X } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Wordmark } from "@/components/radix/ui";

const VIDEO = "/images/hero-poster.jpg"; // CDN video replaced with local poster for dev

/** Fades children in (small upward move) the first time they enter the viewport. */
function Reveal({ children, delay = 0, className = "" }: { children: ReactNode; delay?: number; className?: string }) {
  const ref = useRef<HTMLDivElement>(null);
  const [shown, setShown] = useState(false);
  useEffect(() => {
    const el = ref.current;
    if (!el || typeof IntersectionObserver === "undefined") return setShown(true);
    const io = new IntersectionObserver(([e]) => { if (e?.isIntersecting) { setShown(true); io.disconnect(); } }, { threshold: 0.15, rootMargin: "0px 0px -40px 0px" });
    io.observe(el);
    return () => io.disconnect();
  }, []);
  return <div ref={ref} data-shown={shown} className={`reveal ${className}`} style={{ transitionDelay: `${delay}ms` }}>{children}</div>;
}

/** Subtle parallax: shifts the hero video up to 32px over the hero's scroll range. */
function useParallax() {
  const ref = useRef<HTMLDivElement>(null);
  useEffect(() => {
    const el = ref.current;
    if (!el) return;
    const mq = window.matchMedia("(prefers-reduced-motion: reduce), (max-width: 767px)");
    let raf = 0;
    const update = () => {
      raf = 0;
      if (mq.matches) { el.style.transform = ""; return; }
      const h = el.parentElement?.offsetHeight || window.innerHeight;
      const p = Math.min(1, Math.max(0, window.scrollY / h));
      el.style.transform = `translate3d(0, ${(p * 32).toFixed(1)}px, 0)`;
    };
    const onScroll = () => { if (!raf) raf = requestAnimationFrame(update); };
    window.addEventListener("scroll", onScroll, { passive: true });
    mq.addEventListener("change", update);
    update();
    return () => { window.removeEventListener("scroll", onScroll); mq.removeEventListener("change", update); if (raf) cancelAnimationFrame(raf); };
  }, []);
  return ref;
}

export const Route = createFileRoute("/")({
  head: () => ({
    meta: [
      { title: "RADIX — A clearer path to the work you want" },
      { name: "description", content: "Understand your strengths, uncover the skills to build next, and find roles that fit the work you can prove." },
      { property: "og:title", content: "RADIX — A clearer path to the work you want" },
      { property: "og:description", content: "A calm, evidence-first career workspace for candidates." },
      { property: "og:type", content: "website" },
      { name: "twitter:card", content: "summary_large_image" },
    ],
  }),
  component: Landing,
});

const STEPS = [
  { icon: UserRound, n: "01", t: "Build your profile", d: "Import a resume or start by hand. Review every extracted detail before it's saved." },
  { icon: FileSearch, n: "02", t: "Compare skills with a role", d: "Drop in a job description and see exactly where your evidence meets its requirements." },
  { icon: Target, n: "03", t: "Turn gaps into a plan", d: "Get a short, ranked list of actions — in the order that moves you furthest." },
];

function Landing() {
  const [menu, setMenu] = useState(false);
  const parallax = useParallax();
  const links = [
    { href: "#how", label: "How it works" },
    { href: "#evidence", label: "For candidates" },
  ];
  return (
    <div className="landing bg-background">
      <section className="relative h-[92svh] min-h-[660px] overflow-hidden">
        <div ref={parallax} className="absolute inset-x-0 -top-10 -bottom-10 bg-sky will-change-transform">
          <video
            className="absolute inset-0 h-full w-full object-cover object-[50%_65%]"
            src={VIDEO} poster="/images/hero-poster.jpg" autoPlay loop muted playsInline preload="auto" aria-hidden
          />
        </div>
        <div className="absolute inset-0 bg-veil-day" />

        <nav className="relative z-10 mx-auto mt-5 flex max-w-[1440px] items-center justify-between px-5 md:px-10">
          <div className="glass flex w-full items-center justify-between rounded-full py-2 pl-5 pr-2 text-foreground">
            <Link to="/"><Wordmark /></Link>
            <div className="hidden items-center gap-8 text-sm text-muted-foreground md:flex">
              {links.map((l) => <a key={l.href} href={l.href} className="transition-colors hover:text-primary">{l.label}</a>)}
            </div>
            <Button asChild className="hidden md:inline-flex"><Link to="/onboarding">Get started</Link></Button>
            <Button variant="ghost" size="icon" className="md:hidden" aria-label={menu ? "Close menu" : "Open menu"} aria-expanded={menu} onClick={() => setMenu(!menu)}>
              {menu ? <X className="h-5 w-5" /> : <Menu className="h-5 w-5" />}
            </Button>
          </div>
        </nav>
        {menu && (
          <div className="glass absolute inset-x-0 z-20 mx-5 mt-2 flex flex-col gap-1 rounded-lg p-3 text-foreground md:hidden">
            {links.map((l) => <a key={l.href} href={l.href} onClick={() => setMenu(false)} className="rounded-md px-4 py-3 hover:bg-accent">{l.label}</a>)}
            <Button asChild className="mt-2"><Link to="/onboarding">Get started</Link></Button>
          </div>
        )}

        <div className="relative z-10 mx-auto flex h-[calc(100%-96px)] max-w-[1440px] flex-col justify-end px-5 pb-12 md:px-10 md:pb-16">

          <h1 className="animate-rise font-display max-w-4xl text-5xl leading-[1.02] text-foreground sm:text-7xl lg:text-8xl" style={{ animationDelay: "80ms" }}>
            A clearer path to the <em className="text-primary">work you want.</em>
          </h1>
          <p className="animate-rise mt-6 max-w-xl text-base leading-relaxed text-foreground/80 md:text-lg" style={{ animationDelay: "180ms" }}>
            Understand your strengths, uncover the skills to build next, and find opportunities that fit the work you can prove.
          </p>
          <div className="animate-rise mt-10 flex flex-wrap gap-3" style={{ animationDelay: "280ms" }}>
            <Button asChild size="lg"><Link to="/onboarding">Get started <ArrowRight /></Link></Button>
            <Button asChild size="lg" variant="outline" className="bg-background/70"><a href="#how">See how it works</a></Button>
          </div>
        </div>
      </section>

      <section id="how" className="relative mx-auto max-w-[1440px] scroll-mt-8 px-5 py-16 md:px-10 md:py-24">
        <Reveal>
          <p className="text-xs font-semibold text-primary">How it works / 01</p>
          <h2 className="landing-heading mt-4 max-w-2xl text-3xl leading-tight md:text-5xl">Three quiet steps.</h2>
        </Reveal>
        <div className="mt-12 grid gap-10 border-y border-border py-10 md:grid-cols-3 md:gap-0">
          {STEPS.map((s, i) => (
            <Reveal key={s.n} delay={i * 90} className="group md:px-8 md:first:pl-0 md:last:pr-0 md:border-r md:border-border md:last:border-r-0">
              <div className="flex items-center justify-between">
                <span className="flex h-11 w-11 items-center justify-center rounded-full bg-accent"><s.icon className="h-5 w-5 text-primary" /></span>
                <span className="font-display text-4xl text-muted-foreground/40">{s.n}</span>
              </div>
              <h3 className="landing-heading mt-8 text-xl leading-snug">{s.t}</h3>
              <p className="mt-3 max-w-sm text-[15px] leading-7 text-muted-foreground">{s.d}</p>
            </Reveal>
          ))}
        </div>
      </section>

      <section id="evidence" className="mx-auto grid max-w-[1440px] scroll-mt-8 items-center gap-10 px-5 pb-20 md:grid-cols-2 md:gap-16 md:px-10 md:pb-24">
        <Reveal className="relative overflow-hidden rounded-lg">
          <img src="/images/hero-poster.jpg" alt="Students studying outdoors in a bright garden with books and flowers" className="aspect-[4/3] w-full object-cover" loading="lazy" />
        </Reveal>
        <Reveal delay={120}>
          <p className="text-xs font-semibold text-primary">Built around evidence / 02</p>
          <h2 className="landing-heading mt-4 text-3xl leading-tight md:text-4xl">Honest about where every skill comes from.</h2>
          <p className="mt-6 text-base leading-7 text-muted-foreground">
            Extracted, self-reported, verified, partial, missing — RADIX keeps them distinct. You always see the job's requirement next to your own proof, never an invented one.
          </p>
          <ul className="mt-8 space-y-3 text-sm">
            {["Gaps shown first, critical ones clearly marked", "Exact reasoning for every match", "A score you can trace — never a hire probability"].map((t) => (
              <li key={t} className="flex items-start gap-3 border-t border-border pt-3 leading-relaxed"><span className="mt-2 h-1.5 w-1.5 shrink-0 rounded-full bg-primary" />{t}</li>
            ))}
          </ul>
        </Reveal>
      </section>

      <section className="border-y border-border bg-secondary">
        <Reveal className="mx-auto max-w-[1440px] px-5 py-16 text-center md:px-10 md:py-20">
          <h2 className="landing-heading relative text-3xl md:text-5xl">A useful next step.</h2>
          <p className="relative mx-auto mt-4 max-w-md text-muted-foreground">Set up your profile in a few minutes. Nothing is saved until you confirm it.</p>
          <Button asChild size="lg" className="relative mt-8"><Link to="/onboarding">Begin onboarding <ArrowRight /></Link></Button>
        </Reveal>
      </section>

      <footer className="border-t border-border">
        <div className="mx-auto flex max-w-[1440px] flex-col gap-3 px-5 py-8 text-sm text-muted-foreground md:flex-row md:items-center md:justify-between md:px-10">
          <Wordmark className="text-foreground" />
          <p>Your data stays yours. Decision support, not a hiring guarantee.</p>
        </div>
      </footer>
    </div>
  );
}
