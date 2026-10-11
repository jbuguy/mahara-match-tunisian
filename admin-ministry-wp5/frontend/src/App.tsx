import ModuleStatus from "./ModuleStatus";
import SkillsPage from "./SkillsPage";

export default function App() {
  return (
    <div className="mx-auto flex min-h-full max-w-4xl flex-col gap-6 px-4 py-8">
      <header className="flex flex-wrap items-end justify-between gap-3 border-b border-line pb-4">
        <div>
          <h1 className="font-[family-name:var(--font-display)] text-2xl font-bold text-primary">
            Mahara — Admin &amp; Ministère
          </h1>
          <p className="mt-1 text-sm text-ink-soft">Référentiel national des compétences</p>
        </div>
        <ModuleStatus />
      </header>

      <main>
        <SkillsPage />
      </main>
    </div>
  );
}