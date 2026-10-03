/**
 * Public landing page ("/") — what Atlas AI (a Web Triggers product) is, who it's for, how it works,
 * and its honest limits. First-time visitors get a short "Get started" dialog.
 * The app itself lives at /app. No API calls here, so it loads instantly and works even when
 * the backend or the AI providers are down.
 */
import { useEffect, useState } from 'react'
import { Link, useNavigate } from 'react-router-dom'
import { motion } from 'framer-motion'
import {
  ArrowRight, Briefcase, Building2, Code2, Download, FileSearch, FileText, GitCompareArrows,
  HardHat, Lock, MessageSquareText, Quote, Scale, ShieldCheck, Sparkles, Upload,
} from 'lucide-react'
import { cn } from '@/lib/utils'
import { Button, Modal, STATUS_ICONS } from '@/components/kit'
import { Logo, ThemeToggle } from '@/components/layout'

// Source link hidden for now:
// const REPO = 'https://github.com/webtriggers11-pixel/atlas-ai'
const WEBTRIGGERS = 'https://www.webtriggers.online'
const WELCOME_KEY = 'atlas-welcome-seen'

// Vercel-style headline emphasis: text fades from full contrast to grey
const GRADIENT_TEXT = 'bg-gradient-to-b from-foreground to-muted bg-clip-text pr-2 text-transparent'

// ── Content ──────────────────────────────────────────────────────────────────

const STEPS = [
  { icon: Upload, title: 'Add the checklist', text: 'What the document should contain: a review checklist, a job description, a specification, tender conditions.' },
  { icon: FileText, title: 'Add the document', text: 'What actually exists: the contract, the resume, the design docs, the bid. PDF, Word or text.' },
  { icon: Sparkles, title: 'Confirm the points', text: 'Atlas turns the checklist into numbered points. You edit, merge or reject them before anything is judged.' },
  { icon: FileSearch, title: 'Get evidence-backed results', text: 'Every point is marked covered, partial, missing or in conflict — each with the exact quote it relied on.' },
]

const RESULTS = [
  { status: 'covered', label: 'Covered', text: 'The point is there. You see the sentence that proves it.' },
  { status: 'partial', label: 'Partial', text: 'Dealt with, but a detail is missing — e.g. a liability clause with no cap.' },
  { status: 'missing', label: 'Missing', text: 'Nothing in the document deals with this point.' },
  { status: 'conflict', label: 'Conflict', text: 'The document says something different — 7 days instead of 30.' },
  { status: 'unclear', label: 'Unclear', text: 'Related text exists, but a person should decide.' },
]

// Same idea — "what should exist" vs "what exists" — in different jobs
const USE_CASES = [
  {
    key: 'legal', icon: Scale, label: 'Legal',
    who: 'Lawyers, in-house counsel, paralegals',
    reference: 'Firm’s review checklist or the client’s term sheet',
    existing: 'The counterparty’s draft contract',
    finding: { status: 'conflict', point: 'Termination needs 30 days’ notice', quote: '“Either party may terminate this Agreement by giving 7 days’ written notice.”' },
  },
  {
    key: 'hiring', icon: Briefcase, label: 'Hiring',
    who: 'Job seekers, recruiters, hiring managers',
    reference: 'The job description',
    existing: 'The resume or CV',
    finding: { status: 'partial', point: '3+ years building REST APIs', quote: '“Built FastAPI services for asset maintenance (2 years).”' },
  },
  {
    key: 'software', icon: Code2, label: 'Software',
    who: 'Business analysts, tech leads, QA',
    reference: 'Requirements (SRS / BRD)',
    existing: 'Design documents and API docs',
    finding: { status: 'missing', point: 'Accounts lock after 5 failed logins', quote: 'No passage found in the design documents.' },
  },
  {
    key: 'construction', icon: HardHat, label: 'Construction',
    who: 'Civil engineers, consultants, site QA',
    reference: 'Project specification or BOQ',
    existing: 'Contractor submittals and method statements',
    finding: { status: 'covered', point: 'Concrete grade M30 for columns', quote: '“All RCC columns shall be cast in M30 grade concrete.”' },
  },
  {
    key: 'compliance', icon: ShieldCheck, label: 'Compliance',
    who: 'Compliance, HR and policy teams',
    reference: 'Legal or regulatory requirements',
    existing: 'The company’s policy documents',
    finding: { status: 'partial', point: 'Users can ask for their data to be deleted', quote: '“Users may contact support about their data.” (no deletion right stated)' },
  },
  {
    key: 'tenders', icon: Building2, label: 'Tenders',
    who: 'Bid teams and procurement',
    reference: 'Tender’s mandatory conditions',
    existing: 'Your bid documents',
    finding: { status: 'missing', point: 'Bid security of 2% must be enclosed', quote: 'No passage found in the bid documents.' },
  },
]

