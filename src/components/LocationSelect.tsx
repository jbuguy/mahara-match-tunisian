import { useEffect, useId, useMemo, useState } from "react";
import { API_BASE_URL } from "../auth";

export type Governorate = {
  code: string;
  name_fr: string;
  name_ar: string;
  latitude: number;
  longitude: number;
};

export type Municipality = {
  code: string;
  governorate_code: string;
  name_fr: string;
  name_ar: string;
  delegation_name_fr?: string | null;
  sort_order: number;
};

const cache = new Map<string, Governorate[] | Municipality[]>();

function normalize(value: string): string {
  return value.normalize("NFD").replace(/[\u0300-\u036f]/g, "").toLocaleLowerCase("fr");
}

function PlaceCombobox({
  label,
  id,
  items,
  selectedCode,
  disabled = false,
  required = false,
  placeholder,
  emptyLabel,
  onSelect,
}: {
  label: string;
  id: string;
  items: Array<{ code: string; name_fr: string; name_ar: string }>;
  selectedCode: string;
  disabled?: boolean;
  required?: boolean;
  placeholder: string;
  emptyLabel?: string;
  onSelect: (code: string) => void;
}) {
  const [query, setQuery] = useState("");
  const [open, setOpen] = useState(false);
  const selected = items.find((item) => item.code === selectedCode);

  useEffect(() => {
    setQuery(selected ? `${selected.name_fr}${selected.name_ar ? ` — ${selected.name_ar}` : ""}` : "");
    setOpen(false);
  }, [selectedCode, selected?.name_fr, selected?.name_ar]);

  const matches = useMemo(() => {
    const normalizedQuery = normalize(query);
    return items.filter((item) => normalize(`${item.name_fr} ${item.name_ar}`).includes(normalizedQuery));
  }, [items, query]);

  const choose = (code: string) => {
    const item = items.find((entry) => entry.code === code);
    setQuery(item ? `${item.name_fr}${item.name_ar ? ` — ${item.name_ar}` : ""}` : "");
    setOpen(false);
    onSelect(code);
  };

  return (
    <div className="place-combobox">
      <label className="form-field__label" htmlFor={id}>{label}</label>
      <div className="place-combobox__control">
        <input
          id={id}
          className="input"
          role="combobox"
          aria-expanded={open}
          aria-controls={`${id}-options`}
          aria-autocomplete="list"
          autoComplete="off"
          required={required}
          disabled={disabled}
          value={query}
          placeholder={placeholder}
          onFocus={() => { if (!disabled) setOpen(true); }}
          onChange={(event) => {
            setQuery(event.target.value);
            setOpen(true);
            if (!event.target.value && selectedCode) onSelect("");
          }}
          onKeyDown={(event) => {
            if (event.key === "Escape") setOpen(false);
            if (event.key === "Enter" && open && matches.length === 1) {
              event.preventDefault();
              choose(matches[0].code);
            }
            if (event.key === "ArrowDown") {
              event.preventDefault();
              setOpen(true);
            }
          }}
          onBlur={() => window.setTimeout(() => setOpen(false), 100)}
        />
        {open && !disabled ? (
          <div id={`${id}-options`} className="place-combobox__options" role="listbox" aria-label={label}>
            {matches.length ? matches.map((item) => (
              <button key={item.code} type="button" role="option" aria-selected={item.code === selectedCode}
                onClick={() => choose(item.code)}>
                <span>{item.name_fr}</span>
                {item.name_ar && <small>{item.name_ar}</small>}
              </button>
            )) : <p>{emptyLabel ?? "Aucun résultat"}</p>}
          </div>
        ) : null}
      </div>
    </div>
  );
}

async function readJson<T>(url: string, key: string): Promise<T[]> {
  const cached = cache.get(key) as T[] | undefined;
  if (cached) return cached;
  const response = await fetch(url);
  if (!response.ok) throw new Error("Impossible de charger les zones géographiques.");
  const contentType = response.headers.get("content-type") ?? "";
  if (contentType.includes("text/html")) {
    throw new Error("Le serveur de localisation est indisponible.");
  }
  const data = await response.json() as T[];
  cache.set(key, data as Governorate[] | Municipality[]);
  return data;
}

export function LocationSelect({
  governorateCode,
  municipalityCode,
  streetAddress = "",
  onChange,
  governorateRequired = false,
  municipalityOptional = true,
}: {
  governorateCode: string;
  municipalityCode: string;
  streetAddress?: string;
  onChange: (value: { governorateCode: string; municipalityCode: string; streetAddress: string }) => void;
  governorateRequired?: boolean;
  municipalityOptional?: boolean;
}) {
  const governorateId = useId();
  const municipalityId = useId();
  const addressId = useId();
  const [governorates, setGovernorates] = useState<Governorate[]>([]);
  const [municipalities, setMunicipalities] = useState<Municipality[]>([]);
  const [error, setError] = useState("");

  useEffect(() => {
    const baseUrl = API_BASE_URL.replace(/\/$/, "");
    void readJson<Governorate>(`${baseUrl}/locations/governorates`, "governorates")
      .then(setGovernorates)
      .catch((cause: Error) => setError(cause.message));
  }, []);

  useEffect(() => {
    setMunicipalities([]);
    if (!governorateCode) return;
    const baseUrl = API_BASE_URL.replace(/\/$/, "");
    void readJson<Municipality>(
      `${baseUrl}/locations/governorates/${encodeURIComponent(governorateCode)}/municipalities`,
      `municipalities:${governorateCode}`,
    ).then(setMunicipalities).catch((cause: Error) => setError(cause.message));
  }, [governorateCode]);

  const sortedGovernorates = useMemo(() => {
    return [...governorates]
      .sort((left, right) => left.name_fr.localeCompare(right.name_fr, "fr"));
  }, [governorates]);

  const sortedMunicipalities = useMemo(() => {
    return [...municipalities]
      .sort((left, right) => left.name_fr.localeCompare(right.name_fr, "fr"));
  }, [municipalities]);

  return (
    <fieldset className="location-select">
      <legend>Localisation</legend>
      {error && <p role="alert">{error}</p>}
      {!governorateCode && <p role="status">Veuillez choisir votre gouvernorat.</p>}
      <div className="location-select__grid">
        <PlaceCombobox
          id={`${governorateId}-input`}
          label="Gouvernorat"
          items={sortedGovernorates}
          selectedCode={governorateCode}
          required={governorateRequired}
          placeholder="Rechercher un gouvernorat"
          onSelect={(code) => onChange({ governorateCode: code, municipalityCode: "", streetAddress })}
        />
        <PlaceCombobox
          id={`${municipalityId}-input`}
          label="Municipalité"
          items={sortedMunicipalities}
          selectedCode={municipalityCode}
          disabled={!governorateCode}
          required={!municipalityOptional}
          placeholder={governorateCode ? "Rechercher une municipalité" : "Choisissez un gouvernorat"}
          emptyLabel="Aucune municipalité ne correspond."
          onSelect={(code) => onChange({ governorateCode, municipalityCode: code, streetAddress })}
        />
      </div>
      <label className="form-field" htmlFor={addressId}>
        <span className="form-field__label">Adresse / quartier</span>
        <input id={addressId} className="input" maxLength={200} value={streetAddress}
          onChange={(event) => onChange({ governorateCode, municipalityCode, streetAddress: event.target.value })} />
      </label>
    </fieldset>
  );
}
