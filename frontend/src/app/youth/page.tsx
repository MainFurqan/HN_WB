"use client";

import { Suspense, useEffect, useMemo, useRef, useState } from "react";
import { useSearchParams, useRouter } from "next/navigation";
import {
  api,
  type SkillCandidate,
  type SkillCategory,
  type Readiness,
  type Opportunity,
  type Passport,
  type CvProfile,
} from "@/lib/api";
import { COUNTRY_LANGS, LANG_LABEL, isRtl, t, type Lang } from "@/lib/i18n";
import { KEY, load, save } from "@/lib/storage";

type Step = "input" | "confirm" | "result";

type Profile = {
  about: string;
  education: string;
  work: string;
  selfTaught: string;
  tools: string;
  aspirations: string;
};

const EMPTY_PROFILE: Profile = {
  about: "",
  education: "",
  work: "",
  selfTaught: "",
  tools: "",
  aspirations: "",
};

const COUNTRY_FLAG: Record<string, string> = { PK: "🇵🇰", GH: "🇬🇭" };
const COUNTRY_NAME: Record<string, string> = { PK: "Pakistan", GH: "Ghana" };

const CATEGORY_META: Record<
  SkillCategory,
  { label: Record<Lang, string>; tone: string; ring: string }
> = {
  hard: {
    label: { en: "Hard skills", ur: "تکنیکی مہارتیں", tw: "Adwuma nimdeɛ" },
    tone: "bg-blue-50 text-blue-800 border-blue-200",
    ring: "border-blue-200",
  },
  soft: {
    label: { en: "Soft skills", ur: "ساخت مہارتیں", tw: "Nipa nimdeɛ" },
    tone: "bg-emerald-50 text-emerald-800 border-emerald-200",
    ring: "border-emerald-200",
  },
  knowledge: {
    label: { en: "Knowledge areas", ur: "علم کے شعبے", tw: "Nimdeɛ horow" },
    tone: "bg-violet-50 text-violet-800 border-violet-200",
    ring: "border-violet-200",
  },
};

function profileToText(p: Profile, lang: Lang): string {
  const parts: string[] = [];
  if (p.about.trim()) parts.push(`ABOUT: ${p.about.trim()}`);
  if (p.education.trim()) parts.push(`EDUCATION: ${p.education.trim()}`);
  if (p.work.trim()) parts.push(`WORK / EXPERIENCE: ${p.work.trim()}`);
  if (p.selfTaught.trim()) parts.push(`SELF-TAUGHT: ${p.selfTaught.trim()}`);
  if (p.tools.trim()) parts.push(`TOOLS / TECH: ${p.tools.trim()}`);
  if (p.aspirations.trim()) parts.push(`ASPIRATIONS: ${p.aspirations.trim()}`);
  parts.push(`PROFILE LANGUAGE: ${lang}`);
  return parts.join("\n\n");
}

function profileLength(p: Profile): number {
  return Object.values(p).reduce((a, s) => a + s.trim().length, 0);
}

function nameFromAbout(about: string): string {
  // Simple heuristic: first capitalised word sequence after "I am" or first 1-2 caps words.
  const m = about.match(/I am\s+([A-Z][a-zA-Z]+(?:\s+[A-Z][a-zA-Z]+)?)/);
  if (m) return m[1];
  const m2 = about.match(/\b([A-Z][a-zA-Z]+(?:\s+[A-Z][a-zA-Z]+)?)\b/);
  if (m2) return m2[1];
  return "";
}

export default function YouthPage() {
  return (
    <Suspense fallback={<YouthSkeleton />}>
      <YouthInner />
    </Suspense>
  );
}

function YouthSkeleton() {
  return (
    <main className="flex-1 max-w-4xl mx-auto w-full px-4 sm:px-6 py-5 sm:py-8">
      <div className="skeleton h-8 w-40 rounded mb-8" />
      <div className="skeleton h-12 w-full rounded mb-3" />
      <div className="skeleton h-32 w-full rounded mb-3" />
      <div className="skeleton h-32 w-full rounded mb-3" />
      <div className="skeleton h-32 w-full rounded" />
    </main>
  );
}

