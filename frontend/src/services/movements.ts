import api from './api';

export const issueItem = async (payload: any) => {
  const res = await api.post('/movements/issue', payload);
  return res.data;
};

export const returnItem = async (payload: any) => {
  const res = await api.post('/movements/return', payload);
  return res.data;
};

export const listIssues = async (params = {}) => {
  const res = await api.get('/movements/issues', { params });
  return res.data;
};

export const listReturns = async (params = {}) => {
  const res = await api.get('/movements/returns', { params });
  return res.data;
};

export const listMovementHistory = async (params = {}) => {
  const res = await api.get('/movements/history', { params });
  return res.data;
};
