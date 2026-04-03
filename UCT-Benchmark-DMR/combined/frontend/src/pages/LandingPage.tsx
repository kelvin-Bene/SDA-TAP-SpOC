import { LandingNav } from './landing/LandingNav';
import { HeroSection } from './landing/HeroSection';
import { ProblemSection } from './landing/ProblemSection';
import { SolutionSection } from './landing/SolutionSection';
import { CapabilitiesSection } from './landing/CapabilitiesSection';
import { TiersSection } from './landing/TiersSection';
import { CTASection } from './landing/CTASection';

export default function LandingPage() {
  return (
    <div className="min-h-screen space-bg text-foreground">
      <div className="starfield" />
      <LandingNav />
      <HeroSection />
      <ProblemSection />
      <SolutionSection />
      <CapabilitiesSection />
      <TiersSection />
      <CTASection />
    </div>
  );
}
