import type { Config } from "tailwindcss";

const config: Config = {
  darkMode: ["class"],
  content: ["./index.html", "./src/**/*.{ts,tsx}"],
  theme: {
    extend: {
      colors: {
        background: "#f8f5f1",
        foreground: "#171412",
        border: "#eadfd5",
        muted: "#f2ede7",
        primary: {
          DEFAULT: "#e35d50",
          foreground: "#fff8f5",
        },
        ink: "#2b2521",
        coral: "#e35d50",
      },
      borderRadius: {
        "2xl": "1.25rem",
      },
      boxShadow: {
        soft: "0 14px 40px rgba(43, 37, 33, 0.08)",
      },
      fontFamily: {
        sans: ["Inter", "ui-sans-serif", "system-ui", "Segoe UI", "Arial", "sans-serif"],
      },
    },
  },
  plugins: [],
};

export default config;
