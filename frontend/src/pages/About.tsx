import { Link } from 'react-router-dom';
import {
  ArrowRight,
  Building2,
  Camera,
  CheckCircle2,
  ChevronRight,
  CircleAlert,
  Database,
  Eye,
  FileImage,
  FileText,
  Fingerprint,
  Globe2,
  Hash,
  Image as ImageIcon,
  Languages,
  Layers3,
  MapPin,
  MapPinned,
  Network,
  Radar,
  ScanSearch,
  ShieldCheck,
  Sparkles,
  Users,
  Waypoints,
} from 'lucide-react';

const workflowStages = [
  {
    title: 'Stage 1: Citizens report issues',
    icon: Camera,
    tone: 'bg-brand-500/10 text-brand-400 border-brand-500/20',
    items: ['Photographs', 'Descriptions', 'Issue categories', 'Geographic locations'],
  },
  {
    title: 'Stage 2: Related reports are evaluated',
    icon: ScanSearch,
    tone: 'bg-amber-500/10 text-amber-300 border-amber-500/20',
    items: [
      'Exact image matching using SHA-256',
      'Perceptual image similarity',
      'Geographic proximity',
      'Category compatibility',
      'Semantic similarity where enabled',
    ],
  },
  {
    title: 'Stage 3: Incidents become easier to understand',
    icon: Layers3,
    tone: 'bg-emerald-500/10 text-emerald-300 border-emerald-500/20',
    items: [
      'Related reports can be associated with an incident, subject to moderation rules',
      'Original submissions and evidence remain preserved',
      'Map and admin views provide incident-level visibility',
    ],
  },
];

const matchingSignals = [
  {
    title: 'Semantic similarity',
    icon: Sparkles,
    status: 'Local AI config only',
    description:
      'Compares report descriptions using sentence embeddings to identify reports that may describe the same problem in different words.',
    limitation:
      'Available in the local semantic AI configuration, but disabled in the current hosted production environment due Render Free memory limits. It is a similarity signal, not proof of a duplicate.',
  },
  {
    title: 'Exact image matching',
    icon: Hash,
    status: 'Active in lightweight mode',
    description:
      'Uses SHA-256 image hashes to detect when the same image file or identical image content is submitted again.',
    limitation:
      'Exact matches are strong evidence, but identical photos can be reused in different contexts; location and incident state still need review.',
  },
  {
    title: 'Perceptual hashing',
    icon: Fingerprint,
    status: 'Active in lightweight mode',
    description:
      'Uses perceptual hashing (pHash) to compare images that look similar even when files are not byte-for-byte identical.',
    limitation:
      'Similar-looking photos can still depict different nearby issues, so pHash is used with other signals and human review.',
  },
  {
    title: 'Geographic matching',
    icon: MapPinned,
    status: 'Active in lightweight mode',
    description:
      'Measures distance between report coordinates to understand whether submissions are close enough to describe the same physical issue.',
    limitation:
      'GPS coordinates can be imprecise, and nearby issues may be distinct. Distance alone cannot confirm an incident match.',
  },
  {
    title: 'Category matching',
    icon: Layers3,
    status: 'Active in lightweight mode',
    description:
      'Checks whether reports share a compatible issue category, such as pothole, streetlight, or drainage.',
    limitation:
      'Category mismatch is a useful caution signal, but citizens may categorize similar problems differently.',
  },
  {
    title: 'Human moderation',
    icon: ShieldCheck,
    status: 'Active',
    description:
      'Administrators review uncertain matches, accept or reject suggestions, and manage incident status through auditable workflows.',
    limitation:
      'Human review improves safety, but it depends on available evidence, reviewer capacity, and clear governance processes.',
  },
];

const roadmap = [
  {
    stage: 'Stage 1: Local civic visibility',
    status: 'Prototype foundation',
    items: [
      'Functional citizen reporting',
      'Incident-level organization',
      'Map-based exploration',
      'Administrative moderation',
    ],
  },
  {
    stage: 'Stage 2: Ward-level deployment',
    status: 'Future proposal',
    items: [
      'Ward-specific dashboards',
      'Local issue distribution',
      'Department-based incident organization',
      'Incident status and resolution monitoring',
    ],
  },
  {
    stage: 'Stage 3: Multilingual accessibility',
    status: 'Future proposal',
    items: [
      'Hindi and Bengali',
      'Other regional Indian languages',
      'Multilingual semantic understanding',
      'Low-bandwidth and mobile-friendly reporting',
      'Accessible reporting workflows',
    ],
  },
  {
    stage: 'Stage 4: Municipal integration',
    status: 'Future proposal',
    items: [
      'Approved integrations with existing grievance systems',
      'Municipality-specific dashboards',
      'Department workflows',
      'Resolution verification',
      'Incident analytics',
    ],
  },
  {
    stage: 'Stage 5: City-wide infrastructure intelligence',
    status: 'Future proposal',
    items: [
      'Historical infrastructure trends',
      'Geospatial hotspot analysis',
      'Repeated issue identification',
      'Department workload insights',
      'Cross-ward incident patterns',
      'Multi-municipality support',
    ],
  },
];

