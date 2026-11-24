/** @type {import('tailwindcss').Config} */
module.exports = {
  content: [
    "./app/**/*.{js,ts,jsx,tsx,mdx}",
    "./pages/**/*.{js,ts,jsx,tsx,mdx}",
    "./components/**/*.{js,ts,jsx,tsx,mdx}",
  ],
  darkMode: 'class',
  theme: {
    extend: {
      colors: {
        salmon: {
          DEFAULT: '#FA8072',
          50: '#FFF5F4',
          100: '#FFE8E5',
          200: '#FFD1CB',
          300: '#FFAEA4',
          400: '#FA8072',
          500: '#F05845',
          600: '#DC3A25',
          700: '#BA2B18',
          800: '#992617',
          900: '#7F2418',
        },
        dark: {
          bg: '#0B0D13',
          card: '#121622',
          border: '#1E2538',
          hover: '#192033',
          input: '#151A29',
        },
        opusGreen: '#00FF66',
        cyberYellow: '#FFE600'
      },
      fontFamily: {
        sans: ['Inter', 'sans-serif'],
      },
      animation: {
        'pulse-glow': 'pulseGlow 2s infinite ease-in-out',
        'fade-in': 'fadeIn 0.3s ease-in-out',
      },
      keyframes: {
        pulseGlow: {
          '0%, 100%': { boxShadow: '0 0 15px rgba(250, 128, 114, 0.3)' },
          '50%': { boxShadow: '0 0 25px rgba(250, 128, 114, 0.7)' },
        },
        fadeIn: {
          '0%': { opacity: '0', transform: 'translateY(10px)' },
          '100%': { opacity: '1', transform: 'translateY(0)' },
        }
      }
    },
  },
  plugins: [],
}
