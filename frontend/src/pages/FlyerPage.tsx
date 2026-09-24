import React from 'react';
import { Printer, ArrowLeft, ExternalLink } from 'lucide-react';
import { Link } from 'react-router-dom';

export const FlyerPage: React.FC = () => {
  return (
    <div className="min-h-screen bg-slate-900 text-slate-100 flex flex-col items-center py-8 px-4 font-sans">
      
      {/* Top Header Navigation & Controls */}
      <div className="w-full max-w-4xl bg-slate-800/90 backdrop-blur-md border border-slate-700/80 rounded-2xl p-4 mb-8 shadow-xl flex flex-wrap items-center justify-between gap-4">
        <div className="flex items-center gap-3">
          <Link 
            to="/" 
            className="p-2.5 rounded-xl bg-slate-700/60 hover:bg-slate-700 text-slate-200 transition-colors flex items-center gap-2 text-sm font-medium"
          >
            <ArrowLeft className="w-4 h-4" />
            <span>Accueil</span>
          </Link>
          <div>
            <h1 className="text-lg font-bold text-emerald-400">Flyer Officiel MyNkap</h1>
            <p className="text-xs text-slate-400">Structure "Avant / Après" (Format A5 / A4 / Web)</p>
          </div>
        </div>

        <div className="flex flex-wrap items-center gap-3">
          <a 
            href="/flyer.html" 
            target="_blank" 
            rel="noopener noreferrer"
            className="px-4 py-2.5 rounded-xl bg-slate-700 hover:bg-slate-600 text-slate-200 text-xs font-semibold flex items-center gap-2 transition-all"
          >
            <ExternalLink className="w-3.5 h-3.5 text-emerald-400" />
            <span>Plein Écran HTML</span>
          </a>

          <button 
            onClick={() => {
              const iframe = document.getElementById('flyer-frame') as HTMLIFrameElement;
              if (iframe && iframe.contentWindow) {
                iframe.contentWindow.print();
              } else {
                window.print();
              }
            }}
            className="px-5 py-2.5 rounded-xl bg-emerald-600 hover:bg-emerald-500 text-white text-xs font-bold flex items-center gap-2 transition-all shadow-lg shadow-emerald-900/30"
          >
            <Printer className="w-4 h-4" />
            <span>Imprimer / Télécharger PDF</span>
          </button>
        </div>
      </div>

      {/* Embedded Flyer Preview Frame */}
      <div className="w-full max-w-2xl bg-white rounded-3xl overflow-hidden shadow-2xl border border-slate-700 flex justify-center p-2 sm:p-6 bg-slate-950/40 backdrop-blur-xl">
        <iframe 
          id="flyer-frame"
          src="/flyer.html" 
          title="MyNkap Flyer Avant/Après"
          className="w-[595px] h-[842px] border-0 rounded-2xl bg-white shadow-2xl transform scale-90 sm:scale-100 origin-top"
          style={{ maxWidth: '100%' }}
        />
      </div>

      {/* Footer Info */}
      <div className="mt-8 text-center text-xs text-slate-500 space-y-1">
        <p>Ce flyer est prêt pour l'impression physique A5 / A4 (300 DPI) et la distribution digitale.</p>
        <p>Lien direct : <a href="https://my-nkap.com/flyer.html" className="text-emerald-400 underline">my-nkap.com/flyer.html</a></p>
      </div>

    </div>
  );
};

export default FlyerPage;
