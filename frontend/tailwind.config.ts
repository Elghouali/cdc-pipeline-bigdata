import type { Config } from 'tailwindcss';

const config: Config = {
  content: ['./index.html', './src/**/*.{ts,tsx}'],
  theme: {
    extend: {
      colors: {
        base: 'var(--bg-base)',
        surface: 'var(--bg-surface)',
        elevated: 'var(--bg-elevated)',
        border: 'var(--border)',
        'text-primary': 'var(--text-primary)',
        'text-secondary': 'var(--text-secondary)',
        'text-muted': 'var(--text-muted)',
        cyan: 'var(--accent-cyan)',
        emerald: 'var(--accent-emerald)',
        amber: 'var(--accent-amber)',
        red: 'var(--accent-red)',
        purple: 'var(--accent-purple)',
      },
      fontFamily: {
        mono: ['var(--font-mono)'],
      },
    },
  },
  plugins: [],
};

export default config;