function YouthInner() {
  const params = useSearchParams();
  const router = useRouter();
  const country = (params.get("country") || "PK").toUpperCase();
  const otherCountry = country === "PK" ? "GH" : "PK";
  const langConfig = COUNTRY_LANGS[country] ?? COUNTRY_LANGS.PK;

  const [hydrated, setHydrated] = useState(false);
  const [lang, setLang] = useState<Lang>("en");
  const [profile, setProfile] = useState<Profile>(EMPTY_PROFILE);
  const [name, setName] = useState("");

  useEffect(() => {
    const storedLang = (load(KEY.lang) as Lang) || langConfig.default;
    const useLang = langConfig.available.includes(storedLang)
      ? storedLang
      : langConfig.default;
    setLang(useLang);
    const stored = load(KEY.profile);
    if (stored) {
      try {
        setProfile({ ...EMPTY_PROFILE, ...JSON.parse(stored) });
      } catch {
        setProfile(EMPTY_PROFILE);
      }
    }
    setName(load(KEY.name) || "");
    setHydrated(true);
  }, [country, langConfig]);

  useEffect(() => {
    if (hydrated) save(KEY.profile, JSON.stringify(profile));
  }, [profile, hydrated]);
  useEffect(() => {
    if (hydrated) save(KEY.lang, lang);
  }, [lang, hydrated]);
  useEffect(() => {
    if (hydrated) save(KEY.name, name);
  }, [name, hydrated]);

  const [step, setStep] = useState<Step>("input");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [candidates, setCandidates] = useState<SkillCandidate[]>([]);
  const [iscoHint, setIscoHint] = useState<string | null>(null);
  const [confirmed, setConfirmed] = useState<Set<string>>(new Set());
  const [passport, setPassport] = useState<Passport | null>(null);
  const [readiness, setReadiness] = useState<Readiness | null>(null);
  const [opps, setOpps] = useState<Opportunity[] | null>(null);

  const isReady = profileLength(profile) >= 60;

  async function runExtract() {
    setLoading(true);
    setError(null);
    try {
      const text = profileToText(profile, lang);
      const r = await api.extract(text, country, lang);
      setCandidates(r.candidates);
      setIscoHint(r.isco_hint);
      setConfirmed(new Set()); // user owns the passport — start unchecked
      // Auto-derive a name from "About you" if user didn't type one.
      if (!name) {
        const guess = nameFromAbout(profile.about);
        if (guess) setName(guess);
      }
      setStep("confirm");
    } catch {
      setError(t(lang, "common.error.llm"));
    } finally {
      setLoading(false);
    }
  }

  async function runFinalize() {
    setLoading(true);
    setError(null);
    const uris = Array.from(confirmed);
    try {
      const [p, r, o] = await Promise.all([
        api.passport({
          confirmed_skill_uris: uris,
          holder_name: name || "Anonymous",
          country,
          isco_cluster: iscoHint,
        }),
        api.readiness(uris, iscoHint, country),
        api.match(uris, iscoHint, country),
      ]);
      setPassport(p);
      setReadiness(r);
      setOpps(o);
      setStep("result");
    } catch {
      setError(t(lang, "common.error.generic"));
    } finally {
      setLoading(false);
    }
  }

  const dir = isRtl(lang) ? "rtl" : "ltr";

  return (
    <main
      dir={dir}
      lang={lang}
      className="flex-1 max-w-4xl mx-auto w-full px-4 sm:px-6 py-5 sm:py-8"
    >
      <PageHeader
        lang={lang}
        country={country}
        otherCountry={otherCountry}
        onLang={setLang}
        availableLangs={langConfig.available}
        onBack={() => router.push("/")}
      />

      {error && <ErrorBanner lang={lang} error={error} onRetry={step === "input" ? runExtract : runFinalize} />}

      {step === "input" && (
        <InputStep
          lang={lang}
          name={name}
          setName={setName}
          profile={profile}
          setProfile={setProfile}
          loading={loading}
          ready={isReady}
          onSubmit={runExtract}
        />
      )}

      {step === "confirm" && (
        <ConfirmStep
          lang={lang}
          candidates={candidates}
          iscoHint={iscoHint}
          confirmed={confirmed}
          setConfirmed={setConfirmed}
          loading={loading}
          onSubmit={runFinalize}
          onBack={() => setStep("input")}
        />
      )}

      {step === "result" && passport && readiness && opps && (
        <ResultStep
          lang={lang}
          name={name || "Anonymous"}
          country={country}
          passport={passport}
          readiness={readiness}
          opps={opps}
          onEdit={() => setStep("input")}
        />
      )}
    </main>
  );
}

