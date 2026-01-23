/** @type {import('tailwindcss').Config} */
export default {
  darkMode: ['class'],
  content: ['./index.html', './src/**/*.{js,ts,jsx,tsx}'],
  theme: {
    extend: {
      colors: {
        // Space Theme Core
        'space-void': 'hsl(var(--space-void))',
        'space-deep': 'hsl(var(--space-deep))',
        'space-nebula': 'hsl(var(--space-nebula))',

        // Cosmic Accent Colors
        'cosmic-cyan': 'hsl(var(--cosmic-cyan))',
        'cosmic-blue': 'hsl(var(--cosmic-blue))',
        'stellar-purple': 'hsl(var(--stellar-purple))',
        'nova-orange': 'hsl(var(--nova-orange))',
        'aurora-green': 'hsl(var(--aurora-green))',

        // Orbital Regime Colors
        'orbital-leo': 'hsl(var(--orbital-leo))',
        'orbital-meo': 'hsl(var(--orbital-meo))',
        'orbital-geo': 'hsl(var(--orbital-geo))',
        'orbital-heo': 'hsl(var(--orbital-heo))',

        // Tier Colors
        'tier-1': 'hsl(var(--tier-1))',
        'tier-2': 'hsl(var(--tier-2))',
        'tier-3': 'hsl(var(--tier-3))',
        'tier-4': 'hsl(var(--tier-4))',

        // Status Colors
        'status-success': '#22C55E',
        'status-warning': '#EAB308',
        'status-error': '#EF4444',
        'status-processing': '#3B82F6',

        // shadcn/ui color system
        border: 'hsl(var(--border))',
        input: 'hsl(var(--input))',
        ring: 'hsl(var(--ring))',
        background: 'hsl(var(--background))',
        foreground: 'hsl(var(--foreground))',
        primary: {
          DEFAULT: 'hsl(var(--primary))',
          foreground: 'hsl(var(--primary-foreground))',
        },
        secondary: {
          DEFAULT: 'hsl(var(--secondary))',
          foreground: 'hsl(var(--secondary-foreground))',
        },
        destructive: {
          DEFAULT: 'hsl(var(--destructive))',
          foreground: 'hsl(var(--destructive-foreground))',
        },
        muted: {
          DEFAULT: 'hsl(var(--muted))',
          foreground: 'hsl(var(--muted-foreground))',
        },
        accent: {
          DEFAULT: 'hsl(var(--accent))',
          foreground: 'hsl(var(--accent-foreground))',
        },
        popover: {
          DEFAULT: 'hsl(var(--popover))',
          foreground: 'hsl(var(--popover-foreground))',
        },
        card: {
          DEFAULT: 'hsl(var(--card))',
          foreground: 'hsl(var(--card-foreground))',
        },
      },
      fontFamily: {
        sans: ['Outfit', 'system-ui', 'sans-serif'],
        display: ['Sora', 'system-ui', 'sans-serif'],
        mono: ['JetBrains Mono', 'Consolas', 'monospace'],
      },
      fontSize: {
        tiny: ['0.75rem', { lineHeight: '1rem' }],
        small: ['0.875rem', { lineHeight: '1.25rem' }],
      },
      spacing: {
        xs: '4px',
        sm: '8px',
        md: '16px',
        lg: '24px',
        xl: '32px',
        '2xl': '48px',
      },
      borderRadius: {
        lg: 'var(--radius)',
        md: 'calc(var(--radius) - 2px)',
        sm: 'calc(var(--radius) - 4px)',
      },
      boxShadow: {
        'glow-sm': '0 0 10px -3px hsl(var(--primary) / 0.4)',
        'glow-md': '0 0 20px -5px hsl(var(--primary) / 0.4)',
        'glow-lg': '0 0 30px -5px hsl(var(--primary) / 0.5)',
        'glow-cyan': '0 0 20px -5px hsl(var(--cosmic-cyan) / 0.5)',
        'glow-purple': '0 0 20px -5px hsl(var(--stellar-purple) / 0.5)',
        'glow-blue': '0 0 20px -5px hsl(var(--cosmic-blue) / 0.5)',
        'inner-glow': 'inset 0 1px 0 0 hsl(var(--primary) / 0.1)',
        'card-hover': '0 20px 40px -15px hsl(var(--primary) / 0.15)',
      },
      backgroundImage: {
        'gradient-radial': 'radial-gradient(var(--tw-gradient-stops))',
        'gradient-cosmic': 'linear-gradient(135deg, hsl(var(--cosmic-cyan)) 0%, hsl(var(--cosmic-blue)) 50%, hsl(var(--stellar-purple)) 100%)',
        'gradient-aurora': 'linear-gradient(135deg, hsl(var(--aurora-green)) 0%, hsl(var(--cosmic-cyan)) 100%)',
        'gradient-space': 'radial-gradient(ellipse at 50% 50%, hsl(var(--space-nebula)) 0%, hsl(var(--space-void)) 100%)',
      },
      keyframes: {
        'accordion-down': {
          from: { height: '0' },
          to: { height: 'var(--radix-accordion-content-height)' },
        },
        'accordion-up': {
          from: { height: 'var(--radix-accordion-content-height)' },
          to: { height: '0' },
        },
        'fade-in': {
          from: { opacity: '0' },
          to: { opacity: '1' },
        },
        'slide-up': {
          from: { transform: 'translateY(10px)', opacity: '0' },
          to: { transform: 'translateY(0)', opacity: '1' },
        },
        'slide-down': {
          from: { transform: 'translateY(-10px)', opacity: '0' },
          to: { transform: 'translateY(0)', opacity: '1' },
        },
        'slide-in-left': {
          from: { transform: 'translateX(-20px)', opacity: '0' },
          to: { transform: 'translateX(0)', opacity: '1' },
        },
        'slide-in-right': {
          from: { transform: 'translateX(20px)', opacity: '0' },
          to: { transform: 'translateX(0)', opacity: '1' },
        },
        'scale-in': {
          from: { transform: 'scale(0.95)', opacity: '0' },
          to: { transform: 'scale(1)', opacity: '1' },
        },
        'pulse-slow': {
          '0%, 100%': { opacity: '1' },
          '50%': { opacity: '0.5' },
        },
        'pulse-glow': {
          '0%, 100%': {
            opacity: '1',
            boxShadow: '0 0 20px -5px hsl(var(--primary) / 0.5)',
          },
          '50%': {
            opacity: '0.8',
            boxShadow: '0 0 30px -5px hsl(var(--primary) / 0.7)',
          },
        },
        orbit: {
          from: { transform: 'rotate(0deg)' },
          to: { transform: 'rotate(360deg)' },
        },
        'orbit-reverse': {
          from: { transform: 'rotate(360deg)' },
          to: { transform: 'rotate(0deg)' },
        },
        float: {
          '0%, 100%': { transform: 'translateY(0px)' },
          '50%': { transform: 'translateY(-10px)' },
        },
        twinkle: {
          '0%, 100%': { opacity: '0.3', transform: 'scale(1)' },
          '50%': { opacity: '1', transform: 'scale(1.2)' },
        },
        shimmer: {
          '0%': { backgroundPosition: '-200% 0' },
          '100%': { backgroundPosition: '200% 0' },
        },
        'gradient-shift': {
          '0%, 100%': { backgroundPosition: '0% 50%' },
          '50%': { backgroundPosition: '100% 50%' },
        },
        'beam-scan': {
          '0%': { transform: 'translateX(-100%)', opacity: '0' },
          '50%': { opacity: '1' },
          '100%': { transform: 'translateX(100%)', opacity: '0' },
        },
      },
      animation: {
        'accordion-down': 'accordion-down 0.2s ease-out',
        'accordion-up': 'accordion-up 0.2s ease-out',
        'fade-in': 'fade-in 0.3s ease-out',
        'slide-up': 'slide-up 0.4s ease-out',
        'slide-down': 'slide-down 0.4s ease-out',
        'slide-in-left': 'slide-in-left 0.4s ease-out',
        'slide-in-right': 'slide-in-right 0.4s ease-out',
        'scale-in': 'scale-in 0.3s ease-out',
        'pulse-slow': 'pulse-slow 2s ease-in-out infinite',
        'pulse-glow': 'pulse-glow 3s ease-in-out infinite',
        orbit: 'orbit 20s linear infinite',
        'orbit-slow': 'orbit 40s linear infinite',
        'orbit-reverse': 'orbit-reverse 25s linear infinite',
        float: 'float 6s ease-in-out infinite',
        twinkle: 'twinkle 3s ease-in-out infinite',
        shimmer: 'shimmer 2s linear infinite',
        'gradient-shift': 'gradient-shift 8s ease infinite',
        'beam-scan': 'beam-scan 3s ease-in-out infinite',
      },
      backdropBlur: {
        xs: '2px',
      },
    },
  },
  plugins: [require('tailwindcss-animate')],
};
