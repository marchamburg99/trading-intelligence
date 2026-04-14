/** @type {import('tailwindcss').Config} */
export default {
  content: ["./index.html", "./src/**/*.{js,ts,jsx,tsx}"],
  theme: {
    extend: {
      fontFamily: {
        sans: ['"DM Sans"', "system-ui", "sans-serif"],
        mono: ['"JetBrains Mono"', "monospace"],
      },
      colors: {
        surface: {
          DEFAULT: "#FFFFFF",
          subtle: "#FAFAF9",
          muted: "#F5F5F4",
          raised: "#FFFFFF",
        },
        ink: {
          DEFAULT: "#1C1917",
          secondary: "#57534E",
          tertiary: "#A8A29E",
          faint: "#D6D3D1",
        },
        border: {
          DEFAULT: "#E7E5E4",
          subtle: "#F5F5F4",
        },
        accent: {
          DEFAULT: "#1D4ED8",
          light: "#EFF6FF",
          hover: "#1E40AF",
        },
        gain: {
          DEFAULT: "#15803D",
          bg: "#F0FDF4",
          light: "#DCFCE7",
        },
        loss: {
          DEFAULT: "#DC2626",
          bg: "#FEF2F2",
          light: "#FEE2E2",
        },
        warn: {
          DEFAULT: "#D97706",
          bg: "#FFFBEB",
          light: "#FEF3C7",
        },
        leverage: {
          DEFAULT: "#EA580C",
          bg: "#FFF7ED",
          light: "#FFEDD5",
        },
        brand: {
          accent: "#1D4ED8",
        },
      },
      boxShadow: {
        card: "0 1px 3px 0 rgb(0 0 0 / 0.04), 0 1px 2px -1px rgb(0 0 0 / 0.04)",
        "card-hover": "0 4px 12px 0 rgb(0 0 0 / 0.06), 0 2px 4px -2px rgb(0 0 0 / 0.04)",
        float: "0 8px 30px rgb(0 0 0 / 0.08)",
      },
    },
  },
  plugins: [],
};
