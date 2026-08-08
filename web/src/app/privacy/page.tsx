import type { Metadata } from 'next';
import { CloudOff, Database, EyeOff, HardDrive, Server, UserX } from 'lucide-react';
import { Callout, Card, PageHeader, Section, SectionHead } from '@/components/ui';
import { site } from '@/lib/site';

export const metadata: Metadata = {
  title: 'Privacy',
  description:
    'RestoreForge AI processes video entirely on your own computer. No uploads, no accounts, no telemetry.',
};

export default function PrivacyPage() {
  return (
    <>
      <PageHeader
        kicker="Local-first"
        title="Privacy"
        lede="The short version: your video never leaves your computer, because there is nowhere for it to go."
      />

      <Section>
        <SectionHead
          index="01"
          title="Privacy by architecture, not by policy"
          lede="This is not a promise about how data is handled after collection. There is no collection."
        />
        <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-3">
          {[
            { icon: HardDrive, title: 'Processing is local', body: 'The restoration engine is a desktop application. It reads your file from disk, uses your GPU, and writes the result back to disk.' },
            { icon: CloudOff, title: 'No upload path exists', body: 'The application contains no code to transmit video. This website has no upload form and no server-side processing.' },
            { icon: UserX, title: 'No accounts', body: 'There is no sign-up, no licence key, no activation and no identity of any kind.' },
            { icon: EyeOff, title: 'No telemetry', body: 'No usage statistics, crash reports, analytics or heartbeats are sent from the desktop application.' },
            { icon: Server, title: 'Static website', body: 'These pages are pre-rendered static files. The estimator computes entirely in your browser from numbers you type.' },
            { icon: Database, title: 'No database', body: 'Nothing about you is stored anywhere. Settings live in a local JSON file next to the application.' },
          ].map((f) => (
            <Card key={f.title} className="p-5">
              <f.icon size={18} aria-hidden className="text-accent" />
              <h3 className="mt-3.5 text-sm font-medium text-ink">{f.title}</h3>
              <p className="mt-2 text-[13px] leading-relaxed text-faint">{f.body}</p>
            </Card>
          ))}
        </div>
      </Section>

      <Section className="bg-panel">
        <SectionHead index="02" title="What does touch the network" />
        <div className="max-w-3xl space-y-4 text-sm leading-relaxed text-sub">
          <p>Being precise is more useful than claiming nothing at all happens. During setup, and only during setup, the application downloads:</p>
          <ul className="list-disc space-y-2 pl-5 marker:text-faint">
            <li>PyTorch and its dependencies, from the official PyTorch wheel index and PyPI.</li>
            <li>Model weights for SCUNet and Real-ESRGAN, from their published GitHub release URLs.</li>
          </ul>
          <p>
            These are ordinary outbound downloads of public files. Nothing about your video, your
            machine or your usage is sent as part of them. After setup completes, the application
            works fully offline — you can disconnect the machine entirely and restorations will
            still run.
          </p>
          <Callout tone="ok" title="Verify it yourself">
            <p>
              The source is public and MIT licensed. Search it for network calls, or run the
              application behind a firewall that blocks it after setup and confirm restorations
              continue to work.
            </p>
            <p>
              <a href={site.repo} className="link" target="_blank" rel="noopener noreferrer">
                Read the source on GitHub
              </a>
            </p>
          </Callout>
        </div>
      </Section>

      <Section>
        <SectionHead index="03" title="This website" />
        <div className="max-w-3xl space-y-4 text-sm leading-relaxed text-sub">
          <p>
            The site is a statically exported set of HTML, CSS and JavaScript files. It sets no
            cookies, embeds no third-party trackers, loads no external fonts or scripts, and has
            no analytics.
          </p>
          <p>
            If it is hosted on a platform such as Vercel, that platform will keep standard server
            access logs — IP address, requested path, user agent — as any web host does. That is
            outside the control of this project and is governed by the host&apos;s own policy. No
            video or restoration data is ever involved, because none is ever sent.
          </p>
          <p>
            The estimator on the home page reads nothing from your machine. It takes the numbers
            you type, does arithmetic in your browser, and displays the result.
          </p>
        </div>
      </Section>
    </>
  );
}
