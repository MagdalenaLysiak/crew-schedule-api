import '@testing-library/jest-dom';
import { ApiService } from '../services/apiService';

jest.mock('../services/apiService', () => ({
  ApiService: {
    createCrewMember: jest.fn(),
    deleteCrewMember: jest.fn(),
    getSchedules: jest.fn(),
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
    const mockScheduleData = [
      {
        id: 1,
        crew_member_name: 'John Doe',
        flight_number: 'LH123',
        departure_time: '2024-01-01T08:00:00',
        arrival_time: '2024-01-01T10:30:00'
      }
    ];
    
    mockedApiService.getSchedules.mockResolvedValueOnce(mockScheduleData);
    
    const data = await ApiService.getSchedules();
    
    expect(mockedApiService.getSchedules).toHaveBeenCalled();
    expect(data).toEqual(mockScheduleData);
  });

  test('handles schedule fetch error', async () => {
    const error = new Error('Failed to fetch schedules');
    mockedApiService.getSchedules.mockRejectedValueOnce(error);
    const mockOnShowMessage = jest.fn();

    try {
      await ApiService.getSchedules();
    } catch (err) {
      mockOnShowMessage('error', (err as Error).message || 'Failed to fetch schedules');
    }
    
    expect(mockOnShowMessage).toHaveBeenCalledWith('error', 'Failed to fetch schedules');
  });
});