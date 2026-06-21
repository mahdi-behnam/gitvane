import { env } from "@/lib/env";

const navigationItems = [
  "Overview",
  "Repositories",
  "Search",
  "Impact",
  "Graph",
  "Risk",
  "Tests",
  "Evaluation",
  "Settings",
];

const workflowItems = [
  {
    title: "Register repositories",
    description:
      "Connect local paths or clone URLs, then index code when the backend is ready.",
  },
  {
    title: "Trace impact",
    description:
      "Prepare changed files, raw diffs, or refs for evidence-based predictions.",
  },
  {
    title: "Review evidence",
    description:
      "Inspect scores, reasons, graph relationships, risk, and recommended tests.",
  },
];

export default function Home() {
  return (
    <main className="min-h-screen bg-canvas text-foreground">
      <div className="grid min-h-screen lg:grid-cols-[264px_1fr]">
        <aside className="border-b border-border bg-panel px-5 py-4 lg:border-b-0 lg:border-r lg:py-6">
          <div className="flex items-center gap-3">
            <div
              aria-hidden="true"
              className="grid size-9 place-items-center rounded-md border border-border bg-canvas"
            >
              <span className="size-3 rounded-[4px] border-2 border-primary" />
            </div>
            <div>
              <p className="text-sm font-semibold leading-none">RepoLens</p>
              <p className="mt-1 text-xs text-muted">Trace change before it spreads.</p>
            </div>
          </div>

          <nav
            aria-label="Primary"
            className="mt-6 flex gap-1 overflow-x-auto lg:block"
          >
            {navigationItems.map((item) => (
              <a
                className="block rounded-md px-3 py-2 text-sm text-muted transition hover:bg-canvas hover:text-foreground"
                href="#overview"
                key={item}
              >
                {item}
              </a>
            ))}
          </nav>
        </aside>

        <section className="px-5 py-6 sm:px-8 lg:px-10">
          <header className="flex flex-col gap-4 border-b border-border pb-6 md:flex-row md:items-center md:justify-between">
            <div>
              <p className="font-mono text-xs uppercase tracking-[0.12em] text-muted">
                Overview
              </p>
              <h1 className="mt-2 text-3xl font-semibold tracking-normal md:text-4xl">
                RepoLens dashboard
              </h1>
            </div>
            <div className="rounded-md border border-border bg-panel px-3 py-2 font-mono text-xs text-muted">
              {env.NEXT_PUBLIC_API_BASE_URL}
            </div>
          </header>

          <div id="overview" className="grid gap-4 py-6 xl:grid-cols-[1.2fr_0.8fr]">
            <section className="rounded-lg border border-border bg-panel p-6">
              <p className="text-sm font-medium text-foreground">
                No repositories registered yet
              </p>
              <p className="mt-3 max-w-2xl text-sm leading-6 text-muted">
                The frontend foundation is ready for the backend integrations that will
                add repository registration, indexing, semantic search, impact analysis,
                graphs, risk ranking, test recommendations, and evaluation reports.
              </p>
              <div className="mt-6 grid gap-3 md:grid-cols-3">
                {workflowItems.map((item) => (
                  <article
                    className="rounded-lg border border-border bg-canvas p-4"
                    key={item.title}
                  >
                    <h2 className="text-sm font-semibold">{item.title}</h2>
                    <p className="mt-2 text-sm leading-6 text-muted">
                      {item.description}
                    </p>
                  </article>
                ))}
              </div>
            </section>

            <aside className="rounded-lg border border-border bg-panel p-6">
              <p className="text-sm font-medium">Project status</p>
              <dl className="mt-5 space-y-4 text-sm">
                <div className="flex items-center justify-between gap-4">
                  <dt className="text-muted">Frontend stack</dt>
                  <dd className="font-medium">Next.js App Router</dd>
                </div>
                <div className="flex items-center justify-between gap-4">
                  <dt className="text-muted">Styling</dt>
                  <dd className="font-medium">Tailwind CSS</dd>
                </div>
                <div className="flex items-center justify-between gap-4">
                  <dt className="text-muted">Type safety</dt>
                  <dd className="font-medium">Strict TypeScript</dd>
                </div>
                <div className="flex items-center justify-between gap-4">
                  <dt className="text-muted">Backend URL</dt>
                  <dd className="font-mono text-xs text-muted">Configured</dd>
                </div>
              </dl>
            </aside>
          </div>
        </section>
      </div>
    </main>
  );
}
