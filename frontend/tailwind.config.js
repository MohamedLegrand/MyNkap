/** @type {import('tailwindcss').Config} */
export default {
  darkMode: 'class',
  content: [
    "./index.html",
    "./src/**/*.{js,ts,jsx,tsx}",
  ],
  theme: {
    extend: {
      colors: {
        border: "hsl(var(--border))",
        input: "hsl(var(--input))",
        ring: "hsl(var(--ring))",
        background: "hsl(var(--background))",
        foreground: "hsl(var(--foreground))",
        primary: {
          DEFAULT: "hsl(var(--primary))",
          foreground: "hsl(var(--primary-foreground))",
        },
        secondary: {
          DEFAULT: "hsl(var(--secondary))",
          foreground: "hsl(var(--secondary-foreground))",
        },
        destructive: {
          DEFAULT: "hsl(var(--destructive))",
          foreground: "hsl(var(--destructive-foreground))",
        },
        muted: {
          DEFAULT: "hsl(var(--muted))",
          foreground: "hsl(var(--muted-foreground))",
        },
        accent: {
          DEFAULT: "hsl(var(--accent))",
          foreground: "hsl(var(--accent-foreground))",
        },
        popover: {
          DEFAULT: "hsl(var(--popover))",
          foreground: "hsl(var(--popover-foreground))",
        },
        card: {
          DEFAULT: "hsl(var(--card))",
          foreground: "hsl(var(--card-foreground))",
        },
        // Palettes fixes réutilisables
        forest: {
          50: '#f2f8f3',
          100: '#e1efe3',
          200: '#c4dec7',
          300: '#98c39e',
          400: '#67a16e',
          500: '#42834a',
          600: '#316938',
          700: '#254e2a', // Vert forêt
          800: '#203f23',
          900: '#1b321e',
          950: '#0e1b10',
        },
        brandblue: {
          50: '#edf4ff',
          100: '#d6e5ff',
          200: '#b5d0ff',
          300: '#83b1ff',
          400: '#4b8aff',
          500: '#2260ff', // Bleu
          600: '#0a3cfa',
          700: '#002be6',
          800: '#0024be',
          900: '#072199',
          950: '#0a145c',
        },
      },
      borderRadius: {
        lg: "var(--radius)",
        md: "calc(var(--radius) - 2px)",
        sm: "calc(var(--radius) - 4px)",
      },
    },
  },
  plugins: [],
}