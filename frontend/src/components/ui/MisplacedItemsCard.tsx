import React, { useState } from 'react';
import { AlertTriangle, ChevronDown, ChevronUp, Package, Clock, MapPin } from 'lucide-react';
import { useMisplacedItemsStats, useMisplacedItems, type MisplacedItem } from '../../hooks/useMisplacedItems';
import { cn } from '../../lib/utils';

export const MisplacedItemsCard: React.FC<{
  className?: string;
  onItemClick?: (item: MisplacedItem) => void;
  limit?: number;
}> = ({ className, onItemClick, limit = 10 }) => {
  const [isExpanded, setIsExpanded] = useState(false);
  const stats = useMisplacedItemsStats();
  const { data: allItems = [], isLoading } = useMisplacedItems({ limit: 50 });

  // Show top items sorted by severity
  const displayItems = allItems.slice(0, limit);

  const getSeverityColor = (severity: string) => {
    switch (severity) {
      case 'HIGH':
        return 'bg-red-100 text-red-800 border-red-300';
      case 'MEDIUM':
        return 'bg-yellow-100 text-yellow-800 border-yellow-300';
      case 'LOW':
        return 'bg-blue-100 text-blue-800 border-blue-300';
      default:
        return 'bg-gray-100 text-gray-800 border-gray-300';
    }
  };

  const getSeverityBadgeColor = (severity: string) => {
    switch (severity) {
      case 'HIGH':
        return 'bg-red-500';
      case 'MEDIUM':
        return 'bg-yellow-500';
      case 'LOW':
        return 'bg-blue-500';
      default:
        return 'bg-gray-500';
    }
  };

  const getItemTypeIcon = (itemType: string) => {
    switch (itemType) {
      case 'asset':
        return '📱';
      case 'inventory':
        return '📦';
      case 'inventory_instance':
        return '🔖';
      default:
        return '📋';
    }
  };

  if (isLoading) {
    return (
      <div className={cn(
        'bg-white rounded-lg shadow p-6 border border-gray-200',
        className,
      )}>
        <div className="animate-pulse">
          <div className="h-6 bg-gray-200 rounded w-1/3 mb-4"></div>
          <div className="space-y-3">
            <div className="h-4 bg-gray-200 rounded"></div>
            <div className="h-4 bg-gray-200 rounded"></div>
          </div>
        </div>
      </div>
    );
  }

  if (stats.total === 0) {
    return (
      <div className={cn(
        'bg-green-50 border border-green-200 rounded-lg p-6',
        className,
      )}>
        <div className="flex items-center gap-3">
          <div className="p-2 bg-green-100 rounded-lg">
            <Package className="w-5 h-5 text-green-600" />
          </div>
          <div>
            <h3 className="font-semibold text-green-900">All Clear</h3>
            <p className="text-sm text-green-700">No misplaced items detected</p>
          </div>
        </div>
      </div>
    );
  }

  return (
    <div className={cn(
      'bg-white rounded-lg shadow border',
      stats.highSeverity > 0 ? 'border-red-300' : 'border-gray-200',
      className,
    )}>
      {/* Header */}
      <div
        className={cn(
          'p-4 border-b cursor-pointer hover:bg-gray-50 transition',
          stats.highSeverity > 0 ? 'bg-red-50' : 'bg-gray-50',
        )}
        onClick={() => setIsExpanded(!isExpanded)}
      >
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-3">
            <AlertTriangle
              className={cn(
                'w-5 h-5',
                stats.highSeverity > 0 ? 'text-red-600' : 'text-yellow-600',
              )}
            />
            <div>
              <h3 className="font-semibold text-gray-900">Misplaced Items</h3>
              <p className="text-sm text-gray-600">
                {stats.total} item{stats.total !== 1 ? 's' : ''} detected
                {stats.highSeverity > 0 && (
                  <span className="ml-2 font-semibold text-red-600">
                    ({stats.highSeverity} high priority)
                  </span>
                )}
              </p>
            </div>
          </div>

          {/* Stats Pills */}
          <div className="flex items-center gap-2">
            {stats.highSeverity > 0 && (
              <span className="inline-flex items-center gap-1 px-2 py-1 rounded-full text-xs font-semibold bg-red-100 text-red-800">
                <span className="w-2 h-2 bg-red-600 rounded-full"></span>
                HIGH: {stats.highSeverity}
              </span>
            )}
            {stats.mediumSeverity > 0 && (
              <span className="inline-flex items-center gap-1 px-2 py-1 rounded-full text-xs font-semibold bg-yellow-100 text-yellow-800">
                <span className="w-2 h-2 bg-yellow-600 rounded-full"></span>
                MEDIUM: {stats.mediumSeverity}
              </span>
            )}
            {stats.lowSeverity > 0 && (
              <span className="inline-flex items-center gap-1 px-2 py-1 rounded-full text-xs font-semibold bg-blue-100 text-blue-800">
                <span className="w-2 h-2 bg-blue-600 rounded-full"></span>
                LOW: {stats.lowSeverity}
              </span>
            )}
            {isExpanded ? (
              <ChevronUp className="w-4 h-4 text-gray-600" />
            ) : (
              <ChevronDown className="w-4 h-4 text-gray-600" />
            )}
          </div>
        </div>
      </div>

      {/* Expanded Content */}
      {isExpanded && (
        <div className="divide-y max-h-96 overflow-y-auto">
          {displayItems.length === 0 ? (
            <div className="p-4 text-center text-gray-500">No items to display</div>
          ) : (
            displayItems.map((item) => (
              <div
                key={`${item.item_type}-${item.item_id}`}
                className={cn(
                  'p-4 hover:bg-gray-50 cursor-pointer transition border-l-4',
                  getSeverityColor(item.severity).split(' ').filter(c => c.startsWith('border'))[0] === 'border-red-300'
                    ? 'border-l-red-500'
                    : getSeverityColor(item.severity).split(' ').filter(c => c.startsWith('border'))[0] === 'border-yellow-300'
                      ? 'border-l-yellow-500'
                      : 'border-l-blue-500',
                )}
                onClick={() => onItemClick?.(item)}
              >
                <div className="flex items-start justify-between gap-3 mb-2">
                  <div className="flex items-start gap-3 flex-1 min-w-0">
                    <span className="text-lg mt-1">{getItemTypeIcon(item.item_type)}</span>
                    <div className="flex-1 min-w-0">
                      <h4 className="font-medium text-gray-900 truncate">
                        {item.item_name}
                      </h4>
                      <p className="text-xs text-gray-500">{item.item_code}</p>
                    </div>
                  </div>
                  <span
                    className={cn(
                      'px-2 py-1 rounded-full text-xs font-semibold whitespace-nowrap',
                      getSeverityColor(item.severity),
                    )}
                  >
                    {item.severity}
                  </span>
                </div>

                {/* Location Info */}
                <div className="space-y-1 ml-11">
                  <div className="flex items-center gap-2 text-sm text-gray-700">
                    <MapPin className="w-3 h-3 text-gray-400" />
                    <span className="truncate">
                      Expected: <span className="font-medium">{item.expected_location.warehouse_name}</span>
                    </span>
                  </div>
                  <div className="flex items-center gap-2 text-sm text-gray-700">
                    <MapPin className="w-3 h-3 text-red-400" />
                    <span className="truncate">
                      Found: <span className="font-medium">{item.actual_location.warehouse_name}</span>
                    </span>
                  </div>
                </div>

                {/* Time Info */}
                {item.days_since_scan !== undefined && (
                  <div className="flex items-center gap-2 text-xs text-gray-500 ml-11 mt-1">
                    <Clock className="w-3 h-3" />
                    Last scanned {item.days_since_scan} day{item.days_since_scan !== 1 ? 's' : ''} ago
                  </div>
                )}

                {/* Message */}
                <p className="text-xs text-gray-600 ml-11 mt-2 line-clamp-2">
                  {item.message}
                </p>
              </div>
            ))
          )}
        </div>
      )}

      {/* Footer */}
      {isExpanded && allItems.length > limit && (
        <div className="p-3 bg-gray-50 border-t text-center text-sm text-gray-600 hover:bg-gray-100 cursor-pointer">
          View all {allItems.length} items →
        </div>
      )}
    </div>
  );
};

export default MisplacedItemsCard;