const FEATURES = [
  { icon: Quote, title: 'Every result has proof', text: 'Findings cite the exact sentence and page. Quotes are checked word-for-word against your document before they are shown.' },
  { icon: MessageSquareText, title: 'Ask in plain English', text: '“What should I negotiate?” “Which skills am I missing?” Answers come with the passages they used.' },
  { icon: FileSearch, title: 'A second look on doubtful points', text: 'Re-check a finding and Atlas searches again more carefully. It only changes a result when it finds real evidence.' },
  { icon: Download, title: 'Reports you can share', text: 'Download a PDF summary, a Markdown report, or a CSV checklist for your file or your client.' },
  { icon: GitCompareArrows, title: 'Compare versions', text: 'Run again on the revised draft and see exactly which points improved and which got worse.' },
  { icon: Lock, title: 'Private when it matters', text: 'Optional sign-in keeps each person’s work separate. For confidential files, run it on your own machine with a local AI.' },
]

const FAQ = [
  {
    q: 'Is it accurate?',
    a: 'In our tests on labelled document sets it agrees with a careful human reviewer about 8 times out of 10. That is why every finding shows its quote — you check the evidence and make the call. Treat it as a fast first review, not a final opinion.',
  },
  {
    q: 'Can I upload confidential client documents?',
    a: 'Not on the free online version: it uses outside AI services (Google Gemini, Groq), and free tiers may use what is sent to improve their models. Use sample, template or redacted documents here. For confidential work, Atlas can run entirely on your own computer with a local AI, so nothing leaves your office.',
  },
  {
    q: 'Which files work?',
    a: 'PDF (with selectable text), Word (.docx), plain text and Markdown, up to 20 MB each. Scanned paper (photos of pages) is not read yet.',
  },
  {
    q: 'Does it give legal, hiring or engineering advice?',
    a: 'No. It finds where things are, where they are missing and where they disagree. The judgement stays with you.',
  },
  {
    q: 'Do I need to be technical?',
    a: 'No. You upload two sets of documents, confirm the checklist points, and read the results. Everything is in plain English.',
  },
]

// ── Pieces ───────────────────────────────────────────────────────────────────

const STATUS_TEXT = {
  covered: 'text-covered bg-covered/10 border-covered/30',
  partial: 'text-partial bg-partial/10 border-partial/30',
  missing: 'text-missing bg-missing/10 border-missing/30',
  conflict: 'text-conflict bg-conflict/10 border-conflict/30',
  unclear: 'text-unclear bg-unclear/10 border-unclear/30',
}

/** Rounded status badge with icon (never colour alone). */
function Badge({ status, children }) {
  const Icon = STATUS_ICONS[status]
  return (
    <span className={cn('inline-flex items-center gap-1.5 rounded-pill border px-2.5 py-0.5 text-xs font-medium whitespace-nowrap', STATUS_TEXT[status])}>
      <Icon className="size-3.5" aria-hidden />
      {children}
    </span>
  )
}

/** Section wrapper with a consistent width, spacing and fade-in. */
function Section({ id, className, children }) {
  return (
    <motion.section
      id={id}
      initial={{ opacity: 0, y: 16 }}
      whileInView={{ opacity: 1, y: 0 }}
      viewport={{ once: true, margin: '-80px' }}
      transition={{ duration: 0.45, ease: 'easeOut' }}
      className={cn('mx-auto w-full max-w-6xl scroll-mt-20 px-4 sm:px-6', className)}
    >
      {children}
    </motion.section>
  )
}

/** Small cobalt label + serif heading + optional intro. */
function Heading({ eyebrow, title, children }) {
  return (
    <div className="max-w-2xl">
      <p className="text-xs font-semibold tracking-[0.18em] text-secondary uppercase">{eyebrow}</p>
      <h2 className="mt-3 font-serif text-4xl leading-tight tracking-tight sm:text-5xl">{title}</h2>
      {children && <p className="mt-4 text-lg leading-relaxed text-muted">{children}</p>}
    </div>
  )
}

