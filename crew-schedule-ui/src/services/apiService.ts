import { CrewMember, NewCrewMember, UpdateCrewMember, Flight, Schedule, AvailabilityCheck } from '../types';

const API_BASE = process.env.VITE_API_BASE_URL || 'http://localhost:8001';

export class ApiService {
  private static async handleResponse<T>(response: Response): Promise<T> {
    if (!response.ok) {
      const error = await response.json().catch(() => ({ detail: 'Network error' }));
      throw new Error(error.detail || `HTTP ${response.status}`);
    }
    return response.json();
  }

  //crew management
  static async getCrewMembers(): Promise<CrewMember[]> {
    const response = await fetch(`${API_BASE}/crew`);
    const data = await this.handleResponse<CrewMember[]>(response);
    return Array.isArray(data) ? data : [];
  }

  static async createCrewMember(crew: NewCrewMember): Promise<CrewMember> {
    const response = await fetch(`${API_BASE}/crew`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(crew)
    });
    return this.handleResponse<CrewMember>(response);
  }

  static async updateCrewMember(crewId: number, updates: UpdateCrewMember): Promise<CrewMember> {
    const response = await fetch(`${API_BASE}/crew/${crewId}`, {
      method: 'PATCH',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(updates)
    });
    return this.handleResponse<CrewMember>(response);
  }

  static async deleteCrewMember(crewId: number): Promise<void> {
    const response = await fetch(`${API_BASE}/crew/${crewId}`, {
      method: 'DELETE'
    });
    if (!response.ok) {
      throw new Error('Failed to delete crew member');
    }
  }



  //flight management
  static async getFlights(): Promise<Flight[]> {
    const response = await fetch(`${API_BASE}/flights`);
    const data = await this.handleResponse<Flight[]>(response);
    return Array.isArray(data) ? data : [];
  }

  static async loadFlights(): Promise<{ message: string }> {
    const response = await fetch(`${API_BASE}/load-flights`, {
      method: 'POST'
    });
    return this.handleResponse<{ message: string }>(response);
  }

  static async removeAllFlights(): Promise<{ message: string }> {
    const response = await fetch(`${API_BASE}/flights`, {
      method: 'DELETE'
    });
    return this.handleResponse<{ message: string }>(response);
  }

  // schedule managment
  static async getSchedules(): Promise<Schedule[]> {
    const response = await fetch(`${API_BASE}/schedules`);
    const data = await this.handleResponse<Schedule[]>(response);
    return Array.isArray(data) ? data : [];
  }

  static async deleteAssignment(assignmentId: number): Promise<void> {
    const response = await fetch(`${API_BASE}/assignment/${assignmentId}`, {
      method: 'DELETE'
    });
    if (!response.ok) {
      throw new Error('Failed to delete assignment');
    }
  }

  // flight assignment
  static async checkAvailability(crewId: number, flightId: number): Promise<AvailabilityCheck> {
    const response = await fetch(`${API_BASE}/crew/${crewId}/availability-check/${flightId}`);
    return this.handleResponse<AvailabilityCheck>(response);
  }

  static async assignFlight(crewId: number, flightId: number): Promise<{ message: string }> {
    const response = await fetch(`${API_BASE}/assign-flight/${crewId}/${flightId}`, {
      method: 'POST'
    });
    return this.handleResponse<{ message: string }>(response);
  }
}