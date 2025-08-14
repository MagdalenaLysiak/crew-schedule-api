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
    <div className="space-y-6">
      <div className="bg-white p-6 rounded-lg shadow-md">
        <div className="flex justify-between items-center mb-4">
          <h3 className="text-lg font-semibold flex items-center">
            <Calendar className="mr-2" size={20} />
            Flight Schedules ({filteredSchedules.length})
          </h3>
          <div className="flex items-center space-x-2">
            <Calendar size={16} />
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
                <th className="text-left p-3">Crew Member</th>
                <th className="text-left p-3">Flight</th>
                <th className="text-left p-3">Times converted to UTC</th>
                <th className="text-left p-3">Route</th>
                <th className="text-left p-3">Duration</th>
                <th className="text-left p-3">Actions</th>
              </tr>
            </thead>
            <tbody>
              {filteredSchedules.map((schedule) => (
                <tr key={schedule.id} className="border-b hover:bg-gray-50">
                  <td className="p-3">
                    <div className="font-medium">{schedule.crew_name}</div>
                    <div className="text-sm text-gray-600">ID: {schedule.crew_id}</div>
                  </td>
                  <td className="p-3 font-medium">{schedule.flight_number}</td>
                  <td className="p-3 text-sm">
                    <div className="flex items-center">
                      <Clock size={14} className="mr-1" />
                      {new Date(schedule.departure_time).toLocaleTimeString()} → {new Date(schedule.arrival_time).toLocaleTimeString()}
                    </div>
                  </td>
                  <td className="p-3">{schedule.origin} → {schedule.destination}</td>
                  <td className="p-3">{schedule.duration_text}</td>
                  <td className="p-3">
                    <button
                      onClick={() => deleteAssignment(schedule.id)}
                      className="text-red-600 hover:text-red-800"
                      title="Delete Assignment"
                    >
                      <Trash2 size={16} />
                    </button>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
          {filteredSchedules.length === 0 && (
            <div className="text-center py-8 text-gray-500">
              {schedules.length === 0 
                ? "No schedules found. Assign flights to crew members to view them."
                : `No schedules found for ${selectedDate.toLocaleDateString()}. Try selecting a different date.`
              }
            </div>
          )}
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