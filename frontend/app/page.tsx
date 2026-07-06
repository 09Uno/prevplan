"use client";

import { ChangeEvent, useMemo, useState } from "react";
import {
  AlertTriangle,
  CalendarClock,
  CheckCircle2,
  Download,
  FileCheck2,
  FileText,
  Gauge,
  Landmark,
  Loader2,
  Lock,
  Scale,
  ShieldCheck,
  UploadCloud
} from "lucide-react";

type Gender = "male" | "female";
type DocumentType = "cnis" | "ctps" | "ppp" | "ltcat" | "ctc" | "report" | "id" | "other";
type Status = "available" | "projected" | "needs_review" | "not_applicable";
type Severity = "info" | "warning" | "critical";

type InsuredProfile = {
  name: string;
  gender: Gender;
  birth_date: string;
  analysis_date: string;
  current_contribution_years: number;
  current_contribution_months: number;
  current_contribution_days: number;
  contribution_base: string;
  contributor_type: "employee" | "individual";
  special_months_before_2019: number;
  special_factor: string;
  target_monthly_income?: string;
};

type DocumentInsight = {
  id: string;
  file_name: string;
  document_type: DocumentType;
  pages: number;
  confidence: number;
  extracted_name?: string;
  contribution_duration_text?: string;
  detected_signals: string[];
};

type Scenario = {
  id: string;
  rule_code: string;
  title: string;
  status: Status;
  eligibility_date?: string;
  age_at_der: string;
  contribution_time: string;
  points?: string;
  estimated_rmi: string;
  coefficient: string;
  future_contribution_months: number;
  future_investment: string;
  recovery_months?: string;
  roi_estimate: string;
  recommendation_score: string;
  legal_basis: string;
  caveats: string[];
};

type PendingIssue = {
  id: string;
  severity: Severity;
  title: string;
  description: string;
  document_type?: DocumentType;
};

type NormativeReference = {
  code: string;
  title: string;
  effective_from: string;
  summary: string;
  source_url: string;
  tags: string[];
};

type PlanningCase = {
  id: string;
  profile: InsuredProfile;
  documents: DocumentInsight[];
  normative_references: NormativeReference[];
  scenarios: Scenario[];
  pending_issues: PendingIssue[];
  recommendation: string;
  report_markdown: string;
};

const ACCESS_TOKEN_STORAGE_KEY = "previdenciario-planner-access-token";

const DEFAULT_PROFILE: InsuredProfile = {
  name: "Segurado(a) em validacao",
  gender: "male",
  birth_date: "1973-03-05",
  analysis_date: "2026-06-04",
  current_contribution_years: 32,
  current_contribution_months: 6,
  current_contribution_days: 0,
  contribution_base: "8475.55",
  contributor_type: "employee",
  special_months_before_2019: 0,
  special_factor: "1.4",
  target_monthly_income: ""
};

const DOC_LABELS: Record<DocumentType, string> = {
  cnis: "CNIS",
  ctps: "CTPS",
  ppp: "PPP",
  ltcat: "LTCAT",
  ctc: "CTC",
  report: "Parecer",
  id: "Identificacao",
  other: "Outro"
};

const STATUS_LABELS: Record<Status, string> = {
  available: "Disponivel",
  projected: "Projetado",
  needs_review: "Revisar",
  not_applicable: "Nao aplicavel"
};

