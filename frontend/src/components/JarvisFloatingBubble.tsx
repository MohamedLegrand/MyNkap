import React, { useState } from 'react';
import { Bot, X } from 'lucide-react';
import { JarvisWidget } from './JarvisWidget';

export const JarvisFloatingBubble: React.FC = () => {
  const [isOpen, setIsOpen] = useState(false);

  return (
    <>
      {isOpen && (
        <div className="fixed bottom-24 right-4 sm:right-6 z-50 w-[calc(100vw-2rem)] sm:w-96 max-h-[75vh] overflow-y-auto animate-in slide-in-from-bottom-4 fade-in duration-200">
          <div className="relative">
            <button
              onClick={() => setIsOpen(false)}
              title="Fermer"
              className="absolute -top-2 -right-2 z-10 h-7 w-7 rounded-full bg-foreground text-background shadow-md flex items-center justify-center hover:opacity-90 transition-opacity"
            >
              <X className="h-3.5 w-3.5" />
            </button>
            <JarvisWidget />
          </div>
        </div>
      )}

      <button
        onClick={() => setIsOpen((prev) => !prev)}
        title="Assistant JARVIS"
        className="fixed bottom-6 right-4 sm:right-6 z-50 h-14 w-14 rounded-full bg-secondary text-secondary-foreground shadow-xl flex items-center justify-center hover:scale-105 active:scale-95 transition-transform"
      >
        {isOpen ? <X className="h-6 w-6" /> : <Bot className="h-6 w-6" />}
      </button>
    </>
  );
};
