"use client";

import { ChangeEvent, ReactNode, useMemo, useState } from "react";
import {
  AlertTriangle,
  Archive,
  BadgeDollarSign,
  Building2,
  Download,
  FileSearch,
  FileText,
  Gavel,
  Landmark,
  Loader2,
  Lock,
  Scale,
  ShieldAlert,
  UploadCloud
} from "lucide-react";

type Source = "office" | "inss" | "court_accounting" | "unknown";
type DivergenceType =
  | "index"
  | "marco"
  | "abatement"
  | "interest"
  | "honoraries"
  | "rmi"
  | "total"
  | "other";
type Severity = "info" | "warning" | "critical";

type EvidenceRef = {
  file_name: string;
  page?: number | null;
  text: string;
  locator?: string | null;
};

type ExtractedValue = {
  value?: unknown;
  normalized?: unknown;
  confidence: number;
  evidence?: EvidenceRef | null;
};

type ExtractedCalculation = {
  id: string;
  source: Source;
  file_name: string;
  process_number?: ExtractedValue | null;
  beneficiary_name?: ExtractedValue | null;
  rmi?: ExtractedValue | null;
  dib?: ExtractedValue | null;
  dip?: ExtractedValue | null;
  calculation_until?: ExtractedValue | null;
  correction_index?: ExtractedValue | null;
  interest_rate?: ExtractedValue | null;
  principal?: ExtractedValue | null;
  arrears?: ExtractedValue | null;
  abatements?: ExtractedValue | null;
  honoraries?: ExtractedValue | null;
  total?: ExtractedValue | null;
  flags: string[];
};

type Divergence = {
  id: string;
  type: DivergenceType;
  field: string;
  title: string;
  description: string;
  sources: Source[];
  values: Record<string, unknown>;
  magnitude_money?: string | number | null;
  magnitude_percent?: string | number | null;
  favored_party: "segurado" | "inss" | "neutral" | "unknown";
  severity: Severity;
  legal_basis?: string | null;
  evidence: EvidenceRef[];
};

type ComparisonResult = {
  id: string;
  process_number?: string | null;
  calculations: ExtractedCalculation[];
  divergences: Divergence[];
  summary: {
    calculation_count?: number;
    divergence_count?: number;
    divergences_by_type?: Record<string, number>;
    sources?: Source[];
  };
  created_at: string;
};

type DraftResult = {
  mode: "template" | "anthropic";
  text: string;
  model?: string | null;
  warnings: string[];
};

const ACCESS_TOKEN_STORAGE_KEY = "previdenciario-comparador-access-token";

const SOURCE_LABELS: Record<Source, string> = {
  office: "Escritório / autor",
  inss: "INSS",
  court_accounting: "Contadoria judicial",
  unknown: "Fonte não identificada"
};

const SOURCE_SHORT: Record<Source, string> = {
  office: "Autor",
  inss: "INSS",
  court_accounting: "Contadoria",
  unknown: "Não identificado"
};

const TYPE_LABELS: Record<DivergenceType, string> = {
  index: "Índices",
  marco: "Marcos",
  abatement: "Abatimentos",
  interest: "Juros",
  honoraries: "Honorários",
  rmi: "RMI",
  total: "Valores totais",
  other: "Outros"
};

const FIELD_LABELS: Record<string, string> = {
  rmi: "RMI",
  dib: "DIB",
  dip: "DIP",
  calculation_until: "Atualização até",
  correction_index: "Índice",
  interest_rate: "Juros",
  principal: "Principal",
  arrears: "Atrasados",
  abatements: "Abatimentos",
  honoraries: "Honorários",
  total: "Total"
};

const FIELD_ORDER = [
  "rmi",
  "dib",
  "dip",
  "calculation_until",
  "correction_index",
  "interest_rate",
  "principal",
  "arrears",
  "abatements",
  "honoraries",
  "total"
];

const MONEY_FIELDS = new Set(["rmi", "principal", "arrears", "abatements", "honoraries", "total"]);
const DATE_FIELDS = new Set(["dib", "dip", "calculation_until"]);