function PageHeader({
  lang,
  country,
  otherCountry,
  onLang,
  availableLangs,
  onBack,
}: {
  lang: Lang;
  country: string;
  otherCountry: string;
  onLang: (l: Lang) => void;
  availableLangs: Lang[];
  onBack: () => void;
}) {
  return (
    <header className="flex items-center justify-between gap-3 mb-8 flex-wrap">
      <button
        onClick={onBack}
        className="text-sm font-medium text-zinc-500 hover:text-zinc-900 inline-flex items-center gap-1"
      >
        <span>←</span> UNMAPPED
      </button>
      <div className="flex items-center gap-2 flex-wrap">
        {availableLangs.length >= 2 && (
          <div className="flex items-center text-xs rounded-full border border-zinc-300 bg-white overflow-hidden shadow-sm">
            {availableLangs.map((l) => (
              <button
                key={l}
                onClick={() => onLang(l)}
                className={`px-3 py-1.5 transition-colors ${
                  l === lang ? "bg-zinc-900 text-white" : "text-zinc-700 hover:bg-zinc-100"
                }`}
              >
                {LANG_LABEL[l]}
              </button>
            ))}
          </div>
        )}
        <div className="text-xs text-zinc-600 flex items-center gap-1.5">
          <span className="rounded-full bg-zinc-100 border border-zinc-200 px-3 py-1.5 font-medium">
            {COUNTRY_FLAG[country]} {COUNTRY_NAME[country]}
          </span>
          <a
            href={`/youth?country=${otherCountry}`}
            className="rounded-full border border-zinc-300 bg-white px-3 py-1.5 hover:border-blue-400 transition-colors"
            title="Country Pack swap = no code change"
          >
            → {COUNTRY_FLAG[otherCountry]} {COUNTRY_NAME[otherCountry]}
          </a>
        </div>
      </div>
    </header>
  );
}

function ErrorBanner({
  lang,
  error,
  onRetry,
}: {
  lang: Lang;
  error: string;
  onRetry: () => void;
}) {
  return (
    <div className="mb-5 rounded-lg border border-red-200 bg-red-50 p-3.5 text-sm text-red-900 flex items-center justify-between gap-3">
      <span>{error}</span>
      <button
        onClick={onRetry}
        className="text-xs rounded-md bg-red-700 hover:bg-red-800 text-white px-3 py-1.5 font-medium"
      >
        {t(lang, "common.retry")}
      </button>
    </div>
  );
}

function InputStep(props: {
  lang: Lang;
  name: string;
  setName: (s: string) => void;
  profile: Profile;
  setProfile: (p: Profile) => void;
  loading: boolean;
  ready: boolean;
  onSubmit: () => void;
}) {
  const { lang, profile, setProfile } = props;
  const update = (k: keyof Profile) => (v: string) =>
    setProfile({ ...profile, [k]: v });
  const totalChars = profileLength(profile);

  return (
    <div>
      <div className="mb-6">
        <h1 className="text-3xl sm:text-4xl font-bold tracking-tight mb-2">
          {t(lang, "youth.title")}
        </h1>
        <p className="text-zinc-600 text-sm sm:text-base max-w-2xl leading-relaxed">
          {t(lang, "youth.help")}
        </p>
      </div>

      <CvUpload lang={lang} setProfile={setProfile} />

      <div className="flex items-center gap-3 my-5 text-xs text-zinc-400">
        <span className="h-px bg-zinc-200 flex-1" />
        <span className="uppercase tracking-[0.18em]">{t(lang, "youth.cv.or")}</span>
        <span className="h-px bg-zinc-200 flex-1" />
      </div>

      <div className="space-y-3">
        <Section
          icon="👤"
          title={t(lang, "youth.section.about")}
          help={t(lang, "youth.section.about.help")}
          placeholder={t(lang, "youth.section.about.ph")}
          value={profile.about}
          onChange={update("about")}
          rows={3}
        />
        <Section
          icon="🎓"
          title={t(lang, "youth.section.education")}
          help={t(lang, "youth.section.education.help")}
          placeholder={t(lang, "youth.section.education.ph")}
          value={profile.education}
          onChange={update("education")}
          rows={3}
        />
        <Section
          icon="💼"
          title={t(lang, "youth.section.work")}
          help={t(lang, "youth.section.work.help")}
          placeholder={t(lang, "youth.section.work.ph")}
          value={profile.work}
          onChange={update("work")}
          rows={4}
        />
        <Section
          icon="📚"
          title={t(lang, "youth.section.selftaught")}
          help={t(lang, "youth.section.selftaught.help")}
          placeholder={t(lang, "youth.section.selftaught.ph")}
          value={profile.selfTaught}
          onChange={update("selfTaught")}
          rows={3}
        />
        <Section
          icon="🛠️"
          title={t(lang, "youth.section.tools")}
          help={t(lang, "youth.section.tools.help")}
          placeholder={t(lang, "youth.section.tools.ph")}
          value={profile.tools}
          onChange={update("tools")}
          rows={2}
        />
        <Section
          icon="🎯"
          title={t(lang, "youth.section.aspirations")}
          help={t(lang, "youth.section.aspirations.help")}
          placeholder={t(lang, "youth.section.aspirations.ph")}
          value={profile.aspirations}
          onChange={update("aspirations")}
          rows={2}
          optional
        />
      </div>

      <div className="mt-8 flex items-center justify-between gap-4 sticky bottom-3 bg-white/80 backdrop-blur-md border border-zinc-200 rounded-xl p-3 shadow-sm">
        <div className="text-xs text-zinc-500 hidden sm:block">
          {totalChars} / 4000 chars · min 60 to continue
        </div>
        <button
          disabled={props.loading || !props.ready}
          onClick={props.onSubmit}
          className="btn btn-primary flex-1 sm:flex-initial sm:px-6"
        >
          {props.loading ? (
            <>
              <Spinner /> {t(lang, "youth.mapping")}
            </>
          ) : (
            <>{t(lang, "youth.find")} →</>
          )}
        </button>
      </div>

      {props.loading && <SkillsSkeleton />}
    </div>
  );
}

