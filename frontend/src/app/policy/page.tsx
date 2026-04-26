import Link from "next/link";
import { api, type PolicyAggregate } from "@/lib/api";
import { COUNTRY_LANGS, isRtl, LANG_LABEL, t, type Lang } from "@/lib/i18n";

export const dynamic = "force-dynamic";

type SearchParams = { [key: string]: string | string[] | undefined };

const COUNTRY_FLAG: Record<string, string> = { PK: "🇵🇰", GH: "🇬🇭" };
const COUNTRY_NAME: Record<string, string> = { PK: "Pakistan", GH: "Ghana" };

export default async function PolicyPage({
  searchParams,
}: {
  searchParams: Promise<SearchParams>;
}) {
  const sp = await searchParams;
  const country = String(sp.country || "PK").toUpperCase();
  const requestedLang = sp.lang ? String(sp.lang).toLowerCase() : null;
  const langConfig = COUNTRY_LANGS[country] ?? COUNTRY_LANGS.PK;
  const lang: Lang =
    requestedLang && langConfig.available.includes(requestedLang as Lang)
      ? (requestedLang as Lang)
      : langConfig.default;
  const dir = isRtl(lang) ? "rtl" : "ltr";
  const other = country === "PK" ? "GH" : "PK";

  let agg: PolicyAggregate | null = null;
  let fetchError: string | null = null;
  try {
    agg = await api.policy(country);
  } catch {
    fetchError = t(lang, "common.error.generic");
  }

  return (
    <main
      dir={dir}
      lang={lang}
      className="flex-1 max-w-5xl mx-auto w-full px-4 sm:px-6 py-5 sm:py-8"
    >
      <header className="flex items-center justify-between mb-8 flex-wrap gap-3">
        <Link
          href="/"
          className="text-sm font-medium text-zinc-500 hover:text-zinc-900 inline-flex items-center gap-1"
        >
          ← UNMAPPED
        </Link>
        <div className="flex items-center gap-2 flex-wrap">
          {langConfig.available.length >= 2 && (
            <div className="flex items-center text-xs rounded-full border border-zinc-300 bg-white overflow-hidden shadow-sm">
              {langConfig.available.map((l) => (
                <Link
                  key={l}
                  href={`/policy?country=${country}&lang=${l}`}
                  className={`px-3 py-1.5 transition-colors ${
                    l === lang ? "bg-zinc-900 text-white" : "text-zinc-700 hover:bg-zinc-100"
                  }`}
                >
                  {LANG_LABEL[l]}
                </Link>
              ))}
            </div>
          )}
          <div className="text-xs text-zinc-600 flex items-center gap-1.5">
            <span className="rounded-full bg-zinc-100 border border-zinc-200 px-3 py-1.5 font-medium">
              {COUNTRY_FLAG[country]} {COUNTRY_NAME[country]}
            </span>
            <Link
              href={`/policy?country=${other}`}
              className="rounded-full border border-zinc-300 bg-white px-3 py-1.5 hover:border-blue-400 transition-colors"
            >
              → {COUNTRY_FLAG[other]} {COUNTRY_NAME[other]}
            </Link>
          </div>
        </div>
      </header>

      <div className="mb-8">
        <h1 className="text-3xl sm:text-4xl font-bold tracking-tight mb-2">
          {t(lang, "policy.title")}
        </h1>
        <p className="text-zinc-600 text-sm sm:text-base max-w-3xl leading-relaxed">
          {t(lang, "policy.sub")}
        </p>
      </div>

      {fetchError && (
        <div className="rounded-lg border border-red-200 bg-red-50 p-3.5 text-sm text-red-900">
          {fetchError}
        </div>
      )}

      {agg && (
        <>
          <div className="grid sm:grid-cols-3 gap-3 sm:gap-4 mb-6 sm:mb-8">
            <KPI
              label={t(lang, "policy.neet")}
              value={agg.neet_rate ? `${agg.neet_rate.value.toFixed(1)}%` : "—"}
              year={agg.neet_rate?.year}
              source="WDI · SL.UEM.NEET.ZS"
              accent="amber"
            />
            <KPI
              label={t(lang, "policy.informal")}
              value={
                agg.informal_employment_share
                  ? `${agg.informal_employment_share.value.toFixed(1)}%`
                  : "—"
              }
              year={agg.informal_employment_share?.year}
              source="WDI · SL.ISV.IFRM.ZS"
              accent="blue"
            />
            <KPI
              label={t(lang, "policy.broadband")}
              value={
                agg.fixed_broadband_per_100
                  ? agg.fixed_broadband_per_100.value.toFixed(1)
                  : "—"
              }
              year={agg.fixed_broadband_per_100?.year}
              source="WDI · IT.NET.BBND.P2"
              accent="emerald"
            />
          </div>

          <section className="rounded-2xl border border-zinc-200 bg-white p-5 sm:p-7 mb-6 shadow-sm">
            <div className="text-[10px] tracking-[0.18em] uppercase text-zinc-500 font-semibold mb-4">
              {t(lang, "policy.sectors")}
            </div>
            <div className="grid grid-cols-3 gap-4 sm:gap-6">
              <SectorBar
                label="Agriculture"
                value={agg.sector_employment.agriculture?.value}
                color="#15803d"
              />
              <SectorBar
                label="Industry"
                value={agg.sector_employment.industry?.value}
                color="#b45309"
              />
              <SectorBar
                label="Services"
                value={agg.sector_employment.services?.value}
                color="#1d4ed8"
              />
            </div>
          </section>

          <section className="rounded-2xl border border-zinc-200 bg-white p-5 sm:p-7 mb-6 shadow-sm">
            <div className="text-[10px] tracking-[0.18em] uppercase text-zinc-500 font-semibold mb-4">
              {t(lang, "policy.cohort")}
            </div>
            <CohortChart lang={lang} rows={agg.cohort_projection_2020_2035} />
          </section>

          {agg.skill_supply_divergence_note && (
            <section className="rounded-2xl border border-amber-200 bg-amber-50 p-5 sm:p-7">
              <div className="text-[10px] tracking-[0.18em] uppercase text-amber-900 font-semibold mb-2">
                {t(lang, "policy.divergence")}
              </div>
              <p className="text-sm text-amber-900 leading-relaxed">
                {agg.skill_supply_divergence_note}
              </p>
            </section>
          )}
        </>
      )}
    </main>
  );
}