/** The product in one picture: checklist rows judged against a contract, one expanded with its quote. */
function HeroDemo() {
  const rows = [
    ['Governing law stated', 'covered', 'Covered'],
    ['Termination: 30 days’ notice', 'conflict', 'Conflict'],
    ['Liability capped at 12 months’ fees', 'partial', 'Partial'],
    ['Professional indemnity insurance', 'missing', 'Missing'],
  ]
  return (
    <div className="rounded-2xl border border-border bg-surface p-2 shadow-[0_24px_60px_-24px_var(--glow)]">
      <div className="flex items-center justify-between rounded-t-xl border-b border-border px-4 py-3">
        <div className="flex items-center gap-2 text-sm font-medium">
          <Scale className="size-4 text-secondary" aria-hidden />
          Services Agreement · review checklist
        </div>
        <span className="text-xs whitespace-nowrap text-muted">7 points</span>
      </div>
      <ul className="divide-y divide-border">
        {rows.map(([point, status, label], i) => (
          <motion.li
            key={point}
            initial={{ opacity: 0, x: -8 }}
            animate={{ opacity: 1, x: 0 }}
            transition={{ delay: 0.25 + i * 0.12 }}
            className={cn('px-4 py-3', status === 'conflict' && 'bg-conflict/5')}
          >
            <div className="flex items-center justify-between gap-3">
              <span className="text-sm">{point}</span>
              <Badge status={status}>{label}</Badge>
            </div>
            {status === 'conflict' && (
              <div className="mt-2.5 flex items-start gap-2 rounded-lg border-l-2 border-conflict bg-surface px-3 py-2 text-sm">
                <Quote className="mt-0.5 size-3.5 shrink-0 text-conflict" aria-hidden />
                <span className="font-serif text-[15px] leading-snug">
                  “Either party may terminate this Agreement by giving 7 days’ written notice.”
                  <span className="ml-2 rounded bg-foreground px-1.5 py-0.5 font-sans text-[10px] font-semibold text-background">Page 1</span>
                </span>
              </div>
            )}
          </motion.li>
        ))}
      </ul>
    </div>
  )
}

/** Tabs showing the same comparison for different professions. */
function UseCases() {
  const [active, setActive] = useState(USE_CASES[0].key)
  const uc = USE_CASES.find((u) => u.key === active)
  return (
    <div className="mt-10">
      <div role="tablist" aria-label="Who uses Atlas" className="flex flex-wrap gap-2">
        {USE_CASES.map((u) => (
          <button
            key={u.key}
            role="tab"
            type="button"
            aria-selected={u.key === active}
            onClick={() => setActive(u.key)}
            className={cn(
              'inline-flex cursor-pointer items-center gap-2 rounded-pill border px-4 py-2 text-sm transition-colors',
              u.key === active ? 'border-primary bg-primary text-primary-foreground' : 'border-border bg-surface text-muted hover:text-foreground',
            )}
          >
            <u.icon className="size-4" aria-hidden />
            {u.label}
          </button>
        ))}
      </div>

      <motion.div
        key={uc.key}
        role="tabpanel"
        initial={{ opacity: 0, y: 6 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.25 }}
        className="mt-6 grid gap-4 rounded-2xl border border-border bg-surface p-5 sm:p-7 lg:grid-cols-[1fr_auto_1fr_1.3fr] lg:items-stretch"
      >
        <div className="rounded-xl bg-fill p-4">
          <p className="text-xs font-semibold tracking-wider text-muted uppercase">What should exist</p>
          <p className="mt-2 font-medium">{uc.reference}</p>
        </div>
        <div className="hidden items-center text-muted lg:flex"><ArrowRight className="size-5" aria-hidden /></div>
        <div className="rounded-xl bg-fill p-4">
          <p className="text-xs font-semibold tracking-wider text-muted uppercase">What currently exists</p>
          <p className="mt-2 font-medium">{uc.existing}</p>
        </div>
        <div className="rounded-xl border border-border p-4">
          <div className="flex flex-wrap items-center justify-between gap-2">
            <p className="text-xs font-semibold tracking-wider text-muted uppercase">Example finding</p>
            <Badge status={uc.finding.status}>{RESULTS.find((r) => r.status === uc.finding.status).label}</Badge>
          </div>
          <p className="mt-2 font-medium">{uc.finding.point}</p>
          <p className="mt-1.5 font-serif text-[15px] leading-snug text-muted">{uc.finding.quote}</p>
        </div>
        <p className="text-sm text-muted lg:col-span-4">For: {uc.who}</p>
      </motion.div>
    </div>
  )
}

