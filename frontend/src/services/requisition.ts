import api from './api';

export type ReturnItem = { item_id: number; quantity: number };

export async function returnRequisition(risId: number, items?: ReturnItem[]) {
  const payload = items ? { items } : {};
  const resp = await api.post(`/requisition/issue-slips/${risId}/return`, payload);
  return resp.data;
}

export async function getRequisition(risId: number) {
  const resp = await api.get(`/requisition/issue-slips/${risId}`);
  return resp.data;
}

export async function getRequisitions(q?: string, limit = 10) {
  const params: Record<string, any> = {};
  if (q) params.q = q;
  if (limit) params.limit = limit;
  const resp = await api.get(`/requisition/issue-slips`, { params });
  // backend returns { items: [...] }
  return resp.data?.items || [];
}

export async function getRequisitionsPage(q?: string, limit = 10, offset = 0) {
  const params: Record<string, any> = {};
  if (q) params.q = q;
  if (limit) params.limit = limit;
  if (offset) params.offset = offset;
  const resp = await api.get(`/requisition/issue-slips`, { params });
  // return full response (items + pagination metadata)
  return resp.data || { items: [], next_offset: offset, has_more: false };
}
