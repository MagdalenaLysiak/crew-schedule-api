import React, { useState, useMemo } from 'react';
import { Plus, Users, Eye, Trash2, Edit, Check, X } from 'lucide-react';
import { CrewMember, NewCrewMember, UpdateCrewMember, Message } from '../types';
import { ApiService } from '../services/apiService';

interface CrewManagerProps {
  crewMembers: CrewMember[];
  loading: boolean;
  onShowMessage: (type: Message['type'], text: string) => void;
  onRefreshCrew: () => void;
  onRefreshSchedules: () => void;
}

const CrewManager: React.FC<CrewManagerProps> = ({
  crewMembers,
  loading,
  onShowMessage,
  onRefreshCrew,
  onRefreshSchedules
}) => {
  const [newCrew, setNewCrew] = useState<NewCrewMember>({
    name: '',
    role: 'Pilot',
  });
  const [isCreating, setIsCreating] = useState(false);
  const [editingCrew, setEditingCrew] = useState<CrewMember | null>(null);
  const [editForm, setEditForm] = useState<UpdateCrewMember>({});
  const [showRoleDropdown, setShowRoleDropdown] = useState(false);
  const [showFilterRoleDropdown, setShowFilterRoleDropdown] = useState(false);
  const [showEditRoleDropdown, setShowEditRoleDropdown] = useState(false);
  const [showEditStatusDropdown, setShowEditStatusDropdown] = useState(false);
  const [nameFilter, setNameFilter] = useState<string>('');
  const [roleFilter, setRoleFilter] = useState<string>('');
  const [availabilityFilter, setAvailabilityFilter] = useState<string>('');
  const [showAvailabilityDropdown, setShowAvailabilityDropdown] = useState(false);

  const filteredCrewMembers = useMemo(() => {
    return crewMembers.filter((crew) => {
      const nameMatch = !nameFilter || crew.name.toLowerCase().includes(nameFilter.toLowerCase());
      const roleMatch = !roleFilter || crew.role === roleFilter;
      const availabilityMatch = !availabilityFilter || 
        (availabilityFilter === 'available' && !crew.is_on_leave) ||
        (availabilityFilter === 'on-leave' && crew.is_on_leave);
      return nameMatch && roleMatch && availabilityMatch;
    });
  }, [crewMembers, nameFilter, roleFilter, availabilityFilter]);

  const createCrew = async (): Promise<void> => {
    if (!newCrew.name.trim()) {
      onShowMessage('error', 'Name is required');
      return;
    }

    setIsCreating(true);
    try {
      await ApiService.createCrewMember(newCrew);
      onShowMessage('success', 'Crew member created successfully!');
      setNewCrew({ name: '', role: 'Pilot'});
      onRefreshCrew();
    } catch (error) {
      onShowMessage('error', (error as Error).message || 'Failed to add crew member');
    }
    setIsCreating(false);
  };

  const startEdit = (crew: CrewMember) => {
    setEditingCrew(crew);
    setEditForm({ name: crew.name, role: crew.role, is_on_leave: crew.is_on_leave });
  };

  const cancelEdit = () => {
    setEditingCrew(null);
    setEditForm({});
  };

  const saveEdit = async () => {
    if (!editingCrew) return;
    
    try {
      await ApiService.updateCrewMember(editingCrew.id, editForm);
      onShowMessage('success', 'Crew member updated successfully!');
      setEditingCrew(null);
      setEditForm({});
      onRefreshCrew();
    } catch (error) {
      onShowMessage('error', (error as Error).message || 'Failed to update crew member');
    }
  };

  const deleteCrew = async (crewId: number): Promise<void> => {
    if (!window.confirm('Are you sure you want to delete this crew member?')) return;

    try {
      await ApiService.deleteCrewMember(crewId);
      onShowMessage('success', 'Crew member deleted successfully!');
      onRefreshCrew();
      onRefreshSchedules();
    } catch (error) {
      onShowMessage('error', (error as Error).message || 'Failed to delete crew member');
    }
  };

  const viewCrewSchedule = async (crewId: number): Promise<void> => {
    try {
      const schedules = await ApiService.getSchedules();
      const crewSchedules = schedules.filter(s => s.crew_id === crewId);
      const crewMember = crewMembers.find(c => c.id === crewId);
      
      if (crewSchedules.length === 0) {
        onShowMessage('info', `No flights assigned to ${crewMember?.name || 'this crew member'}`);
        return;
      }
      
      const scheduleText = `Schedule for ${crewMember?.name || 'Crew Member'}:\n\n` +
        `Total flights: ${crewSchedules.length}\n\n` +
        `Flights:\n${crewSchedules.map(s =>
          `${s.flight_number}: ${s.origin} → ${s.destination}\n` +
          `Departure: ${new Date(s.departure_time).toLocaleString()}\n` +
          `Arrival: ${new Date(s.arrival_time).toLocaleString()}\n`
        ).join('\n')}`;
      
      window.alert(scheduleText);
    } catch (error) {
      onShowMessage('error', (error as Error).message || 'Failed to fetch crew schedule');
    }
  };

  return (
    <div className="space-y-4">
      <div className="card">
        <h3 className="heading-mb">
          <Plus className="mr-2" size={20} />
          Add New Crew Member
        </h3>
        <div className="form-grid">
          <div>
            <label className="label">Full Name</label>
            <input
              type="text"
              placeholder="Enter crew member name"
              value={newCrew.name}
              onChange={(e) => setNewCrew({ ...newCrew, name: e.target.value })}
              className="input-field"
              required
            />
          </div>
          <div className="relative">
            <label className="label">Select Role</label>
            <input
              type="text"
              value={newCrew.role}
              onChange={() => {}}
              onFocus={() => setShowRoleDropdown(true)}
              onBlur={() => {
                setTimeout(() => {
                  setShowRoleDropdown(false);
                }, 200);
              }}
              placeholder="Choose role..."
              className="input-field"
              readOnly
            />
            {showRoleDropdown && (
              <div className="dropdown-container">
                <div
                  onMouseDown={() => {
                    setNewCrew({ ...newCrew, role: 'Pilot' });
                    setShowRoleDropdown(false);
                  }}
                  className="dropdown-sug"
                >
                  <div className="font-medium">Pilot</div>
                  <div className="text-sm">Aircraft pilot</div>
                </div>
                <div
                  onMouseDown={() => {
                    setNewCrew({ ...newCrew, role: 'Flight attendant' });
                    setShowRoleDropdown(false);
                  }}
                  className="dropdown-sug"
                >
                  <div className="font-medium">Flight Attendant</div>
                  <div className="text-sm">Cabin crew member</div>
                </div>
              </div>
            )}
          </div>
        </div>
        <div className="button-group mt-4">
          <button
            onClick={createCrew}
            disabled={loading || isCreating}
            className="btn-assign"
          >
            <Plus className="mr-2" size={16} />
            {isCreating ? 'Adding...' : 'Add Crew Member'}
          </button>
        </div>
      </div>

      <div className="card">
        <h3 className="section-title">Crew Members ({filteredCrewMembers.length} of {crewMembers.length})</h3>
        <div className="filter-container">
          <div>
            <label className="label">Filter by Name</label>
            <input
              type="text"
              value={nameFilter}
              onChange={(e) => setNameFilter(e.target.value)}
              placeholder="Search by name..."
              className="input-small"
            />
          </div>
          <div className="relative">
            <label className="label">Filter by Role</label>
            <input
              type="text"
              value={roleFilter ? (roleFilter === 'Pilot' ? 'Pilot' : 'Flight Attendant') : ''}
              onChange={() => {}}
              onFocus={() => setShowFilterRoleDropdown(true)}
              onBlur={() => {
                setTimeout(() => {
                  setShowFilterRoleDropdown(false);
                }, 200);
              }}
              placeholder="All Roles"
              className="input-small"
              readOnly
            />
            {showFilterRoleDropdown && (
              <div className="dropdown-container">
                <div
                  onMouseDown={() => {
                    setRoleFilter('');
                    setShowFilterRoleDropdown(false);
                  }}
                  className="dropdown-sug"
                >
                  <div className="font-medium">All Roles</div>
                  <div className="text-sm">Show all crew members</div>
                </div>
                <div
                  onMouseDown={() => {
                    setRoleFilter('Pilot');
                    setShowFilterRoleDropdown(false);
                  }}
                  className="dropdown-sug"
                >
                  <div className="font-medium">Pilot</div>
                  <div className="text-sm">Aircraft pilots only</div>
                </div>
                <div
                  onMouseDown={() => {
                    setRoleFilter('Flight attendant');
                    setShowFilterRoleDropdown(false);
                  }}
                  className="dropdown-sug"
                >
                  <div className="font-medium">Flight Attendant</div>
                  <div className="text-sm">Cabin crew only</div>
                </div>
              </div>
            )}
          </div>
          <div className="relative">
            <label className="label">Filter by Availability</label>
            <input
              type="text"
              value={availabilityFilter ? (availabilityFilter === 'available' ? 'Available' : 'On Leave') : ''}
              onChange={() => {}}
              onFocus={() => setShowAvailabilityDropdown(true)}
              onBlur={() => {
                setTimeout(() => {
                  setShowAvailabilityDropdown(false);
                }, 200);
              }}
              placeholder="All Status"
              className="input-small"
              readOnly
            />
            {showAvailabilityDropdown && (
              <div className="dropdown-container">
                <div
                  onMouseDown={() => {
                    setAvailabilityFilter('');
                    setShowAvailabilityDropdown(false);
                  }}
                  className="dropdown-sug"
                >
                  <div className="font-medium">All Status</div>
                  <div className="text-sm">Show all crew members</div>
                </div>
                <div
                  onMouseDown={() => {
                    setAvailabilityFilter('available');
                    setShowAvailabilityDropdown(false);
                  }}
                  className="dropdown-sug"
                >
                  <div className="font-medium">Available</div>
                  <div className="text-sm">Available crew only</div>
                </div>
                <div
                  onMouseDown={() => {
                    setAvailabilityFilter('on-leave');
                    setShowAvailabilityDropdown(false);
                  }}
                  className="dropdown-sug"
                >
                  <div className="font-medium">On Leave</div>
                  <div className="text-sm">Crew on leave only</div>
                </div>
              </div>
            )}
          </div>
          <div className="sm:col-span-3">
            <button
              onClick={() => {
                setNameFilter('');
                setRoleFilter('');
                setAvailabilityFilter('');
              }}
              className="btn-secondary-sm"
            >
              Clear Filters
            </button>
          </div>
        </div>

        <div className="table-container">
          <table className="w-full table-fixed">
            <thead className="sticky top-0 z-0">
              <tr className="table-header-row">
                <th className="table-header">Name</th>
                <th className="table-header-hidden">Role</th>
                <th className="table-header-hidden">Status</th>
                <th className="table-header">Actions</th>
              </tr>
            </thead>
          </table>
          <div className="scrollable-container">
            <table className="w-full table-fixed">
            <tbody>
              {filteredCrewMembers.map((crew) => (
                <tr key={crew.id} className={`table-row ${editingCrew?.id === crew.id ? 'editing-row' : ''}`}>
                  <td className="table-cell">
                    <div className="font-medium">
                      {editingCrew?.id === crew.id ? (
                        <input
                          type="text"
                          value={editForm.name || ''}
                          onChange={(e) => setEditForm({ ...editForm, name: e.target.value })}
                          className="input-field w-full"
                        />
                      ) : (
                        crew.name
                      )}
                    </div>
                    <div className="mobile-info-centered">
                      {editingCrew?.id === crew.id ? (
                        <div className="space-y-2 mt-2">
                          <div className="relative mt-2">
                            <input
                              type="text"
                              value={editForm.role || crew.role}
                              onChange={() => {}}
                              onFocus={() => setShowEditRoleDropdown(true)}
                              onBlur={() => {
                                setTimeout(() => {
                                  setShowEditRoleDropdown(false);
                                }, 200);
                              }}
                              className="input-field text-sm"
                              readOnly
                            />
                            {showEditRoleDropdown && (
                              <div className="dropdown-container">
                                <div
                                  onMouseDown={() => {
                                    setEditForm({ ...editForm, role: 'Pilot' });
                                    setShowEditRoleDropdown(false);
                                  }}
                                  className="dropdown-sug text-left"
                                >
                                  <div className="font-medium">Pilot</div>
                                  <div className="text-sm">Aircraft pilot</div>
                                </div>
                                <div
                                  onMouseDown={() => {
                                    setEditForm({ ...editForm, role: 'Flight attendant' });
                                    setShowEditRoleDropdown(false);
                                  }}
                                  className="dropdown-sug text-left"
                                >
                                  <div className="font-medium">Flight Attendant</div>
                                  <div className="text-sm">Cabin crew member</div>
                                </div>
                              </div>
                            )}
                          </div>
                          <div className="relative">
                            <input
                              type="text"
                              value={editForm.is_on_leave !== undefined ? (editForm.is_on_leave ? 'On Leave' : 'Available') : (crew.is_on_leave ? 'On Leave' : 'Available')}
                              onChange={() => {}}
                              onFocus={() => setShowEditStatusDropdown(true)}
                              onBlur={() => {
                                setTimeout(() => {
                                  setShowEditStatusDropdown(false);
                                }, 200);
                              }}
                              className="input-field text-sm"
                              readOnly
                            />
                            {showEditStatusDropdown && (
                              <div className="dropdown-container">
                                <div
                                  onMouseDown={() => {
                                    setEditForm({ ...editForm, is_on_leave: false });
                                    setShowEditStatusDropdown(false);
                                  }}
                                  className="dropdown-sug text-left"
                                >
                                  <div className="font-medium">Available</div>
                                  <div className="text-sm">Ready for assignments</div>
                                </div>
                                <div
                                  onMouseDown={() => {
                                    setEditForm({ ...editForm, is_on_leave: true });
                                    setShowEditStatusDropdown(false);
                                  }}
                                  className="dropdown-sug text-left"
                                >
                                  <div className="font-medium">On Leave</div>
                                  <div className="text-sm">Not available for assignments</div>
                                </div>
                              </div>
                            )}
                          </div>
                        </div>
                      ) : (
                        `${crew.role} • ${crew.is_on_leave ? 'On Leave' : 'Available'}`
                      )}
                    </div>
                  </td>
                  <td className="table-cell-hidden">
                    {editingCrew?.id === crew.id ? (
                      <div className="relative">
                        <input
                          type="text"
                          value={editForm.role || crew.role}
                          onChange={() => {}}
                          onFocus={() => setShowEditRoleDropdown(true)}
                          onBlur={() => {
                            setTimeout(() => {
                              setShowEditRoleDropdown(false);
                            }, 200);
                          }}
                          className="input-field"
                          readOnly
                        />
                        {showEditRoleDropdown && (
                          <div className="dropdown-container">
                            <div
                              onMouseDown={() => {
                                setEditForm({ ...editForm, role: 'Pilot' });
                                setShowEditRoleDropdown(false);
                              }}
                              className="dropdown-sug text-left"
                            >
                              <div className="font-medium">Pilot</div>
                              <div className="text-sm">Aircraft pilot</div>
                            </div>
                            <div
                              onMouseDown={() => {
                                setEditForm({ ...editForm, role: 'Flight attendant' });
                                setShowEditRoleDropdown(false);
                              }}
                              className="dropdown-sug text-left"
                            >
                              <div className="font-medium">Flight Attendant</div>
                              <div className="text-sm">Cabin crew member</div>
                            </div>
                          </div>
                        )}
                      </div>
                    ) : (
                      <span className={`px-2 py-1 rounded-full text-xs ${
                        crew.role === 'Pilot' ? 'bg-blue-100 text-blue-800' : 'bg-green-100 text-green-800'
                      }`}>
                        {crew.role}
                      </span>
                    )}
                  </td>
                  <td className="table-cell-hidden">
                    {editingCrew?.id === crew.id ? (
                      <div className="relative">
                        <input
                          type="text"
                          value={editForm.is_on_leave !== undefined ? (editForm.is_on_leave ? 'On Leave' : 'Available') : (crew.is_on_leave ? 'On Leave' : 'Available')}
                          onChange={() => {}}
                          onFocus={() => setShowEditStatusDropdown(true)}
                          onBlur={() => {
                            setTimeout(() => {
                              setShowEditStatusDropdown(false);
                            }, 200);
                          }}
                          className="input-field"
                          readOnly
                        />
                        {showEditStatusDropdown && (
                          <div className="dropdown-container">
                            <div
                              onMouseDown={() => {
                                setEditForm({ ...editForm, is_on_leave: false });
                                setShowEditStatusDropdown(false);
                              }}
                              className="dropdown-sug text-left"
                            >
                              <div className="font-medium">Available</div>
                              <div className="text-sm">Ready for assignments</div>
                            </div>
                            <div
                              onMouseDown={() => {
                                setEditForm({ ...editForm, is_on_leave: true });
                                setShowEditStatusDropdown(false);
                              }}
                              className="dropdown-sug text-left"
                            >
                              <div className="font-medium">On Leave</div>
                              <div className="text-sm">Not available for assignments</div>
                            </div>
                          </div>
                        )}
                      </div>
                    ) : (
                      <span className={`px-2 py-1 rounded-full text-xs ${
                        crew.is_on_leave ? 'bg-red-100 text-red-800' : 'bg-green-100 text-green-800'
                      }`}>
                        {crew.is_on_leave ? 'On Leave' : 'Available'}
                      </span>
                    )}
                  </td>
                  <td className="table-cell">
                    <div className="flex flex-wrap gap-1 justify-center">
                      {editingCrew?.id === crew.id ? (
                        <>
                          <button onClick={saveEdit} className="text-green-600 dark:text-green-400 p-1" title="Save">
                            <Check size={20} className="sm:w-4 sm:h-4" />
                          </button>
                          <button onClick={cancelEdit} className="text-gray-600 dark:text-gray-400 p-1" title="Cancel">
                            <X size={20} className="sm:w-4 sm:h-4" />
                          </button>
                        </>
                      ) : (
                        <>
                          <button onClick={() => viewCrewSchedule(crew.id)} className="text-blue-600 dark:text-blue-400 p-1" title="View">
                            <Eye size={18} className="sm:w-4 sm:h-4" />
                          </button>
                          <button onClick={() => startEdit(crew)} className="text-yellow-600 dark:text-yellow-400 p-1" title="Edit">
                            <Edit size={18} className="sm:w-4 sm:h-4" />
                          </button>
                          <button onClick={() => deleteCrew(crew.id)} className="text-red-600 dark:text-red-400 p-1" title="Delete">
                            <Trash2 size={18} className="sm:w-4 sm:h-4" />
                          </button>
                        </>
                      )}
                    </div>
                  </td>
                </tr>
              ))}
            </tbody>
            </table>
            {filteredCrewMembers.length === 0 && (
              <div className="text-empty">
                {crewMembers.length === 0 ? 'No crew members found. Add crew members to get started.' : 'No crew members match the selected filters.'}
              </div>
            )}
          </div>
        </div>
      </div>
    </div>
  );
};

export default CrewManager;