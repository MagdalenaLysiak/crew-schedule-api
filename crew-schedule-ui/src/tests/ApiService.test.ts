import { ApiService } from '../services/apiService';
import { CrewMember } from '../types';

global.fetch = jest.fn();
const mockFetch = fetch as jest.MockedFunction<typeof fetch>;

describe('ApiService', () => {
  beforeEach(() => {
    mockFetch.mockClear();
  });

  describe('Error Handling', () => {
    it('should handle network errors gracefully', async () => {
      mockFetch.mockRejectedValueOnce(new Error('Network error'));
      
      await expect(ApiService.getCrewMembers()).rejects.toThrow('Network error');
    });

    it('should parse API error responses correctly', async () => {
      const errorResponse = {
        ok: false,
        status: 400,
        json: jest.fn().mockResolvedValueOnce({
          detail: 'Crew member already assigned to flight'
        })
      };
      
      mockFetch.mockResolvedValueOnce(errorResponse as any);
      
      await expect(ApiService.getCrewMembers()).rejects.toThrow(
        'Crew member already assigned to flight'
      );
    });

    it('should handle malformed error responses', async () => {
      const errorResponse = {
        ok: false,
        status: 500,
        json: jest.fn().mockRejectedValueOnce(new Error('Invalid JSON'))
      };
      
      mockFetch.mockResolvedValueOnce(errorResponse as any);
      
      await expect(ApiService.getCrewMembers()).rejects.toThrow('Network error');
    });
  });

  describe('Data Validation', () => {
    it('should return empty array for non-array crew response', async () => {
      const response = {
        ok: true,
        json: jest.fn().mockResolvedValueOnce({ message: 'No crew found' })
      };
      
      mockFetch.mockResolvedValueOnce(response as any);
      
      const result = await ApiService.getCrewMembers();
      expect(result).toEqual([]);
    });

    it('should return empty array for non-array flight response', async () => {
      const response = {
        ok: true,
        json: jest.fn().mockResolvedValueOnce(null)
      };
      
      mockFetch.mockResolvedValueOnce(response as any);
      
      const result = await ApiService.getFlights();
      expect(result).toEqual([]);
    });

    it('should handle valid crew data correctly', async () => {
      const mockCrewData: CrewMember[] = [
        { id: 1, name: 'John Doe', role: 'Pilot', is_on_leave: false },
        { id: 2, name: 'Jane Smith', role: 'Flight attendant', is_on_leave: true }
      ];

      const response = {
        ok: true,
        json: jest.fn().mockResolvedValueOnce(mockCrewData)
      };
      
      mockFetch.mockResolvedValueOnce(response as any);
      
      const result = await ApiService.getCrewMembers();
      expect(result).toEqual(mockCrewData);
      expect(result).toHaveLength(2);
    });
  });

  describe('API Endpoint Calls', () => {
    it('should call correct endpoint for crew creation', async () => {
      const newCrew = { name: 'Test Pilot', role: 'Pilot' as const };
      const createdCrew: CrewMember = { 
        id: 1, 
        name: 'Test Pilot', 
        role: 'Pilot', 
        is_on_leave: false 
      };

      const response = {
        ok: true,
        json: jest.fn().mockResolvedValueOnce(createdCrew)
      };
      
      mockFetch.mockResolvedValueOnce(response as any);
      
      const result = await ApiService.createCrewMember(newCrew);
      
      expect(mockFetch).toHaveBeenCalledWith('http://localhost:8000/crew', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(newCrew)
      });
      expect(result).toEqual(createdCrew);
    });

    it('should call availability check with correct parameters', async () => {
      const availabilityResponse = {
        available: true,
        crew_name: 'John Doe',
        flight_number: 'EZY123',
        message: 'Available'
      };

      const response = {
        ok: true,
        json: jest.fn().mockResolvedValueOnce(availabilityResponse)
      };
      
      mockFetch.mockResolvedValueOnce(response as any);
      
      const result = await ApiService.checkAvailability(1, 100);
      
      expect(mockFetch).toHaveBeenCalledWith(
        'http://localhost:8000/crew/1/availability-check/100'
      );
      expect(result.available).toBe(true);
    });
  });
});