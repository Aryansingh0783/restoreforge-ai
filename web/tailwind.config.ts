import type { Config } from 'tailwindcss';

const config: Config = {
  content: ['./src/**/*.{ts,tsx}'],
  theme: {
    extend: {
      colors: {
        base: '#08090b',
        panel: '#0b0d10',
        card: '#0f1216',
        cardhi: '#141821',
        line: '#1b2029',
        linehi: '#272e3a',
        ink: '#e9edf2',
        sub: '#98a2b3',
        faint: '#6b7686',
        accent: '#22d3ee',
        accentdim: '#0d3540',
        violet: '#a78bfa',
        ok: '#34d399',
        warn: '#fbbf24',
        bad: '#f87171',
      },
      fontFamily: {
        sans: ['ui-sans-serif', 'Inter', 'Segoe UI', 'system-ui', 'sans-serif'],
        mono: ['ui-monospace', 'JetBrains Mono', 'Consolas', 'monospace'],
      },
      maxWidth: { content: '76rem' },
      borderRadius: { xl2: '0.875rem' },
    },
  },
  plugins: [],
};
export default config;