export default function Home() {
  const [officeFiles, setOfficeFiles] = useState<File[]>([]);
  const [inssFiles, setInssFiles] = useState<File[]>([]);
  const [courtFiles, setCourtFiles] = useState<File[]>([]);
  const [autoFiles, setAutoFiles] = useState<File[]>([]);
  const [comparison, setComparison] = useState<ComparisonResult | null>(null);
  const [draft, setDraft] = useState("");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  const [accessToken, setAccessToken] = useState(() => {
    if (typeof window === "undefined") {
      return "";
    }
    return window.localStorage.getItem(ACCESS_TOKEN_STORAGE_KEY) ?? "";
  });

  const relevantCalculations = comparison?.calculations.filter((item) => item.source !== "unknown") ?? [];
  const moneyDivergences = comparison?.divergences.filter((item) => item.magnitude_money != null) ?? [];
  const priorityDivergences = useMemo(
    () => [...(comparison?.divergences ?? [])].sort(sortDivergences).slice(0, 5),
    [comparison]
  );

  async function analyze() {
    setBusy(true);
    setError("");
    setDraft("");
    try {
      const form = new FormData();
      appendFiles(form, "office_files", officeFiles);
      appendFiles(form, "inss_files", inssFiles);
      appendFiles(form, "court_files", courtFiles);
      appendFiles(form, "auto_files", autoFiles);

      window.localStorage.setItem(ACCESS_TOKEN_STORAGE_KEY, accessToken);
      const response = await fetch("/api/cases/analyze", {
        method: "POST",
        headers: accessToken ? { "X-Access-Token": accessToken } : undefined,
        body: form
      });
      if (!response.ok) {
        throw new Error(await readableError(response));
      }
      const result = (await response.json()) as ComparisonResult;
      setComparison(result);
      await buildDraft(result);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Falha ao analisar os cálculos.");
    } finally {
      setBusy(false);
    }
  }

  async function buildDraft(result: ComparisonResult) {
    const response = await fetch("/api/drafts", {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
        ...(accessToken ? { "X-Access-Token": accessToken } : {})
      },
      body: JSON.stringify({ comparison: result, target: "both", use_ai: false })
    });
    if (response.ok) {
      const payload = (await response.json()) as DraftResult;
      setDraft(payload.text);
    }
  }

  return (
    <main className="appShell">
      <header className="topbar">
        <div>
          <p className="eyebrow">Borges e Camargo · Cumprimento de sentença</p>
          <h1>Comparador de cálculos previdenciários</h1>
        </div>
        <label className="tokenBox">
          <Lock size={17} />
          <input
            aria-label="Token de acesso"
            onChange={(event) => setAccessToken(event.target.value)}
            placeholder="Token"
            type="password"
            value={accessToken}
          />
        </label>
      </header>

      <section className="workbench">
        <aside className="controlRail">
          <div className="railHeader">
            <UploadCloud size={21} />
            <strong>Entrada do caso</strong>
          </div>

          <UploadBox
            files={officeFiles}
            icon={<Scale size={22} />}
            label="Cálculo do escritório"
            onChange={setOfficeFiles}
          />
          <UploadBox
            files={inssFiles}
            icon={<Gavel size={22} />}
            label="Cálculo / impugnação do INSS"
            onChange={setInssFiles}
          />
          <UploadBox
            files={courtFiles}
            icon={<Landmark size={22} />}
            label="Cálculo da contadoria judicial"
            onChange={setCourtFiles}
          />
          <UploadBox
            files={autoFiles}
            icon={<Archive size={22} />}
            label="Processo completo, ZIP ou material misto"
            onChange={setAutoFiles}
          />

          <button className="primary" disabled={busy} onClick={analyze}>
            {busy ? <Loader2 className="spin" size={18} /> : <FileSearch size={18} />}
            Analisar deterministicamente
          </button>
          {error && <p className="error">{error}</p>}
        </aside>

        <section className="desk">
          <section className="snapshot">
            <Metric icon={<FileText size={18} />} label="Documentos úteis" value={relevantCalculations.length} />
            <Metric
              icon={<AlertTriangle size={18} />}
              label="Pontos de atenção"
              tone={comparison?.divergences.length ? "alert" : undefined}
              value={comparison?.divergences.length ?? 0}
            />
            <Metric
              icon={<BadgeDollarSign size={18} />}
              label="Com impacto em valor"
              tone={moneyDivergences.length ? "money" : undefined}
              value={moneyDivergences.length}
            />
            <div className="sourceMetric">
              <span>Fontes identificadas</span>
              <div className="sourcePills">
                {sourceList(comparison).map((source) => (
                  <SourceBadge key={source} source={source} />
                ))}
                {!comparison && <span className="muted">Aguardando análise</span>}
              </div>
            </div>
          </section>

          <section className="priorityPanel">
            <div className="sectionHead">
              <ShieldAlert size={20} />
              <h2>Prioridades para revisão</h2>
            </div>
            <div className="priorityGrid">
              {priorityDivergences.map((divergence, index) => (
                <article className={`priorityCard ${divergence.severity}`} key={divergence.id}>
                  <div className="priorityTop">
                    <span className="rank">P{index + 1}</span>
                    <div>
                      <span>{TYPE_LABELS[divergence.type]}</span>
                      <small>{divergence.sources.map((source) => SOURCE_SHORT[source]).join(" x ")}</small>
                    </div>
                  </div>
                  <strong>{divergence.title}</strong>
                  <p>{shortDescription(divergence.description)}</p>
                  {divergence.magnitude_money != null && (
                    <b>{formatMoney(divergence.magnitude_money)}</b>
                  )}
                </article>
              ))}
              {!comparison && <p className="empty">Envie os cálculos para o sistema ordenar os pontos mais relevantes.</p>}
              {comparison && !priorityDivergences.length && <p className="empty">Nenhuma divergência material foi encontrada.</p>}
            </div>
          </section>

          <section className="twoColumns">
            <section className="surface">
              <div className="sectionHead">
                <AlertTriangle size={19} />
                <h2>Divergências classificadas</h2>
              </div>
              <div className="divergenceList">
                {(comparison?.divergences ?? []).map((divergence) => (
                  <details className={`divergence ${divergence.severity}`} key={divergence.id}>
                    <summary>
                      <span>
                        <strong>{divergence.title}</strong>
                        <small>{divergence.description}</small>
                      </span>
                      {divergence.magnitude_money != null && <b>{formatMoney(divergence.magnitude_money)}</b>}
                    </summary>
                    <div className="detailGrid">
                      <Info label="Tipo" value={TYPE_LABELS[divergence.type]} />
                      <Info label="Favorece" value={favoredLabel(divergence.favored_party)} />
                      <Info label="Base" value={divergence.legal_basis ?? "Regra comparativa"} />
                    </div>
                    {!!divergence.evidence.length && (
                      <div className="evidenceList">
                        {divergence.evidence.map((evidence, index) => (
                          <blockquote key={`${divergence.id}-${index}`}>
                            <strong>{docLabel(evidence.file_name)}</strong>
                            {evidence.page ? <span> pág. {evidence.page}</span> : null}
                            <p>{evidence.text}</p>
                          </blockquote>
                        ))}
                      </div>
                    )}
                  </details>
                ))}
                {!comparison && <p className="empty">As divergências aparecerão aqui com tipo, impacto e evidência.</p>}
              </div>
            </section>

            <section className="surface draftPanel">
              <div className="sectionHead">
                <FileText size={19} />
                <h2>Minuta preliminar</h2>
              </div>
              <textarea
                readOnly={!draft}
                value={draft || "A minuta será gerada após a comparação determinística."}
                onChange={(event) => setDraft(event.target.value)}
              />
              {draft && (
                <button className="secondary" onClick={() => downloadText(draft)}>
                  <Download size={17} />
                  Baixar minuta .txt
                </button>
              )}
            </section>
          </section>

          <section className="surface">
            <div className="sectionHead">
              <FileText size={19} />
              <h2>Documentos e campos extraídos</h2>
            </div>
            <div className="extractedTable">
              <div className="tableHeader">
                <span>Origem</span>
                <span>Documento</span>
                {FIELD_ORDER.map((field) => (
                  <span key={field}>{FIELD_LABELS[field]}</span>
                ))}
              </div>
              {(comparison?.calculations ?? []).map((calculation) => (
                <div className="tableRow" key={calculation.id}>
                  <SourceBadge source={calculation.source} />
                  <span className="docCell">{docLabel(calculation.file_name)}</span>
                  {FIELD_ORDER.map((field) => (
                    <span className={cellClass(field)} key={field}>
                      {displayValue(field, calculation[field as keyof ExtractedCalculation] as ExtractedValue | null)}
                    </span>
                  ))}
                </div>
              ))}
              {!comparison && <p className="empty">Após a análise, cada linha mostrará os campos extraídos e a origem do dado.</p>}
            </div>
          </section>
        </section>
      </section>
    </main>
  );
}