function CvUpload({
  lang,
  setProfile,
}: {
  lang: Lang;
  setProfile: (p: Profile) => void;
}) {
  const [state, setState] = useState<"idle" | "parsing" | "success" | "error">("idle");
  const [errorMsg, setErrorMsg] = useState<string | null>(null);
  const [filename, setFilename] = useState<string | null>(null);
  const inputRef = useRef<HTMLInputElement | null>(null);

  async function handleFile(file: File) {
    setState("parsing");
    setErrorMsg(null);
    setFilename(file.name);
    try {
      const parsed: CvProfile = await api.parseCv(file);
      setProfile({
        about: parsed.about || "",
        education: parsed.education || "",
        work: parsed.work || "",
        selfTaught: parsed.selfTaught || "",
        tools: parsed.tools || "",
        aspirations: parsed.aspirations || "",
      });
      setState("success");
    } catch (e) {
      setState("error");
      setErrorMsg(t(lang, "youth.cv.error"));
      console.error(e);
    }
  }

  function onChange(e: React.ChangeEvent<HTMLInputElement>) {
    const f = e.target.files?.[0];
    if (f) void handleFile(f);
  }

  function onDrop(e: React.DragEvent<HTMLLabelElement>) {
    e.preventDefault();
    const f = e.dataTransfer.files?.[0];
    if (f) void handleFile(f);
  }

  return (
    <div className="rounded-2xl border border-blue-200 bg-gradient-to-br from-blue-50 via-white to-white p-5 sm:p-6 shadow-sm">
      <div className="flex items-start justify-between gap-4 flex-wrap">
        <div className="flex-1 min-w-0">
          <div className="flex items-center gap-2 mb-1">
            <span className="text-2xl" aria-hidden>
              📄
            </span>
            <div className="font-semibold text-base">{t(lang, "youth.cv.title")}</div>
          </div>
          <p className="text-xs text-zinc-600 leading-relaxed max-w-md">
            {t(lang, "youth.cv.help")}
          </p>
          {state === "success" && filename && (
            <div className="mt-2 text-xs text-emerald-700 font-medium flex items-center gap-1.5">
              <span>✓</span>
              <span className="truncate">{filename}</span>
              <span className="text-emerald-600">— {t(lang, "youth.cv.success")}</span>
            </div>
          )}
          {state === "error" && (
            <div className="mt-2 text-xs text-red-700 font-medium">
              {errorMsg ?? t(lang, "youth.cv.error")}
            </div>
          )}
        </div>
        <label
          onDragOver={(e) => e.preventDefault()}
          onDrop={onDrop}
          className="cursor-pointer btn btn-primary whitespace-nowrap relative"
        >
          {state === "parsing" ? (
            <>
              <Spinner /> {t(lang, "youth.cv.parsing")}
            </>
          ) : (
            <>📎 {t(lang, "youth.cv.button")}</>
          )}
          <input
            ref={inputRef}
            type="file"
            accept=".pdf,.docx,.txt,.md"
            className="sr-only"
            onChange={onChange}
            disabled={state === "parsing"}
          />
        </label>
      </div>
    </div>
  );
}

