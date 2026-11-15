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
        surface: {
          950: "#0B0D12",
          900: "#10131A",
          850: "#151922",
          800: "#1B202C",
          700: "#242B3A",
        },
      },
    },
  },
  plugins: [],
};

