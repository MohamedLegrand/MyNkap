import React, { useState } from 'react';
import { Info } from 'lucide-react';

interface HintTooltipProps {
  text: string;
}

// Petite bulle d'aide cliquable (pas seulement au survol, pour rester
// utilisable au doigt sur mobile) — explique une fonctionnalité sans
// occuper de place tant qu'on ne la consulte pas.
export const HintTooltip: React.FC<HintTooltipProps> = ({ text }) => {
  const [isOpen, setIsOpen] = useState(false);

  return (
    <span className="relative inline-flex shrink-0">
      <button
        type="button"
        onClick={() => setIsOpen((prev) => !prev)}
        onBlur={() => setIsOpen(false)}
        aria-label={text}
        aria-expanded={isOpen}
        className="text-muted-foreground hover:text-primary transition-colors"
      >
        <Info className="h-4 w-4" />
      </button>
      {isOpen && (
        <span
          role="tooltip"
          className="absolute left-0 top-full mt-2 w-64 z-50 p-3 rounded-xl border border-border bg-card shadow-lg text-xs font-normal normal-case tracking-normal text-muted-foreground leading-relaxed"
        >
          {text}
        </span>
      )}
    </span>
  );
};
