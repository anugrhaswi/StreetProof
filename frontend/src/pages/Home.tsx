import { MapPin, Camera, Brain, ShieldCheck } from 'lucide-react';
import ConnectionStatus from '../components/ConnectionStatus';

const features = [
  {
    icon: Camera,
    title: 'Photo Evidence',
    description: 'Report infrastructure issues with photographs and clear descriptions.',
  },
  {
    icon: MapPin,
    title: 'Geo-Located',
    description: 'Pinpoint problems with precise geographic coordinates for faster response.',
  },
  {
    icon: Brain,
    title: 'AI-Assisted Matching',
    description: 'Semantic and geographic analysis identifies potential duplicate reports.',
  },
  {
    icon: ShieldCheck,
    title: 'Human-Verified',
    description: 'Moderators review and approve incident grouping before consolidation.',
  },
];

export default function Home() {
  return (
    <div className="max-w-6xl mx-auto px-6 py-16 md:py-24">
      <section className="max-w-3xl">
        <p className="text-brand-400 text-sm font-medium tracking-wide uppercase mb-4">
          Civic Infrastructure Intelligence
        </p>
        <h1 className="text-4xl md:text-5xl font-bold text-white tracking-tight leading-tight mb-6">
          Report issues.
          <br />
          <span className="text-gray-400">Reveal patterns.</span>
        </h1>
        <p className="text-lg text-gray-400 leading-relaxed mb-8 max-w-2xl">
          StreetProof helps citizens report infrastructure problems and gives moderators
          AI-assisted tools to identify duplicates, group incidents, and act on verified evidence.
        </p>
        <div className="flex items-center gap-4">
          <ConnectionStatus />
        </div>
      </section>

      <section className="mt-20 grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-6">
        {features.map((feature) => {
          const Icon = feature.icon;
          return (
            <div
              key={feature.title}
              className="p-5 rounded-xl border border-gray-800/70 bg-gray-900/30 hover:bg-gray-900/50 transition-colors"
            >
              <div className="w-10 h-10 rounded-lg bg-brand-500/10 border border-brand-500/20 flex items-center justify-center mb-4">
                <Icon size={20} className="text-brand-400" />
              </div>
              <h3 className="text-white font-medium mb-2">{feature.title}</h3>
              <p className="text-sm text-gray-400 leading-relaxed">{feature.description}</p>
            </div>
          );
        })}
      </section>
    </div>
  );
}
