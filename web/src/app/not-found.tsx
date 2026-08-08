import { Btn } from '@/components/ui';

export default function NotFound() {
  return (
    <div className="gridwash flex min-h-[60vh] items-center justify-center px-5">
      <div className="text-center">
        <p className="kicker">Error /404</p>
        <h1 className="mt-4 text-3xl font-semibold tracking-tight sm:text-4xl">Page not found</h1>
        <p className="lede mx-auto mt-4 max-w-md">
          That page does not exist. It may have been renamed, or the link may be out of date.
        </p>
        <div className="mt-8 flex flex-wrap justify-center gap-3">
          <Btn href="/" variant="primary">
            Back to home
          </Btn>
          <Btn href="/docs">Documentation</Btn>
        </div>
      </div>
    </div>
  );
}
