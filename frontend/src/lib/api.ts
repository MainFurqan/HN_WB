// Accept either name — different deploy environments use slightly different conventions.
const API_BASE =
  process.env.NEXT_PUBLIC_API_BASE ||
  process.env.NEXT_PUBLIC_API_URL ||
  "http://127.0.0.1:8000";

async function post<T>(path: string, body: unknown): Promise<T> {
  const r = await fetch(`${API_BASE}${path}`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body),
    cache: "no-store",
  });
  if (!r.ok) throw new Error(`${path} failed: ${r.status} ${await r.text()}`);
  return r.json();
}

async function get<T>(path: string): Promise<T> {
  const r = await fetch(`${API_BASE}${path}`, { cache: "no-store" });
  if (!r.ok) throw new Error(`${path} failed: ${r.status}`);
  return r.json();
}

export type SkillCategory = "hard" | "soft" | "knowledge";

export type SkillCandidate = {
  esco_uri: string;
  label: string;
  confidence: number;
  evidence_quote: string;
  category: SkillCategory;
};

export type ExtractResponse = {
  candidates: SkillCandidate[];
  isco_hint: string | null;
  shortlist_size: number;
};

export type Passport = {
  jsonld: Record<string, unknown>;
  qr_png_b64: string;
};

export type Readiness = {
  automation_risk: number;
  automation_risk_uncalibrated: number;
  durable_skills: { esco_uri: string; label: string; rationale_bucket: string }[];
  at_risk_skills: { esco_uri: string; label: string; rationale_bucket: string }[];
  mixed_skills: { esco_uri: string; label: string; rationale_bucket: string }[];
  adjacent_skills: {
    conceptUri: string;
    preferredLabel: string;
    description: string;
    score: number;
  }[];
  cohort_projection: { year: number; edu_level: string; share_pct: number }[];
  calibration_notes: string;
  limits: string[];
};

export type Opportunity = {
  esco_uri: string;
  title: string;
  isco_code: string;
  type: string;
  match_score: number;
  wage_low: number | null;
  wage_p50: number | null;
  wage_high: number | null;
  wage_currency: string | null;
  wage_basis: string | null;
  sector_growth_pct: number | null;
  sector_label: string | null;
  why_match: string;
};

export type PolicyAggregate = {
  country: string;
  neet_rate: { year: number; value: number } | null;
  informal_employment_share: { year: number; value: number } | null;
  sector_employment: {
    agriculture: { year: number; value: number } | null;
    industry: { year: number; value: number } | null;
    services: { year: number; value: number } | null;
  };
  fixed_broadband_per_100: { year: number; value: number } | null;
  gdp_per_capita_growth: { year: number; value: number } | null;
  cohort_projection_2020_2035: { year: number; edu_level: string; share_pct: number }[];
  skill_supply_divergence_note: string | null;
};

export type CvProfile = {
  about: string;
  education: string;
  work: string;
  selfTaught: string;
  tools: string;
  aspirations: string;
  raw_text_chars?: number;
};

async function postFile<T>(path: string, file: File): Promise<T> {
  const fd = new FormData();
  fd.append("file", file);
  const r = await fetch(`${API_BASE}${path}`, { method: "POST", body: fd, cache: "no-store" });
  if (!r.ok) throw new Error(`${path} failed: ${r.status} ${await r.text()}`);
  return r.json();
}

export const api = {
  packs: () => get<{ available: string[] }>("/packs"),
  extract: (description: string, country: string, language = "en") =>
    post<ExtractResponse>("/skills/extract", { description, country, language }),
  parseCv: (file: File) => postFile<CvProfile>("/skills/parse-cv", file),
  passport: (params: {
    confirmed_skill_uris: string[];
    holder_name: string;
    country: string;
    education_level?: string | null;
    isco_cluster?: string | null;
    share_url?: string;
  }) =>
    post<Passport>("/skills/passport", {
      ...params,
      share_url: params.share_url ?? "https://unmapped.dev/p/demo",
    }),
  readiness: (skill_uris: string[], isco_cluster: string | null, country: string) =>
    post<Readiness>("/readiness/", { skill_uris, isco_cluster, country }),
  match: (skill_uris: string[], isco_cluster: string | null, country: string) =>
    post<Opportunity[]>("/opportunities/match", { skill_uris, isco_cluster, country }),
  policy: (country: string) => get<PolicyAggregate>(`/policy/aggregate?country=${country}`),
};
