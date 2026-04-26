import Link from "next/link";

export default function Home() {
  return (
    <main className="hero-bg flex-1 flex flex-col items-center px-6 py-16 sm:py-24">
      <div className="w-full max-w-3xl">
        <div className="text-center mb-12 sm:mb-16">
          <div className="inline-flex items-center gap-2 rounded-full bg-white/80 backdrop-blur-sm border border-zinc-200 text-[11px] font-medium px-3 py-1 mb-6 tracking-[0.18em] uppercase text-zinc-700 shadow-sm">
            <span className="inline-block w-1.5 h-1.5 rounded-full bg-blue-600" />
            Open Infrastructure · World Bank Challenge 05
          </div>
          <h1 className="text-5xl sm:text-7xl font-bold tracking-tight text-zinc-950 mb-5">
            UNMAPPED
          </h1>
          <p className="text-base sm:text-lg text-zinc-600 max-w-xl mx-auto leading-relaxed">
            Closing the distance between real skills and economic opportunity
            in the age of AI.
          </p>
        </div>

        <div className="grid sm:grid-cols-2 gap-3 sm:gap-4 max-w-2xl mx-auto">
          <Link
            href="/youth?country=PK"
            className="card-lift block rounded-xl border border-zinc-200 bg-white px-6 py-6 hover:border-blue-400 group"
          >
            <div className="flex items-start justify-between mb-3">
              <div className="text-[10px] font-semibold tracking-[0.18em] text-blue-700 uppercase">
                Youth
              </div>
              <span className="text-zinc-300 group-hover:text-blue-500 transition-colors text-lg leading-none">
                →
              </span>
            </div>
            <div className="text-lg font-semibold mb-1.5">Map my skills</div>
            <div className="text-sm text-zinc-600 leading-relaxed">
              Free-text profile → ESCO-grounded portable Skills Passport with
              QR + JSON-LD.
            </div>
          </Link>

          <Link
            href="/policy?country=PK"
            className="card-lift block rounded-xl border border-zinc-200 bg-white px-6 py-6 hover:border-blue-400 group"
          >
            <div className="flex items-start justify-between mb-3">
              <div className="text-[10px] font-semibold tracking-[0.18em] text-emerald-700 uppercase">
                Policymaker
              </div>
              <span className="text-zinc-300 group-hover:text-blue-500 transition-colors text-lg leading-none">
                →
              </span>
            </div>
            <div className="text-lg font-semibold mb-1.5">Aggregate dashboard</div>
            <div className="text-sm text-zinc-600 leading-relaxed">
              NEET, sector employment, cohort projections, skill-supply
              divergence diagnostics.
            </div>
          </Link>
        </div>

        <div className="mt-16 sm:mt-20 text-center">
          <div className="text-[10px] tracking-[0.18em] uppercase text-zinc-500 mb-3">
            Configured for
          </div>
          <div className="inline-flex flex-wrap justify-center gap-2 mb-3">
            <Link
              href="/youth?country=PK"
              className="rounded-full border border-zinc-300 bg-white px-3.5 py-1.5 text-sm hover:border-blue-400 transition-colors"
            >
              🇵🇰 Pakistan · Urdu
            </Link>
            <Link
              href="/youth?country=GH"
              className="rounded-full border border-zinc-300 bg-white px-3.5 py-1.5 text-sm hover:border-blue-400 transition-colors"
            >
              🇬🇭 Ghana · English
            </Link>
          </div>
          <div className="text-xs text-zinc-500 max-w-md mx-auto leading-relaxed">
            Country Pack swap = no code change. Same binary, different language,
            different LMIC calibration, different opportunity mix.
          </div>
        </div>

        <div className="mt-16 sm:mt-20 grid sm:grid-cols-3 gap-3 max-w-3xl mx-auto text-xs">
          <Stat value="1,490" label="ESCO skills" sub="live API crawl" />
          <Stat value="411" label="ESCO occupations" sub="grounded URIs" />
          <Stat value="2" label="Country Packs" sub="PK + GH (PR-able)" />
        </div>
      </div>
    </main>
  );
}

function Stat({ value, label, sub }: { value: string; label: string; sub: string }) {
  return (
    <div className="rounded-lg border border-zinc-200 bg-white/60 backdrop-blur-sm px-4 py-3">
      <div className="text-2xl font-semibold tracking-tight">{value}</div>
      <div className="text-[11px] text-zinc-700 font-medium mt-0.5">{label}</div>
      <div className="text-[10px] text-zinc-500 mt-0.5">{sub}</div>
    </div>
  );
}