function Section({
  icon,
  title,
  help,
  placeholder,
  value,
  onChange,
  rows = 3,
  optional = false,
}: {
  icon: string;
  title: string;
  help: string;
  placeholder: string;
  value: string;
  onChange: (s: string) => void;
  rows?: number;
  optional?: boolean;
}) {
  return (
    <div className="rounded-xl border border-zinc-200 bg-white p-4 sm:p-5 hover:border-zinc-300 transition-colors">
      <div className="flex items-center gap-2 mb-1">
        <span className="text-lg" aria-hidden>
          {icon}
        </span>
        <div className="font-semibold text-sm">{title}</div>
        {optional && (
          <span className="text-[10px] tracking-wider uppercase text-zinc-400 font-medium">
            optional
          </span>
        )}
      </div>
      <p className="text-xs text-zinc-500 mb-3 leading-relaxed">{help}</p>
      <textarea
        value={value}
        onChange={(e) => onChange(e.target.value)}
        rows={rows}
        placeholder={placeholder}
        maxLength={1500}
        className="w-full rounded-lg border border-zinc-200 bg-zinc-50 px-3 py-2 text-sm focus:bg-white focus:border-blue-400 transition-colors resize-none"
      />
    </div>
  );
}

function Spinner() {
  return (
    <svg
      className="animate-spin h-4 w-4"
      viewBox="0 0 24 24"
      fill="none"
      stroke="currentColor"
      strokeWidth="2.5"
    >
      <circle cx="12" cy="12" r="9" opacity="0.25" />
      <path d="M21 12a9 9 0 0 0-9-9" />
    </svg>
  );
}

function SkillsSkeleton() {
  return (
    <div className="mt-6 space-y-2">
      {[0, 1, 2, 3].map((i) => (
        <div key={i} className="rounded-lg border border-zinc-200 p-3">
          <div className="skeleton h-4 w-1/3 rounded mb-2" />
          <div className="skeleton h-3 w-2/3 rounded" />
        </div>
      ))}
    </div>
  );
}

function ConfirmStep(props: {
  lang: Lang;
  candidates: SkillCandidate[];
  iscoHint: string | null;
  confirmed: Set<string>;
  setConfirmed: (s: Set<string>) => void;
  loading: boolean;
  onSubmit: () => void;
  onBack: () => void;
}) {
  const { lang, candidates } = props;
  const [showAll, setShowAll] = useState<Record<SkillCategory, boolean>>({
    hard: false,
    soft: false,
    knowledge: false,
  });

  const grouped = useMemo(() => {
    const g: Record<SkillCategory, SkillCandidate[]> = {
      hard: [],
      soft: [],
      knowledge: [],
    };
    for (const c of candidates) {
      const cat = (c.category in g ? c.category : "hard") as SkillCategory;
      g[cat].push(c);
    }
    return g;
  }, [candidates]);

  function toggle(uri: string) {
    const n = new Set(props.confirmed);
    if (n.has(uri)) n.delete(uri);
    else n.add(uri);
    props.setConfirmed(n);
  }

  function selectAll() {
    props.setConfirmed(new Set(candidates.map((c) => c.esco_uri)));
  }
  function clearAll() {
    props.setConfirmed(new Set());
  }

  const order: SkillCategory[] = ["hard", "knowledge", "soft"];

  return (
    <div>
      <div className="mb-5">
        <h1 className="text-3xl sm:text-4xl font-bold tracking-tight mb-1">
          {t(lang, "youth.confirm.title")}
        </h1>
        <p className="text-zinc-600 text-sm sm:text-base max-w-2xl leading-relaxed">
          {t(lang, "youth.confirm.help")} ({candidates.length})
        </p>
        {props.iscoHint && (
          <p className="text-xs text-zinc-500 mt-2">
            {t(lang, "youth.confirm.isco")}{" "}
            <code className="bg-zinc-100 px-1.5 py-0.5 rounded font-mono">
              {props.iscoHint}
            </code>
          </p>
        )}
      </div>

      <div className="flex items-center gap-2 mb-5 text-xs">
        <button
          onClick={selectAll}
          className="rounded-full border border-zinc-300 bg-white px-3 py-1 hover:border-blue-400"
        >
          Select all
        </button>
        <button
          onClick={clearAll}
          className="rounded-full border border-zinc-300 bg-white px-3 py-1 hover:border-blue-400"
        >
          Clear
        </button>
        <span className="text-zinc-500 ms-auto">
          {props.confirmed.size} / {candidates.length} selected
        </span>
      </div>

      <div className="space-y-6 mb-8">
        {order.map((cat) => {
          const list = grouped[cat];
          if (list.length === 0) return null;
          const visible = showAll[cat] ? list : list.slice(0, 6);
          const meta = CATEGORY_META[cat];
          return (
            <section key={cat}>
              <div className="flex items-center justify-between mb-3">
                <div className={`text-[11px] tracking-[0.18em] uppercase font-semibold ${meta.tone.split(" ")[1]}`}>
                  {meta.label[lang] ?? meta.label.en}
                  <span className="text-zinc-400 font-normal ms-2">{list.length}</span>
                </div>
                {list.length > 6 && (
                  <button
                    onClick={() =>
                      setShowAll({ ...showAll, [cat]: !showAll[cat] })
                    }
                    className="text-xs text-blue-700 hover:text-blue-900 font-medium"
                  >
                    {showAll[cat] ? "Show less" : `Show ${list.length - 6} more →`}
                  </button>
                )}
              </div>
              <div className="space-y-2">
                {visible.map((c) => (
                  <SkillCard
                    key={c.esco_uri}
                    candidate={c}
                    checked={props.confirmed.has(c.esco_uri)}
                    onToggle={() => toggle(c.esco_uri)}
                    meta={meta}
                  />
                ))}
              </div>
            </section>
          );
        })}
      </div>

      <div className="flex items-center justify-between gap-3 sticky bottom-3 bg-white/80 backdrop-blur-md border border-zinc-200 rounded-xl p-3 shadow-sm">
        <button onClick={props.onBack} className="btn btn-ghost">
          ← {t(lang, "youth.back")}
        </button>
        <button
          disabled={props.loading || props.confirmed.size === 0}
          onClick={props.onSubmit}
          className="btn btn-primary flex-1 sm:flex-initial sm:px-6"
        >
          {props.loading ? (
            <>
              <Spinner /> {t(lang, "youth.confirm.building")}
            </>
          ) : (
            <>
              {t(lang, "youth.confirm.cta")} →
            </>
          )}
        </button>
      </div>
    </div>
  );
}

