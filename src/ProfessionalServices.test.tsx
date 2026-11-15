import { fireEvent, render, screen, waitFor, within } from "@testing-library/react";
import { afterEach, describe, expect, it, vi } from "vitest";
import { ProfessionalServicesPage } from "./ProfessionalServices";

const profile = {
  user_id: "candidate-1",
  public_id: "public-candidate",
  display_name: "Candidate",
  headline: "Designer",
  introduction: "",
  photo_url: null,
  location: null,
  languages: [],
  skills: [],
  years_experience: null,
  visibility: "private",
  available: true,
  accepting_requests: true,
  availability: {},
  service_area: [],
  portfolio_items: [{ title: "Work sample", url: "https://example.test/work", description: "A sample project." }],
  created_at: "2026-01-01T00:00:00Z",
  updated_at: "2026-01-01T00:00:00Z",
};

function jsonResponse(payload: unknown, status = 200) {
  return { ok: status < 400, status, json: async () => payload };
}

afterEach(() => {
  vi.unstubAllGlobals();
});

describe("professional services workspace", () => {
  it("preserves portfolio details and creates a service with its portfolio entries", async () => {
    const fetchMock = vi.fn().mockImplementation(async (input: string, init?: RequestInit) => {
      if (input.endsWith("/me/professional-profile") && init?.method === "PUT") {
        expect(JSON.parse(String(init.body)).portfolio_items).toEqual(profile.portfolio_items);
        return jsonResponse(profile);
      }
      if (input.endsWith("/me/professional-profile")) return jsonResponse(profile);
      if (input.endsWith("/me/services") && init?.method === "POST") {
        const request = JSON.parse(String(init.body));
        expect(request.portfolio_items).toEqual([{
          title: "Service sample",
          url: "https://example.test/service",
          description: "A service sample.",
        }]);
        return jsonResponse({
          ...request,
          id: "service-1",
          owner_user_id: "candidate-1",
          status: "draft",
          created_at: "2026-01-01T00:00:00Z",
          updated_at: "2026-01-01T00:00:00Z",
        }, 201);
      }
      if (input.endsWith("/me/services")) return jsonResponse([]);
      throw new Error(`Unexpected API request: ${input}`);
    });
    vi.stubGlobal("fetch", fetchMock);
    render(<ProfessionalServicesPage token="token" />);

    expect(await screen.findByDisplayValue("Work sample")).toBeVisible();
    expect(screen.getByDisplayValue("https://example.test/work")).toBeVisible();
    fireEvent.click(screen.getByRole("button", { name: "Enregistrer le profil" }));
    await waitFor(() => {
      expect(fetchMock).toHaveBeenCalledWith(
        expect.stringContaining("/me/professional-profile"),
        expect.objectContaining({ method: "PUT" }),
      );
    });

    fireEvent.click(screen.getByRole("button", { name: "Créer un service" }));
    const dialog = await screen.findByRole("dialog");
    fireEvent.change(within(dialog).getByLabelText("Nom du service"), { target: { value: "Design review" } });
    fireEvent.change(within(dialog).getByLabelText("Catégorie"), { target: { value: "Design" } });
    fireEvent.change(within(dialog).getByLabelText("Description"), { target: { value: "Review and feedback for a design." } });
    fireEvent.click(within(dialog).getByRole("button", { name: "Ajouter un projet" }));
    fireEvent.change(within(dialog).getByLabelText("Nom du projet"), { target: { value: "Service sample" } });
    fireEvent.change(within(dialog).getByLabelText("Lien"), { target: { value: "https://example.test/service" } });
    fireEvent.change(within(dialog).getAllByLabelText("Description")[1], { target: { value: "A service sample." } });
    fireEvent.click(within(dialog).getByRole("button", { name: "Créer le brouillon" }));

    expect(await screen.findByText("Service créé comme brouillon.")).toBeVisible();
    expect(await screen.findByText("Design review")).toBeVisible();
  });

  it("loads accepted AI suggestions into editable fields without saving them", async () => {
    const fetchMock = vi.fn().mockImplementation(async (input: string, init?: RequestInit) => {
      if (input.endsWith("/me/professional-profile")) return jsonResponse(profile);
      if (input.endsWith("/me/services") && init?.method === "POST") {
        throw new Error("A service suggestion must not be saved before confirmation.");
      }
      if (input.endsWith("/me/services")) return jsonResponse([]);
      throw new Error(`Unexpected API request: ${input}`);
    });
    vi.stubGlobal("fetch", fetchMock);
    render(<ProfessionalServicesPage
      token="token"
      assistantDraftEvents={[
        { kind: "profile", field: "introduction", value: "Je crée des identités visuelles." },
        { kind: "profile", field: "languages", value: ["français", "arabe"] },
        {
          kind: "service",
          suggestion: {
            title: "Création de logo",
            category: "Design",
            description: "Conception d'une identité visuelle.",
            skills: ["Illustrator"],
            service_mode: "remote",
            price_type: "quote",
          },
        },
      ]}
    />);

    const dialog = await screen.findByRole("dialog");
    expect(within(dialog).getByLabelText("Nom du service")).toHaveValue("Création de logo");
    expect(within(dialog).getByLabelText("Catégorie")).toHaveValue("Design");
    expect(screen.getByLabelText("Présentation")).toHaveValue("Je crée des identités visuelles.");
    expect(screen.getByText("français")).toBeVisible();
    expect(fetchMock).not.toHaveBeenCalledWith(
      expect.stringContaining("/me/services"),
      expect.objectContaining({ method: "POST" }),
    );
  });

  it("saves only the chosen professional section and keeps other edits as a draft", async () => {
    const savedRequests: Array<Record<string, unknown>> = [];
    vi.stubGlobal("fetch", vi.fn().mockImplementation(async (input: string, init?: RequestInit) => {
      if (input.endsWith("/me/professional-profile") && init?.method === "PUT") {
        const request = JSON.parse(String(init.body)) as Record<string, unknown>;
        savedRequests.push(request);
        return jsonResponse({ ...profile, ...request });
      }
      if (input.endsWith("/me/professional-profile")) return jsonResponse(profile);
      if (input.endsWith("/me/services")) return jsonResponse([]);
      throw new Error(`Unexpected API request: ${input}`);
    }));
    render(<ProfessionalServicesPage token="token" />);

    await screen.findByDisplayValue("Designer");
    fireEvent.change(screen.getByLabelText("Présentation"), { target: { value: "A new introduction." } });
    fireEvent.click(screen.getByRole("button", { name: "Enregistrer le portfolio" }));

    await waitFor(() => expect(savedRequests).toHaveLength(1));
    expect(savedRequests[0]).toMatchObject({
      introduction: "",
      portfolio_items: profile.portfolio_items,
    });

    fireEvent.click(screen.getByRole("button", { name: "Enregistrer l’identité" }));
    await waitFor(() => expect(savedRequests).toHaveLength(2));
    expect(savedRequests[1]).toMatchObject({
      introduction: "A new introduction.",
      portfolio_items: profile.portfolio_items,
    });
  });
});
