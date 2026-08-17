/** @type {import('tailwindcss').Config} */
export default {
  content: ['./index.html', './src/**/*.{js,ts,jsx,tsx}'],
  theme: {
    extend: {
      colors: {
        primary: {
          50: '#E8F5F1',
          100: '#C5E6DA',
          200: '#9DD4BF',
          300: '#6FBEA0',
          400: '#3FA680',
          500: '#0E7C66',
          600: '#0C6A57',
          700: '#0A5647',
          800: '#084237',
          900: '#052D26',
          DEFAULT: '#0E7C66',
        },
        accent: {
          50: '#FEF5E1',
          100: '#FDE8B8',
          200: '#FCDA87',
          300: '#F9C74F',
          400: '#F4A300',
          500: '#E09300',
          600: '#C78200',
          700: '#9A6500',
          800: '#6D4800',
          900: '#402B00',
          DEFAULT: '#F4A300',
        },
      },
      fontFamily: {
        sans: ['Inter', 'system-ui', '-apple-system', 'sans-serif'],
      },
    },
  },
  plugins: [],
};
