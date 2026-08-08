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
export const GITHUB_OWNER = 'your-github-username';
export const GITHUB_REPO = 'restoreforge-ai';
```

Replace them once the repository exists. Until you do, `REPO_CONFIGURED` is
`false` and the download page shows an explicit notice instead of presenting
links that would 404.

No environment variables are required, so there is no `.env.example`.

## Deploying to Vercel

1. Push the repository to GitHub.
2. In Vercel, choose **Add New → Project** and import it.
3. Set **Root Directory** to `web`. This matters — the repository root is the
   Python desktop application, not a Node project.
4. Vercel detects **Next.js** automatically. Leave the build command, output
   directory and install command at their defaults.
5. No environment variables are needed.
6. Deploy, then add the production URL to the root `README.md`.

There is no `vercel.json`: the defaults are correct for this project, and an
unnecessary config file is one more thing to drift out of date.

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