function UploadBox({
  files,
  icon,
  label,
  onChange
}: {
  files: File[];
  icon: ReactNode;
  label: string;
  onChange: (files: File[]) => void;
}) {
  function handleFiles(event: ChangeEvent<HTMLInputElement>) {
    onChange(Array.from(event.target.files ?? []));
  }

  return (
    <label className="uploadBox">
      {icon}
      <strong>{label}</strong>
      <span>{files.length ? `${files.length} arquivo(s)` : "PDF, XLSX, CSV ou ZIP"}</span>
      <input multiple type="file" onChange={handleFiles} />
    </label>
  );
}

function Metric({
  icon,
  label,
  value,
  tone
}: {
  icon: ReactNode;
  label: string;
  value: string | number;
  tone?: "alert" | "money";
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

function SourceBadge({ source }: { source: Source }) {
  return <span className={`sourceBadge ${source}`}>{SOURCE_LABELS[source]}</span>;
}

function Info({ label, value }: { label: string; value: string }) {
  return (
    <div>
      <span>{label}</span>
      <strong>{value}</strong>
    </div>
  );
}

function appendFiles(form: FormData, field: string, files: File[]) {
  for (const file of files) {
    form.append(field, file);
  }
}

function sortDivergences(left: Divergence, right: Divergence) {
  const severityScore = { critical: 3, warning: 2, info: 1 };
  const moneyLeft = Number(left.magnitude_money ?? 0);
  const moneyRight = Number(right.magnitude_money ?? 0);
  return severityScore[right.severity] - severityScore[left.severity] || moneyRight - moneyLeft;
}

function sourceList(comparison: ComparisonResult | null): Source[] {
  if (!comparison) {
    return [];
  }
  return Array.from(new Set(comparison.calculations.map((item) => item.source).filter((source) => source !== "unknown")));
}

function favoredLabel(value: Divergence["favored_party"]) {
  const labels = {
    segurado: "Segurado",
    inss: "INSS / contadoria",
    neutral: "Neutro",
    unknown: "A apurar"
  };
  return labels[value];
}

function shortDescription(value: string) {
  return value.length > 135 ? `${value.slice(0, 132)}...` : value;
}

function docLabel(fileName: string) {
  const docMatch = fileName.match(/doc\s*(\d+)/i);
  const pageMatch = fileName.match(/pp?\.?\s*(\d+(?:-\d+)?)/i);
  const name = docMatch ? `Doc. ${docMatch[1]}` : fileName.replace(/\.[^.]+$/, "");
  return pageMatch ? `${name} · págs. ${pageMatch[1]}` : name;
}

function cellClass(field: string) {
  if (MONEY_FIELDS.has(field)) {
    return "numeric";
  }
  if (DATE_FIELDS.has(field)) {
    return "dateCell";
  }
  return "";
}

function displayValue(field: string, value?: ExtractedValue | null) {
  const normalized = value?.normalized;
  if (normalized == null || normalized === "") {
    return "-";
  }
  if (MONEY_FIELDS.has(field)) {
    return formatMoney(normalized);
  }
  if (DATE_FIELDS.has(field)) {
    return formatDate(String(normalized));
  }
  return String(normalized);
}

function formatDate(value: string) {
  if (/^\d{4}-\d{2}-\d{2}/.test(value)) {
    const [year, month, day] = value.slice(0, 10).split("-");
    return `${day}/${month}/${year}`;
  }
  return value;
}

function formatMoney(value: unknown) {
  const numberValue = Number(value ?? 0);
  return numberValue.toLocaleString("pt-BR", { style: "currency", currency: "BRL" });
}

function downloadText(text: string) {
  const blob = new Blob([text], { type: "text/plain;charset=utf-8" });
  const url = URL.createObjectURL(blob);
  const anchor = document.createElement("a");
  anchor.href = url;
  anchor.download = "minuta-comparacao-calculos.txt";
  anchor.click();
  URL.revokeObjectURL(url);
}

async function readableError(response: Response) {
  try {
    const payload = await response.json();
    return payload.detail ?? response.statusText;
  } catch {
    return response.statusText;
  }
}