function KPI({
  label,
  value,
  year,
  source,
  accent,
}: {
  label: string;
  value: string;
  year?: number;
  source: string;
  accent: "amber" | "blue" | "emerald";
}) {
  const tones: Record<string, string> = {
    amber: "from-amber-50",
    blue: "from-blue-50",
    emerald: "from-emerald-50",
  };
  return (
    <div
      className={`rounded-2xl border border-zinc-200 bg-gradient-to-br ${tones[accent]} to-white p-4 sm:p-5 shadow-sm`}
    >
      <div className="text-xs text-zinc-600 mb-1 font-medium">{label}</div>
      <div className="text-3xl sm:text-4xl font-bold tracking-tight">{value}</div>
      <div className="text-[11px] text-zinc-500 mt-2">
        {year ?? "—"} · <span className="font-mono">{source}</span>
      </div>
    </div>
  );
}

function SectorBar({
  label,
  value,
  color,
}: {
  label: string;
  value: number | undefined;
  color: string;
}) {
  return (
    <div>
      <div className="flex justify-between text-xs mb-2">
        <span className="font-medium">{label}</span>
        <span className="text-zinc-500 font-semibold">
          {value !== undefined ? `${value.toFixed(1)}%` : "—"}
        </span>
      </div>
      <div className="h-2.5 bg-zinc-100 rounded-full overflow-hidden">
        <div
          className="h-full rounded-full transition-all"
          style={{ width: `${value ?? 0}%`, backgroundColor: color }}
        />
      </div>
    </div>
  );
}

function CohortChart({
  lang,
  rows,
}: {
  lang: Lang;
  rows: { year: number; edu_level: string; share_pct: number }[];
}) {
  const years = Array.from(new Set(rows.map((r) => r.year))).sort();
  const levels = [
    "No Education",
    "Primary",
    "Lower Secondary",
    "Upper Secondary",
    "Post Secondary",
  ];
  const colors: Record<string, string> = {
    "No Education": "#dc2626",
    Primary: "#f59e0b",
    "Lower Secondary": "#fbbf24",
    "Upper Secondary": "#3b82f6",
    "Post Secondary": "#15803d",
  };
  const labelKey = (lvl: string) => `edu.${lvl.replace(/\s/g, "")}`;
  return (
    <div>
      <div className="space-y-1.5">
        {years.map((y) => (
          <div key={y} className="flex items-center gap-3 text-xs">
            <div className="w-12 text-zinc-500 font-medium">{y}</div>
            <div className="flex-1 flex h-6 rounded overflow-hidden ring-1 ring-zinc-100">
              {levels.map((lvl) => {
                const v = rows.find((r) => r.year === y && r.edu_level === lvl);
                if (!v) return null;
                return (
                  <div
                    key={lvl}
                    style={{ width: `${v.share_pct}%`, backgroundColor: colors[lvl] }}
                    title={`${t(lang, labelKey(lvl))}: ${v.share_pct}%`}
                    aria-label={`${t(lang, labelKey(lvl))}: ${v.share_pct}%`}
                  />
                );
              })}
            </div>
          </div>
        ))}
      </div>
      <div className="grid grid-cols-2 sm:flex sm:flex-wrap gap-x-4 gap-y-1.5 mt-4 text-[10px]">
        {levels.map((lvl) => (
          <span key={lvl} className="flex items-center gap-1.5">
            <span
              className="inline-block w-2.5 h-2.5 rounded-sm flex-shrink-0"
              style={{ backgroundColor: colors[lvl] }}
            />
            {t(lang, labelKey(lvl))}
          </span>
        ))}
      </div>
    </div>
  );
}