/** Ways to start, each opening "New analysis" with the right type already chosen. */
const STARTS = [
  { icon: Scale, title: 'Check a contract or policy', text: 'Against your review checklist, term sheet or legal requirements.', type: 'spec_coverage' },
  { icon: Briefcase, title: 'Match a resume to a job', text: 'See which job requirements the resume proves, and which are missing.', type: 'resume_jd' },
  { icon: Code2, title: 'Compare requirements with documentation', text: 'SRS vs design docs, specification vs submittals, tender vs bid.', type: 'spec_coverage' },
]

/** First-visit "Get started" dialog: pick what to check and go straight to the right setup. */
function WelcomeDialog({ open, onClose }) {
  const navigate = useNavigate()
  return (
    <Modal
      open={open}
      onClose={onClose}
      title="Welcome to Atlas AI"
      description="What would you like to check? Pick one — you can upload your files on the next screen."
      footer={<Button variant="ghost" onClick={onClose}>Just look around</Button>}
    >
      <div className="space-y-2">
        {STARTS.map((s) => (
          <button
            key={s.title}
            type="button"
            onClick={() => { onClose(); navigate(`/analyses/new?type=${s.type}`) }}
            className="group flex w-full cursor-pointer items-start gap-3 border border-border bg-background p-4 text-left transition-colors hover:border-accent hover:bg-accent/5"
          >
            <span className="grid size-9 shrink-0 place-items-center bg-accent/10 text-accent"><s.icon className="size-4" aria-hidden /></span>
            <span className="min-w-0 flex-1">
              <span className="block font-medium">{s.title}</span>
              <span className="mt-0.5 block text-sm text-muted">{s.text}</span>
            </span>
            <ArrowRight className="mt-2 size-4 shrink-0 text-muted transition-transform group-hover:translate-x-0.5 group-hover:text-accent" aria-hidden />
          </button>
        ))}
      </div>
      <p className="mt-4 text-xs text-muted">Tip: on the free version, use sample or redacted documents — not confidential files.</p>
    </Modal>
  )
}

/** Whether this browser has already seen (and closed) the welcome dialog. */
function welcomeSeen() {
  try { return localStorage.getItem(WELCOME_KEY) === '1' } catch { return false }
}

// ── Page ─────────────────────────────────────────────────────────────────────

