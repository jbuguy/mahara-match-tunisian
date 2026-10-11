import { useEffect, useState } from "react";
import { apiGet } from "./api";
import type { Readiness } from "./types";

export default function ModuleStatus() {
  const [label, setLabel] = useState("vérification…");
  const [ok, setOk] = useState<boolean | null>(null);

  useEffect(() => {
    apiGet<Readiness>("/health/ready")
      .then((readiness) => {
        setOk(readiness.status === "ready");
        setLabel(readiness.status === "ready" ? "module opérationnel" : "module dégradé");
      })
      .catch(() => {
        setOk(false);
        setLabel("backend injoignable");
      });
  }, []);

  return (
    <span className="flex items-center gap-2 text-xs text-ink-soft">
      <span
        aria-hidden
        className={
          "h-2 w-2 rounded-full " +
          (ok === null ? "bg-line" : ok ? "bg-primary" : "bg-danger")
        }
      />
      {label}
    </span>
  );
}