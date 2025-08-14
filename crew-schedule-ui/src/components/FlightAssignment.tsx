import React, { useState } from 'react';
import { Plane, Search, CheckCircle, XCircle } from 'lucide-react';
import { CrewMember, Flight, AvailabilityCheck, Message } from '../types';
import { ApiService } from '../services/apiService.ts';
import DatePicker from 'react-datepicker';
import 'react-datepicker/dist/react-datepicker.css';

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
  const [flightSearch, setFlightSearch] = useState<string>('');
  const [showFlightSuggestions, setShowFlightSuggestions] = useState(false);
  const [showCrewSuggestions, setShowCrewSuggestions] = useState(false);
  const [availabilityCheck, setAvailabilityCheck] = useState<AvailabilityCheck | null>(null);
  const [isChecking, setIsChecking] = useState(false);
  const [isAssigning, setIsAssigning] = useState(false);
  const [isLoadingFlights, setIsLoadingFlights] = useState(false);
  const [filterDate, setFilterDate] = useState<Date | null>(null);
  const [filterDirection, setFilterDirection] = useState<string>('');
  const [showDirectionDropdown, setShowDirectionDropdown] = useState(false);

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
    const flightDate = new Date(flight.departure_time);
    const dateMatch = !filterDate || flightDate.toDateString() === filterDate.toDateString();
    const directionMatch = !filterDirection || flight.direction === filterDirection;
    return dateMatch && directionMatch;
  });

  const searchFilteredFlights = flights.filter((flight) => {
    if (!flightSearch) return false;
    const searchLower = flightSearch.toLowerCase();
    return flight.flight_number.toLowerCase().includes(searchLower);
  }).slice(0, 10);

  const selectFlight = (flight: Flight) => {
    setSelectedFlight(flight.id.toString());
    setFlightSearch(`${flight.flight_number} - ${flight.origin} → ${flight.destination}`);
    setShowFlightSuggestions(false);
  };

  return (
    <div className="space-y-4">
      <div className="bg-white p-4 rounded-lg shadow-md">
        <h3 className="heading-mb">
          <Plane className="mr-2" size={20} />
          Flight Assignment
        </h3>

        <div className="grid grid-cols-1 md:grid-cols-2 gap-4 mb-4">
          <div className="relative">
            <label className="block text-sm font-medium mb-2">Select Crew Member</label>
            <input
              type="text"
              value={selectedCrew ? crewMembers.find(c => c.id.toString() === selectedCrew)?.name + ` (${crewMembers.find(c => c.id.toString() === selectedCrew)?.role})` || '' : ''}
              onChange={(e) => {
                const searchValue = e.target.value.toLowerCase();
                setShowCrewSuggestions(true);
                if (!e.target.value) {
                  setSelectedCrew('');
                  setShowCrewSuggestions(false);
                }
              }}
              onFocus={() => setShowCrewSuggestions(true)}
              onBlur={() => {
                setTimeout(() => {
                  setShowCrewSuggestions(false);
                }, 200);
              }}
              placeholder="Choose crew member..."
              className="input-field"
            />
            {showCrewSuggestions && (
              <div className="dropdown-container">
                {crewMembers.map((crew) => (
                  <div
                    key={crew.id}
                    onMouseDown={() => {
                      setSelectedCrew(crew.id.toString());
                      setShowCrewSuggestions(false);
                    }}
                    className="dropdown-sug"
                  >
                    <div className="font-medium">{crew.name}</div>
                    <div className="text-sm">{crew.role} | {crew.is_on_leave ? 'On Leave' : 'Available'}</div>
                  </div>
                ))}
              </div>
            )}
          </div>

          <div className="relative">
            <label className="block text-sm font-medium mb-2">Search Flight</label>
            <input
              type="text"
              value={flightSearch}
              onChange={(e) => {
                setFlightSearch(e.target.value);
                setShowFlightSuggestions(true);
                if (!e.target.value) {
                  setSelectedFlight('');
                  setShowFlightSuggestions(false);
                }
              }}
              onFocus={() => flightSearch && setShowFlightSuggestions(true)}
              onBlur={() => {
                setTimeout(() => {
                  setShowFlightSuggestions(false);
                  if (!selectedFlight) {
                    setFlightSearch('');
                  }
                }, 200);
              }}
              placeholder="Search by flight number (e.g., BA123, EZY456)..."
              className="input-field"
            />
            {showFlightSuggestions && searchFilteredFlights.length > 0 && (
              <div className="dropdown-container">
                {searchFilteredFlights.map((flight) => {
                  const depDate = new Date(flight.departure_time);
                  const dateStr = depDate.toLocaleDateString();
                  return (
                    <div
                      key={flight.id}
                      onMouseDown={() => selectFlight(flight)}
                      className="dropdown-sug"
                    >
                      <div className="font-medium">{flight.flight_number}</div>
                      <div className="text-sm">
                        {flight.origin} → {flight.destination} | {dateStr} | {flight.duration_text}
                      </div>
                    </div>
                  );
                })}
              </div>
            )}
          </div>
        </div>

        <div className="button-group">
          <button
            onClick={checkAvailability}
            disabled={!selectedCrew || !selectedFlight || loading || isChecking}
            className="btn-check"
          >
            <Search className="mr-2" size={16} />
            {isChecking ? 'Checking...' : 'Check Availability'}
          </button>

          <button
            onClick={loadFlights}
            disabled={loading || isLoadingFlights}
            className="btn-load"
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
                  className="btn-blue"
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

      <div className="bg-white p-4 rounded-lg shadow-md">
        <h3 className="section-title">Available Flights ({filteredFlights.length} of {flights.length})</h3>
        <div className="filter-container">
          <div>
            <label className="block text-sm font-medium mb-2">Filter by Date</label>
            <div className="w-full">
              <DatePicker
                selected={filterDate}
                onChange={(date) => setFilterDate(date)}
                placeholderText="Select date..."
                className="input-small"
                dateFormat="MMM d, yyyy"
                isClearable
                wrapperClassName="w-full"
              />
            </div>
          </div>
          <div className="relative">
            <label className="block text-sm font-medium mb-2">Filter by Direction</label>
            <input
              type="text"
              value={filterDirection ? (filterDirection === 'departure' ? 'Departure' : 'Arrival') : ''}
              onChange={() => {}}
              onFocus={() => setShowDirectionDropdown(true)}
              onBlur={() => {
                setTimeout(() => {
                  setShowDirectionDropdown(false);
                }, 200);
              }}
              placeholder="All Directions"
              className="input-small"
              readOnly
            />
            {showDirectionDropdown && (
              <div className="dropdown-container">
                <div
                  onMouseDown={() => {
                    setFilterDirection('');
                    setShowDirectionDropdown(false);
                  }}
                  className="dropdown-sug"
                >
                  <div className="font-medium">All Directions</div>
                  <div className="text-sm">Show both departures and arrivals</div>
                </div>
                <div
                  onMouseDown={() => {
                    setFilterDirection('departure');
                    setShowDirectionDropdown(false);
                  }}
                  className="dropdown-sug"
                >
                  <div className="font-medium">Departure</div>
                  <div className="text-sm">Flights leaving from LTN</div>
                </div>
                <div
                  onMouseDown={() => {
                    setFilterDirection('arrival');
                    setShowDirectionDropdown(false);
                  }}
                  className="dropdown-sug"
                >
                  <div className="font-medium">Arrival</div>
                  <div className="text-sm">Flights arriving at LTN</div>
                </div>
              </div>
            )}
          </div>
          <div className="sm:col-span-2">
            <button
              onClick={() => {
                setFilterDate(null);
                setFilterDirection('');
              }}
              className="btn-secondary-sm"
            >
              Clear Filters
            </button>
          </div>
        </div>

        <div className="border rounded-lg bg-white">
          <div className="h-[400px] sm:h-[615px] overflow-y-auto rounded-lg pb-4">
            <table className="w-full table-auto">
              <thead className="sticky top-0 border-b bg-gray-50">
                <tr>
                  <th className="table-header">Flight</th>
                  <th className="table-header-hidden">Route</th>
                  <th className="table-header-hidden">Date</th>
                  <th className="table-header-hidden">Times</th>
                  <th className="table-header-hidden">Duration</th>
                  <th className="table-header-hidden">Direction</th>
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
                        <td className="table-cell">
                          <div className="font-medium">{flight.flight_number}</div>
                          <div className="mobile-info">
                            {flight.origin} → {flight.destination}<br/>
                            {dateStr} • {flight.duration_text}<br/>
                            Dep: {dep.toLocaleTimeString()} Arr: {arr.toLocaleTimeString()}<br/>
                            <span className={`px-1 py-0.5 rounded text-xs ${
                              flight.direction === 'departure' 
                                ? 'bg-blue-100 text-blue-800' 
                                : 'bg-purple-100 text-purple-800'
                            }`}>
                              {flight.direction}
                            </span>
                          </div>
                        </td>
                        <td className="table-cell-hidden">{flight.origin} → {flight.destination}</td>
                        <td className="table-cell-hidden">{dateStr}</td>
                        <td className="table-cell-hidden text-sm">
                          <div>Dep: {dep.toLocaleTimeString()}</div>
                          <div>Arr: {arr.toLocaleTimeString()}</div>
                        </td>
                        <td className="table-cell-hidden">{flight.duration_text}</td>
                        <td className="table-cell-hidden">
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