function SkillCard({
  candidate,
  checked,
  onToggle,
  meta,
}: {
  candidate: SkillCandidate;
  checked: boolean;
  onToggle: () => void;
  meta: { tone: string; ring: string };
}) {
  return (
    <label
      className={`flex items-start gap-3 p-3.5 rounded-lg border bg-white cursor-pointer transition-colors hover:border-zinc-300 ${
        checked ? "border-blue-400 ring-1 ring-blue-200" : "border-zinc-200"
      }`}
    >
      <input
        type="checkbox"
        className="mt-0.5 w-4 h-4 accent-blue-700"
        checked={checked}
        onChange={onToggle}
      />
      <div className="flex-1 min-w-0">
        <div className="flex items-center gap-2 flex-wrap">
          <span className="font-medium text-sm">{candidate.label}</span>
          <span className={`text-[10px] uppercase tracking-wider px-1.5 py-0.5 rounded border font-medium ${meta.tone}`}>
            {candidate.category}
          </span>
        </div>
        {candidate.evidence_quote && (
          <div className="text-xs text-zinc-500 mt-1 italic break-words">
            “{candidate.evidence_quote}”
          </div>
        )}
        <div className="text-[10px] text-zinc-400 mt-1.5 font-mono break-all">
          {candidate.esco_uri}
        </div>
      </div>
      <div className="text-xs text-zinc-600 whitespace-nowrap font-medium">
        {Math.round(candidate.confidence * 100)}%
      </div>
    </label>
  );
}