export default function Home() {
  const [profile, setProfile] = useState<InsuredProfile>(DEFAULT_PROFILE);
  const [files, setFiles] = useState<File[]>([]);
  const [planning, setPlanning] = useState<PlanningCase | null>(null);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  const [accessToken, setAccessToken] = useState(() => {
    if (typeof window === "undefined") {
      return "";
    }
    return window.localStorage.getItem(ACCESS_TOKEN_STORAGE_KEY) ?? "";
  });

  const bestScenario = useMemo(
    () =>
      planning?.scenarios
        .filter((scenario) => scenario.status !== "not_applicable")
        .sort((a, b) => Number(b.recommendation_score) - Number(a.recommendation_score))[0],
    [planning]
  );

  const criticalIssues = planning?.pending_issues.filter((issue) => issue.severity === "critical").length ?? 0;

  function updateProfile<K extends keyof InsuredProfile>(key: K, value: InsuredProfile[K]) {
    setProfile((current) => ({ ...current, [key]: value }));
  }

  function onFiles(event: ChangeEvent<HTMLInputElement>) {
    setFiles(Array.from(event.target.files ?? []));
  }

  async function analyze() {
    setBusy(true);
    setError("");
    try {
      const form = new FormData();
      form.append("profile_json", JSON.stringify(cleanProfile(profile)));
      for (const file of files) {
        form.append("case_files", file);
      }
      window.localStorage.setItem(ACCESS_TOKEN_STORAGE_KEY, accessToken);
      const response = await fetch("/api/planning/analyze", {
        method: "POST",
        headers: accessToken ? { "X-Access-Token": accessToken } : undefined,
        body: form
      });
      if (!response.ok) {
        throw new Error(await readableError(response));
      }
      setPlanning((await response.json()) as PlanningCase);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Falha ao analisar o planejamento.");
    } finally {
      setBusy(false);
    }
  }

  return (
    <main className="appShell">
      <header className="topbar">
        <div>
          <p className="eyebrow">Breno Borges · Previdenciario</p>
          <h1>Planejamento previdenciario</h1>
        </div>
        <div className="tokenBox">
          <Lock size={17} />
          <input
            aria-label="Token de acesso"
            onChange={(event) => setAccessToken(event.target.value)}
            placeholder="Token"
            type="password"
            value={accessToken}
          />
        </div>
      </header>

      <section className="workbench">
        <aside className="controlRail">
          <div className="railHeader">
            <Scale size={20} />
            <strong>Dados do caso</strong>
          </div>

          <label className="field wide">
            <span>Nome</span>
            <input value={profile.name} onChange={(event) => updateProfile("name", event.target.value)} />
          </label>

          <div className="fieldGrid">
            <label className="field">
              <span>Sexo</span>
              <select
                value={profile.gender}
                onChange={(event) => updateProfile("gender", event.target.value as Gender)}
              >
                <option value="male">Homem</option>
                <option value="female">Mulher</option>
              </select>
            </label>
            <label className="field">
              <span>Nascimento</span>
              <input
                type="date"
                value={profile.birth_date}
                onChange={(event) => updateProfile("birth_date", event.target.value)}
              />
            </label>
          </div>

          <div className="fieldGrid three">
            <NumberField label="Anos" value={profile.current_contribution_years} onChange={(value) => updateProfile("current_contribution_years", value)} />
            <NumberField label="Meses" value={profile.current_contribution_months} onChange={(value) => updateProfile("current_contribution_months", value)} />
            <NumberField label="Dias" value={profile.current_contribution_days} onChange={(value) => updateProfile("current_contribution_days", value)} />
          </div>

          <div className="fieldGrid">
            <label className="field">
              <span>Base futura</span>
              <input
                inputMode="decimal"
                value={profile.contribution_base}
                onChange={(event) => updateProfile("contribution_base", event.target.value)}
              />
            </label>
            <label className="field">
              <span>Categoria</span>
              <select
                value={profile.contributor_type}
                onChange={(event) => updateProfile("contributor_type", event.target.value as "employee" | "individual")}
              >
                <option value="employee">Empregado</option>
                <option value="individual">Individual</option>
              </select>
            </label>
          </div>

          <div className="fieldGrid">
            <NumberField
              label="Meses especiais"
              value={profile.special_months_before_2019}
              onChange={(value) => updateProfile("special_months_before_2019", value)}
            />
            <label className="field">
              <span>Fator</span>
              <select
                value={profile.special_factor}
                onChange={(event) => updateProfile("special_factor", event.target.value)}
              >
                <option value="1.4">1,4</option>
                <option value="1.2">1,2</option>
              </select>
            </label>
          </div>

          <label className="uploadBox">
            <UploadCloud size={21} />
            <strong>{files.length ? `${files.length} arquivo(s)` : "Documentos"}</strong>
            <span>PDF, planilha ou ZIP</span>
            <input multiple type="file" onChange={onFiles} />
          </label>

          <button className="primary" disabled={busy} onClick={analyze}>
            {busy ? <Loader2 className="spin" size={18} /> : <Gauge size={18} />}
            Analisar planejamento
          </button>
          {error && <p className="error">{error}</p>}
        </aside>

        <section className="desk">
          <section className="snapshot">
            <Metric icon={<FileCheck2 size={18} />} label="Documentos" value={planning?.documents.length ?? 0} />
            <Metric icon={<CalendarClock size={18} />} label="Melhor DER" value={formatDate(bestScenario?.eligibility_date)} />
            <Metric icon={<Landmark size={18} />} label="RMI estimada" value={money(bestScenario?.estimated_rmi)} />
            <Metric icon={<AlertTriangle size={18} />} label="Pendencias criticas" value={criticalIssues} tone={criticalIssues ? "alert" : "ok"} />
          </section>

          <section className="decisionBand">
            <div>
              <p className="sectionKicker">Opiniao preliminar</p>
              <h2>{planning?.recommendation ?? "Aguardando analise dos documentos e dados do segurado."}</h2>
            </div>
            {planning && (
              <a className="downloadButton" href={`/api/planning/cases/${planning.id}/report.docx`}>
                <Download size={18} />
                DOCX
              </a>
            )}
          </section>

          <section className="surface">
            <div className="sectionHead">
              <CalendarClock size={19} />
              <h2>Cenarios calculados</h2>
            </div>
            <div className="scenarioTable">
              <div className="tableHeader">
                <span>Regra</span>
                <span>DER</span>
                <span>Tempo</span>
                <span>RMI</span>
                <span>Investimento</span>
                <span>Status</span>
              </div>
              {(planning?.scenarios ?? []).map((scenario) => (
                <div className="tableRow" key={scenario.id}>
                  <strong>{scenario.title}</strong>
                  <span>{formatDate(scenario.eligibility_date)}</span>
                  <span>{scenario.contribution_time}</span>
                  <span>{money(scenario.estimated_rmi)}</span>
                  <span>{money(scenario.future_investment)}</span>
                  <Badge status={scenario.status}>{STATUS_LABELS[scenario.status]}</Badge>
                </div>
              ))}
              {!planning && <p className="empty">Sem cenarios calculados.</p>}
            </div>
          </section>

          <section className="twoColumns">
            <section className="surface">
              <div className="sectionHead">
                <ShieldCheck size={19} />
                <h2>Omissoes e divergencias</h2>
              </div>
              <div className="issueList">
                {(planning?.pending_issues ?? []).map((issue) => (
                  <article className={`issue ${issue.severity}`} key={issue.id}>
                    <strong>{issue.title}</strong>
                    <p>{issue.description}</p>
                  </article>
                ))}
                {planning && !planning.pending_issues.length && (
                  <article className="issue ok">
                    <strong>Sem bloqueios</strong>
                    <p>Nenhuma pendencia impeditiva foi detectada nesta leitura.</p>
                  </article>
                )}
                {!planning && <p className="empty">As pendencias aparecem apos a analise.</p>}
              </div>
            </section>

            <section className="surface">
              <div className="sectionHead">
                <FileText size={19} />
                <h2>Documentos classificados</h2>
              </div>
              <div className="docList">
                {(planning?.documents ?? []).map((document) => (
                  <article className="docItem" key={document.id}>
                    <div>
                      <strong>{document.file_name}</strong>
                      <span>{DOC_LABELS[document.document_type]} · {document.pages} pag.</span>
                    </div>
                    <small>{Math.round(document.confidence * 100)}%</small>
                  </article>
                ))}
                {!planning && <p className="empty">CNIS, CTPS, PPP, LTCAT, CTC e pareceres serao reconhecidos aqui.</p>}
              </div>
            </section>
          </section>

          <section className="surface reportSurface">
            <div className="sectionHead">
              <FileText size={19} />
              <h2>Previa do parecer</h2>
            </div>
            <pre>{planning?.report_markdown ?? "O parecer revisavel sera montado apos a analise."}</pre>
          </section>

          <section className="normativeStrip">
            {(planning?.normative_references ?? []).slice(0, 6).map((reference) => (
              <a href={reference.source_url} key={reference.code} rel="noreferrer" target="_blank">
                <CheckCircle2 size={15} />
                {reference.code}
              </a>
            ))}
          </section>
        </section>
      </section>
    </main>
  );
}

