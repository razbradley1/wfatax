import React, { useState, useEffect } from 'react';
import { useParams, Link, useNavigate } from 'react-router-dom';
import { api } from '../utils/api';
import useStore from '../hooks/useStore';

export default function ScenarioList() {
  const { householdId } = useParams();
  const navigate = useNavigate();
  const notify = useStore(s => s.notify);
  const [scenarios, setScenarios] = useState([]);
  const [household, setHousehold] = useState(null);
  const [loading, setLoading] = useState(true);
  const [newName, setNewName] = useState('');
  const [newYear, setNewYear] = useState(2024);
  const [cloneFrom, setCloneFrom] = useState('');
  const [showCreate, setShowCreate] = useState(false);

  useEffect(() => {
    Promise.all([
      api.getHousehold(householdId),
      api.getScenariosByHousehold(householdId),
    ]).then(([h, s]) => { setHousehold(h); setScenarios(s); }).finally(() => setLoading(false));
  }, [householdId]);

  const handleCreate = async () => {
    try {
      const data = {
        household_id: parseInt(householdId),
        tax_year: newYear,
        name: newName || `Scenario ${scenarios.length + 1}`,
        inputs: { tax_year: newYear, filing_status: household?.filing_status || 'single', state: household?.state || '' },
      };
      if (cloneFrom) data.source_scenario_id = parseInt(cloneFrom);
      const created = await api.createScenario(data);
      notify('Scenario created', 'success');
      navigate(`/households/${householdId}/scenarios/${created.id}`);
    } catch (e) { notify(e.message, 'error'); }
  };

  const handleDelete = async (id) => {
    if (!window.confirm('Delete this scenario?')) return;
    try {
      await api.deleteScenario(id);
      setScenarios(scenarios.filter(s => s.id !== id));
      notify('Scenario deleted', 'success');
    } catch (e) { notify(e.message, 'error'); }
  };

  if (loading) return <div className="text-center py-12 text-gray-500">Loading...</div>;

  return (
    <div className="max-w-4xl mx-auto space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <Link to={`/households/${householdId}`} className="text-sm text-navy-600 hover:underline">&larr; {household?.name}</Link>
          <h1 className="page-title mt-1">Scenarios</h1>
        </div>
        <div className="flex gap-2">
          <button onClick={() => setShowCreate(!showCreate)} className="btn-primary">New Scenario</button>
          {scenarios.length >= 2 && (
            <Link to={`/households/${householdId}/compare`} className="btn-secondary">Compare</Link>
          )}
        </div>
      </div>

      {showCreate && (
        <div className="card space-y-4">
          <h3 className="font-semibold">Create New Scenario</h3>
          <div className="grid grid-cols-3 gap-4">
            <div>
              <label className="label-text">Name</label>
              <input className="input-field" value={newName} onChange={e => setNewName(e.target.value)} placeholder="e.g. Roth Conversion" />
            </div>
            <div>
              <label className="label-text">Tax Year</label>
              <select className="input-field" value={newYear} onChange={e => setNewYear(parseInt(e.target.value))}>
                <option value={2023}>2023</option><option value={2024}>2024</option><option value={2025}>2025</option>
              </select>
            </div>
            <div>
              <label className="label-text">Clone From</label>
              <select className="input-field" value={cloneFrom} onChange={e => setCloneFrom(e.target.value)}>
                <option value="">Start blank</option>
                {scenarios.map(s => <option key={s.id} value={s.id}>{s.name}</option>)}
              </select>
            </div>
          </div>
          <div className="flex gap-2">
            <button onClick={handleCreate} className="btn-primary">Create</button>
            <button onClick={() => setShowCreate(false)} className="btn-secondary">Cancel</button>
          </div>
        </div>
      )}

      <div className="space-y-3">
        {scenarios.map(s => (
          <div key={s.id} className="card flex items-center justify-between">
            <div>
              <div className="flex items-center gap-2">
                <Link to={`/households/${householdId}/scenarios/${s.id}`} className="font-semibold text-navy-800 hover:underline">{s.name}</Link>
                {s.is_readonly && <span className="px-2 py-0.5 bg-gray-100 text-gray-600 text-xs rounded-full">Read-only</span>}
              </div>
              <div className="text-sm text-gray-500">Tax Year {s.tax_year} &middot; Updated {new Date(s.updated_at).toLocaleDateString()}</div>
            </div>
            <div className="flex gap-2">
              <Link to={`/households/${householdId}/report/${s.id}`} className="btn-secondary text-xs">Report</Link>
              <Link to={`/households/${householdId}/range-calc/${s.id}`} className="btn-secondary text-xs">Range Calc</Link>
              {!s.is_readonly && <button onClick={() => handleDelete(s.id)} className="text-red-500 hover:text-red-700 text-xs px-2">Delete</button>}
            </div>
          </div>
        ))}
        {scenarios.length === 0 && <p className="text-gray-500 text-center py-8">No scenarios yet. Create one to start planning.</p>}
      </div>
    </div>
  );
}
