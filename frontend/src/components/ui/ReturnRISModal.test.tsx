import React from "react";
import { render, screen, waitFor, fireEvent } from "@testing-library/react";
import { vi, describe, it, beforeEach, expect } from "vitest";

import ReturnRISModal from "./ReturnRISModal";
import { ToastProvider } from "../../context/ToastContext";

// Mock the requisition service functions
vi.mock("../../services/requisition", () => ({
  getRequisitions: vi.fn(),
  getRequisitionsPage: vi.fn(),
  getRequisition: vi.fn(),
  returnRequisition: vi.fn(),
}));

import {
  getRequisitions,
  getRequisitionsPage,
  getRequisition,
  returnRequisition,
} from "../../services/requisition";

describe("ReturnRISModal", () => {
  beforeEach(() => {
    vi.resetAllMocks();
  });

  it("preloads recent RIS and allows loading a RIS and returning items", async () => {
    // Arrange: mock recent list
    (getRequisitionsPage as any).mockResolvedValueOnce({
      items: [
        { id: 1, ris_number: "RIS-1", status: "issued" },
        { id: 2, ris_number: "RIS-2", status: "partially_issued" },
      ],
      next_offset: 2,
      has_more: false,
    });

    // When loading a RIS, return items
    (getRequisition as any).mockResolvedValueOnce({
      ris_id: 1,
      ris_number: "RIS-1",
      items: [
        {
          id: 10,
          item_id: 100,
          name: "Item A",
          sku: "A-100",
          quantity_requested: 5,
          quantity_issued: 2,
        },
      ],
    });

    (returnRequisition as any).mockResolvedValueOnce({ ris_id: 1 });

    const onClose = vi.fn();
    const onReturned = vi.fn();

    // Act
    render(
      <ToastProvider>
        <ReturnRISModal
          isOpen={true}
          onClose={onClose}
          onReturned={onReturned}
        />
      </ToastProvider>,
    );

    // Assert: recent list is shown
    expect(await screen.findByText("RIS-1")).toBeTruthy();

    // Click Load on the first RIS entry
    const loadButtons = screen.getAllByText("Load");
    fireEvent.click(loadButtons[0]);

    // Wait for the table row with item name
    expect(await screen.findByText("Item A")).toBeTruthy();

    // Enter return qty and submit
    const input = screen.getByRole("spinbutton");
    fireEvent.change(input, { target: { value: "2" } });

    const returnBtn = screen.getByText("Return Selected");
    fireEvent.click(returnBtn);

    await waitFor(() => {
      expect(returnRequisition).toHaveBeenCalledWith(1, [
        { item_id: 100, quantity: 2 },
      ]);
    });

    expect(onReturned).toHaveBeenCalledWith(1);
    expect(onClose).toHaveBeenCalled();
  });
});
