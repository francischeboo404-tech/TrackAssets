import type { ReactNode } from 'react';
import {
  Bar,
  BarChart,
  CartesianGrid,
  Cell,
  Legend,
  Line,
  LineChart,
  Pie,
  PieChart,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from 'recharts';
import type {
  AssetsReportData,
  InventoryReportData,
  TrackingReportData,
} from '../../types/reports';
import { cn } from '../../lib/utils';

const ChartShell = ({
  title,
  subtitle,
  children,
  className,
}: {
  title: string;
  subtitle?: string;
  children: ReactNode;
  className?: string;
}) => (
  <div
    className={cn(
      'enterprise-card p-6 bg-white border-none shadow-xl shadow-slate-200/50',
      className,
    )}
  >
    <h3 className="text-lg font-bold text-slate-900">{title}</h3>
    {subtitle && (
      <p className="text-xs text-slate-400 font-bold uppercase tracking-widest mt-1">
        {subtitle}
      </p>
    )}
    <div className="mt-4 h-72">{children}</div>
  </div>
);

const EmptyChart = ({ message }: { message: string }) => (
  <div className="h-full flex items-center justify-center text-sm text-slate-400 font-medium">
    {message}
  </div>
);

export const AssetReportCharts = ({
  data,
  loading,
}: {
  data?: AssetsReportData;
  loading?: boolean;
}) => {
  if (loading) {
    return <div className="h-64 animate-pulse bg-slate-100 rounded-2xl" />;
  }
  if (!data) {
    return <EmptyChart message="Asset report unavailable" />;
  }

  const pieData = data.by_status.filter((s) => s.count > 0);

  return (
    <div className="grid grid-cols-1 xl:grid-cols-2 gap-6">
      <ChartShell title="Asset Status Distribution" subtitle="Server-computed counts">
        {pieData.length ? (
          <ResponsiveContainer width="100%" height="100%">
            <PieChart>
              <Pie
                data={pieData}
                dataKey="count"
                nameKey="label"
                cx="50%"
                cy="50%"
                innerRadius={50}
                outerRadius={90}
                paddingAngle={2}
              >
                {pieData.map((entry) => (
                  <Cell key={entry.code} fill={entry.color} />
                ))}
              </Pie>
              <Tooltip />
              <Legend />
            </PieChart>
          </ResponsiveContainer>
        ) : (
          <EmptyChart message="No assets in register" />
        )}
      </ChartShell>

      <ChartShell title="Assets by Department" subtitle="Grouped SQL aggregation">
        {data.by_department.length ? (
          <ResponsiveContainer width="100%" height="100%">
            <BarChart data={data.by_department} layout="vertical" margin={{ left: 8 }}>
              <CartesianGrid strokeDasharray="3 3" stroke="#e2e8f0" />
              <XAxis type="number" />
              <YAxis type="category" dataKey="department" width={100} tick={{ fontSize: 11 }} />
              <Tooltip />
              <Bar dataKey="count" fill="#3b82f6" radius={[0, 4, 4, 0]} />
            </BarChart>
          </ResponsiveContainer>
        ) : (
          <EmptyChart message="No department data" />
        )}
      </ChartShell>

      <ChartShell
        title="Lifecycle Transitions"
        subtitle={`Last ${data.period_days} days`}
        className="xl:col-span-2"
      >
        {data.lifecycle_over_time.some((d) => Number(d.total) > 0) ? (
          <ResponsiveContainer width="100%" height="100%">
            <LineChart data={data.lifecycle_over_time}>
              <CartesianGrid strokeDasharray="3 3" stroke="#e2e8f0" />
              <XAxis dataKey="date" tick={{ fontSize: 10 }} />
              <YAxis allowDecimals={false} />
              <Tooltip />
              <Legend />
              <Line type="monotone" dataKey="Approved" stroke="#3b82f6" dot={false} />
              <Line type="monotone" dataKey="In Use" stroke="#10b981" dot={false} />
              <Line type="monotone" dataKey="Maintenance" stroke="#f59e0b" dot={false} />
              <Line type="monotone" dataKey="Disposed" stroke="#f43f5e" dot={false} />
            </LineChart>
          </ResponsiveContainer>
        ) : (
          <EmptyChart message="No lifecycle transitions in period" />
        )}
      </ChartShell>
    </div>
  );
};

export const InventoryReportCharts = ({
  data,
  loading,
}: {
  data?: InventoryReportData;
  loading?: boolean;
}) => {
  if (loading) {
    return <div className="h-64 animate-pulse bg-slate-100 rounded-2xl" />;
  }
  if (!data) {
    return <EmptyChart message="Inventory report unavailable" />;
  }

  return (
    <div className="grid grid-cols-1 xl:grid-cols-2 gap-6">
      <ChartShell title="Stock Levels (Top SKUs)" subtitle="Quantity on hand">
        {data.stock_levels_chart.length ? (
          <ResponsiveContainer width="100%" height="100%">
            <BarChart data={data.stock_levels_chart}>
              <CartesianGrid strokeDasharray="3 3" stroke="#e2e8f0" />
              <XAxis dataKey="name" tick={{ fontSize: 10 }} />
              <YAxis />
              <Tooltip />
              <Bar dataKey="quantity" fill="#10b981" radius={[4, 4, 0, 0]} />
            </BarChart>
          </ResponsiveContainer>
        ) : (
          <EmptyChart message="No active inventory SKUs" />
        )}
      </ChartShell>

      <ChartShell title="Inflow vs Outflow" subtitle="Sum of movement quantities">
        <ResponsiveContainer width="100%" height="100%">
          <LineChart data={data.movement_over_time}>
            <CartesianGrid strokeDasharray="3 3" stroke="#e2e8f0" />
            <XAxis dataKey="date" tick={{ fontSize: 10 }} />
            <YAxis />
            <Tooltip />
            <Legend />
            <Line type="monotone" dataKey="inflow" name="Inflow" stroke="#3b82f6" dot={false} />
            <Line type="monotone" dataKey="outflow" name="Outflow" stroke="#f43f5e" dot={false} />
          </LineChart>
        </ResponsiveContainer>
      </ChartShell>

      <ChartShell
        title="Consumption Frequency"
        subtitle="Heat-style bar (OUT movements)"
        className="xl:col-span-2"
      >
        {data.usage_frequency.length ? (
          <ResponsiveContainer width="100%" height="100%">
            <BarChart data={data.usage_frequency}>
              <CartesianGrid strokeDasharray="3 3" stroke="#e2e8f0" />
              <XAxis dataKey="sku" tick={{ fontSize: 10 }} />
              <YAxis />
              <Tooltip />
              <Bar dataKey="frequency" name="Units consumed">
                {data.usage_frequency.map((_, i) => (
                  <Cell
                    key={i}
                    fill={`hsl(${160 + i * 12}, 70%, ${45 + i * 4}%)`}
                  />
                ))}
              </Bar>
            </BarChart>
          </ResponsiveContainer>
        ) : (
          <EmptyChart message="No outbound consumption in period" />
        )}
      </ChartShell>
    </div>
  );
};

export const TrackingReportCharts = ({
  data,
  loading,
}: {
  data?: TrackingReportData;
  loading?: boolean;
}) => {
  if (loading) {
    return <div className="h-64 animate-pulse bg-slate-100 rounded-2xl" />;
  }
  if (!data) {
    return <EmptyChart message="Tracking report unavailable" />;
  }

  const roleStack = data.actions_per_role.slice(0, 8);

  return (
    <div className="grid grid-cols-1 xl:grid-cols-2 gap-6">
      <ChartShell title="Scan / Action Frequency" subtitle="Daily activity">
        <ResponsiveContainer width="100%" height="100%">
          <LineChart data={data.activity_frequency}>
            <CartesianGrid strokeDasharray="3 3" stroke="#e2e8f0" />
            <XAxis dataKey="date" tick={{ fontSize: 10 }} />
            <YAxis allowDecimals={false} />
            <Tooltip />
            <Line type="monotone" dataKey="scans" stroke="#6366f1" strokeWidth={2} dot={false} />
          </LineChart>
        </ResponsiveContainer>
      </ChartShell>

      <ChartShell title="Actions by Role" subtitle="Audit log aggregation">
        {roleStack.length ? (
          <ResponsiveContainer width="100%" height="100%">
            <BarChart data={roleStack}>
              <CartesianGrid strokeDasharray="3 3" stroke="#e2e8f0" />
              <XAxis dataKey="role" tick={{ fontSize: 10 }} />
              <YAxis allowDecimals={false} />
              <Tooltip />
              <Bar dataKey="count" fill="#8b5cf6" radius={[4, 4, 0, 0]} />
            </BarChart>
          </ResponsiveContainer>
        ) : (
          <EmptyChart message="No role activity in period" />
        )}
      </ChartShell>

      {data.movement_timeline && data.movement_timeline.length > 0 && (
        <div className="xl:col-span-2 enterprise-card p-6 bg-white shadow-xl shadow-slate-200/50">
          <h3 className="text-lg font-bold text-slate-900 mb-4">Movement Timeline</h3>
          <div className="space-y-3 max-h-80 overflow-y-auto">
            {data.movement_timeline.map((ev) => (
              <div
                key={ev.id}
                className="flex gap-4 items-start border-l-2 border-brand-primary pl-4 py-2"
              >
                <div className="text-[10px] font-black text-slate-400 uppercase">
                  {ev.timestamp ? new Date(ev.timestamp).toLocaleString() : '—'}
                </div>
                <div>
                  <p className="text-sm font-bold text-slate-800">
                    {ev.action_type} · {ev.item_type} #{ev.item_id}
                  </p>
                  <p className="text-xs text-slate-500">
                    {ev.user ?? 'System'} {ev.role ? `(${ev.role})` : ''}
                  </p>
                </div>
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  );
};
