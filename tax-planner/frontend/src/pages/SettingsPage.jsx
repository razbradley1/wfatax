import React, { useState, useEffect, useRef } from 'react';
import { api } from '../utils/api';
import useStore from '../hooks/useStore';

export default function SettingsPage() {
  const notify = useStore((s) => s.notify);
  const setSettings = useStore((s) => s.setSettings);

  const [settings, setLocalSettings] = useState({});
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const fileInputRef = useRef(null);

  useEffect(() => {
    async function load() {
      try {
        const data = await api.getSettings();
        setLocalSettings(data);
        setSettings(data);
      } catch (err) {
        notify(err.message, 'error');
      } finally {
        setLoading(false);
      }
    }
    load();
  }, [notify, setSettings]);

  async function handleUpdateSetting(key, value) {
    setSaving(true);
    try {
      await api.updateSetting(key, value);
      setLocalSettings((prev) => ({ ...prev, [key]: value }));
      setSettings({ ...settings, [key]: value });
      notify('Setting saved', 'success');
    } catch (err) {
      notify(err.message, 'error');
    } finally {
      setSaving(false);
    }
  }

  async function handleExport() {
    try {
      const data = await api.exportData();
      const blob = new Blob([JSON.stringify(data, null, 2)], { type: 'application/json' });
      const url = URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url;
      a.download = `tax-planner-backup-${new Date().toISOString().slice(0, 10)}.json`;
      a.click();
      URL.revokeObjectURL(url);
      notify('Data exported successfully', 'success');
    } catch (err) {
      notify(err.message, 'error');
    }
  }

  async function handleImport(e) {
    const file = e.target.files?.[0];
    if (!file) return;
    try {
      const text = await file.text();
      const data = JSON.parse(text);
      await api.importData(data);
      notify('Data imported successfully', 'success');
      window.location.reload();
    } catch (err) {
      notify(err.message || 'Invalid file', 'error');
    }
    if (fileInputRef.current) fileInputRef.current.value = '';
  }

  async function handleClearAll() {
    if (!window.confirm('Are you sure you want to delete ALL data? This cannot be undone.')) return;
    try {
      await api.clearAllData();
      notify('All data cleared', 'success');
      window.location.reload();
    } catch (err) {
      notify(err.message, 'error');
    }
  }

  if (loading) {
    return (
      <div className="flex items-center justify-center py-12">
        <p className="text-gray-500 text-sm">Loading settings...</p>
      </div>
    );
  }

  const settingFields = [
    { key: 'advisor_name', label: 'Advisor Name', type: 'text' },
    { key: 'firm_name', label: 'Firm Name', type: 'text' },
    { key: 'default_tax_year', label: 'Default Tax Year', type: 'select', options: ['2023', '2024', '2025'] },
    { key: 'show_experimental', label: 'Show Experimental Features', type: 'toggle' },
  ];

  return (
    <div className="max-w-2xl">
      <h1 className="page-title mb-6">Settings</h1>

      <div className="card space-y-6 mb-6">
        <h2 className="text-lg font-semibold text-navy-800 border-b border-gray-200 pb-2">
          General
        </h2>
        {settingFields.map((field) => (
          <div key={field.key}>
            <label className="label-text">{field.label}</label>
            {field.type === 'text' && (
              <input
                type="text"
                className="input-field"
                value={settings[field.key] || ''}
                onChange={(e) => setLocalSettings((prev) => ({ ...prev, [field.key]: e.target.value }))}
                onBlur={(e) => handleUpdateSetting(field.key, e.target.value)}
              />
            )}
            {field.type === 'select' && (
              <select
                className="input-field"
                value={settings[field.key] || ''}
                onChange={(e) => handleUpdateSetting(field.key, e.target.value)}
              >
                {field.options.map((opt) => (
                  <option key={opt} value={opt}>{opt}</option>
                ))}
              </select>
            )}
            {field.type === 'toggle' && (
              <label className="flex items-center gap-2 mt-1">
                <input
                  type="checkbox"
                  checked={settings[field.key] === true || settings[field.key] === 'true'}
                  onChange={(e) => handleUpdateSetting(field.key, e.target.checked)}
                />
                <span className="text-sm text-gray-600">Enabled</span>
              </label>
            )}
          </div>
        ))}
      </div>

      <div className="card space-y-4 mb-6">
        <h2 className="text-lg font-semibold text-navy-800 border-b border-gray-200 pb-2">
          Data Management
        </h2>
        <div className="flex gap-3">
          <button onClick={handleExport} className="btn-secondary">
            Export All Data
          </button>
          <button onClick={() => fileInputRef.current?.click()} className="btn-secondary">
            Import Data
          </button>
          <input
            ref={fileInputRef}
            type="file"
            accept=".json"
            className="hidden"
            onChange={handleImport}
          />
        </div>
      </div>

      <div className="card">
        <h2 className="text-lg font-semibold text-red-700 border-b border-red-200 pb-2 mb-4">
          Danger Zone
        </h2>
        <p className="text-sm text-gray-600 mb-3">
          Permanently delete all households, tax returns, scenarios, letters, and settings.
        </p>
        <button onClick={handleClearAll} className="btn-danger">
          Clear All Data
        </button>
      </div>
    </div>
  );
}
