/** @type {import('tailwindcss').Config} */
export default {
  content: [
    "./index.html",
    "./src/**/*.{vue,js,ts,jsx,tsx}",
  ],
  darkMode: 'class',
  theme: {
    extend: {
      colors: {
        stock: {
          up: '#ef4444',     // A股红涨
          down: '#10b981',   // A股绿跌
          flat: '#94a3b8'
        }
      }
    },
  },
  plugins: [],
}
