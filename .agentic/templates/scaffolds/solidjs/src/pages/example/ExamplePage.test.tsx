import { MemoryRouter, Route } from "@solidjs/router"
import { fireEvent, render, screen, waitFor } from "@solidjs/testing-library"

import { i18next } from "@/i18n"
import ExamplePage from "./ExamplePage"

vi.mock("@/api/client", () => ({
  apiClient: {
    GET: vi.fn().mockResolvedValue({
      data: { items: [{ id: "1", label: "Alfa", created_at: "2026-01-01T00:00:00Z" }] },
      error: undefined,
    }),
  },
}))

beforeAll(async () => {
  await i18next.changeLanguage("en")
})

function renderPage() {
  return render(() => (
    <MemoryRouter>
      <Route path="/" component={ExamplePage} />
    </MemoryRouter>
  ))
}

describe("ExamplePage", () => {
  it("renders items from the API", async () => {
    renderPage()
    expect(await screen.findByText("Alfa")).toBeInTheDocument()
  })

  it("opens the dialog on trigger click (Kobalte headless behavior)", async () => {
    renderPage()
    fireEvent.click(screen.getByText("New"))
    await waitFor(() => expect(screen.getByText("New example")).toBeInTheDocument())
  })
})
