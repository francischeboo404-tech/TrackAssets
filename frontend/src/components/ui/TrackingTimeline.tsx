import { Clock, MapPin, User } from 'lucide-react';
import type { ScanEventRecord } from '../../hooks/useTracking';
import { cn } from '../../lib/utils';

interface TrackingTimelineProps {
  events: ScanEventRecord[];
  loading?: boolean;
}

export const TrackingTimeline: React.FC<TrackingTimelineProps> = ({
  events,
  loading,
}) => {
  if (loading) {
    return (
      <div className="space-y-3 animate-pulse">
        {[1, 2, 3].map((i) => (
          <div key={i} className="h-16 bg-slate-100 rounded-xl" />
        ))}
      </div>
    );
  }

  if (!events.length) {
    return (
      <p className="text-sm text-slate-400 italic py-6 text-center">
        No tracking events recorded yet.
      </p>
    );
  }

  return (
    <div className="space-y-3 max-h-[420px] overflow-y-auto pr-1">
      {events.map((event, index) => (
        <div
          key={event.id}
          className={cn(
            'p-4 rounded-2xl border flex gap-3',
            index === 0
              ? 'bg-indigo-50 border-indigo-100'
              : 'bg-white border-slate-100',
          )}
        >
          <div className="w-9 h-9 rounded-xl bg-slate-900 text-white flex items-center justify-center flex-shrink-0">
            <Clock className="w-4 h-4" />
          </div>
          <div className="flex-1 min-w-0">
            <div className="flex items-center justify-between gap-2">
              <p className="text-xs font-black uppercase tracking-widest text-slate-800">
                {event.action.replace('_', ' ')}
              </p>
              <span className="text-[10px] text-slate-400 font-mono">
                {new Date(event.timestamp).toLocaleString()}
              </span>
            </div>
            {event.new_state && (
              <p className="text-[11px] text-slate-600 mt-1">
                State:{' '}
                <span className="font-semibold">
                  {JSON.stringify(event.new_state)}
                </span>
              </p>
            )}
            <div className="flex flex-wrap gap-3 mt-2 text-[10px] text-slate-500 font-bold uppercase">
              {event.user_role && (
                <span className="flex items-center gap-1">
                  <User className="w-3 h-3" /> {event.user_role}
                </span>
              )}
              {event.warehouse_id && (
                <span className="flex items-center gap-1">
                  <MapPin className="w-3 h-3" /> WH #{event.warehouse_id}
                </span>
              )}
            </div>
          </div>
        </div>
      ))}
    </div>
  );
};
