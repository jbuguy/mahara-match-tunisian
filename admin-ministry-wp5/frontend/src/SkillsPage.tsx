import { useCallback, useEffect, useState } from "react";
import { apiGet, apiPost, type Page } from "./api";
import type { Skill, TaxonomyStatus } from "./types";

const FILTERS: { value: TaxonomyStatus | "all"; label: string }[] = [
  { value: "all", label: "Toutes" },
  { value: "draft", label: "Brouillons" },
  { value: "validated", label: "Validées" },
  { value: "deprecated", label: "Retirées" },
];

const BADGES: Record<TaxonomyStatus, string> = {
  draft: "bg-accent/15 text-accent-ink",
  validated: "bg-primary/10 text-primary",
  deprecated: "bg-line text-ink-soft",
};

const BADGE_LABELS: Record<TaxonomyStatus, string> = {
  draft: "brouillon",
  validated: "validée",
  deprecated: "retirée",
};

export default function SkillsPage() {
  const [status, setStatus] = useState<TaxonomyStatus | "all">("all");
  const [typed, setTyped] = useState("");
  const [query, setQuery] = useState("");
  const [data, setData] = useState<Page<Skill> | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);
  const [busy, setBusy] = useState<string | null>(null);
  const [page, setPage] = useState(1);

   // The user types faster than the network answers: wait for a pause.
  useEffect(() => {
    const timer = setTimeout(() => {
      setQuery(typed);
      setPage(1); // a new search starts at the beginning
    }, 300);
    return () => clearTimeout(timer);
  }, [typed]);

  const load = useCallback(async () => {
    setLoading(true);
    setError(null);
    const params = new URLSearchParams({ page: String(page), page_size: "25" });
    if (status !== "all") params.set("status", status);
    if (query.trim()) params.set("search", query.trim());
    try {
      setData(await apiGet<Page<Skill>>(`/admin/taxonomy/skills?${params}`));
    } catch (cause) {
      setError((cause as Error).message);
      setData(null);
    } finally {
      setLoading(false);
    }
  }, [status, query,page]);

  useEffect(() => {
    void load();
  }, [load]);

  async function validate(code: string) {
    setBusy(code);
    try {
      await apiPost(`/admin/taxonomy/skills/${code}/validate`);
      await load(); // re-read rather than guess: the server owns the truth
    } catch (cause) {
      setError((cause as Error).message);
    } finally {
      setBusy(null);
    }
  }

  return (
    <section className="flex flex-col gap-4">
      <div className="flex flex-wrap items-center gap-3">
        <div className="flex flex-wrap gap-1">
          {FILTERS.map((filter) => (
            <button
              key={filter.value}
              type="button"
              onClick={() => {
                setStatus(filter.value);
                setPage(1);
              }}
              className={
                "rounded-full px-3 py-1.5 text-sm transition " +
                (status === filter.value
                  ? "bg-primary text-white"
                  : "border border-line bg-surface text-ink-soft hover:border-primary")
              }
            >
              {filter.label}
            </button>
          ))}
        </div>

        <input
          id="skill-search"
          value={typed}
          onChange={(event) => setTyped(event.target.value)}
          placeholder="Rechercher un libellé ou un code"
          aria-label="Rechercher une compétence"
          className="min-w-0 flex-1 rounded-[10px] border border-line bg-surface px-3 py-2 text-sm outline-none focus:border-primary"
        />
      </div>

      {error && (
        <p className="rounded-[10px] bg-danger/10 px-4 py-3 text-sm text-danger">{error}</p>
      )}

      {loading && <p className="text-sm text-ink-soft">Chargement…</p>}

      {!loading && !error && data?.items.length === 0 && (
        <p className="rounded-[10px] border border-dashed border-line px-4 py-10 text-center text-sm text-ink-soft">
          Aucune compétence ne correspond à ces critères.
        </p>
      )}

      {!loading && data && data.items.length > 0 && (
        <>
          <p className="text-xs text-ink-soft">
            {data.total} compétence{data.total > 1 ? "s" : ""}
          </p>
          <ul className="flex flex-col gap-2">
            {data.items.map((skill) => (
              <li
                key={skill.skill_id}
                className="flex flex-wrap items-center gap-3 rounded-[10px] border border-line bg-surface px-4 py-3"
              >
                <code className="text-xs text-ink-soft">{skill.code}</code>
                <span className="min-w-0 flex-1 text-sm">{skill.label_fr}</span>
                <span className={`rounded-full px-2 py-0.5 text-xs ${BADGES[skill.status]}`}>
                  {BADGE_LABELS[skill.status]}
                </span>
                {skill.status === "draft" && (
                  <button
                    type="button"
                    disabled={busy === skill.code}
                    onClick={() => void validate(skill.code)}
                    className="rounded-full border border-primary px-3 py-1.5 text-xs font-semibold text-primary transition hover:bg-primary hover:text-white disabled:opacity-50"
                  >
                    {busy === skill.code ? "…" : "Valider"}
                  </button>
                )}
              </li>
            ))}
          </ul>
                    {data.total > data.page_size && (
            <nav className="flex items-center justify-between gap-3 pt-2">
              <button
                type="button"
                disabled={page <= 1}
                onClick={() => setPage((current) => current - 1)}
                className="rounded-full border border-line bg-surface px-3 py-1.5 text-sm text-ink-soft transition hover:border-primary disabled:opacity-40"
              >
                Précédent
              </button>

              <span className="text-xs text-ink-soft">
                Page {data.page} sur {Math.ceil(data.total / data.page_size)}
              </span>

              <button
                type="button"
                disabled={page >= Math.ceil(data.total / data.page_size)}
                onClick={() => setPage((current) => current + 1)}
                className="rounded-full border border-line bg-surface px-3 py-1.5 text-sm text-ink-soft transition hover:border-primary disabled:opacity-40"
              >
                Suivant
              </button>
            </nav>
          )}
        </>
      )}
    </section>
  );
}