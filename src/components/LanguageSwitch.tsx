import { translate, type Language } from "../i18n";

export function LanguageSwitch({
  language,
  onChange,
}: {
  language: Language;
  onChange: (language: Language) => void;
}) {
  return (
    <button
      className="language-toggle"
      type="button"
      aria-label={language === "fr" ? "التبديل إلى العربية" : "التبديل إلى الفرنسية"}
      onClick={() => onChange(language === "fr" ? "ar" : "fr")}
    >
      {translate(language, language === "fr" ? "العربية" : "Français")}
    </button>
  );
}