function ResultStep(props: {
  lang: Lang;
  name: string;
  country: string;
  passport: Passport;
  readiness: Readiness;
  opps: Opportunity[];
  onEdit: () => void;
}) {
  const { lang } = props;
  const r = props.readiness;
  const riskPct = Math.round(r.automation_risk * 100);
  const baseRiskPct = Math.round(r.automation_risk_uncalibrated * 100);

  return (
    <div className="space-y-6 sm:space-y-8">
      {/* Skills Passport */}
      <section className="rounded-2xl border border-zinc-200 bg-white p-5 sm:p-7 shadow-sm">
        <div className="flex items-start justify-between gap-4 mb-4 flex-wrap">
          <div>
            <div className="text-[11px] tracking-[0.18em] uppercase text-zinc-500 mb-1 font-semibold">
              {t(lang, "youth.passport")}
            </div>
            <h2 className="text-2xl sm:text-3xl font-bold tracking-tight">
              {props.name}
            </h2>
            <div className="text-sm text-zinc-600 mt-1">
              {COUNTRY_FLAG[props.country]} {COUNTRY_NAME[props.country]} · JSON-LD · ESCO-grounded
            </div>
          </div>
          {props.passport.qr_png_b64 && (
            <img
              src={`data:image/png;base64,${props.passport.qr_png_b64}`}
              alt="Skills Passport QR code"
              loading="lazy"
              className="w-20 h-20 sm:w-24 sm:h-24 rounded border border-zinc-200"
            />
          )}
        </div>
        <div className="flex flex-wrap gap-2 text-xs mt-4">
          <button onClick={props.onEdit} className="btn btn-ghost text-xs py-1.5 px-3">
            ← Edit profile
          </button>
        </div>
        <details className="text-xs mt-4 group">
          <summary className="cursor-pointer text-zinc-500 hover:text-zinc-900 select-none">
            <span className="group-open:hidden">▸</span>
            <span className="hidden group-open:inline">▾</span>{" "}
            {t(lang, "youth.passport.viewjson")}
          </summary>
          <pre className="mt-3 max-h-80 overflow-auto bg-zinc-50 border border-zinc-200 rounded-lg p-3 text-[11px] font-mono leading-relaxed">
            {JSON.stringify(props.passport.jsonld, null, 2)}
          </pre>
        </details>
      </section>

      {/* AI Readiness Lens */}
      <section className="rounded-2xl border border-zinc-200 bg-white p-5 sm:p-7 shadow-sm">
        <div className="flex items-baseline justify-between mb-1 flex-wrap gap-2">
          <h2 className="text-2xl sm:text-3xl font-bold tracking-tight">
            {t(lang, "youth.readiness")}
          </h2>
          <div className="text-[10px] tracking-[0.18em] uppercase text-zinc-500 font-semibold">
            Frey-Osborne · LMIC-calibrated
          </div>
        </div>
        <p className="text-xs text-zinc-500 mb-5 leading-relaxed">
          {r.calibration_notes}
        </p>

        <div className="grid sm:grid-cols-2 gap-3 sm:gap-4 mb-5">
          <div className="rounded-xl border border-zinc-200 p-4 sm:p-5 bg-gradient-to-br from-blue-50 to-white">
            <div className="text-[10px] tracking-[0.18em] uppercase text-blue-800 font-semibold mb-1">
              {t(lang, "youth.risk.calibrated")}
            </div>
            <div className="text-4xl sm:text-5xl font-bold text-blue-900 tracking-tight">
              {riskPct}%
            </div>
            <div className="text-xs text-zinc-500 mt-1.5">
              {t(lang, "youth.risk.base")}: {baseRiskPct}%
            </div>
          </div>
          <div className="rounded-xl border border-zinc-200 p-4 sm:p-5">
            <div className="text-[10px] tracking-[0.18em] uppercase text-zinc-500 font-semibold mb-2">
              {t(lang, "youth.skills.breakdown")}
            </div>
            <div className="space-y-1 text-sm">
              <div className="flex items-center justify-between">
                <span className="text-emerald-700">● {t(lang, "youth.skills.durable")}</span>
                <span className="font-semibold">{r.durable_skills.length}</span>
              </div>
              <div className="flex items-center justify-between">
                <span className="text-amber-700">● {t(lang, "youth.skills.atrisk")}</span>
                <span className="font-semibold">{r.at_risk_skills.length}</span>
              </div>
              <div className="flex items-center justify-between">
                <span className="text-zinc-600">● {t(lang, "youth.skills.mixed")}</span>
                <span className="font-semibold">{r.mixed_skills.length}</span>
              </div>
            </div>
          </div>
        </div>

        {r.adjacent_skills.length > 0 && (
          <div className="mb-5">
            <div className="text-[10px] tracking-[0.18em] uppercase text-zinc-500 font-semibold mb-2">
              {t(lang, "youth.adjacent")}
            </div>
            <div className="flex flex-wrap gap-1.5">
              {r.adjacent_skills.slice(0, 8).map((a) => (
                <span
                  key={a.conceptUri}
                  className="text-xs bg-blue-50 text-blue-800 border border-blue-100 px-2.5 py-1 rounded-full"
                  title={a.description}
                >
                  {a.preferredLabel}
                </span>
              ))}
            </div>
          </div>
        )}

        {r.cohort_projection.length > 0 && (
          <CohortChart lang={lang} rows={r.cohort_projection} />
        )}

        {r.limits.length > 0 && (
          <div className="mt-6 rounded-xl border border-amber-200 bg-amber-50 p-4 sm:p-5">
            <div className="text-[10px] tracking-[0.18em] uppercase text-amber-900 font-semibold mb-2">
              {t(lang, "youth.limits")}
            </div>
            <ul className="list-disc list-inside text-xs text-amber-900 space-y-1 leading-relaxed">
              {r.limits.map((l, i) => (
                <li key={i}>{l}</li>
              ))}
            </ul>
          </div>
        )}
      </section>

      {/* Opportunities */}
      <section className="rounded-2xl border border-zinc-200 bg-white p-5 sm:p-7 shadow-sm">
        <div className="flex items-baseline justify-between mb-5 flex-wrap gap-2">
          <h2 className="text-2xl sm:text-3xl font-bold tracking-tight">
            {t(lang, "youth.opps.title")}
          </h2>
          <div className="text-[10px] tracking-[0.18em] uppercase text-zinc-500 font-semibold">
            ILOSTAT · WDI · ISCO-08
          </div>
        </div>
        <div className="space-y-3">
          {props.opps.length === 0 && (
            <div className="text-sm text-zinc-500 italic">
              No opportunity matches yet — add more detail to your profile and try again.
            </div>
          )}
          {props.opps.map((o) => (
            <OpportunityCard key={o.esco_uri} lang={lang} o={o} />
          ))}
        </div>
      </section>
    </div>
  );
}

