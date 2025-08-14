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
        <div className="px-2 sm:px-4">
          <div className="app-header">
            <div className="header-brand">
              <Plane className="brand-icon" />
              <div>
                <h1 className="brand-title">Flight Crew Management</h1>
                <div className="text-sm text-gray-500 sm:hidden">
                  Your easy scheduling app!
                </div>
              </div>
            </div>
            <div className="brand-tagline">
              Your easy scheduling app!
            </div>
          </div>

          <nav className="nav-container">
            {tabs.map(({ id, label, icon: Icon }) => (
              <button
                key={id}
                onClick={() => setActiveTab(id)}
                className={`nav-tab ${
                  activeTab === id
                    ? 'border-blue-500 text-blue-600'
                    : 'border-transparent text-gray-500'
                }`}
              >
                <Icon className="sm:mr-2" size={16} />
                <span className="mt-1 sm:mt-0">{label.split(' ')[0]}<span className="hidden sm:inline"> {label.split(' ').slice(1).join(' ')}</span></span>
              </button>
            ))}
          </nav>
        </div>
      </div>

      <main className="px-2 sm:px-4 py-4">
        <MessageBanner message={message} />
        {renderActiveTab()}
      </main>
    </div>
  );
};

export default CrewManagementApp;