const references = [
  {
    label: 'Swachhata platform dashboard',
    href: 'https://dashboard.swachh.city/',
    note: 'Official Swachh Bharat Mission (Urban) dashboard reference.',
  },
  {
    label: 'CPGRAMS: About Us',
    href: 'https://pgportal.gov.in/Home/AboutUs',
    note: 'Government of India public grievance platform overview.',
  },
  {
    label: 'Smart Cities ICCC press release (PIB)',
    href: 'https://www.pib.gov.in/PressReleasePage.aspx?PRID=2288501',
    note: 'Government information on Integrated Command and Control Centres.',
  },
];

function SectionLabel({ children }: { children: string }) {
  return <p className="text-sm font-medium tracking-wide uppercase text-brand-400 mb-3">{children}</p>;
}

function Card({
  children,
  className = '',
}: {
  children: React.ReactNode;
  className?: string;
}) {
  return <div className={`rounded-2xl border border-gray-200 bg-white shadow-sm ${className}`}>{children}</div>;
}

export default function About() {
  return (
    <div className="bg-[#f7f9fc] text-slate-900">
      <section className="relative overflow-hidden border-b border-slate-200">
        <div className="absolute inset-0 bg-[radial-gradient(circle_at_top_right,rgba(59,130,246,0.12),transparent_45%),radial-gradient(circle_at_left,rgba(15,23,42,0.04),transparent_35%)]" />
        <div className="relative max-w-7xl mx-auto px-4 sm:px-6 py-16 sm:py-20 lg:py-24">
          <div className="grid lg:grid-cols-[1.1fr_0.9fr] gap-10 items-center">
            <div>
              <SectionLabel>About StreetProof</SectionLabel>
              <h1 className="text-4xl sm:text-5xl lg:text-6xl font-semibold tracking-tight text-slate-950 leading-[1.08] max-w-4xl">
                Cities don&apos;t just need more complaint forms. They need better ways to understand the problems citizens are reporting.
              </h1>
              <p className="mt-6 text-lg sm:text-xl text-slate-700 max-w-3xl leading-relaxed">
                StreetProof is an AI-powered civic infrastructure intelligence platform designed to connect fragmented citizen reports to the real-world incidents they describe.
              </p>
              <p className="mt-4 text-base sm:text-lg text-slate-600 max-w-3xl leading-relaxed">
                From potholes and broken streetlights to damaged sidewalks and drainage problems, StreetProof explores how technology can help organize public infrastructure reports into more meaningful, geographically grounded incident information.
              </p>
              <div className="mt-8 flex flex-col sm:flex-row gap-3">
                <Link
                  to="/"
                  className="inline-flex items-center justify-center gap-2 px-5 py-3 rounded-lg bg-brand-500 hover:bg-brand-400 text-white font-medium transition-colors"
                >
                  Explore the Map
                  <ArrowRight size={16} />
                </Link>
                <Link
                  to="/report"
                  className="inline-flex items-center justify-center gap-2 px-5 py-3 rounded-lg border border-slate-300 bg-white hover:bg-slate-50 text-slate-800 font-medium transition-colors"
                >
                  Report an Issue
                </Link>
              </div>
            </div>

            <Card className="p-6 sm:p-8 bg-white/90 backdrop-blur">
              <div className="flex items-center gap-2 text-sm font-medium text-slate-500 mb-5">
                <MapPin size={16} className="text-brand-500" />
                Map-first civic intelligence
              </div>
              <div className="rounded-xl border border-slate-200 bg-slate-950 p-5 text-slate-100">
                <div className="flex items-center justify-between text-xs text-slate-400 mb-4">
                  <span>Incident map view</span>
                  <span className="inline-flex items-center gap-1"><span className="w-2 h-2 rounded-full bg-emerald-400" />Live prototype</span>
                </div>
                <div className="relative h-52 rounded-lg border border-slate-800 bg-[linear-gradient(180deg,#111827_0%,#0f172a_100%)] overflow-hidden">
                  <div className="absolute inset-0 opacity-30 bg-[linear-gradient(to_right,#334155_1px,transparent_1px),linear-gradient(to_bottom,#334155_1px,transparent_1px)] bg-[size:32px_32px]" />
                  <div className="absolute left-[18%] top-[28%] w-8 h-8 rounded-full bg-red-500/90 border-2 border-red-200 flex items-center justify-center text-white text-xs font-semibold">!</div>
                  <div className="absolute left-[58%] top-[40%] w-8 h-8 rounded-full bg-amber-400/90 border-2 border-amber-100 flex items-center justify-center text-slate-900 text-xs font-semibold">2</div>
                  <div className="absolute left-[72%] top-[62%] w-8 h-8 rounded-full bg-green-500/90 border-2 border-green-100 flex items-center justify-center text-white text-xs font-semibold">✓</div>
                  <div className="absolute left-4 bottom-4 right-4 rounded-lg bg-slate-900/90 border border-slate-700 p-3">
                    <p className="text-xs text-slate-400">Selected incident</p>
                    <p className="text-sm font-medium text-white mt-0.5">Pothole near college entrance</p>
                    <p className="text-xs text-slate-400 mt-1">3 reports • Open • Human review preserved</p>
                  </div>
                </div>
              </div>
              <div className="mt-5 grid grid-cols-3 gap-3 text-center">
                <div className="rounded-lg bg-slate-50 border border-slate-200 p-3">
                  <p className="text-xs text-slate-500">Reports</p>
                  <p className="text-sm font-semibold text-slate-900 mt-1">Citizen evidence</p>
                </div>
                <div className="rounded-lg bg-slate-50 border border-slate-200 p-3">
                  <p className="text-xs text-slate-500">Signals</p>
                  <p className="text-sm font-semibold text-slate-900 mt-1">AI-assisted</p>
                </div>
                <div className="rounded-lg bg-slate-50 border border-slate-200 p-3">
                  <p className="text-xs text-slate-500">Incidents</p>
                  <p className="text-sm font-semibold text-slate-900 mt-1">Map visibility</p>
                </div>
              </div>
            </Card>
          </div>
        </div>
      </section>
      <section className="max-w-7xl mx-auto px-4 sm:px-6 py-16 sm:py-20">
        <SectionLabel>The problem we&apos;re addressing</SectionLabel>
        <div className="max-w-3xl">
          <h2 className="text-3xl sm:text-4xl font-semibold tracking-tight text-slate-950">One problem. Many reports. Fragmented information.</h2>
          <p className="mt-4 text-slate-600 leading-relaxed">
            StreetProof is designed around common civic-reporting challenges. The goal is not to claim that every municipal system has the same limitations, but to address the information fragmentation that can appear when public infrastructure issues are reported by many people over time.
          </p>
        </div>

        <div className="mt-10 grid md:grid-cols-2 xl:grid-cols-3 gap-5">
          {[
            {
              icon: FileText,
              title: 'Fragmented reporting',
              text: 'Different citizens may independently report the same physical issue using different descriptions, photographs and submission times.',
            },
            {
              icon: CircleAlert,
              title: 'Repeated complaints',
              text: 'Multiple submissions concerning one underlying problem can make it difficult to distinguish the number of reports from the number of distinct incidents.',
            },
            {
              icon: FileImage,
              title: 'Disconnected evidence',
              text: 'Each report contains its own context, image, description and timestamp. Important relationships between submissions may not be immediately visible.',
            },
            {
              icon: Eye,
              title: 'Limited incident-level visibility',
              text: 'Looking at individual reports does not always provide a clear picture of recurring or geographically concentrated infrastructure problems.',
            },
            {
              icon: Waypoints,
              title: 'Why it matters',
              text: 'A better-organized incident picture can help citizens and authorized organizations understand which real-world problems are receiving repeated attention.',
            },
          ].map((item) => (
            <Card key={item.title} className="p-6">
              <div className="w-10 h-10 rounded-lg bg-brand-500/10 text-brand-600 flex items-center justify-center mb-4">
                <item.icon size={20} />
              </div>
              <h3 className="text-lg font-semibold text-slate-900">{item.title}</h3>
              <p className="mt-2 text-sm leading-relaxed text-slate-600">{item.text}</p>
            </Card>
          ))}
        </div>
      </section>

      <section className="bg-white border-y border-slate-200">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 py-16 sm:py-20">
          <SectionLabel>Reports versus incidents</SectionLabel>
          <div className="max-w-3xl">
            <h2 className="text-3xl sm:text-4xl font-semibold tracking-tight text-slate-950">Understanding the difference between a report and an incident.</h2>
            <p className="mt-4 text-slate-600 leading-relaxed">
              This distinction is central to StreetProof. The platform preserves individual citizen submissions while helping identify relationships between reports that may describe the same real-world infrastructure problem.
            </p>
          </div>

          <div className="mt-10 grid lg:grid-cols-[1fr_auto_1fr] gap-6 items-stretch">
            <Card className="p-6">
              <p className="text-xs font-semibold uppercase tracking-wide text-slate-500 mb-4">Individual reports</p>
              <div className="space-y-4">
                <div className="rounded-xl border border-slate-200 bg-slate-50 p-4">
                  <div className="flex items-center gap-2 text-sm font-medium text-slate-900"><Users size={16} className="text-brand-500" /> Citizen A</div>
                  <p className="mt-2 text-sm text-slate-600">"Large pothole near the college entrance."</p>
                </div>
                <div className="rounded-xl border border-slate-200 bg-slate-50 p-4">
                  <div className="flex items-center gap-2 text-sm font-medium text-slate-900"><Users size={16} className="text-brand-500" /> Citizen B</div>
                  <p className="mt-2 text-sm text-slate-600">"Road surface damaged beside the college gate."</p>
                </div>
                <div className="rounded-xl border border-slate-200 bg-slate-50 p-4">
                  <div className="flex items-center gap-2 text-sm font-medium text-slate-900"><ImageIcon size={16} className="text-brand-500" /> Citizen C</div>
                  <p className="mt-2 text-sm text-slate-600">Submits a photograph of the same pothole.</p>
                </div>
              </div>
            </Card>

            <div className="flex lg:flex-col items-center justify-center gap-3 text-slate-400">
              <div className="hidden lg:block w-px h-16 bg-slate-200" />
              <div className="rounded-full border border-slate-200 bg-slate-50 p-3">
                <ChevronRight size={20} className="rotate-90 lg:rotate-0" />
              </div>
              <div className="hidden lg:block w-px h-16 bg-slate-200" />
            </div>

            <Card className="p-6 border-brand-200 bg-brand-50/30">
              <p className="text-xs font-semibold uppercase tracking-wide text-brand-600 mb-4">Underlying incident</p>
              <div className="rounded-xl border border-brand-200 bg-white p-5">
                <div className="flex items-center gap-2 text-brand-600 font-medium text-sm">
                  <MapPin size={16} />
                  One real-world infrastructure problem
                </div>
                <h3 className="mt-3 text-xl font-semibold text-slate-950">Pothole at college entrance</h3>
                <p className="mt-2 text-sm text-slate-600 leading-relaxed">
                  Three independent reports may relate to one underlying physical incident. StreetProof can help make that relationship visible while keeping every original report intact.
                </p>
                <div className="mt-4 flex flex-wrap gap-2 text-xs">
                  <span className="px-2.5 py-1 rounded-full bg-slate-100 text-slate-700 border border-slate-200">3 reports preserved</span>
                  <span className="px-2.5 py-1 rounded-full bg-emerald-50 text-emerald-700 border border-emerald-200">1 incident view</span>
                  <span className="px-2.5 py-1 rounded-full bg-amber-50 text-amber-700 border border-amber-200">Review rules apply</span>
                </div>
              </div>
            </Card>
          </div>

          <div className="mt-8 grid md:grid-cols-3 gap-4 text-sm">
            <div className="rounded-xl bg-slate-50 border border-slate-200 p-4 text-slate-700"><span className="font-semibold text-slate-900">A report</span> is an individual citizen submission.</div>
            <div className="rounded-xl bg-slate-50 border border-slate-200 p-4 text-slate-700"><span className="font-semibold text-slate-900">An incident</span> is the real-world infrastructure problem that one or more reports may describe.</div>
            <div className="rounded-xl bg-slate-50 border border-slate-200 p-4 text-slate-700"><span className="font-semibold text-slate-900">StreetProof preserves</span> each original report while helping identify relationships between reports.</div>
          </div>
          <p className="mt-4 text-sm text-slate-500">StreetProof does not imply that separate reports are automatically merged in all situations. Matching and merge decisions are subject to configured rules and moderation safeguards.</p>
        </div>
      </section>
      <section className="max-w-7xl mx-auto px-4 sm:px-6 py-16 sm:py-20">
        <SectionLabel>How StreetProof works</SectionLabel>
        <div className="max-w-3xl">
          <h2 className="text-3xl sm:text-4xl font-semibold tracking-tight text-slate-950">A clear workflow from citizen report to incident visibility.</h2>
          <p className="mt-4 text-slate-600 leading-relaxed">
            The platform combines citizen evidence, AI-assisted similarity signals, and human moderation. Each stage is designed to improve visibility while preserving original submissions.
          </p>
        </div>

        <div className="mt-10 grid lg:grid-cols-3 gap-5">
          {workflowStages.map((stage, index) => (
            <Card key={stage.title} className="p-6 relative">
              <div className="flex items-center justify-between mb-5">
                <div className={`w-11 h-11 rounded-xl border flex items-center justify-center ${stage.tone}`}>
                  <stage.icon size={20} />
                </div>
                <span className="text-xs font-semibold text-slate-400">0{index + 1}</span>
              </div>
              <h3 className="text-lg font-semibold text-slate-900">{stage.title}</h3>
              <ul className="mt-4 space-y-2.5">
                {stage.items.map((item) => (
                  <li key={item} className="flex gap-2.5 text-sm text-slate-600 leading-relaxed">
                    <CheckCircle2 size={16} className="text-brand-500 mt-0.5 shrink-0" />
                    <span>{item}</span>
                  </li>
                ))}
              </ul>
            </Card>
          ))}
        </div>
        <div className="mt-6 rounded-xl border border-amber-200 bg-amber-50 px-4 py-3 text-sm text-amber-900">
          Matching signals help identify <span className="font-medium">potential relationships</span>; they do not guarantee a correct match. Automatic merging is disabled in the current production configuration.
        </div>
      </section>

      <section className="bg-slate-950 text-slate-100 border-y border-slate-800">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 py-16 sm:py-20">
          <SectionLabel>How we&apos;re different</SectionLabel>
          <div className="max-w-3xl">
            <h2 className="text-3xl sm:text-4xl font-semibold tracking-tight text-white">Different focus. Complementary purpose.</h2>
            <p className="mt-4 text-slate-300 leading-relaxed">
              India already has important civic grievance and urban operations platforms. StreetProof does not replace them. It explores a specific product focus: organizing citizen reports into incident-level, geographically grounded intelligence with transparent matching evidence.
            </p>
          </div>

          <div className="mt-10 grid xl:grid-cols-3 gap-5">
            <div className="rounded-2xl border border-slate-800 bg-slate-900/70 p-6">
              <div className="flex items-center gap-2 text-brand-300 font-medium"><Building2 size={18} /> Swachhata platform</div>
              <p className="mt-3 text-sm text-slate-300 leading-relaxed">
                The Swachhata platform is associated with Swachh Bharat Mission (Urban). Its official dashboard describes citizen reporting with photograph-based complaints, geolocation, and status updates.
              </p>
              <p className="mt-3 text-sm text-slate-400 leading-relaxed">
                <span className="text-slate-200 font-medium">StreetProof focus:</span> exploring how multiple related reports can be evaluated as potential evidence for one underlying incident, while preserving each submission.
              </p>
            </div>
            <div className="rounded-2xl border border-slate-800 bg-slate-900/70 p-6">
              <div className="flex items-center gap-2 text-brand-300 font-medium"><Network size={18} /> CPGRAMS</div>
              <p className="mt-3 text-sm text-slate-300 leading-relaxed">
                CPGRAMS is the Government of India&apos;s public grievance platform, allowing citizens to submit grievances, track status, and use appeal mechanisms as described by the official portal.
              </p>
              <p className="mt-3 text-sm text-slate-400 leading-relaxed">
                <span className="text-slate-200 font-medium">StreetProof focus:</span> a map-first, report-to-incident model for public infrastructure issues, with multimodal matching signals and moderation-oriented incident review.
              </p>
            </div>
            <div className="rounded-2xl border border-slate-800 bg-slate-900/70 p-6">
              <div className="flex items-center gap-2 text-brand-300 font-medium"><Radar size={18} /> Smart Cities ICCCs</div>
              <p className="mt-3 text-sm text-slate-300 leading-relaxed">
                Smart Cities Integrated Command and Control Centres are described by government sources as technology-enabled urban operations systems that bring information from different service areas together.
              </p>
              <p className="mt-3 text-sm text-slate-400 leading-relaxed">
                <span className="text-slate-200 font-medium">StreetProof focus:</span> a lightweight citizen-report intelligence layer that could complement broader urban operations by making duplicate/report relationships easier to inspect.
              </p>
            </div>
          </div>

          <div className="mt-8 rounded-2xl border border-slate-800 bg-slate-900/50 p-6">
            <h3 className="text-lg font-semibold text-white">StreetProof&apos;s specific product focus</h3>
            <div className="mt-4 grid sm:grid-cols-2 lg:grid-cols-3 gap-3 text-sm text-slate-300">
              {[
                'Treating report-to-incident relationships as a central concept.',
                'Exploring multimodal similarity across images, geography, categories and descriptions.',
                'Preserving individual submissions while allowing incident-level visibility.',
                'Providing a map-first way to explore reported infrastructure issues.',
                'Supporting human moderation and auditable incident management.',
                'Designed as a complementary concept, not a replacement for official grievance systems.',
              ].map((item) => (
                <div key={item} className="flex gap-2.5 rounded-lg border border-slate-800 bg-slate-950/40 p-3">
                  <CheckCircle2 size={16} className="text-brand-400 mt-0.5 shrink-0" />
                  <span>{item}</span>
                </div>
              ))}
            </div>
            <p className="mt-4 text-xs text-slate-400 leading-relaxed">
              StreetProof is a prototype and is not government-approved, government-integrated, or officially partnered with the platforms mentioned above.
            </p>
          </div>
        </div>
      </section>
      <section className="max-w-7xl mx-auto px-4 sm:px-6 py-16 sm:py-20">
        <SectionLabel>What makes the approach interesting</SectionLabel>
        <div className="max-w-3xl">
          <h2 className="text-3xl sm:text-4xl font-semibold tracking-tight text-slate-950">Multiple signals, conservative decisions.</h2>
          <p className="mt-4 text-slate-600 leading-relaxed">
            StreetProof treats duplicate detection as an evidence problem. Different signals contribute different kinds of confidence, and uncertain cases are designed for human review rather than silent automation.
          </p>
        </div>

        <div className="mt-6 rounded-xl border border-blue-200 bg-blue-50 px-4 py-3 text-sm text-blue-950">
          <span className="font-semibold">Current implementation status:</span> the current hosted production environment uses the lightweight matching path. Semantic matching is available in the local AI configuration but disabled in production because semantic model loading exceeded Render Free memory limits. Automatic merging is also disabled in production.
        </div>

        <div className="mt-8 grid md:grid-cols-2 xl:grid-cols-3 gap-5">
          {matchingSignals.map((signal) => (
            <Card key={signal.title} className="p-6">
              <div className="flex items-start justify-between gap-3">
                <div className="w-10 h-10 rounded-lg bg-brand-500/10 text-brand-600 flex items-center justify-center">
                  <signal.icon size={20} />
                </div>
                <span className={`text-[11px] px-2 py-1 rounded-full border ${
                  signal.status === 'Active'
                    ? 'bg-emerald-50 text-emerald-700 border-emerald-200'
                    : signal.status === 'Active in lightweight mode'
                    ? 'bg-blue-50 text-blue-700 border-blue-200'
                    : 'bg-amber-50 text-amber-700 border-amber-200'
                }`}>{signal.status}</span>
              </div>
              <h3 className="mt-4 text-lg font-semibold text-slate-900">{signal.title}</h3>
              <p className="mt-2 text-sm text-slate-600 leading-relaxed">{signal.description}</p>
              <div className="mt-4 pt-4 border-t border-slate-100">
                <p className="text-xs font-medium uppercase tracking-wide text-slate-500">Limitation</p>
                <p className="mt-1 text-sm text-slate-600 leading-relaxed">{signal.limitation}</p>
              </div>
            </Card>
          ))}
        </div>
      </section>

      <section className="bg-white border-y border-slate-200">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 py-16 sm:py-20">
          <div className="grid lg:grid-cols-[1fr_1fr] gap-10 items-start">
            <div>
              <SectionLabel>Why India</SectionLabel>
              <h2 className="text-3xl sm:text-4xl font-semibold tracking-tight text-slate-950">Built with Indian cities in mind.</h2>
              <p className="mt-4 text-slate-600 leading-relaxed">
                StreetProof is being explored as a civic technology prototype relevant to Indian urban environments, where growing cities, diverse municipal structures, and high volumes of citizen feedback make clear incident visibility valuable.
              </p>
              <p className="mt-4 text-slate-600 leading-relaxed">
                India already has established civic grievance platforms and urban command systems. StreetProof&apos;s ambition is to explore an additional report-consolidation and incident-intelligence layer that could complement those systems where appropriate and approved.
              </p>
            </div>
            <Card className="p-6">
              <h3 className="text-lg font-semibold text-slate-900 mb-4">Relevant considerations</h3>
              <div className="space-y-3">
                {[
                  { icon: Building2, text: 'Growing and changing cities with evolving public infrastructure needs.' },
                  { icon: MapPinned, text: 'Geographical organization of local problems across wards, neighborhoods, and roads.' },
                  { icon: Globe2, text: 'Diverse municipal structures and administrative workflows across states and cities.' },
                  { icon: Languages, text: 'The value of multilingual and mobile-first interfaces for accessible reporting.' },
                  { icon: Network, text: 'The possibility of complementing existing municipal digital systems rather than replacing them.' },
                ].map((item) => (
                  <div key={item.text} className="flex gap-3 rounded-lg bg-slate-50 border border-slate-200 p-3">
                    <item.icon size={18} className="text-brand-500 mt-0.5 shrink-0" />
                    <p className="text-sm text-slate-700 leading-relaxed">{item.text}</p>
                  </div>
                ))}
              </div>
            </Card>
          </div>
        </div>
      </section>
      <section className="max-w-7xl mx-auto px-4 sm:px-6 py-16 sm:py-20">
        <SectionLabel>Future vision for India</SectionLabel>
        <div className="max-w-3xl">
          <h2 className="text-3xl sm:text-4xl font-semibold tracking-tight text-slate-950">A roadmap grounded in possibility, not promises.</h2>
          <p className="mt-4 text-slate-600 leading-relaxed">
            The stages below are future proposals. They describe directions StreetProof could explore with the right partnerships, safeguards, and operational readiness.
          </p>
        </div>

        <div className="mt-10 grid lg:grid-cols-5 gap-4">
          {roadmap.map((stage) => (
            <Card key={stage.stage} className="p-5">
              <p className="text-[11px] font-semibold uppercase tracking-wide text-brand-600">{stage.status}</p>
              <h3 className="mt-2 text-base font-semibold text-slate-900 leading-snug">{stage.stage}</h3>
              <ul className="mt-4 space-y-2">
                {stage.items.map((item) => (
                  <li key={item} className="text-sm text-slate-600 leading-relaxed flex gap-2">
                    <span className="mt-1.5 w-1.5 h-1.5 rounded-full bg-slate-400 shrink-0" />
                    <span>{item}</span>
                  </li>
                ))}
              </ul>
            </Card>
          ))}
        </div>

        <Card className="mt-8 p-6 bg-slate-50">
          <h3 className="text-lg font-semibold text-slate-900">What responsible progress would require</h3>
          <div className="mt-4 grid sm:grid-cols-2 lg:grid-cols-3 gap-3 text-sm text-slate-700">
            {[
              'Municipal cooperation and clearly defined workflows',
              'Data protection and privacy safeguards',
              'Responsible AI and transparent limitations',
              'Reliable infrastructure and operational support',
              'Local language support and accessibility',
              'Human oversight, governance, and accountability',
            ].map((item) => (
              <div key={item} className="rounded-lg bg-white border border-slate-200 px-3 py-2">{item}</div>
            ))}
          </div>
          <p className="mt-4 text-sm text-slate-500">
            StreetProof does not promise nationwide deployment and is not presented as production-ready for municipal use without further validation, governance, security review, and approved integrations.
          </p>
        </Card>
      </section>

      <section className="bg-slate-950 text-slate-100 border-y border-slate-800">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 py-16 sm:py-20">
          <div className="grid lg:grid-cols-[1fr_1fr] gap-10">
            <div>
              <SectionLabel>Technology and architecture</SectionLabel>
              <h2 className="text-3xl sm:text-4xl font-semibold tracking-tight text-white">Built with a practical, inspectable stack.</h2>
              <p className="mt-4 text-slate-300 leading-relaxed">
                The prototype uses a web frontend, Python API, relational data model, map rendering, and optional local semantic AI components. The stack below reflects technologies present in the repository.
              </p>
              <div className="mt-6 flex flex-wrap gap-2">
                {[
                  'React', 'Vite', 'TypeScript', 'Tailwind CSS', 'Python', 'FastAPI', 'SQLAlchemy', 'Alembic',
                  'PostgreSQL', 'Supabase', 'MapLibre GL JS', 'Sentence Transformers (local AI config)', 'Image hashing / pHash',
                ].map((tech) => (
                  <span key={tech} className="px-3 py-1.5 rounded-full bg-slate-900 border border-slate-700 text-sm text-slate-200">{tech}</span>
                ))}
              </div>
            </div>

            <div className="rounded-2xl border border-slate-800 bg-slate-900/60 p-6">
              <h3 className="text-lg font-semibold text-white mb-4">Compact architecture</h3>
              <div className="space-y-3 text-sm">
                <div className="rounded-xl border border-slate-700 bg-slate-950/60 p-4">
                  <div className="flex items-center gap-2 text-brand-300 font-medium"><Globe2 size={16} /> Frontend</div>
                  <p className="mt-1 text-slate-300">React + Vite + TypeScript + Tailwind + MapLibre. Citizen and admin interfaces.</p>
                </div>
                <div className="flex justify-center text-slate-500"><ArrowRight className="rotate-90" size={18} /></div>
                <div className="rounded-xl border border-slate-700 bg-slate-950/60 p-4">
                  <div className="flex items-center gap-2 text-brand-300 font-medium"><Database size={16} /> FastAPI backend</div>
                  <p className="mt-1 text-slate-300">REST API, auth/CSRF, report ingestion, matching jobs, merge/audit services.</p>
                </div>
                <div className="flex justify-center text-slate-500"><ArrowRight className="rotate-90" size={18} /></div>
                <div className="grid sm:grid-cols-2 gap-3">
                  <div className="rounded-xl border border-slate-700 bg-slate-950/60 p-4">
                    <div className="flex items-center gap-2 text-brand-300 font-medium"><Database size={16} /> Data</div>
                    <p className="mt-1 text-slate-300">SQLite dev / PostgreSQL Supabase + Alembic migrations.</p>
                  </div>
                  <div className="rounded-xl border border-slate-700 bg-slate-950/60 p-4">
                    <div className="flex items-center gap-2 text-brand-300 font-medium"><FileImage size={16} /> Storage</div>
                    <p className="mt-1 text-slate-300">Local uploads in dev or Supabase Storage in production config.</p>
                  </div>
                </div>
              </div>
            </div>
          </div>
        </div>
      </section>
      <section className="max-w-7xl mx-auto px-4 sm:px-6 py-16 sm:py-20">
        <div className="grid lg:grid-cols-[1fr_1fr] gap-10">
          <div>
            <SectionLabel>Responsible design</SectionLabel>
            <h2 className="text-3xl sm:text-4xl font-semibold tracking-tight text-slate-950">Civic technology needs caution as much as capability.</h2>
            <p className="mt-4 text-slate-600 leading-relaxed">
              StreetProof is designed around evidence preservation, conservative matching, and clear boundaries between reporting, review, and resolution.
            </p>
            <div className="mt-6 space-y-3">
              {[
                'Preserving original citizen submissions and evidence.',
                'Avoiding false duplicate merges by treating similarity as evidence, not certainty.',
                'Human review of uncertain matches and auditable administrative actions.',
                'Protecting administrative functions with authentication and CSRF controls.',
                'Avoiding exposure of sensitive personal information in public interfaces.',
                'Recognizing the difference between reporting an issue and resolving it.',
              ].map((item) => (
                <div key={item} className="flex gap-3 rounded-xl border border-slate-200 bg-white p-4">
                  <ShieldCheck size={18} className="text-brand-500 mt-0.5 shrink-0" />
                  <p className="text-sm text-slate-700 leading-relaxed">{item}</p>
                </div>
              ))}
            </div>
          </div>

          <div>
            <SectionLabel>References</SectionLabel>
            <Card className="p-6">
              <p className="text-sm text-slate-600 leading-relaxed mb-4">
                External platform descriptions above are based on official public sources. StreetProof is discussed as a complementary prototype concept and is not affiliated with these platforms.
              </p>
              <div className="space-y-3">
                {references.map((ref) => (
                  <a
                    key={ref.href}
                    href={ref.href}
                    target="_blank"
                    rel="noreferrer"
                    className="block rounded-lg border border-slate-200 hover:border-brand-300 hover:bg-slate-50 p-4 transition-colors"
                  >
                    <div className="flex items-center justify-between gap-3">
                      <span className="font-medium text-slate-900">{ref.label}</span>
                      <ExternalLinkIcon />
                    </div>
                    <p className="text-sm text-slate-500 mt-1">{ref.note}</p>
                    <p className="text-xs text-brand-600 mt-2 break-all">{ref.href}</p>
                  </a>
                ))}
              </div>
            </Card>
          </div>
        </div>
      </section>

      <section className="border-t border-slate-200 bg-[linear-gradient(180deg,#f7f9fc_0%,#eef4ff_100%)]">
        <div className="max-w-5xl mx-auto px-4 sm:px-6 py-16 sm:py-20 text-center">
          <SectionLabel>Take part</SectionLabel>
          <h2 className="text-3xl sm:text-4xl font-semibold tracking-tight text-slate-950">Better visibility starts with a report.</h2>
          <p className="mt-4 text-slate-600 leading-relaxed max-w-3xl mx-auto">
            Citizens can help document public infrastructure problems by submitting clear reports with photos and locations. Each report contributes evidence that can help communities and authorized organizations better understand where issues are being reported.
          </p>
          <div className="mt-8 flex flex-col sm:flex-row gap-3 justify-center">
            <Link
              to="/"
              className="inline-flex items-center justify-center gap-2 px-5 py-3 rounded-lg bg-brand-500 hover:bg-brand-400 text-white font-medium transition-colors"
            >
              Explore the Map
              <ArrowRight size={16} />
            </Link>
            <Link
              to="/report"
              className="inline-flex items-center justify-center gap-2 px-5 py-3 rounded-lg border border-slate-300 bg-white hover:bg-slate-50 text-slate-800 font-medium transition-colors"
            >
              Report an Issue
            </Link>
          </div>
          <p className="mt-4 text-xs text-slate-500">
            Submitting a report helps document an issue. It does not guarantee immediate government action or resolution.
          </p>
        </div>
      </section>
    </div>
  );
}

function ExternalLinkIcon() {
  return (
    <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" className="text-slate-400">
      <path d="M15 3h6v6" />
      <path d="M10 14 21 3" />
      <path d="M21 14v5a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h5" />
    </svg>
  );
}
