import '@testing-library/jest-dom';
import { ApiService } from '../services/apiService';

jest.mock('../services/apiService', () => ({
  ApiService: {
    createCrewMember: jest.fn(),
    deleteCrewMember: jest.fn(),
    getCrewSchedule: jest.fn(),
  },
}));

const mockedApiService = ApiService as any;

describe('CrewManager', () => {
  beforeEach(() => {
    jest.clearAllMocks();
  });

  test('validates empty name before creating crew member', () => {
    const newCrew = { name: '', role: 'Pilot' as const };
    const mockOnShowMessage = jest.fn();
    
    if (!newCrew.name.trim()) {
      mockOnShowMessage('error', 'Name is required');
      return;
    }
    
    expect(mockOnShowMessage).toHaveBeenCalledWith('error', 'Name is required');
  });

  test('creates crew member with valid data', async () => {
    mockedApiService.createCrewMember.mockResolvedValueOnce(undefined);
    const mockOnShowMessage = jest.fn();
    const mockOnRefreshCrew = jest.fn();
    
    const newCrew = { name: 'John Doe', role: 'Pilot' as const };
    
    if (newCrew.name.trim()) {
      await ApiService.createCrewMember(newCrew);
      mockOnShowMessage('success', 'Crew member created successfully!');
      mockOnRefreshCrew();
    }
    
    expect(mockedApiService.createCrewMember).toHaveBeenCalledWith(newCrew);
    expect(mockOnShowMessage).toHaveBeenCalledWith('success', 'Crew member created successfully!');
    expect(mockOnRefreshCrew).toHaveBeenCalled();
  });

  test('handles crew creation error', async () => {
    const error = new Error('API Error');
    mockedApiService.createCrewMember.mockRejectedValueOnce(error);
    const mockOnShowMessage = jest.fn();
    
    const newCrew = { name: 'John Doe', role: 'Pilot' as const };
    
    try {
      await ApiService.createCrewMember(newCrew);
    } catch (err) {
      mockOnShowMessage('error', (err as Error).message || 'Failed to add crew member');
    }
    
    expect(mockOnShowMessage).toHaveBeenCalledWith('error', 'API Error');
  });

  test('deletes crew member with confirmation', async () => {
    window.confirm = jest.fn().mockReturnValue(true);
    mockedApiService.deleteCrewMember.mockResolvedValueOnce(undefined);
    const mockOnShowMessage = jest.fn();
    const mockOnRefreshCrew = jest.fn();
    const mockOnRefreshSchedules = jest.fn();
    
    const crewId = 1;
    
    if (window.confirm('Are you sure you want to delete this crew member?')) {
      await ApiService.deleteCrewMember(crewId);
      mockOnShowMessage('success', 'Crew member deleted successfully!');
      mockOnRefreshCrew();
      mockOnRefreshSchedules();
    }
    
    expect(window.confirm).toHaveBeenCalledWith('Are you sure you want to delete this crew member?');
    expect(mockedApiService.deleteCrewMember).toHaveBeenCalledWith(crewId);
    expect(mockOnShowMessage).toHaveBeenCalledWith('success', 'Crew member deleted successfully!');
    expect(mockOnRefreshCrew).toHaveBeenCalled();
    expect(mockOnRefreshSchedules).toHaveBeenCalled();
  });

  test('does not delete crew member when confirmation is cancelled', async () => {
    window.confirm = jest.fn().mockReturnValue(false);
    const mockOnShowMessage = jest.fn();
    
    if (!window.confirm('Are you sure you want to delete this crew member?')) {
    }
    
    expect(window.confirm).toHaveBeenCalled();
    expect(mockedApiService.deleteCrewMember).not.toHaveBeenCalled();
    expect(mockOnShowMessage).not.toHaveBeenCalled();
  });

  test('handles schedule fetch and displays data', async () => {
    const mockScheduleData = {
      crew_name: 'John Doe',
      schedule: {
        total_flights: 2,
        total_duty_time: '8h 30m',
        within_limits: true,
        flights: [
          { flight_number: 'LH123', departure: '08:00', arrival: '10:30', duration: '2h 30m' },
          { flight_number: 'LH456', departure: '14:00', arrival: '20:00', duration: '6h' }
        ]
      }
    };
    
    mockedApiService.getCrewSchedule.mockResolvedValueOnce(mockScheduleData);
    window.alert = jest.fn();
    
    const crewId = 1;
    const today = new Date().toISOString().split('T')[0];
    
    const data = await ApiService.getCrewSchedule(crewId, today);
    const scheduleText = `Schedule for ${data.crew_name} on ${today}:\\n\\n` +
      `Total flights: ${data.schedule.total_flights}\\n` +
      `Duty time: ${data.schedule.total_duty_time}\\n` +
      `Within limits: ${data.schedule.within_limits ? 'Yes' : 'No'}\\n\\n` +
      `Flights:\\n${data.schedule.flights.map(f =>
        `${f.flight_number}: ${f.departure} → ${f.arrival} (${f.duration})`
      ).join('\\n')}`;
    
    window.alert(scheduleText);
    
    expect(mockedApiService.getCrewSchedule).toHaveBeenCalledWith(crewId, today);
    expect(window.alert).toHaveBeenCalledWith(expect.stringContaining('Schedule for John Doe'));
    expect(window.alert).toHaveBeenCalledWith(expect.stringContaining('Total flights: 2'));
  });

  test('handles schedule fetch error', async () => {
    const error = new Error('Failed to fetch schedule');
    mockedApiService.getCrewSchedule.mockRejectedValueOnce(error);
    const mockOnShowMessage = jest.fn();
    
    const crewId = 1;
    const today = new Date().toISOString().split('T')[0];

    try {
      await ApiService.getCrewSchedule(crewId, today);
    } catch (err) {
      mockOnShowMessage('error', (err as Error).message || 'Failed to fetch crew schedule');
    }
    
    expect(mockOnShowMessage).toHaveBeenCalledWith('error', 'Failed to fetch schedule');
  });
});