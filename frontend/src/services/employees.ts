import api from './api';

export const listEmployees = async (params = {}) => {
  const res = await api.get('/employees', { params });
  return res.data;
};

export const getEmployee = async (id: number) => {
  const res = await api.get(`/employees/${id}`);
  return res.data;
};

export const createEmployee = async (payload: any) => {
  const res = await api.post('/employees', payload);
  return res.data;
};

export const updateEmployee = async (id: number, payload: any) => {
  const res = await api.put(`/employees/${id}`, payload);
  return res.data;
};

export const deleteEmployee = async (id: number) => {
  const res = await api.delete(`/employees/${id}`);
  return res.data;
};
