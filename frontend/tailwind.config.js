/** @type {import('tailwindcss').Config} */
export default {
  content: ["./index.html", "./src/**/*.{js,ts,jsx,tsx}"],
  theme: {
    extend: {
      fontFamily: {
        sans: ["Inter", "system-ui", "-apple-system", "sans-serif"],
        mono: ["JetBrains Mono", "ui-monospace", "SFMono-Regular", "monospace"],
      },
      colors: {
        // Two lighter shades architecture:
        // Shade 1: #F8FAFC (Slate-50 canvas)
        // Shade 2: #FFFFFF (Pure white card & panel surface)
        surface: {
          950: "#F8FAFC", // Shade 1: Main page canvas
          900: "#FFFFFF", // Shade 2: Cards, sidebar, header, containers
          850: "#F1F5F9", // Nested containers & hover states
          800: "#E2E8F0", // Secondary controls & light borders
          750: "#CBD5E1",
          700: "#E2E8F0", // Crisp card dividers & borders
        },
        slate: {
          50: "#020617",
          100: "#0F172A", // Primary high-contrast heading text (Slate-900)
          200: "#1E293B", // Strong title text (Slate-800)
          300: "#334155", // Neutral body text (Slate-700)
          400: "#64748B", // Muted metadata & caption text (Slate-500)
          500: "#94A3B8", // Fine print (Slate-400)
          600: "#475569",
          700: "#E2E8F0", // Clean light dividers
          800: "#F1F5F9", // Soft pill background
          850: "#F8FAFC",
          900: "#FFFFFF",
          950: "#F8FAFC",
        },
      },
    },
  },
  plugins: [],
};
