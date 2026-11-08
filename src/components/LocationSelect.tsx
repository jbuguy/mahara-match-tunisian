import { useEffect, useId, useMemo, useState } from "react";

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

async function readJson<T>(url: string, key: string): Promise<T[]> {
  const cached = cache.get(key) as T[] | undefined;
  if (cached) return cached;
  const response = await fetch(url);
  if (!response.ok) throw new Error("Impossible de charger les zones géographiques.");
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
  const [governorateSearch, setGovernorateSearch] = useState("");
  const [municipalitySearch, setMunicipalitySearch] = useState("");
  const [error, setError] = useState("");

  useEffect(() => {
    void readJson<Governorate>("/locations/governorates", "governorates")
      .then(setGovernorates)
      .catch((cause: Error) => setError(cause.message));
  }, []);

  useEffect(() => {
    setMunicipalities([]);
    setMunicipalitySearch("");
    if (!governorateCode) return;
    void readJson<Municipality>(
      `/locations/governorates/${encodeURIComponent(governorateCode)}/municipalities`,
      `municipalities:${governorateCode}`,
    ).then(setMunicipalities).catch((cause: Error) => setError(cause.message));
  }, [governorateCode]);

  const filteredGovernorates = useMemo(() => {
    const query = normalize(governorateSearch);
    return governorates
      .filter((item) => !query || `${normalize(item.name_fr)} ${item.name_ar}`.includes(query))
      .sort((left, right) => left.name_fr.localeCompare(right.name_fr, "fr"));
  }, [governorates, governorateSearch]);

  const filteredMunicipalities = useMemo(() => {
    const query = normalize(municipalitySearch);
    return municipalities
      .filter((item) => !query || `${normalize(item.name_fr)} ${normalize(item.name_ar)}`.includes(query))
      .sort((left, right) => left.name_fr.localeCompare(right.name_fr, "fr"));
  }, [municipalities, municipalitySearch]);

  return (
    <fieldset className="location-select">
      <legend>Localisation</legend>
      {error && <p role="alert">{error}</p>}
      {!governorateCode && <p role="status">Veuillez choisir votre gouvernorat.</p>}
      <div className="location-select__grid">
        <div className="form-field">
          <label className="form-field__label" htmlFor={`${governorateId}-search`}>Gouvernorat</label>
          <input id={`${governorateId}-search`} className="input" value={governorateSearch}
            onChange={(event) => setGovernorateSearch(event.target.value)} placeholder="Rechercher" />
          <select id={`${governorateId}-select`} className="select" required={governorateRequired}
            aria-label="Gouvernorat" value={governorateCode}
            onChange={(event) => onChange({ governorateCode: event.target.value, municipalityCode: "", streetAddress })}>
            <option value="">Sélectionner</option>
            {filteredGovernorates.map((item) => (
              <option key={item.code} value={item.code}>{item.name_fr} — {item.name_ar}</option>
            ))}
          </select>
        </div>
        <div className="form-field">
          <label className="form-field__label" htmlFor={`${municipalityId}-search`}>Municipalité</label>
          <input id={`${municipalityId}-search`} className="input" value={municipalitySearch}
            disabled={!governorateCode} onChange={(event) => setMunicipalitySearch(event.target.value)}
            placeholder="Rechercher" />
          <select id={`${municipalityId}-select`} className="select" disabled={!governorateCode}
            required={!municipalityOptional} aria-label="Municipalité" value={municipalityCode}
            onChange={(event) => onChange({ governorateCode, municipalityCode: event.target.value, streetAddress })}>
            <option value="">{municipalityOptional ? "Non renseignée" : "Sélectionner"}</option>
            {filteredMunicipalities.map((item) => (
              <option key={item.code} value={item.code}>{item.name_fr}{item.name_ar ? ` — ${item.name_ar}` : ""}</option>
            ))}
          </select>
        </div>
      </div>
      <label className="form-field" htmlFor={addressId}>
        <span className="form-field__label">Adresse / quartier</span>
        <input id={addressId} className="input" maxLength={200} value={streetAddress}
          onChange={(event) => onChange({ governorateCode, municipalityCode, streetAddress: event.target.value })} />
      </label>
    </fieldset>
  );
}
