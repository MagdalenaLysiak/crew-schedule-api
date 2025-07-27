import React, { useState } from 'react';
import { Plane, Search, CheckCircle, XCircle, Clock } from 'lucide-react';
import { CrewMember, Flight, AvailabilityCheck, Message } from '../types';
import { ApiService } from '../services/apiService.ts';

interface FlightAssignmentProps {
  crewMembers: CrewMember[];
  flights: Flight[];
  loading: boolean;
  onShowMessage: (type: Message['type'], text: string) => void;
  onRefreshFlights: () => void;
  onRefreshSchedules: () => void;
}

const FlightAssignment: React.FC<FlightAssignmentProps> = ({
  crewMembers,
  flights,
  loading,
  onShowMessage,
  onRefreshFlights,
  onRefreshSchedules
}) => {
  const [selectedCrew, setSelectedCrew] = useState<string>('');
  const [selectedFlight, setSelectedFlight] = useState<string>('');
  const [availabilityCheck, setAvailabilityCheck] = useState<AvailabilityCheck | null>(null);
  const [isChecking, setIsChecking] = useState(false);
  const [isAssigning, setIsAssigning] = useState(false);
  const [isLoadingFlights, setIsLoadingFlights] = useState(false);

  const checkAvailability = async (): Promise<void> => {
    if (!selectedCrew || !selectedFlight) return;

    setIsChecking(true);
    try {
      const data = await ApiService.checkAvailability(
        parseInt(selectedCrew),
        parseInt(selectedFlight)
      );
      setAvailabilityCheck(data);
    } catch (error) {
      onShowMessage('error', (error as Error).message || 'Failed to check availability');
    }
    setIsChecking(false);
  };

  const assignFlight = async (): Promise<void> => {
    if (!selectedCrew || !selectedFlight) return;

    setIsAssigning(true);
    try {
      const data = await ApiService.assignFlight(
        parseInt(selectedCrew),
        parseInt(selectedFlight)
      );
      onShowMessage('success', data.message);
      onRefreshSchedules();
      setAvailabilityCheck(null);
      setSelectedCrew('');
      setSelectedFlight('');
    } catch (error) {
      onShowMessage('error', (error as Error).message || 'Failed to assign flight');
    }
    setIsAssigning(false);
  };

  const loadFlights = async (): Promise<void> => {
    setIsLoadingFlights(true);
    try {
      const data = await ApiService.loadFlights();
      onShowMessage('success', data.message);
      onRefreshFlights();
    } catch (error) {
      onShowMessage('error', (error as Error).message || 'Failed to load flights');
    }
    setIsLoadingFlights(false);
  };

  return (
    <div className="space-y-6">
      <div className="bg-white p-6 rounded-lg shadow-md">
        <h3 className="text-lg font-semibold mb-4 flex items-center">
          <Plane className="mr-2" size={20} />
          Flight Assignment
        </h3>

        <div className="grid grid-cols-1 md:grid-cols-2 gap-4 mb-4">
          <div>
            <label className="block text-sm font-medium mb-2">Select Crew Member</label>
            <select
              value={selectedCrew}
              onChange={(e) => setSelectedCrew(e.target.value)}
              className="w-full p-3 border rounded-lg focus:ring-2 focus:ring-blue-500"
            >
              <option value="">Choose crew member...</option>
              {crewMembers.map((crew) => (
                <option key={crew.id} value={crew.id.toString()}>
                  {crew.name} ({crew.role})
                </option>
              ))}
            </select>
          </div>

          <div>
            <label className="block text-sm font-medium mb-2">Select Flight</label>
            <select
              value={selectedFlight}
              onChange={(e) => setSelectedFlight(e.target.value)}
              className="w-full p-3 border rounded-lg focus:ring-2 focus:ring-blue-500"
            >
              <option value="">Choose flight...</option>
              {flights.map((flight) => (
                <option key={flight.id} value={flight.id.toString()}>
                  {flight.flight_number} - {flight.origin} → {flight.destination}
                  ({flight.duration_text})
                </option>
              ))}
            </select>
          </div>
        </div>

        <div className="flex space-x-4 mb-4">
          <button
            onClick={checkAvailability}
            disabled={!selectedCrew || !selectedFlight || loading || isChecking}
            className="bg-yellow-600 text-white px-4 py-2 rounded-lg hover:bg-yellow-700 disabled:opacity-50 flex items-center"
          >
            <Search className="mr-2" size={16} />
            {isChecking ? 'Checking...' : 'Check Availability'}
          </button>

          <button
            onClick={loadFlights}
            disabled={loading || isLoadingFlights}
            className="bg-green-600 text-white px-4 py-2 rounded-lg hover:bg-green-700 disabled:opacity-50"
          >
            {isLoadingFlights ? 'Loading...' : 'Load Today\'s Flights'}
          </button>
        </div>

        {availabilityCheck && (
          <div className={`p-4 rounded-lg mb-4 ${
            availabilityCheck.available 
              ? 'bg-green-50 border border-green-200' 
              : 'bg-red-50 border border-red-200'
          }`}>
            <div className="flex items-center mb-2">
              {availabilityCheck.available ? (
                <CheckCircle className="text-green-600 mr-2" size={20} />
              ) : (
                <XCircle className="text-red-600 mr-2" size={20} />
              )}
              <span className="font-medium">{availabilityCheck.message}</span>
            </div>

            {availabilityCheck.available ? (
              <div>
                {availabilityCheck.buffer_info && (
                  <p className="text-sm text-gray-600 mb-3">{availabilityCheck.buffer_info}</p>
                )}
                <button
                  onClick={assignFlight}
                  disabled={loading || isAssigning}
                  className="bg-blue-600 text-white px-4 py-2 rounded-lg hover:bg-blue-700 disabled:opacity-50"
                >
                  {isAssigning ? 'Assigning...' : 'Assign Flight'}
                </button>
              </div>
            ) : (
              availabilityCheck.conflict_details && (
                <p className="text-sm text-red-600">{availabilityCheck.conflict_details}</p>
              )
            )}
          </div>
        )}
      </div>

      <div className="bg-white p-6 rounded-lg shadow-md">
        <h3 className="text-lg font-semibold mb-4">Available Flights ({flights.length})</h3>
        <div className="overflow-x-auto">
          <table className="w-full table-auto">
            <thead>
              <tr className="border-b">
                <th className="text-left p-3">Flight</th>
                <th className="text-left p-3">Route</th>
                <th className="text-left p-3">Times</th>
                <th className="text-left p-3">Duration</th>
                <th className="text-left p-3">Direction</th>
              </tr>
            </thead>
            <tbody>
              {flights.slice(0, 10).map((flight) => (
                <tr key={flight.id} className="border-b hover:bg-gray-50">
                  <td className="p-3 font-medium">{flight.flight_number}</td>
                  <td className="p-3">{flight.origin} → {flight.destination}</td>
                  <td className="p-3 text-sm">
                    <div>Dep: {new Date(flight.departure_time).toLocaleTimeString()}</div>
                    <div>Arr: {new Date(flight.arrival_time).toLocaleTimeString()}</div>
                  </td>
                  <td className="p-3">{flight.duration_text}</td>
                  <td className="p-3">
                    <span className={`px-2 py-1 rounded-full text-xs ${
                      flight.direction === 'departure' 
                        ? 'bg-blue-100 text-blue-800' 
                        : 'bg-purple-100 text-purple-800'
                    }`}>
                      {flight.direction}
                    </span>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  );
};

export default FlightAssignment;