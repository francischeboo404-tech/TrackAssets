import React from 'react';
import { useParams, Link } from 'react-router-dom';
import { useQuery } from '@tanstack/react-query';
import { getEmployee } from '../services/employees';

const EmployeeDetails: React.FC = () => {
  const { id } = useParams<{ id: string }>();
  const empId = Number(id || 0);
  const { data, isLoading, error } = useQuery({ queryKey: ['employee', empId], queryFn: () => getEmployee(empId), enabled: empId > 0 as boolean });

  if (!empId) return <div className="p-4">Invalid employee id</div>;
  if (isLoading) return <div className="p-4">Loading...</div>;
  if (error) return <div className="p-4">Failed to load employee</div>;

  const emp: any = data || {};

  return (
    <div className="p-4">
      <Link to="/employees" className="btn btn-sm mb-4 inline-block">Back to Employees</Link>
      <div className="bg-white p-6 rounded shadow">
        <h2 className="text-xl font-semibold mb-2">{emp.name}</h2>
        <div className="text-sm text-slate-600 mb-4">Code: {emp.code}</div>
        <div className="grid grid-cols-2 gap-3">
          <div>
            <div className="text-xs text-slate-500">Email</div>
            <div>{emp.email || '-'}</div>
          </div>
          <div>
            <div className="text-xs text-slate-500">Phone</div>
            <div>{emp.phone || '-'}</div>
          </div>
          <div>
            <div className="text-xs text-slate-500">Department</div>
            <div>{emp.department_name || emp.department_id || '-'}</div>
          </div>
          <div>
            <div className="text-xs text-slate-500">Date Joined</div>
            <div>{emp.date_of_join || '-'}</div>
          </div>
        </div>
      </div>
    </div>
  );
};

export default EmployeeDetails;
