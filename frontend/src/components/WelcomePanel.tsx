import { Compass, Info, X } from 'lucide-react';
import { Link } from 'react-router-dom';

interface WelcomePanelProps {
  onDismiss: () => void;
}

export default function WelcomePanel({ onDismiss }: WelcomePanelProps) {
  return (
    <div className="absolute top-[168px] sm:top-[176px] left-3 sm:left-4 z-20 w-[calc(100%-1.5rem)] max-w-[360px]">
      <div className="bg-gray-950 border border-gray-600/70 rounded-xl shadow-[0_12px_40px_rgba(0,0,0,0.55)] ring-1 ring-white/10 p-4 sm:p-5">
        <div className="flex items-start justify-between gap-3">
          <div className="flex items-center gap-2 text-brand-400">
            <Info size={16} />
            <span className="text-xs font-medium uppercase tracking-wide text-gray-400">Welcome to StreetProof</span>
          </div>
          <button
            type="button"
            onClick={onDismiss}
            className="text-gray-500 hover:text-white transition-colors -mt-1 -mr-1 p-1"
            aria-label="Dismiss welcome panel"
          >
            <X size={16} />
          </button>
        </div>

        <h2 className="mt-3 text-xl sm:text-[1.35rem] font-semibold text-white leading-snug">
          Your city. Your streets. Your voice.
        </h2>
        <p className="mt-2 text-sm text-gray-300 leading-relaxed">
          StreetProof helps communities turn individual reports of public infrastructure problems into a clearer picture of the issues affecting their neighbourhoods.
        </p>

        <div className="mt-4 flex flex-col sm:flex-row gap-2">
          <button
            type="button"
            onClick={onDismiss}
            className="inline-flex items-center justify-center gap-2 px-3.5 py-2.5 rounded-lg bg-brand-500 hover:bg-brand-400 text-white text-sm font-medium transition-colors"
          >
            <Compass size={15} />
            Explore Incidents
          </button>
          <Link
            to="/about"
            className="inline-flex items-center justify-center gap-2 px-3.5 py-2.5 rounded-lg border border-gray-700 text-gray-200 hover:text-white hover:border-gray-500 text-sm font-medium transition-colors"
          >
            Discover StreetProof
          </Link>
        </div>
      </div>
    </div>
  );
}
