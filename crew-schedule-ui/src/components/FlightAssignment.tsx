import React, { useState } from 'react';
import { Plane, Search, CheckCircle, XCircle } from 'lucide-react';
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
  const [filterDate, setFilterDate] = useState<string>('');
  const [filterDirection, setFilterDirection] = useState<string>('');

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

  const filteredFlights = flights.filter((flight) => {
    const flightDate = new Date(flight.departure_time).toISOString().split('T')[0];
    const dateMatch = !filterDate || flightDate === filterDate;
    const directionMatch = !filterDirection || flight.direction === filterDirection;
    return dateMatch && directionMatch;
  });

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
              {flights.map((flight) => {
                const depDate = new Date(flight.departure_time);
                const dateStr = depDate.toLocaleDateString();
                return (
                  <option key={flight.id} value={flight.id.toString()}>
                    {flight.flight_number} - {flight.origin} → {flight.destination} ({flight.duration_text}) [{dateStr}]
                  </option>
                )
              })}
            </select>
          </div>
        </div>

        <div className="flex space-x-4 mb-4">
          <button
            onClick={checkAvailability}
            disabled={!selectedCrew || !selectedFlight || loading || isChecking}
            className="bg-blue-600 text-white px-4 py-2 rounded-lg hover:bg-yellow-700 disabled:opacity-50 flex items-center"
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
              <span className="font-medium">
                {availabilityCheck.available 
                  ? availabilityCheck.message 
                  : ((availabilityCheck as any).reason || availabilityCheck.message)
                }
              </span>
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
              <div>
              </div>
            )}
          </div>
        )}
      </div>

      <div className="bg-white p-6 rounded-lg shadow-md">
        <h3 className="text-lg font-semibold mb-4">Available Flights ({filteredFlights.length} of {flights.length})</h3>
        <div className="grid grid-cols-1 md:grid-cols-2 gap-4 mb-4 p-4 bg-gray-50 rounded-lg">
          <div>
            <label className="block text-sm font-medium mb-2">Filter by Date</label>
            <input
              type="date"
              value={filterDate}
              onChange={(e) => setFilterDate(e.target.value)}
              className="w-full p-2 border rounded-lg focus:ring-2 focus:ring-blue-500"
            />
          </div>
          <div>
            <label className="block text-sm font-medium mb-2">Filter by Direction</label>
            <select
              value={filterDirection}
              onChange={(e) => setFilterDirection(e.target.value)}
              className="w-full p-2 border rounded-lg focus:ring-2 focus:ring-blue-500"
            >
              <option value="">All Directions</option>
              <option value="departure">Departure</option>
              <option value="arrival">Arrival</option>
            </select>
          </div>
          <div className="md:col-span-2">
            <button
              onClick={() => {
                setFilterDate('');
                setFilterDirection('');
              }}
              className="bg-blue-600 text-white px-4 py-2 rounded-lg hover:bg-gray-700 text-sm"
            >
              Clear Filters
            </button>
          </div>
        </div>

        <div className="border rounded-lg bg-white">
          <div className="max-h-96 overflow-y-auto">
            <table className="w-full table-auto">
              <thead className="sticky top-0 bg-gray-100 border-b">
                <tr>
                  <th className="text-left p-3 font-medium">Flight</th>
                  <th className="text-left p-3 font-medium">Route</th>
                  <th className="text-left p-3 font-medium">Date</th>
                  <th className="text-left p-3 font-medium">Times converted to LTN</th>
                  <th className="text-left p-3 font-medium">Duration</th>
                  <th className="text-left p-3 font-medium">Direction</th>
                </tr>
              </thead>
              <tbody>
                {filteredFlights.length === 0 ? (
                  <tr>
                    <td colSpan={6} className="text-center p-8 text-gray-500">
                      {flights.length === 0 ? 'No flights available' : 'No flights match the selected filters'}
                    </td>
                  </tr>
                ) : (
                  filteredFlights.map((flight) => {
                    const dep = new Date(flight.departure_time);
                    const arr = new Date(flight.arrival_time);
                    const dateStr = dep.toLocaleDateString();
                    return (
                      <tr key={flight.id} className="border-b hover:bg-gray-50">
                        <td className="p-3 font-medium">{flight.flight_number}</td>
                        <td className="p-3">{flight.origin} → {flight.destination}</td>
                        <td className="p-3">{dateStr}</td>
                        <td className="p-3 text-sm">
                          <div>Dep: {dep.toLocaleTimeString()}</div>
                          <div>Arr: {arr.toLocaleTimeString()}</div>
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
                    )
                  })
                )}
              </tbody>
            </table>
          </div>
        </div>
      </div>
    </div>
  );
};

export default FlightAssignment;