export default function LandingPage() {
  const [welcomeOpen, setWelcomeOpen] = useState(false)

  // First visit: open "Get started" after a moment, once the visitor has seen the headline
  useEffect(() => {
    if (welcomeSeen()) return undefined
    const timer = setTimeout(() => setWelcomeOpen(true), 1200)
    return () => clearTimeout(timer)
  }, [])

  const closeWelcome = () => {
    setWelcomeOpen(false)
    try { localStorage.setItem(WELCOME_KEY, '1') } catch { /* storage blocked: it may show again next visit */ }
  }

  return (
    <div className="min-h-screen bg-background text-foreground">
      {/* Nav */}
      <header className="sticky top-0 z-40 border-b border-border bg-background/85 backdrop-blur">
        <div className="mx-auto flex h-16 max-w-6xl items-center gap-6 px-4 sm:px-6">
          <Link to="/" aria-label="Atlas AI by Web Triggers — home"><Logo byline /></Link>
          <nav className="hidden items-center gap-6 text-sm text-muted md:flex" aria-label="Sections">
            <a href="#how" className="hover:text-foreground">How it works</a>
            <a href="#uses" className="hover:text-foreground">Who it’s for</a>
            <a href="#trust" className="hover:text-foreground">Trust &amp; privacy</a>
            <a href="#faq" className="hover:text-foreground">FAQ</a>
          </nav>
          <div className="ml-auto flex items-center gap-2">
            <ThemeToggle />
            <Link to="/app" className="hidden text-sm text-muted hover:text-foreground sm:inline">My analyses</Link>
            <Button size="sm" onClick={() => setWelcomeOpen(true)}>Get started</Button>
          </div>
        </div>
      </header>

      <main>
        {/* Hero */}
        <section className="relative overflow-hidden">
          <div aria-hidden className="pointer-events-none absolute inset-x-0 -top-40 mx-auto h-96 max-w-4xl rounded-full bg-glow/10 blur-3xl" />
          <div className="relative mx-auto grid max-w-6xl gap-12 px-4 pt-16 pb-20 sm:px-6 lg:grid-cols-[1.05fr_1fr] lg:items-center lg:pt-24">
            <motion.div initial={{ opacity: 0, y: 12 }} animate={{ opacity: 1, y: 0 }} transition={{ duration: 0.5 }}>
              <p className="inline-flex items-center gap-2 rounded-pill border border-border bg-surface px-3 py-1 text-xs font-medium text-muted">
                <span className="size-1.5 rounded-full bg-accent" /> Document gap analysis
              </p>
              <h1 className="mt-6 font-serif text-5xl leading-[1.05] tracking-tight sm:text-6xl lg:text-7xl">
                Check any document against what it <em className={GRADIENT_TEXT}>should</em> contain.
              </h1>
              <p className="mt-6 max-w-xl text-lg leading-relaxed text-muted">
                Give Atlas your checklist and your document. It goes point by point and shows what is covered,
                what is partial, what is missing and what contradicts you — with the exact quote for every finding.
              </p>
              <div className="mt-8 flex flex-wrap items-center gap-3">
                <Link to="/analyses/new"><Button size="lg" icon={ArrowRight}>Start a free check</Button></Link>
                <a href="#how"><Button size="lg" variant="outline">See how it works</Button></a>
              </div>
              <p className="mt-5 text-sm text-muted">
                No setup. PDF, Word or text. For confidential files, use redacted copies or a private install.
              </p>
            </motion.div>
            <HeroDemo />
          </div>
        </section>

        {/* Problem → promise */}
        <Section className="pb-8">
          <div className="grid gap-4 rounded-2xl border border-border bg-surface p-6 sm:grid-cols-3 sm:p-8">
            {[
              ['Hours', 'Checking a long document against a checklist by hand, line by line.'],
              ['Minutes', 'Atlas does the first pass and lines up the evidence for every point.'],
              ['You decide', 'Each result shows its quote, so checking it takes seconds — not trust.'],
            ].map(([big, text]) => (
              <div key={big}>
                <p className="font-serif text-3xl">{big}</p>
                <p className="mt-2 text-muted">{text}</p>
              </div>
            ))}
          </div>
        </Section>

        {/* How it works */}
        <Section id="how" className="py-20">
          <Heading eyebrow="How it works" title="Four steps, no jargon.">
            The same flow works for a contract, a resume, a specification or a tender.
          </Heading>
          <ol className="mt-12 grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
            {STEPS.map((s, i) => (
              <li key={s.title} className="rounded-2xl border border-border bg-surface p-6">
                <div className="flex items-center justify-between">
                  <span className="grid size-10 place-items-center rounded-xl bg-accent/10 text-accent"><s.icon className="size-5" aria-hidden /></span>
                  <span className="font-serif text-3xl text-muted/50">{i + 1}</span>
                </div>
                <h3 className="mt-5 text-lg font-semibold">{s.title}</h3>
                <p className="mt-2 text-sm leading-relaxed text-muted">{s.text}</p>
              </li>
            ))}
          </ol>

          <div className="mt-6 grid gap-3 rounded-2xl border border-border bg-surface p-6 sm:grid-cols-2 lg:grid-cols-5">
            {RESULTS.map((r) => (
              <div key={r.status}>
                <Badge status={r.status}>{r.label}</Badge>
                <p className="mt-2 text-sm text-muted">{r.text}</p>
              </div>
            ))}
          </div>
        </Section>

        {/* Who it's for */}
        <Section id="uses" className="py-20">
          <Heading eyebrow="Who it’s for" title="One idea, many desks.">
            Wherever there is a list of what should be there and a document that should match it, Atlas can check it.
          </Heading>
          <UseCases />
        </Section>

        {/* Features */}
        <Section className="py-20">
          <Heading eyebrow="What you get" title="More than a yes/no checklist." />
          <div className="mt-12 grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
            {FEATURES.map((f) => (
              <div key={f.title} className="rounded-2xl border border-border bg-surface p-6">
                <f.icon className="size-5 text-accent" aria-hidden />
                <h3 className="mt-4 font-semibold">{f.title}</h3>
                <p className="mt-2 text-sm leading-relaxed text-muted">{f.text}</p>
              </div>
            ))}
          </div>
        </Section>

        {/* Trust */}
        <Section id="trust" className="py-20">
          <div className="grid gap-10 rounded-3xl bg-foreground p-8 text-background sm:p-12 lg:grid-cols-2">
            <div>
              <p className="text-xs font-semibold tracking-[0.18em] text-accent uppercase">Trust &amp; privacy</p>
              <h2 className="mt-3 font-serif text-4xl leading-tight sm:text-5xl">An assistant that shows its work.</h2>
              <p className="mt-4 text-lg leading-relaxed opacity-75">
                Atlas is built to be checked, not blindly trusted. It tells you where it looked and what it found —
                and it says plainly what it can’t do.
              </p>
            </div>
            <ul className="space-y-5">
              {[
                ['Evidence, not opinions', 'Quotes are verified word-for-word against your document. A finding without real evidence is never upgraded.'],
                ['Honest about accuracy', 'About 8 in 10 findings match a careful human reviewer in our tests. Always read the quote.'],
                ['Your confidentiality', 'The free version uses outside AI services — use redacted or sample files. Confidential work: run Atlas on your own machine.'],
                ['Your work stays yours', 'With sign-in on, each person sees only their own analyses. Nothing is shared between accounts.'],
              ].map(([title, text]) => (
                <li key={title} className="flex gap-3">
                  <ShieldCheck className="mt-0.5 size-5 shrink-0 text-accent" aria-hidden />
                  <div>
                    <p className="font-semibold">{title}</p>
                    <p className="mt-1 text-sm leading-relaxed opacity-75">{text}</p>
                  </div>
                </li>
              ))}
            </ul>
          </div>
        </Section>

        {/* FAQ */}
        <Section id="faq" className="py-20">
          <Heading eyebrow="FAQ" title="Good questions." />
          <div className="mt-10 divide-y divide-border rounded-2xl border border-border bg-surface">
            {FAQ.map((f) => (
              <details key={f.q} className="group px-6 py-5">
                <summary className="flex cursor-pointer list-none items-center justify-between gap-4 font-medium">
                  {f.q}
                  <span className="text-xl leading-none text-muted transition-transform group-open:rotate-45" aria-hidden>+</span>
                </summary>
                <p className="mt-3 max-w-3xl leading-relaxed text-muted">{f.a}</p>
              </details>
            ))}
          </div>
        </Section>

        {/* Final CTA */}
        <Section className="pb-24">
          <div className="flex flex-col items-start gap-6 rounded-3xl border border-border bg-surface p-8 sm:p-12 lg:flex-row lg:items-center lg:justify-between">
            <div>
              <h2 className="font-serif text-4xl leading-tight sm:text-5xl">Try it on your next document.</h2>
              <p className="mt-3 text-lg text-muted">Two uploads, one checklist, results in minutes.</p>
            </div>
            <Link to="/analyses/new"><Button size="lg" icon={ArrowRight}>Start a free check</Button></Link>
          </div>
        </Section>
      </main>

      <footer className="border-t border-border">
        <div className="mx-auto flex max-w-6xl flex-col gap-4 px-4 py-8 text-sm text-muted sm:flex-row sm:items-center sm:justify-between sm:px-6">
          <div>
            <Logo />
            <p className="mt-2 text-xs">A product by <a href={WEBTRIGGERS} target="_blank" rel="noreferrer" className="font-medium text-foreground hover:underline">Web Triggers</a>.</p>
          </div>
          <p>Findings are a first review, not professional advice. Always verify the quoted evidence.</p>
          <div className="flex gap-5">
            <Link to="/app" className="hover:text-foreground">My analyses</Link>
            <a href={WEBTRIGGERS} target="_blank" rel="noreferrer" className="hover:text-foreground">Web Triggers</a>
            {/* Hidden for now: <a href={REPO} target="_blank" rel="noreferrer" className="hover:text-foreground">GitHub</a> */}
          </div>
        </div>
      </footer>

      <WelcomeDialog open={welcomeOpen} onClose={closeWelcome} />
    </div>
  )
}
