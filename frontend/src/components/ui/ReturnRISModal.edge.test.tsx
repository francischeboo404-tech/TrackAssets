import React from "react";
import { render, screen, waitFor, fireEvent } from "@testing-library/react";
import { vi, describe, it, beforeEach, expect } from "vitest";

import ReturnRISModal from "./ReturnRISModal";
import { ToastProvider } from "../../context/ToastContext";

// Mock requisition service functions (reuse shape from main test)
vi.mock("../../services/requisition", () => ({
  getRequisitions: vi.fn(),
  getRequisitionsPage: vi.fn(),
  getRequisition: vi.fn(),
  returnRequisition: vi.fn(),
}));

import { getRequisitionsPage } from "../../services/requisition";

describe("ReturnRISModal edge cases", () => {
  beforeEach(() => {
    vi.resetAllMocks();
  });

  it("debounces search input and only calls search after idle", async () => {
    // Use real timers and a small wait to let the debounce elapse.

    // First call: preload when modal opens
    (getRequisitionsPage as any).mockResolvedValueOnce({
      items: [],
      next_offset: 0,
      has_more: false,
    });
    // Second call: the debounced search
    (getRequisitionsPage as any).mockResolvedValueOnce({
      items: [],
      next_offset: 0,
      has_more: false,
    });

    render(
      <ToastProvider>
        <ReturnRISModal isOpen={true} onClose={() => {}} />
      </ToastProvider>,
    );

    // Wait for preload to complete and UI to settle
    await waitFor(() => expect(getRequisitionsPage).toHaveBeenCalledTimes(1));

    const input = screen.getByPlaceholderText("Search RIS number");

    // Type in parts quickly
    fireEvent.change(input, { target: { value: "R" } });
    fireEvent.change(input, { target: { value: "RI" } });
    fireEvent.change(input, { target: { value: "RIS-1" } });

    // Wait slightly longer than the component debounce (300ms)
    await new Promise((r) => setTimeout(r, 350));

    // Wait for the debounced search call
    await waitFor(() =>
      expect(getRequisitionsPage as any).toHaveBeenCalledTimes(2),
    );

    // Verify the debounced call included the final query
    const secondCallArgs = (getRequisitionsPage as any).mock.calls[1];
    expect(secondCallArgs[0]).toBe("RIS-1");
  }, 15000);

  it("triggers loadMore when sentinel intersects (infinite-scroll)", async () => {
    const preloadItems = [
      { id: 1, ris_number: "RIS-1", status: "issued" },
      { id: 2, ris_number: "RIS-2", status: "issued" },
    ];
    const moreItems = [{ id: 3, ris_number: "RIS-3", status: "issued" }];

    // Preload page: has_more true and next_offset set
    (getRequisitionsPage as any).mockResolvedValueOnce({
      items: preloadItems,
      next_offset: 2,
      has_more: true,
    });
    // loadMore page
    (getRequisitionsPage as any).mockResolvedValueOnce({
      items: moreItems,
      next_offset: 3,
      has_more: false,
    });

    // Stub IntersectionObserver so tests can trigger the callback on demand
    const createdObservers: any[] = [];
    class MockIntersectionObserver {
      cb: IntersectionObserverCallback;
      constructor(cb: IntersectionObserverCallback) {
        this.cb = cb;
        createdObservers.push(this);
      }
      observe() {}
      unobserve() {}
      disconnect() {}
    }
    const originalObserver = (globalThis as any).IntersectionObserver;
    vi.stubGlobal("IntersectionObserver", MockIntersectionObserver as any);

    render(
      <ToastProvider>
        <ReturnRISModal isOpen={true} onClose={() => {}} />
      </ToastProvider>,
    );

    // Wait for preload to complete and for the UI to render the initial RIS entries
    await waitFor(() => expect(screen.getByText("RIS-1")).toBeTruthy());

    // Ensure an observer instance was created
    expect(createdObservers.length).toBeGreaterThan(0);

    // Simulate sentinel entering the viewport (after UI state settled)
    createdObservers[0].cb(
      [{ isIntersecting: true, target: {} } as any],
      createdObservers[0] as any,
    );

    // Wait for loadMore to call the API again
    await waitFor(() => expect(getRequisitionsPage).toHaveBeenCalledTimes(2));

    const secondCall = (getRequisitionsPage as any).mock.calls[1];
    // startOffset should equal the preload next_offset we provided (2)
    expect(secondCall[2]).toBe(2);

    // restore global
    (globalThis as any).IntersectionObserver = originalObserver;
  }, 15000);
});