function OpportunityCard({ lang, o }: { lang: Lang; o: Opportunity }) {
  const wage =
    o.wage_low && o.wage_high && o.wage_currency
      ? `${o.wage_currency} ${Math.round(o.wage_low).toLocaleString()}–${Math.round(o.wage_high).toLocaleString()}/mo`
      : "—";
  const wageMid = o.wage_p50 && o.wage_currency
    ? `median ${o.wage_currency} ${Math.round(o.wage_p50).toLocaleString()}`
    : null;
  const growth =
    o.sector_growth_pct !== null
      ? `${o.sector_growth_pct >= 0 ? "+" : ""}${o.sector_growth_pct.toFixed(1)}%`
      : "—";
  return (
    <div className="rounded-xl border border-zinc-200 p-4 hover:border-zinc-300 transition-colors">
      <div className="flex items-start justify-between gap-3 mb-3 flex-wrap">
        <div className="min-w-0">
          <div className="font-semibold break-words">{o.title}</div>
          <div className="text-xs text-zinc-500 mt-0.5">
            {o.type.replace("_", " ")}
            {o.isco_code ? ` · ISCO ${o.isco_code}` : ""}
          </div>
        </div>
        <div className="text-xs text-zinc-600 whitespace-nowrap font-medium">
          {t(lang, "youth.opps.match")} {Math.round(o.match_score * 100)}%
        </div>
      </div>
      <div className="grid sm:grid-cols-2 gap-2 sm:gap-3 mt-2 text-sm">
        <div className="rounded-lg bg-blue-50 border border-blue-100 p-2.5">
          <div className="text-[10px] tracking-[0.12em] uppercase text-blue-800 font-semibold mb-0.5">
            {t(lang, "youth.opps.wage")}
          </div>
          <div className="font-semibold text-blue-900">{wage}</div>
          {wageMid && <div className="text-[11px] text-blue-700">{wageMid}</div>}
          {o.wage_basis && (
            <div className="text-[10px] text-blue-600 mt-0.5">{o.wage_basis}</div>
          )}
        </div>
        <div className="rounded-lg bg-emerald-50 border border-emerald-100 p-2.5">
          <div className="text-[10px] tracking-[0.12em] uppercase text-emerald-800 font-semibold mb-0.5">
            {t(lang, "youth.opps.growth")}
          </div>
          <div className="font-semibold text-emerald-900">{growth}</div>
          {o.sector_label && (
            <div className="text-[11px] text-emerald-700">{o.sector_label}</div>
          )}
        </div>
      </div>
      <div className="text-xs text-zinc-600 mt-3 italic break-words">{o.why_match}</div>
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
    <div className="mt-2">
      <div className="text-[10px] tracking-[0.18em] uppercase text-zinc-500 font-semibold mb-3">
        {t(lang, "youth.cohort")}
      </div>
      <div className="space-y-1.5">
        {years.map((y) => (
          <div key={y} className="flex items-center gap-3 text-xs">
            <div className="w-10 text-zinc-500 font-medium">{y}</div>
            <div className="flex-1 flex h-5 rounded overflow-hidden ring-1 ring-zinc-100">
              {levels.map((lvl) => {
                const v = rows.find((r) => r.year === y && r.edu_level === lvl);
                if (!v) return null;
                return (
                  <div
                    key={lvl}
                    style={{
                      width: `${v.share_pct}%`,
                      backgroundColor: colors[lvl],
                    }}
                    title={`${t(lang, labelKey(lvl))}: ${v.share_pct}%`}
                    aria-label={`${t(lang, labelKey(lvl))}: ${v.share_pct}%`}
                  />
                );
              })}
            </div>
          </div>
        ))}
      </div>
      <div className="grid grid-cols-2 sm:flex sm:flex-wrap gap-x-3 gap-y-1 mt-3 text-[10px]">
        {levels.map((lvl) => (
          <span key={lvl} className="flex items-center gap-1.5">
            <span
              className="inline-block w-2 h-2 rounded-sm flex-shrink-0"
              style={{ backgroundColor: colors[lvl] }}
            />
            {t(lang, labelKey(lvl))}
          </span>
        ))}
      </div>
    </div>
  );
}
