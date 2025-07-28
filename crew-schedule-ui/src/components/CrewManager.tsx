import React, { useState } from 'react';
import { Plus, Users, Eye, Trash2 } from 'lucide-react';
import { CrewMember, NewCrewMember, Message } from '../types';
import { ApiService } from '../services/apiService';

interface CrewManagerProps {
  crewMembers: CrewMember[];
  loading: boolean;
  onShowMessage: (type: Message['type'], text: string) => void;
  onRefreshCrew: () => void;
  onRefreshSchedules: () => void;
}

const CrewManager: React.FC<CrewManagerProps> = ({
  crewMembers,
  loading,
  onShowMessage,
  onRefreshCrew,
  onRefreshSchedules
}) => {
  const [newCrew, setNewCrew] = useState<NewCrewMember>({
    name: '',
    role: 'Pilot',
  });
  const [isCreating, setIsCreating] = useState(false);

  const createCrew = async (): Promise<void> => {
    if (!newCrew.name.trim()) {
      onShowMessage('error', 'Name is required');
      return;
    }

    setIsCreating(true);
    try {
      await ApiService.createCrewMember(newCrew);
      onShowMessage('success', 'Crew member created successfully!');
      setNewCrew({ name: '', role: 'Pilot'});
      onRefreshCrew();
    } catch (error) {
      onShowMessage('error', (error as Error).message || 'Failed to add crew member');
    }
    setIsCreating(false);
  };

  const deleteCrew = async (crewId: number): Promise<void> => {
    if (!window.confirm('Are you sure you want to delete this crew member?')) return;

    try {
      await ApiService.deleteCrewMember(crewId);
      onShowMessage('success', 'Crew member deleted successfully!');
      onRefreshCrew();
      onRefreshSchedules();
    } catch (error) {
      onShowMessage('error', (error as Error).message || 'Failed to delete crew member');
    }
  };

  const viewCrewSchedule = async (crewId: number): Promise<void> => {
    try {
      const today = new Date().toISOString().split('T')[0];
      const data = await ApiService.getCrewSchedule(crewId, today);
      const scheduleText = `Schedule for ${data.crew_name} on ${today}:\n\n` +
        `Total flights: ${data.schedule.total_flights}\n` +
        `Duty time: ${data.schedule.total_duty_time}\n` +
        `Within limits: ${data.schedule.within_limits ? 'Yes' : 'No'}\n\n` +
        `Flights:\n${data.schedule.flights.map(f =>
          `${f.flight_number}: ${f.departure} → ${f.arrival} (${f.duration})`
        ).join('\n')}`;
      
      window.alert(scheduleText);
    } catch (error) {
      onShowMessage('error', (error as Error).message || 'Failed to fetch crew schedule');
    }
  };

  return (
    <div className="space-y-6">
      <div className="bg-white p-6 rounded-lg shadow-md">
        <h3 className="text-lg font-semibold mb-4 flex items-center">
          <Plus className="mr-2" size={20} />
          Add New Crew Member
        </h3>
        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
          <input
            type="text"
            placeholder="Full Name"
            value={newCrew.name}
            onChange={(e) => setNewCrew({ ...newCrew, name: e.target.value })}
            className="p-3 border rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent"
            required
          />
          <select
            value={newCrew.role}
            onChange={(e) => setNewCrew({ ...newCrew, role: e.target.value as 'Pilot' | 'Flight attendant' })}
            className="p-3 border rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent"
            required
          >
            <option value="Pilot">Pilot</option>
            <option value="Flight attendant">Flight Attendant</option>
          </select>
          <button
            onClick={createCrew}
            disabled={loading || isCreating}
            className="md:col-span-2 bg-blue-600 text-white p-3 rounded-lg hover:bg-blue-700 disabled:opacity-50 flex items-center justify-center"
          >
            {isCreating ? 'Adding...' : 'Add Crew Member'}
          </button>
        </div>
      </div>

      <div className="bg-white p-6 rounded-lg shadow-md">
        <div className="flex justify-between items-center mb-4">
          <h3 className="text-lg font-semibold flex items-center">
            <Users className="mr-2" size={20} />
            Crew Members ({crewMembers.length})
          </h3>
        </div>

        <div className="overflow-x-auto">
          <table className="w-full table-auto">
            <thead>
              <tr className="border-b">
                <th className="text-left p-3">Name</th>
                <th className="text-left p-3">Role</th>
                <th className="text-left p-3">Status</th>
                <th className="text-left p-3">Actions</th>
              </tr>
            </thead>
            <tbody>
              {crewMembers.map((crew) => (
                <tr key={crew.id} className="border-b hover:bg-gray-50">
                  <td className="p-3 font-medium">{crew.name}</td>
                  <td className="p-3">
                    <span className={`px-2 py-1 rounded-full text-xs ${
                      crew.role === 'Pilot' ? 'bg-blue-100 text-blue-800' : 'bg-green-100 text-green-800'
                    }`}>
                      {crew.role}
                    </span>
                  </td>
                  <td className="p-3">
                    <span className={`px-2 py-1 rounded-full text-xs ${
                      crew.is_on_leave ? 'bg-red-100 text-red-800' : 'bg-green-100 text-green-800'
                    }`}>
                      {crew.is_on_leave ? 'On Leave' : 'Available'}
                    </span>
                  </td>
                  <td className="p-3">
                    <div className="flex space-x-2">
                      <button
                        onClick={() => viewCrewSchedule(crew.id)}
                        className="text-blue-600 hover:text-blue-800"
                        title="View Today's Schedule"
                      >
                        <Eye size={16} />
                      </button>
                      <button
                        onClick={() => deleteCrew(crew.id)}
                        className="text-red-600 hover:text-red-800"
                        title="Delete"
                      >
                        <Trash2 size={16} />
                      </button>
                    </div>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
          {crewMembers.length === 0 && (
            <div className="text-center py-8 text-gray-500">
              No crew members found. Add crew members to get started.
            </div>
          )}
        </div>
      </div>
    </div>
  );
};

export default CrewManager;