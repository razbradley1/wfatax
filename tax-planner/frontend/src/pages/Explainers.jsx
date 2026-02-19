import React, { useState, useEffect } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import { api } from '../utils/api';
import useStore from '../hooks/useStore';

const EXPLAINER_TYPES = [
  { key: 'tax', label: 'Tax Return Explainer', description: 'Line-by-line Form 1040 breakdown' },
  { key: 'roth', label: 'Roth Conversion Guide', description: 'Roth conversion analysis and guidance' },
  { key: 'qcd', label: 'QCD Guide', description: 'Qualified Charitable Distribution overview' },
  { key: 'daf', label: 'DAF Guide', description: 'Donor Advised Fund strategy overview' },
];

export default function Explainers() {
  const { householdId, scenarioId } = useParams();
  const navigate = useNavigate();
  const notify = useStore((s) => s.notify);

  const [household, setHousehold] = useState(null);
  const [scenario, setScenario] = useState(null);
  const [activeType, setActiveType] = useState('tax');
  const [content, setContent] = useState(null);
  const [loading, setLoading] = useState(false);
  const [fetching, setFetching] = useState(true);

  useEffect(() => {
    async function load() {
      try {
        const [hh, sc] = await Promise.all([
          api.getHousehold(householdId),
          api.getScenario(scenarioId),
        ]);
        setHousehold(hh);
        setScenario(sc);
      } catch (err) {
        notify(err.message, 'error');
      } finally {
        setFetching(false);
      }
    }
    load();
  }, [householdId, scenarioId, notify]);

  useEffect(() => {
    async function loadExplainer() {
      setLoading(true);
      setContent(null);
      try {
        const fetchers = {
          tax: api.getTaxExplainer,
          roth: api.getRothExplainer,
          qcd: api.getQcdExplainer,
          daf: api.getDafExplainer,
        };
        const result = await fetchers[activeType](scenarioId);
        setContent(result);
      } catch (err) {
        notify(err.message, 'error');
      } finally {
        setLoading(false);
      }
    }
    if (!fetching) loadExplainer();
  }, [activeType, scenarioId, fetching, notify]);

  if (fetching) {
    return (
      <div className="flex items-center justify-center py-12">
        <p className="text-gray-500 text-sm">Loading...</p>
      </div>
    );
  }

  function renderContent() {
    if (loading) {
      return <p className="text-gray-500 text-sm py-8 text-center">Loading explainer...</p>;
    }
    if (!content) return null;

    if (content.sections) {
      return (
        <div className="space-y-6">
          {content.sections.map((section, i) => (
            <div key={i}>
              <h3 className="text-lg font-semibold text-navy-800 mb-2">{section.title}</h3>
              {section.items ? (
                <ul className="space-y-2">
                  {section.items.map((item, j) => (
                    <li key={j} className="text-sm text-gray-700 pl-4 border-l-2 border-navy-200">
                      {item.label && <span className="font-medium">{item.label}: </span>}
                      {item.value || item.text || item.description || (typeof item === 'string' ? item : '')}
                    </li>
                  ))}
                </ul>
              ) : section.content ? (
                <p className="text-sm text-gray-700 whitespace-pre-wrap">{section.content}</p>
              ) : null}
            </div>
          ))}
        </div>
      );
    }

    if (content.lines) {
      return (
        <div className="space-y-2">
          {content.lines.map((line, i) => (
            <div key={i} className="flex justify-between text-sm py-1 border-b border-gray-100">
              <span className="text-gray-700">
                {line.line_number && <span className="font-mono text-gray-400 mr-2">L{line.line_number}</span>}
                {line.label}
              </span>
              <span className="font-mono font-medium">{line.value}</span>
            </div>
          ))}
        </div>
      );
    }

    return <pre className="text-sm text-gray-700 whitespace-pre-wrap">{JSON.stringify(content, null, 2)}</pre>;
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
        <h1 className="page-title">Explainers</h1>
        <p className="text-gray-500 text-sm mt-1">
          Scenario: {scenario?.name} ({scenario?.tax_year})
        </p>
      </div>

      <div className="flex gap-2 mb-6">
        {EXPLAINER_TYPES.map((t) => (
          <button
            key={t.key}
            onClick={() => setActiveType(t.key)}
            className={`px-4 py-2 rounded-lg text-sm font-medium transition-colors ${
              activeType === t.key
                ? 'bg-navy-800 text-white'
                : 'bg-gray-100 text-gray-600 hover:bg-gray-200'
            }`}
          >
            {t.label}
          </button>
        ))}
      </div>

      <div className="card">
        <div className="flex items-center justify-between mb-4">
          <h2 className="text-lg font-semibold text-navy-800">
            {EXPLAINER_TYPES.find((t) => t.key === activeType)?.label}
          </h2>
          <a
            href={api.exportUrl.explainer(activeType, scenarioId)}
            target="_blank"
            rel="noopener noreferrer"
            className="btn-secondary text-sm"
          >
            Export PDF
          </a>
        </div>
        {renderContent()}
      </div>
    </div>
  );
}
