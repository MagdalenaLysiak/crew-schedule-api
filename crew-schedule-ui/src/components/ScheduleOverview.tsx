import React, { useState, useMemo } from 'react';
import { Calendar, BookOpen, Clock, Trash2 } from 'lucide-react';
import { Schedule, Message } from '../types';
import { ApiService } from '../services/apiService.ts';
import DatePicker from 'react-datepicker';
import 'react-datepicker/dist/react-datepicker.css';

interface ScheduleOverviewProps {
  schedules: Schedule[];
  selectedDate: Date;
  onDateChange: (date: Date) => void;
  onShowMessage: (type: Message['type'], text: string) => void;
  onRefreshSchedules: () => void;
}

const ScheduleOverview: React.FC<ScheduleOverviewProps> = ({
  schedules,
  selectedDate,
  onDateChange,
  onShowMessage,
  onRefreshSchedules
}) => {

  const [crewFilter, setCrewFilter] = useState<string>('');
  const [flightFilter, setFlightFilter] = useState<string>('');
  const [timeFilter, setTimeFilter] = useState<string>('');
  const [showTimeDropdown, setShowTimeDropdown] = useState(false);

  const filteredSchedules = useMemo(() => {
    return schedules.filter(schedule => {
      const scheduleDate = new Date(schedule.scheduled_departure_time);
      const dateMatch = scheduleDate.toDateString() === selectedDate.toDateString();
      const crewMatch = !crewFilter || schedule.crew_name.toLowerCase().includes(crewFilter.toLowerCase());
      const flightMatch = !flightFilter || schedule.flight_number.toLowerCase().includes(flightFilter.toLowerCase());
      const timeMatch = !timeFilter || (
        timeFilter === 'am' && new Date(schedule.scheduled_departure_time).getHours() < 12
      ) || (
        timeFilter === 'pm' && new Date(schedule.scheduled_departure_time).getHours() >= 12
      );
      return dateMatch && crewMatch && flightMatch && timeMatch;
    });
  }, [schedules, selectedDate, crewFilter, flightFilter, timeFilter]);

  const deleteAssignment = async (assignmentId: number): Promise<void> => {
    if (!window.confirm('Are you sure you want to delete this assignment?')) return;

    try {
      await ApiService.deleteAssignment(assignmentId);
      onShowMessage('success', 'Assignment deleted successfully!');
      onRefreshSchedules();
    } catch (error) {
      onShowMessage('error', (error as Error).message || 'Failed to delete assignment');
    }
  };

  return (
    <div className="space-y-4">
      <div className="card">
        <div className="header-container">
          <h3 className="section-heading">
            <BookOpen className="icon-mr" size={20} />
            Flight Schedules ({filteredSchedules.length})
          </h3>
          <div className="flex-items">
            <Calendar size={18} className="icon-sm" />
            <div className="relative">
              <DatePicker
                selected={selectedDate}
                onChange={(date) => onDateChange(date || new Date())}
                dateFormat="MMM d, yyyy"
                className="input-small"
              />
              {selectedDate && (
                <button
                  onClick={() => onDateChange(new Date())}
                  className="btn-clear"
                  type="button"
                >
                  ×
                </button>
              )}
            </div>
          </div>
        </div>

        <div className="filter-container">
          <div>
            <label className="label">Filter by Crew Member</label>
            <input
              type="text"
              value={crewFilter}
              onChange={(e) => setCrewFilter(e.target.value)}
              placeholder="Search by crew name..."
              className="input-small"
            />
          </div>
          <div>
            <label className="label">Filter by Flight</label>
            <input
              type="text"
              value={flightFilter}
              onChange={(e) => setFlightFilter(e.target.value)}
              placeholder="Search by flight number..."
              className="input-small"
            />
          </div>
          <div className="relative">
            <label className="label">Filter by Time</label>
            <input
              type="text"
              value={timeFilter ? (timeFilter === 'am' ? 'AM Flights' : 'PM Flights') : ''}
              onChange={() => {}}
              onFocus={() => setShowTimeDropdown(true)}
              onBlur={() => {
                setTimeout(() => {
                  setShowTimeDropdown(false);
                }, 200);
              }}
              placeholder="All Times"
              className="input-small"
              readOnly
            />
            {showTimeDropdown && (
              <div className="dropdown-container">
                <div
                  onMouseDown={() => {
                    setTimeFilter('');
                    setShowTimeDropdown(false);
                  }}
                  className="dropdown-sug"
                >
                  <div className="font-medium">All Times</div>
                  <div className="text-sm">Show all flights</div>
                </div>
                <div
                  onMouseDown={() => {
                    setTimeFilter('am');
                    setShowTimeDropdown(false);
                  }}
                  className="dropdown-sug"
                >
                  <div className="font-medium">AM Flights</div>
                  <div className="text-sm">Flights before 12:00 PM</div>
                </div>
                <div
                  onMouseDown={() => {
                    setTimeFilter('pm');
                    setShowTimeDropdown(false);
                  }}
                  className="dropdown-sug"
                >
                  <div className="font-medium">PM Flights</div>
                  <div className="text-sm">Flights after 12:00 PM</div>
                </div>
              </div>
            )}
          </div>
          <div className="sm:col-span-3">
            <button
              onClick={() => {
                setCrewFilter('');
                setFlightFilter('');
                setTimeFilter('');
              }}
              className="btn-secondary-sm"
            >
              Clear Filters
            </button>
          </div>
        </div>

        <div className="text-info">
          Total schedules in system: {schedules.length} | Showing schedules for: <span className="font-medium">{selectedDate.toLocaleDateString()}</span>
        </div>

        <div className="table-container">
          <table className="w-full table-fixed">
            <thead>
              <tr className="table-header-row">
                <th className="table-header">Crew Member</th>
                <th className="table-header-hidden">Flight</th>
                <th className="table-header-hidden">Times</th>
                <th className="table-header-hidden">Route</th>
                <th className="table-header-hidden">Duration</th>
                <th className="table-header">Actions</th>
              </tr>
            </thead>
          </table>
          <div className="scrollable-container">
            <table className="w-full table-fixed">
            <tbody>
              {filteredSchedules.map((schedule) => (
                <tr key={schedule.id} className="table-row">
                  <td className="table-cell">
                    <div className="font-medium">{schedule.crew_name}</div>
                    <div className="mobile-info">
                      {schedule.flight_number} • {schedule.origin} → {schedule.destination}<br/>
                      <Clock size={14} className="icon-inline" />
                      {new Date(schedule.scheduled_departure_time).toLocaleTimeString()} → {new Date(schedule.scheduled_arrival_time).toLocaleTimeString()}<br/>
                      {schedule.duration_text}
                    </div>
                  </td>
                  <td className="table-cell-hidden font-medium">{schedule.flight_number}</td>
                  <td className="table-cell-hidden text-sm">
                    <div className="flex items-center">
                      <Clock size={14} className="mr-1" />
                      {new Date(schedule.scheduled_departure_time).toLocaleTimeString()} → {new Date(schedule.scheduled_arrival_time).toLocaleTimeString()}
                    </div>
                  </td>
                  <td className="table-cell-hidden">{schedule.origin} → {schedule.destination}</td>
                  <td className="table-cell-hidden">{schedule.duration_text}</td>
                  <td className="table-cell">
                    <div className="flex justify-center">
                      <button
                        onClick={() => deleteAssignment(schedule.id)}
                        className="text-delete p-2"
                        title="Delete"
                      >
                        <Trash2 size={18} className="sm:w-4 sm:h-4" />
                      </button>
                    </div>
                  </td>
                </tr>
              ))}
            </tbody>
            </table>
            {filteredSchedules.length === 0 && (
              <div className="text-empty">
                    {schedules.length === 0 
                      ? "No schedules found. Assign flights to crew members to view them."
                      : (crewFilter || flightFilter || timeFilter) 
                        ? "No schedules match the selected filters."
                        : `No schedules found for ${selectedDate.toLocaleDateString()}. Try selecting a different date.`
                    }
              </div>
            )}
          </div>
        </div>
      </div>
    </div>
  );
};

export default ScheduleOverview;