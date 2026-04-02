import { render, screen } from "@testing-library/react";
import { MemoryRouter } from "react-router-dom";
import { describe, expect, it } from "vitest";

import App, { APP_TAGLINE, APP_TITLE } from "../App";
import { CUSTOMER_CREATE_ROUTE, HOME_ROUTE } from "../lib/routes";

describe("frontend scaffold", () => {
  it("renders the app shell content", () => {
    render(
      <MemoryRouter initialEntries={[HOME_ROUTE]}>
        <App />
      </MemoryRouter>,
    );

    expect(screen.getByRole("heading", { name: APP_TITLE })).toBeTruthy();
    expect(screen.getByText(APP_TAGLINE)).toBeTruthy();
  });

  it("renders the create customer route directly", () => {
    render(
      <MemoryRouter initialEntries={[CUSTOMER_CREATE_ROUTE]}>
        <App />
      </MemoryRouter>,
    );

    expect(screen.getByRole("heading", { name: "Create Customer" })).toBeTruthy();
  });
});