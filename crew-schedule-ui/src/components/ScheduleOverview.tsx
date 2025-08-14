import React, { useState, useMemo } from 'react';
import { Calendar, Clock, Trash2 } from 'lucide-react';
import { Schedule, Message } from '../types';
import { ApiService } from '../services/apiService.ts';
import DatePicker from 'react-datepicker';
import 'react-datepicker/dist/react-datepicker.css';

interface ScheduleOverviewProps {
  schedules: Schedule[];
  onShowMessage: (type: Message['type'], text: string) => void;
  onRefreshSchedules: () => void;
}

const ScheduleOverview: React.FC<ScheduleOverviewProps> = ({
  schedules,
  onShowMessage,
  onRefreshSchedules
}) => {
  const [selectedDate, setSelectedDate] = useState<Date>(new Date());

  const filteredSchedules = useMemo(() => {
    return schedules.filter(schedule => {
      const scheduleDate = new Date(schedule.departure_time);
      return scheduleDate.toDateString() === selectedDate.toDateString();
    });
  }, [schedules, selectedDate]);

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
      <div className="bg-white p-4 rounded-lg shadow-md">
        <div className="header-container">
          <h3 className="section-heading">
            <Calendar className="mr-2" size={20} />
            Flight Schedules ({filteredSchedules.length})
          </h3>
          <div className="flex items-center space-x-2">
            <Calendar size={18} className="sm:w-4 sm:h-4" />
            <DatePicker
              selected={selectedDate}
              onChange={(date) => setSelectedDate(date || new Date())}
              dateFormat="MMM d, yyyy"
              className="input-small"
            />
          </div>
        </div>

        <div className="mb-4 text-sm text-gray-600">
          Showing schedules for: <span className="font-medium">{selectedDate.toLocaleDateString()}</span>
        </div>

        <div className="overflow-x-auto">
          <table className="w-full table-auto">
            <thead>
              <tr className="border-b">
                <th className="table-header">Crew Member</th>
                <th className="table-header-hidden">Flight</th>
                <th className="table-header-hidden">Times</th>
                <th className="table-header-hidden">Route</th>
                <th className="table-header-hidden">Duration</th>
                <th className="table-header">Actions</th>
              </tr>
            </thead>
            <tbody>
              {filteredSchedules.map((schedule) => (
                <tr key={schedule.id} className="border-b hover:bg-gray-50">
                  <td className="table-cell">
                    <div className="font-medium">{schedule.crew_name}</div>
                    <div className="mobile-info">
                      {schedule.flight_number} • {schedule.origin} → {schedule.destination}<br/>
                      <Clock size={14} className="inline mr-1 sm:w-3 sm:h-3" />
                      {new Date(schedule.departure_time).toLocaleTimeString()} → {new Date(schedule.arrival_time).toLocaleTimeString()}<br/>
                      {schedule.duration_text}
                    </div>
                  </td>
                  <td className="table-cell-hidden font-medium">{schedule.flight_number}</td>
                  <td className="table-cell-hidden text-sm">
                    <div className="flex items-center">
                      <Clock size={14} className="mr-1" />
                      {new Date(schedule.departure_time).toLocaleTimeString()} → {new Date(schedule.arrival_time).toLocaleTimeString()}
                    </div>
                  </td>
                  <td className="table-cell-hidden">{schedule.origin} → {schedule.destination}</td>
                  <td className="table-cell-hidden">{schedule.duration_text}</td>
                  <td className="table-cell">
                    <button
                      onClick={() => deleteAssignment(schedule.id)}
                      className="text-red-600 hover:text-red-800 p-2"
                      title="Delete"
                    >
                      <Trash2 size={18} className="sm:w-4 sm:h-4" />
                    </button>
                  </td>
                </tr>
              ))}
              {filteredSchedules.length === 0 && (
                <tr>
                  <td colSpan={6} className="text-center py-8 text-gray-500">
                    {schedules.length === 0 
                      ? "No schedules found. Assign flights to crew members to view them."
                      : `No schedules found for ${selectedDate.toLocaleDateString()}. Try selecting a different date.`
                    }
                  </td>
                </tr>
              )}
            </tbody>
          </table>
        </div>

        {schedules.length > 0 && (
          <div className="mt-4 text-sm text-gray-500">
            Total schedules in system: {schedules.length} | Showing for selected date: {filteredSchedules.length}
          </div>
        )}
      </div>
    </div>
  );
};

export default ScheduleOverview;