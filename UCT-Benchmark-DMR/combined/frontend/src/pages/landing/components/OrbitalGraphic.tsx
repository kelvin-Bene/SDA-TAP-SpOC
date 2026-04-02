export function OrbitalGraphic() {
  return (
    <div className="relative w-full max-w-[420px] aspect-square mx-auto">
      <svg viewBox="0 0 400 400" className="w-full h-full" aria-hidden="true">
        {/* Outer ring - HEO */}
        <circle cx="200" cy="200" r="180" fill="none" stroke="hsl(0 72% 51% / 0.15)" strokeWidth="1" strokeDasharray="8 6" className="animate-orbit-reverse" style={{ transformOrigin: '200px 200px' }} />
        {/* Third ring - GEO */}
        <circle cx="200" cy="200" r="140" fill="none" stroke="hsl(45 93% 47% / 0.2)" strokeWidth="1" className="animate-orbit-slow" style={{ transformOrigin: '200px 200px' }} />
        {/* Second ring - MEO */}
        <circle cx="200" cy="200" r="100" fill="none" stroke="hsl(142 76% 45% / 0.25)" strokeWidth="1" strokeDasharray="4 4" className="animate-orbit" style={{ transformOrigin: '200px 200px' }} />
        {/* Inner ring - LEO */}
        <circle cx="200" cy="200" r="60" fill="none" stroke="hsl(217 91% 60% / 0.3)" strokeWidth="1.5" className="animate-orbit-reverse" style={{ transformOrigin: '200px 200px' }} />

        {/* Central body */}
        <circle cx="200" cy="200" r="8" fill="url(#coreGrad)" />
        <circle cx="200" cy="200" r="16" fill="none" stroke="hsl(192 91% 52% / 0.2)" strokeWidth="1" />

        {/* Orbiting objects */}
        <g className="animate-orbit" style={{ transformOrigin: '200px 200px' }}>
          <circle cx="200" cy="140" r="4" fill="hsl(217 91% 60%)" />
          <circle cx="200" cy="140" r="8" fill="hsl(217 91% 60% / 0.2)" />
        </g>
        <g className="animate-orbit-slow" style={{ transformOrigin: '200px 200px' }}>
          <circle cx="300" cy="200" r="3.5" fill="hsl(142 76% 45%)" />
          <circle cx="300" cy="200" r="7" fill="hsl(142 76% 45% / 0.2)" />
        </g>
        <g className="animate-orbit-reverse" style={{ transformOrigin: '200px 200px' }}>
          <circle cx="200" cy="60" r="3" fill="hsl(45 93% 47%)" />
          <circle cx="200" cy="60" r="6" fill="hsl(45 93% 47% / 0.2)" />
        </g>
        <g className="animate-orbit" style={{ transformOrigin: '200px 200px', animationDuration: '35s' }}>
          <circle cx="380" cy="200" r="2.5" fill="hsl(0 72% 51%)" />
          <circle cx="380" cy="200" r="5" fill="hsl(0 72% 51% / 0.2)" />
        </g>

        {/* Additional orbiting dots for density */}
        <g className="animate-orbit-slow" style={{ transformOrigin: '200px 200px', animationDuration: '28s' }}>
          <circle cx="120" cy="240" r="2" fill="hsl(192 91% 52% / 0.6)" />
        </g>
        <g className="animate-orbit-reverse" style={{ transformOrigin: '200px 200px', animationDuration: '50s' }}>
          <circle cx="260" cy="50" r="2" fill="hsl(265 89% 66% / 0.5)" />
        </g>

        <defs>
          <radialGradient id="coreGrad">
            <stop offset="0%" stopColor="hsl(192 91% 52%)" />
            <stop offset="100%" stopColor="hsl(217 91% 60%)" />
          </radialGradient>
        </defs>
      </svg>
    </div>
  );
}
