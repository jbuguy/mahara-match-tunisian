import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";
import { EmployerPlanningWorkspace } from "./EmployerPlanningWorkspace";
import {
  createEmployerPlanningSession,
  fetchEmployerPlanningSessions,
  type EmployerPlanningSession,
} from "./auth";

vi.mock("./auth", () => ({
  createEmployerPlanningSession: vi.fn(),
  deleteEmployerPlanningSession: vi.fn(),
  fetchEmployerPlanningSessions: vi.fn(),
  updateEmployerPlanningSession: vi.fn(),
}));

const session: EmployerPlanningSession = {
  id: "planning-1",
  organisation_id: "organisation-1",
  created_by_user_id: "employer-1",
  title: "Équipe marketing",
  description: "Développer la présence numérique.",
  project_type: "department",
  status: "draft",
  project_summary: {},
  recommendation_count: 0,
  job_draft_count: 0,
  created_at: "2026-11-07T10:00:00Z",
  updated_at: "2026-11-07T10:00:00Z",
};

describe("employer planning workspace", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    vi.mocked(fetchEmployerPlanningSessions).mockResolvedValue([]);
  });

  it("creates a session and opens the saved project", async () => {
    vi.mocked(createEmployerPlanningSession).mockResolvedValue(session);
    vi.mocked(fetchEmployerPlanningSessions)
      .mockResolvedValueOnce([])
      .mockResolvedValueOnce([session]);

    render(<EmployerPlanningWorkspace token="employer-token"/>);
    fireEvent.change(await screen.findByPlaceholderText("Ex. Lancement d’une équipe marketing"), {
      target: { value: session.title },
    });
    fireEvent.click(screen.getByRole("button", { name: /créer la planification/i }));

    await waitFor(() => expect(createEmployerPlanningSession).toHaveBeenCalledWith(
      "employer-token",
      { title: session.title, description: null, project_type: "other" },
    ));
    expect(await screen.findByRole("heading", { name: session.title })).toBeVisible();
    expect(screen.getByText(/conversation avec l’assistant/i)).toBeVisible();
  });
});
