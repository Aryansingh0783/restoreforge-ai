# RestoreForge AI — website

The public product site and documentation portal. Built with Next.js (App
Router), TypeScript, Tailwind CSS and Lucide icons.

## What this is — and is not

This is **only a website**. It is a statically exported set of HTML, CSS and
JavaScript files.

- It does **not** run the restoration pipeline.
- It does **not** accept video uploads — there is no upload control anywhere.
- It does **not** bundle or serve model weights.
- It has no database, no authentication, no API routes and no server-side
  processing.

The estimator on the home page performs arithmetic in the browser from numbers
the visitor types. Nothing is read from their machine and nothing is
transmitted.

## Local development

Requires Node 18.18 or newer.

```bash
npm install
npm run dev        # http://localhost:3000
```

## Quality gates

```bash
npm run lint       # ESLint via next lint
npm run typecheck  # tsc --noEmit
npm run build      # production build + static export to ./out
```

All three must pass before merging. CI runs them on every pull request.

## Configuration

Every outbound link is derived from two constants in
[`src/lib/site.ts`](src/lib/site.ts):

```ts
export const GITHUB_OWNER: string = 'Aryansingh0783';
export const GITHUB_REPO: string = 'restoreforge-ai';
```

A fork needs exactly one edit here. If they are left at the placeholder
`'your-github-username'`, `REPO_CONFIGURED` is `false` and the download page
shows an explicit notice rather than presenting links that would 404.

No environment variables are required, so there is no `.env.example`.

## Deploying to Vercel

The live site is <https://restoreforge-ai.vercel.app>.

To deploy a fork:

1. Push the repository to GitHub.
2. In Vercel, choose **Add New → Project** and import it.
3. Leave **Root Directory** at the repository root. The root
   [`vercel.json`](../vercel.json) already directs the build into `web/` — see
   below for why.
4. No environment variables are needed.
5. Deploy, then add the production URL to the root `README.md`.

From the command line instead:

```bash
cd web
npx vercel link --yes --project <your-project-name>
npx vercel deploy --prod --yes
```

### Why there is a `vercel.json` at the repository root

Deploying from this directory with the CLI works with no configuration at all.
Git-triggered deploys are different: Vercel builds from the repository root,
where there is no Node project, and the build fails with *"Couldn't find any
`pages` or `app` directory"*.

The usual fix is to set **Root Directory** to `web` in the project's dashboard
settings. That works, but it lives outside the repository — a fresh fork or a
recreated project silently loses it. The root
[`vercel.json`](../vercel.json) encodes the same thing in version control:

```json
{
  "buildCommand": "cd web && npm ci --no-audit --no-fund && npm run build",
  "outputDirectory": "web/out",
  "installCommand": "echo ...",
  "framework": null
}
```

`installCommand` is a deliberate no-op because there is nothing to install at
the root; `buildCommand` handles installation inside `web/`. `framework` is
`null` so Vercel does not try to auto-detect a framework at the root.

If you prefer the dashboard approach, delete this file and set Root Directory
to `web` instead. Do not do both.

### Why `output: 'export'`

`next.config.mjs` sets `output: 'export'`, producing a fully static site. This
is deliberate — it makes it structurally impossible for the deployment to
process user video, and keeps hosting free and trivially cacheable.

If you later add a route requiring a server, you must remove that setting.

## Structure

```
web/
├── src/
│   ├── app/
│   │   ├── layout.tsx          Shell, metadata, skip link
│   │   ├── page.tsx            Landing page
│   │   ├── globals.css         Design tokens and utilities
│   │   ├── not-found.tsx       404
│   │   ├── features/           Product features
│   │   ├── workflow/           Pipeline explanation
│   │   ├── requirements/       Hardware and software requirements
│   │   ├── docs/               Documentation (nested layout with sidebar)
│   │   ├── privacy/            Local-first privacy statement
│   │   ├── download/           Release and install guidance
│   │   └── changelog/          Release history
│   ├── components/
│   │   ├── ui.tsx              Section, Card, Btn, Callout, prose primitives
│   │   ├── site-chrome.tsx     Header and footer (client — mobile nav)
│   │   ├── pipeline.tsx        Pipeline diagram (server)
│   │   └── estimator.tsx       Planning estimator (client)
│   └── lib/
│       └── site.ts             Links, navigation, feature and FAQ content
├── tailwind.config.ts
└── next.config.mjs
```

## Design notes

The visual direction is dark and technical, following the supplied reference
boards: a near-black graphite base, hairline borders forming a grid, monospaced
small-caps labels, section numbering (`/01`, `/02`) and a restrained cyan accent.

Constraints kept throughout:

- Only server components, except where interaction requires otherwise —
  currently just the mobile navigation and the estimator.
- No external fonts or scripts. System font stacks only, so no network request
  leaves the visitor's browser for a third party.
- `prefers-reduced-motion` is honoured globally in `globals.css`.
- Focus rings are visible on every interactive element.
- The FAQ uses native `<details>`/`<summary>`, which is accessible and needs no
  JavaScript.
- No fabricated dashboard data, fake testimonials or unverifiable metrics.

## Content rules

Claims on this site must match what the software actually does. In particular,
do not add: "lossless restoration", "perfect face recovery", "cloud AI",
"works on all GPUs", "real-time", or any benchmark that has not been measured.
The honesty of the copy is a feature — see `CONTRIBUTING.md` in the repository
root.
