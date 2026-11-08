import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";
import { useState } from "react";
import { LocationSelect } from "./LocationSelect";

function LocationHarness() {
  const [value, setValue] = useState({ governorateCode: "", municipalityCode: "", streetAddress: "" });
  return (
    <LocationSelect
      {...value}
      onChange={(next) => setValue(next)}
    />
  );
}

describe("LocationSelect", () => {
  beforeEach(() => {
    vi.restoreAllMocks();
    vi.stubGlobal(
      "fetch",
      vi.fn(async (input: RequestInfo | URL) => {
        const url = String(input);
        if (url.endsWith("/locations/governorates")) {
          return new Response(JSON.stringify([
            { code: "tunis", name_fr: "Tunis", name_ar: "تونس", latitude: 36.8, longitude: 10.2 },
            { code: "sfax", name_fr: "Sfax", name_ar: "صفاقس", latitude: 34.7, longitude: 10.3 },
          ]));
        }
        return new Response(JSON.stringify([
          { code: "tunis-centre-ville", governorate_code: "tunis", name_fr: "Centre-Ville", name_ar: "وسط المدينة", sort_order: 0 },
          { code: "tunis-autre", governorate_code: "tunis", name_fr: "Autre / zone rurale", name_ar: "", sort_order: 999 },
        ]));
      }),
    );
  });

  it("enables municipalities after a governorate is selected and resets them when changed", async () => {
    render(<LocationHarness />);

    const municipality = screen.getByRole("combobox", { name: "Municipalité" });
    expect(municipality).toBeDisabled();

    const governorate = screen.getByRole("combobox", { name: "Gouvernorat" });
    fireEvent.change(governorate, { target: { value: "Tun" } });
    fireEvent.click(await screen.findByRole("option", { name: /Tunis/ }));

    await waitFor(() => expect(municipality).not.toBeDisabled());
    fireEvent.change(municipality, { target: { value: "Centre" } });
    fireEvent.click(await screen.findByRole("option", { name: /Centre-Ville/ }));
    expect(municipality).toHaveValue("Centre-Ville — وسط المدينة");

    fireEvent.change(governorate, { target: { value: "Sfa" } });
    fireEvent.click(await screen.findByRole("option", { name: /Sfax/ }));
    await waitFor(() => expect(municipality).toHaveValue(""));
  });
});
