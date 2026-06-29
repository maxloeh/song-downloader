/** @type {import('tailwindcss').Config} */
export default {
  content: ["./index.html", "./src/**/*.{js,ts,jsx,tsx}"],
  theme: {
    extend: {
      colors: {
        bg: "#08090d",
        panel: "#13151c",
        "panel-alt": "#11131a",
        inset: "#0d0f14",
        raised: "#1b1e27",
        accent: {
          DEFAULT: "#00e0c6",
        },
        soundcloud: "#ff7a2f",
        spotify: "#1ed760",
      },
      fontFamily: {
        sans: ["Space Grotesk", "ui-sans-serif", "system-ui", "sans-serif"],
        mono: ["JetBrains Mono", "ui-monospace", "monospace"],
      },
    },
  },
  plugins: [],
};
