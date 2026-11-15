import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { afterEach, describe, expect, it, vi } from "vitest";
import { CandidateProfilePage } from "./workspaces";

const profile = {
  user_id: "candidate-1",
  full_name: "Amira",
  phone: null,
  location: "Tunis",
  birth_year: null,
  governorate_code: null,
  municipality_code: null,
  street_address: null,
  education: null,
  experience: null,
  education_entries: [],
  experience_entries: [],
  professional_headline: null,
  employer_discoverable: false,
  skills: ["Excel"],
  updated_at: null,
};

function jsonResponse(payload: unknown) {
  return { ok: true, status: 200, json: async () => payload };
}

afterEach(() => {
  vi.unstubAllGlobals();
});

describe("candidate profile sections", () => {
  it("saves the selected section without submitting other profile fields", async () => {
    const updates: Record<string, unknown>[] = [];
    vi.stubGlobal("fetch", vi.fn().mockImplementation(async (input: string, init?: RequestInit) => {
      if (input.endsWith("/candidate/profile") && init?.method === "PUT") {
        const update = JSON.parse(String(init.body)) as Record<string, unknown>;
        updates.push(update);
        return jsonResponse({ ...profile, ...update });
      }
      if (input.endsWith("/candidate/profile")) return jsonResponse(profile);
      throw new Error(`Unexpected API request: ${input}`);
    }));
    render(<CandidateProfilePage token="token" />);

    await screen.findByLabelText("Nouvelle compétence");
    const skillInput = screen.getByLabelText("Nouvelle compétence");
    fireEvent.change(skillInput, { target: { value: "Python" } });
    fireEvent.keyDown(skillInput, { key: "Enter", code: "Enter" });
    fireEvent.click(screen.getByRole("button", { name: "Enregistrer les compétences" }));

    await waitFor(() => expect(updates).toHaveLength(1));
    expect(updates[0]).toEqual({ skills: ["Excel", "Python"] });
    expect(await screen.findByText("Les compétences ont été enregistrées.")).toBeVisible();
  });
});
