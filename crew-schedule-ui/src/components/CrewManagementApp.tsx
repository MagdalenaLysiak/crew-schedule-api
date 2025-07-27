import React, { useState, useEffect } from 'react';
import { Calendar, Users, Plane } from 'lucide-react';
import { CrewMember, Flight, Schedule, Message } from '../types';
import { ApiService } from '../services/apiService';
import CrewManager from './CrewManager';
import FlightAssignment from './FlightAssignment';
import ScheduleOverview from './ScheduleOverview';
import MessageBanner from './MessageBanner';

type TabType = 'crew' | 'assignments' | 'schedules';

interface TabConfig {
  id: TabType;
  label: string;
  icon: React.ComponentType<{ className?: string; size?: number }>;
}

const CrewManagementApp: React.FC = () => {
  const [activeTab, setActiveTab] = useState<TabType>('crew');
  const [crewMembers, setCrewMembers] = useState<CrewMember[]>([]);
  const [flights, setFlights] = useState<Flight[]>([]);
  const [schedules, setSchedules] = useState<Schedule[]>([]);
  const [loading, setLoading] = useState(false);
  const [message, setMessage] = useState<Message>({ type: '', text: '' });

  const tabs: TabConfig[] = [
    { id: 'crew', label: 'Crew Management', icon: Users },
    { id: 'assignments', label: 'Flight Assignments', icon: Plane },
    { id: 'schedules', label: 'Schedule Overview', icon: Calendar }
  ];

  const fetchCrewMembers = async (): Promise<void> => {
    try {
      const data = await ApiService.getCrewMembers();
      setCrewMembers(data);
    } catch (error) {
      console.error('Error fetching crew:', error);
      setCrewMembers([]);
    }
  };

  const fetchFlights = async (): Promise<void> => {
    try {
      const data = await ApiService.getFlights();
      setFlights(data);
    } catch (error) {
      console.error('Error fetching flights:', error);
      setFlights([]);
    }
  };

  const fetchSchedules = async (): Promise<void> => {
    try {
      const data = await ApiService.getSchedules();
      setSchedules(data);
    } catch (error) {
      console.error('Error fetching schedules:', error);
      setSchedules([]);
    }
  };

  const showMessage = (type: Message['type'], text: string): void => {
    setMessage({ type, text });
    setTimeout(() => setMessage({ type: '', text: '' }), 5000);
  };

  useEffect(() => {
    const loadInitialData = async () => {
      setLoading(true);
      await Promise.all([
        fetchCrewMembers(),
        fetchFlights(),
        fetchSchedules()
      ]);
      setLoading(false);
    };

    loadInitialData();
  }, []);

  const renderActiveTab = () => {
    switch (activeTab) {
      case 'crew':
        return (
          <CrewManager
            crewMembers={crewMembers}
            loading={loading}
            onShowMessage={showMessage}
            onRefreshCrew={fetchCrewMembers}
            onRefreshSchedules={fetchSchedules}
          />
        );
      case 'assignments':
        return (
          <FlightAssignment
            crewMembers={crewMembers}
            flights={flights}
            loading={loading}
            onShowMessage={showMessage}
            onRefreshFlights={fetchFlights}
            onRefreshSchedules={fetchSchedules}
          />
        );
      case 'schedules':
        return (
          <ScheduleOverview
            schedules={schedules}
            onShowMessage={showMessage}
            onRefreshSchedules={fetchSchedules}
          />
        );
      default:
        return <div>Invalid tab</div>;
    }
  };

  return (
    <div className="min-h-screen bg-gray-100">
      <div className="bg-white shadow-sm">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <div className="flex justify-between items-center py-6">
            <div className="flex items-center">
              <Plane className="h-8 w-8 text-blue-600 mr-3" />
              <h1 className="text-2xl font-bold text-gray-900">Flight Crew Management</h1>
            </div>
            <div className="text-sm text-gray-500">
              Your easy scheduling app!
            </div>
          </div>

          <nav className="flex space-x-8">
            {tabs.map(({ id, label, icon: Icon }) => (
              <button
                key={id}
                onClick={() => setActiveTab(id)}
                className={`flex items-center px-1 py-4 border-b-2 font-medium text-sm ${
                  activeTab === id
                    ? 'border-blue-500 text-blue-600'
                    : 'border-transparent text-gray-500 hover:text-gray-700 hover:border-gray-300'
                }`}
              >
                <Icon className="mr-2" size={16} />
                {label}
              </button>
            ))}
          </nav>
        </div>
      </div>

      <main className="max-w-7xl mx-auto py-6 px-4 sm:px-6 lg:px-8">
        <MessageBanner message={message} />
        {renderActiveTab()}
      </main>
    </div>
  );
};

export default CrewManagementApp;