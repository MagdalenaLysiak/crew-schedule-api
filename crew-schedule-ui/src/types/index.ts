export interface CrewMember {
  id: number;
  name: string;
  role: 'Pilot' | 'Flight attendant';
  is_on_leave: boolean;
}

export interface NewCrewMember {
  name: string;
  role: 'Pilot' | 'Flight attendant';
}

export interface UpdateCrewMember {
  name?: string;
  role?: 'Pilot' | 'Flight attendant';
  is_on_leave?: boolean;
}

export interface Flight {
  id: number;
  flight_number: string;
  origin: string;
  destination: string;
  departure_time: string;
  arrival_time: string;
  duration_text: string;
  direction: 'departure' | 'arrival';
}

export interface Schedule {
  id: number;
  crew_id: number;
  crew_name: string;
  flight_id: number;
  flight_number: string;
  departure_time: string;
  arrival_time: string;
  origin: string;
  destination: string;
  duration_text: string;
}

export interface AvailabilityCheck {
  available: boolean;
  crew_name: string;
  flight_number: string;
  message: string;
  reason?: string;
  conflict_details?: string;
  buffer_info?: string;
  flight_details?: {
    departure: string;
    arrival: string;
    route: string;
    duration: string;
  };
}

export interface Message {
  type: 'success' | 'error' | 'info' | '';
  text: string;
}

export interface CrewSchedule {
  crew_name: string;
  schedule: {
    total_flights: number;
    total_duty_time: string;
    within_limits: boolean;
    flights: Array<{
      flight_number: string;
      departure: string;
      arrival: string;
      duration: string;
    }>;
  };
}