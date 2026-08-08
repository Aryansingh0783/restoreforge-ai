/** @type {import('next').NextConfig} */
const nextConfig = {
  reactStrictMode: true,
  // Static-first: the site is a product/documentation experience with no
  // server-side work. Exporting keeps Vercel deployment trivial and makes it
  // obvious that no video ever reaches a server.
  output: 'export',
  images: { unoptimized: true },
  trailingSlash: true,
};
export default nextConfig;
