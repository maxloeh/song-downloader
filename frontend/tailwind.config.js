/** @type {import('tailwindcss').Config} */
export default {
  content: ["./index.html", "./src/**/*.{js,ts,jsx,tsx}"],
  theme: {
    extend: {
      colors: {
        ink: {
          950: "#0a0b10",
          900: "#11131c",
          800: "#171a26",
          700: "#222637",
        },
        accent: {
          DEFAULT: "#ff5722",
          soft: "#ff8a65",
        },
        spotify: "#1db954",
        soundcloud: "#ff5500",
      },
      fontFamily: {
        sans: ["Inter", "ui-sans-serif", "system-ui", "sans-serif"],
        mono: ["JetBrains Mono", "ui-monospace", "monospace"],
      },
    },
  },
  plugins: [],
};
