import React from 'react';
import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import { vi, describe, it, beforeEach, expect } from 'vitest';
import { ToastProvider } from '../../context/ToastContext';
import { TransferRequestModal } from './TransferRequestModal';

const mockRequestTransfer = vi.fn();

vi.mock('../../hooks/useDepartments', () => ({
  useDepartments: vi.fn(() => ({
    data: [
      { id: 1, name: 'Sales', code: 'SALES', warehouse_id: 5 },
      { id: 2, name: 'Support', code: 'SUP', warehouse_id: null },
    ],
  })),
}));

vi.mock('../../hooks/useWarehouses', () => ({
  useWarehouses: vi.fn(() => ({ data: [{ id: 5, name: 'Main Warehouse' }, { id: 7, name: 'Other Warehouse' }] })),
  useWarehouseDetails: vi.fn(() => ({ data: [] })),
}));

vi.mock('../../hooks/useTransfers', () => ({
  useRequestTransfer: vi.fn(() => ({
    mutate: mockRequestTransfer,
    isPending: false,
  })),
}));

describe('TransferRequestModal warehouse alignment', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it('shows inline department warehouse message and auto-populates payload', async () => {
    render(
      <ToastProvider>
        <TransferRequestModal
          isOpen={true}
          onClose={() => {}}
          asset={{
            id: 42,
            department_id: 2,
            department_name: 'Support',
            asset_code: 'A123',
            name: 'Laptop',
            status: 'unassigned',
            location: 'Office',
          }}
          itemType="asset"
        />
      </ToastProvider>
    );

    const destinationSelect = screen.getByLabelText('Destination Department');
    fireEvent.change(destinationSelect, { target: { value: '1' } });

    const alignedMessages = await screen.findAllByText('Destination department is linked to warehouse 5. This warehouse will be used for the transfer.');
    expect(alignedMessages.length).toBeGreaterThan(1);

    const warehouseSelect = screen.getByLabelText(/Destination Warehouse/i);
    expect(warehouseSelect).toBeDisabled();

    const submitButton = screen.getByRole('button', { name: /Submit Request/i });
    fireEvent.click(submitButton);

    await waitFor(() => {
      expect(mockRequestTransfer).toHaveBeenCalledTimes(1);
      expect(mockRequestTransfer).toHaveBeenCalledWith(
        expect.objectContaining({
          transfer_type: 'department_to_department',
          new_department_id: 1,
          to_warehouse_id: 5,
        }),
        expect.any(Object),
      );
    });
  });

  it('shows validation error when a different warehouse was selected before choosing the destination department', async () => {
    render(
      <ToastProvider>
        <TransferRequestModal
          isOpen={true}
          onClose={() => {}}
          asset={{
            id: 42,
            department_id: 2,
            department_name: 'Support',
            asset_code: 'A123',
            name: 'Laptop',
            status: 'unassigned',
            location: 'Office',
          }}
          itemType="asset"
        />
      </ToastProvider>
    );

    const warehouseSelect = screen.getByLabelText(/Destination Warehouse/i);
    fireEvent.change(warehouseSelect, { target: { value: '7' } });

    const destinationSelect = screen.getByLabelText('Destination Department');
    fireEvent.change(destinationSelect, { target: { value: '1' } });

    const mismatchMessages = await screen.findAllByText('Selected destination department is linked to a different warehouse. Leave warehouse empty to use the department warehouse or choose the correct warehouse.');
    expect(mismatchMessages.length).toBeGreaterThan(1);

    const submitButton = screen.getByRole('button', { name: /Submit Request/i });
    fireEvent.click(submitButton);

    await waitFor(() => {
      expect(mockRequestTransfer).not.toHaveBeenCalled();
    });
  });
});
