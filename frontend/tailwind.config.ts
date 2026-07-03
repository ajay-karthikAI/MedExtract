import type { Config } from "tailwindcss";

const config: Config = {
  darkMode: "class",
  content: ["./app/**/*.{ts,tsx}", "./components/**/*.{ts,tsx}", "./lib/**/*.ts"],
  theme: {
    extend: {},
  },
  plugins: [],
};

export default config;
