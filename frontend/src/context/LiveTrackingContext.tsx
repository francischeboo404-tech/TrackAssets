import React, { createContext, useContext, useState, useCallback } from 'react';

export interface LivePosition {
  item_type: string;
  item_id: number;
  lat: number;
  lon: number;
  action: string;
  timestamp: string;
  warehouse_id?: number;
}

interface LiveTrackingContextType {
  positions: Record<string, LivePosition>;
  updatePosition: (pos: LivePosition) => void;
}

const LiveTrackingContext = createContext<LiveTrackingContextType | undefined>(undefined);

export const LiveTrackingProvider: React.FC<{ children: React.ReactNode }> = ({ children }) => {
  const [positions, setPositions] = useState<Record<string, LivePosition>>({});

  const updatePosition = useCallback((pos: LivePosition) => {
    setPositions(prev => ({
      ...prev,
      [`${pos.item_type}:${pos.item_id}`]: pos,
    }));
  }, []);

  return (
    <LiveTrackingContext.Provider value={{ positions, updatePosition }}>
      {children}
    </LiveTrackingContext.Provider>
  );
};

export const useLiveTracking = () => {
  const ctx = useContext(LiveTrackingContext);
  if (!ctx) throw new Error('useLiveTracking must be used within LiveTrackingProvider');
  return ctx;
};
