import React, { useState, useEffect } from 'react';
import { Users, Plane, BookOpen, Moon, Sun } from 'lucide-react';
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
  const [selectedDate, setSelectedDate] = useState<Date>(new Date());
  const [isDarkMode, setIsDarkMode] = useState(false);

  const tabs: TabConfig[] = [
    { id: 'crew', label: 'Crew Management', icon: Users },
    { id: 'assignments', label: 'Flight Assignments', icon: Plane },
    { id: 'schedules', label: 'Schedule Overview', icon: BookOpen }
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
            selectedDate={selectedDate}
            onDateChange={setSelectedDate}
            onShowMessage={showMessage}
            onRefreshSchedules={fetchSchedules}
          />
        );
      default:
        return <div>Invalid tab</div>;
    }
  };

  return (
    <div className={`min-h-screen ${isDarkMode ? 'dark bg-gray-900' : 'bg-gray-100'}`}>
      <div className="bg-white dark:bg-gray-800 shadow-sm">
        <div className="app-container">
          <div className="app-header">
            <div className="header-brand">
              <Plane className="brand-icon" />
              <div>
                <h1 className="brand-title dark:text-white">Flight Crew Management</h1>
                <div className="text-slogan">
                  Your easy scheduling app!
                </div>
              </div>
            </div>
            <div className="flex items-center gap-4">
              <div className="brand-tagline dark:text-gray-400">
                Your easy scheduling app!
              </div>
              <button
                onClick={() => setIsDarkMode(!isDarkMode)}
                className="btn-icon-hover"
                title={isDarkMode ? 'Switch to light mode' : 'Switch to dark mode'}
              >
                {isDarkMode ? <Sun size={20} className="text-yellow-500" /> : <Moon size={20} className="text-blue-800" />}
              </button>
            </div>
          </div>

          <nav className="nav-container" data-active={tabs.findIndex(tab => tab.id === activeTab)}>
            {tabs.map(({ id, label, icon: Icon }) => (
              <button
                key={id}
                onClick={() => setActiveTab(id)}
                className={`nav-tab ${
                  activeTab === id
                    ? 'text-blue'
                    : 'text-gray-500 dark:text-gray-400'
                }`}
              >
                <Icon className="sm:mr-2" size={16} />
                <span className="mt-1 sm:mt-0">{label.split(' ')[0]}<span className="hidden sm:inline"> {label.split(' ').slice(1).join(' ')}</span></span>
              </button>
            ))}
          </nav>
        </div>
      </div>

      <main className="app-container py-4">
        <MessageBanner message={message} />
        {renderActiveTab()}
      </main>
    </div>
  );
};

export default CrewManagementApp;