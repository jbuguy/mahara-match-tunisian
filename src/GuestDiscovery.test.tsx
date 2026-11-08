import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";
import App from "./App";
import { GuestDiscovery } from "./GuestDiscovery";
import type { JobOffer } from "./auth";

const job: JobOffer = {
  id: "job-1",
  title: "Développeur Python",
  description: "Rejoignez une équipe produit.",
  location: "Tunis",
  required_skills: ["Python"],
  employment_type: "CDI",
  salary_min: 1800,
  salary_max: 2400,
  created_at: "2026-01-01T00:00:00Z",
};

function mockPublicAPI(jobs: JobOffer[] = []) {
  const fetchMock = vi.fn().mockImplementation(async (input: string) => {
    const url = String(input);
    let payload: unknown = { items: [], total: 0, limit: 6, offset: 0 };
    if (url.includes("/public/jobs/job-1")) {
      payload = job;
    } else if (url.includes("/public/jobs?")) {
      payload = { items: jobs, total: jobs.length, limit: 20, offset: 0 };
    }
    return { ok: true, status: 200, json: async () => payload };
  });
  vi.stubGlobal("fetch", fetchMock);
  return fetchMock;
}

describe("guest discovery", () => {
  beforeEach(() => {
    vi.unstubAllGlobals();
    sessionStorage.clear();
    window.history.replaceState(null, "", "/");
  });

  it("switches the selected results tab without leaving discovery", async () => {
    const fetchMock = mockPublicAPI([job]);
    render(<GuestDiscovery onApply={vi.fn()} onRequestService={vi.fn()} />);

    expect(await screen.findByText("Développeur Python")).toBeVisible();
    const requestCount = fetchMock.mock.calls.length;
    const professionalsTab = screen.getByRole("tab", { name: /Professionnels/ });
    fireEvent.click(professionalsTab);

    expect(professionalsTab).toHaveAttribute("aria-selected", "true");
    expect(screen.getByRole("heading", { name: "Professionnels" })).toBeVisible();
    expect(screen.queryByRole("heading", { name: "Ravi·e de vous revoir" })).toBeNull();
    expect(fetchMock).toHaveBeenCalledTimes(requestCount);
  });

  it("shows a helpful empty state when all categories have no results", async () => {
    mockPublicAPI();
    render(<GuestDiscovery onApply={vi.fn()} onRequestService={vi.fn()} />);

    expect(await screen.findByRole("heading", { name: "Aucun résultat pour cette recherche" })).toBeVisible();
    expect(screen.getByText(/autre mot-clé, une autre ville ou une autre catégorie/i)).toBeVisible();
  });

  it("routes an apply action to the auth page and remembers the offer", async () => {
    mockPublicAPI([job]);
    render(<App />);

    fireEvent.click(await screen.findByRole("button", { name: "Voir l’offre" }));
    fireEvent.click(await screen.findByRole("button", { name: "Se connecter pour postuler" }));

    expect(await screen.findByRole("heading", { name: "Ravi·e de vous revoir" })).toBeVisible();
    expect(screen.getByText("Connectez-vous pour postuler à « Développeur Python »")).toBeVisible();
    await waitFor(() => expect(window.location.hash).toBe("#guest-auth"));
    expect(screen.queryByRole("heading", { name: "Tout découvrir" })).toBeNull();
  });
});