function NumberField({
  label,
  value,
  onChange
}: {
  label: string;
  value: number;
  onChange: (value: number) => void;
}) {
  return (
    <label className="field">
      <span>{label}</span>
      <input
        min={0}
        type="number"
        value={value}
        onChange={(event) => onChange(Number(event.target.value))}
      />
    </label>
  );
}

function Metric({
  icon,
  label,
  value,
  tone
}: {
  icon: React.ReactNode;
  label: string;
  value: string | number;
  tone?: "alert" | "ok";
}) {
  return (
    <div className={`metric ${tone ?? ""}`}>
      <span>
        {icon}
        {label}
      </span>
      <strong>{value}</strong>
    </div>
  );
}

function Badge({ status, children }: { status: Status; children: React.ReactNode }) {
  return <span className={`badge ${status}`}>{children}</span>;
}

function cleanProfile(profile: InsuredProfile) {
  return {
    ...profile,
    contribution_base: Number(profile.contribution_base || 0),
    special_factor: Number(profile.special_factor || 1.4),
    target_monthly_income: profile.target_monthly_income ? Number(profile.target_monthly_income) : null
  };
}

function formatDate(value?: string) {
  if (!value) {
    return "-";
  }
  const [year, month, day] = value.slice(0, 10).split("-");
  return `${day}/${month}/${year}`;
}

function money(value?: string | number) {
  const numberValue = Number(value ?? 0);
  return numberValue.toLocaleString("pt-BR", { style: "currency", currency: "BRL" });
}

async function readableError(response: Response) {
  try {
    const payload = await response.json();
    return payload.detail ?? response.statusText;
  } catch {
    return response.statusText;
  }
}
