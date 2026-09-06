/** @type {import('tailwindcss').Config} */
export default {
  content: ['./index.html', './src/**/*.{js,jsx}'],
  theme: {
    extend: {
      colors: {
        sidebar: 'var(--color-sidebar-bg)',
        page: 'var(--color-page-bg)',
        surface: 'var(--color-surface)',
        'brand-border': 'var(--color-border)',
        primary: {
          DEFAULT: 'var(--color-primary)',
          dark: 'var(--color-primary-dark)',
          text: 'var(--color-primary-text)',
        },
        secondary: {
          DEFAULT: 'var(--color-secondary)',
          dark: 'var(--color-secondary-dark)',
          text: 'var(--color-secondary-text)',
        },
        'tx-primary': 'var(--color-text-primary)',
        'tx-secondary': 'var(--color-text-secondary)',
        'tx-muted': 'var(--color-text-muted)',
        'input-border': 'var(--color-input-border)',
        // Semánticos: todos verificados con contraste AA sobre fondo claro.
        success: {
          DEFAULT: 'var(--color-success)',
          bg: 'var(--color-success-bg)',
        },
        warning: {
          DEFAULT: 'var(--color-warning)',
          bg: 'var(--color-warning-bg)',
        },
        danger: {
          DEFAULT: 'var(--color-danger)',
          bg: 'var(--color-danger-bg)',
        },
        accent: 'var(--color-accent)',
        'conf-high-bg': 'var(--color-confidence-high-bg)',
        'conf-high-text': 'var(--color-confidence-high-text)',
        'conf-medium-bg': 'var(--color-confidence-medium-bg)',
        'conf-medium-text': 'var(--color-confidence-medium-text)',
        'conf-low-bg': 'var(--color-confidence-low-bg)',
        'conf-low-text': 'var(--color-confidence-low-text)',
      },
    },
  },
  plugins: [],
}
