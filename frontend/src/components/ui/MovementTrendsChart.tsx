import React from 'react';
import {
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
  Legend,
  AreaChart,
  Area
} from 'recharts';

interface MovementTrendsChartProps {
  data: Record<string, { IN: number; OUT: number }>;
  loading?: boolean;
}

export const MovementTrendsChart: React.FC<MovementTrendsChartProps> = ({ data, loading }) => {
  if (loading) {
    return (
      <div className="w-full h-full flex items-center justify-center">
        <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-indigo-600"></div>
      </div>
    );
  }

  // Transform object to sorted array for Recharts
  const chartData = Object.entries(data || {})
    .filter(([day]) => !isNaN(new Date(day).getTime())) // Filter out non-date keys (like 'success', 'status_code')
    .sort(([dayA], [dayB]) => new Date(dayA).getTime() - new Date(dayB).getTime())
    .map(([day, values]) => ({
      day: new Date(day).toLocaleDateString(undefined, { month: 'short', day: 'numeric' }),
      ...values
    }));

  return (
    <div className="w-full h-[350px]">
      <ResponsiveContainer width="100%" height="100%">
        <AreaChart
          data={chartData}
          margin={{ top: 10, right: 10, left: 0, bottom: 0 }}
        >
          <defs>
            <linearGradient id="colorIn" x1="0" y1="0" x2="0" y2="1">
              <stop offset="5%" stopColor="#2563eb" stopOpacity={0.2}/>
              <stop offset="95%" stopColor="#2563eb" stopOpacity={0}/>
            </linearGradient>
            <linearGradient id="colorOut" x1="0" y1="0" x2="0" y2="1">
              <stop offset="5%" stopColor="#38bdf8" stopOpacity={0.2}/>
              <stop offset="95%" stopColor="#38bdf8" stopOpacity={0}/>
            </linearGradient>
          </defs>
          <CartesianGrid strokeDasharray="3 3" vertical={false} stroke="#f1f5f9" />
          <XAxis 
            dataKey="day" 
            axisLine={false} 
            tickLine={false} 
            tick={{ fill: '#94a3b8', fontSize: 10, fontWeight: 600 }}
            dy={10}
          />
          <YAxis 
            axisLine={false} 
            tickLine={false} 
            tick={{ fill: '#94a3b8', fontSize: 10, fontWeight: 600 }}
          />
          <Tooltip 
            contentStyle={{ 
              borderRadius: '12px', 
              border: 'none', 
              boxShadow: '0 10px 15px -3px rgb(0 0 0 / 0.1)',
              fontSize: '12px',
              fontWeight: 600
            }}
          />
          <Legend 
            verticalAlign="top" 
            align="right" 
            iconType="circle"
            wrapperStyle={{ paddingBottom: '20px', fontSize: '12px', fontWeight: 700 }}
          />
          <Area 
            type="monotone" 
            dataKey="IN" 
            name="Stock In"
            stroke="#2563eb" 
            strokeWidth={4}
            fillOpacity={1} 
            fill="url(#colorIn)" 
            animationDuration={1500}
          />
          <Area 
            type="monotone" 
            dataKey="OUT" 
            name="Stock Out"
            stroke="#38bdf8" 
            strokeWidth={4}
            fillOpacity={1} 
            fill="url(#colorOut)" 
            animationDuration={1500}
          />
        </AreaChart>
      </ResponsiveContainer>
    </div>
  );
};
