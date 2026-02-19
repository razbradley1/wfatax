import React, { useState, useEffect } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import { api } from '../utils/api';
import useStore from '../hooks/useStore';

const STATUS_OPTIONS = [
  { value: 'draft', label: 'Draft' },
  { value: 'in_review', label: 'In Review' },
  { value: 'complete', label: 'Complete' },
];

export default function TaxLetterEditor() {
  const { householdId, letterId } = useParams();
  const navigate = useNavigate();
  const notify = useStore((s) => s.notify);

  const [household, setHousehold] = useState(null);
  const [letter, setLetter] = useState(null);
  const [sections, setSections] = useState([]);
  const [status, setStatus] = useState('draft');
  const [templates, setTemplates] = useState([]);
  const [loading, setLoading] = useState(false);
  const [fetching, setFetching] = useState(true);

  useEffect(() => {
    async function load() {
      try {
        const [hh, lt, tmpl] = await Promise.all([
          api.getHousehold(householdId),
          api.getLetter(letterId),
          api.getLetterTemplates(),
        ]);
        setHousehold(hh);
        setLetter(lt);
        setSections(lt.sections || []);
        setStatus(lt.status || 'draft');
        setTemplates(tmpl || []);
      } catch (err) {
        notify(err.message, 'error');
      } finally {
        setFetching(false);
      }
    }
    load();
  }, [householdId, letterId, notify]);

  function updateSection(index, field, value) {
    setSections((prev) => {
      const updated = [...prev];
      updated[index] = { ...updated[index], [field]: value };
      return updated;
    });
  }

  function removeSection(index) {
    setSections((prev) => prev.filter((_, i) => i !== index));
  }

  function addSection() {
    setSections((prev) => [...prev, { title: '', content: '', pinned: false }]);
  }

  function addTemplate(template) {
    setSections((prev) => [...prev, { title: template.title, content: template.content, pinned: false }]);
  }

  function moveSection(index, direction) {
    const newIndex = index + direction;
    if (newIndex < 0 || newIndex >= sections.length) return;
    setSections((prev) => {
      const updated = [...prev];
      [updated[index], updated[newIndex]] = [updated[newIndex], updated[index]];
      return updated;
    });
  }

  async function handleSave() {
    setLoading(true);
    try {
      await api.updateLetter(letterId, { sections, status });
      notify('Letter saved', 'success');
    } catch (err) {
      notify(err.message, 'error');
    } finally {
      setLoading(false);
    }
  }

  if (fetching) {
    return (
      <div className="flex items-center justify-center py-12">
        <p className="text-gray-500 text-sm">Loading letter...</p>
      </div>
    );
  }

  return (
    <div className="max-w-4xl">
      <div className="mb-6">
        <button
          onClick={() => navigate(`/households/${householdId}`)}
          className="text-sm text-navy-600 hover:text-navy-800 mb-2 inline-block"
        >
          &larr; Back to {household?.name || 'Household'}
        </button>
        <div className="flex items-center justify-between">
          <h1 className="page-title">Tax Letter — {letter?.tax_year}</h1>
          <a
            href={api.exportUrl.letter(letterId)}
            target="_blank"
            rel="noopener noreferrer"
            className="btn-secondary"
          >
            Export PDF
          </a>
        </div>
      </div>

      <div className="card mb-6">
        <div className="flex items-center gap-4 mb-4">
          <div>
            <label className="label-text">Status</label>
            <select className="input-field" value={status} onChange={(e) => setStatus(e.target.value)}>
              {STATUS_OPTIONS.map((s) => (
                <option key={s.value} value={s.value}>{s.label}</option>
              ))}
            </select>
          </div>
          <div className="flex-1" />
          <div className="flex gap-2">
            <button onClick={addSection} className="btn-secondary text-sm">
              + Blank Section
            </button>
            <div className="relative group">
              <button className="btn-secondary text-sm">+ Template</button>
              <div className="hidden group-hover:block absolute right-0 top-full mt-1 bg-white border border-gray-200 rounded-lg shadow-lg z-10 min-w-[200px]">
                {templates.map((t, i) => (
                  <button
                    key={i}
                    onClick={() => addTemplate(t)}
                    className="block w-full text-left px-4 py-2 text-sm hover:bg-gray-50"
                  >
                    {t.title}
                  </button>
                ))}
              </div>
            </div>
          </div>
        </div>
      </div>

      <div className="space-y-4">
        {sections.map((section, index) => (
          <div key={index} className="card">
            <div className="flex items-center gap-3 mb-3">
              <input
                type="text"
                className="input-field flex-1"
                placeholder="Section title"
                value={section.title}
                onChange={(e) => updateSection(index, 'title', e.target.value)}
              />
              <label className="label-text flex items-center gap-1 whitespace-nowrap">
                <input
                  type="checkbox"
                  checked={section.pinned || false}
                  onChange={(e) => updateSection(index, 'pinned', e.target.checked)}
                />
                Pinned
              </label>
              <button
                onClick={() => moveSection(index, -1)}
                className="text-gray-400 hover:text-navy-600 text-sm"
                disabled={index === 0}
              >
                &uarr;
              </button>
              <button
                onClick={() => moveSection(index, 1)}
                className="text-gray-400 hover:text-navy-600 text-sm"
                disabled={index === sections.length - 1}
              >
                &darr;
              </button>
              <button
                onClick={() => removeSection(index)}
                className="text-red-400 hover:text-red-600 text-sm"
              >
                Remove
              </button>
            </div>
            <textarea
              className="input-field w-full"
              rows={5}
              placeholder="Section content..."
              value={section.content}
              onChange={(e) => updateSection(index, 'content', e.target.value)}
            />
          </div>
        ))}

        {sections.length === 0 && (
          <div className="text-center py-8 text-gray-400">
            No sections yet. Add a blank section or use a template.
          </div>
        )}
      </div>

      <div className="flex gap-3 mt-6">
        <button onClick={handleSave} className="btn-primary" disabled={loading}>
          {loading ? 'Saving...' : 'Save Letter'}
        </button>
        <button className="btn-secondary" onClick={() => navigate(`/households/${householdId}`)}>
          Cancel
        </button>
      </div>
    </div>
  );
}
