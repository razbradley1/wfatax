import React, { useState, useEffect } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import { api, formatMoney, formatPct } from '../utils/api';
import useStore from '../hooks/useStore';

export default function RothProjection() {
  const { householdId, scenarioId } = useParams();
  const navigate = useNavigate();
  const notify = useStore((s) => s.notify);

  const [household, setHousehold] = useState(null);
  const [scenario, setScenario] = useState(null);
  const [fetching, setFetching] = useState(true);
  const [loading, setLoading] = useState(false);
  const [results, setResults] = useState(null);

  const [form, setForm] = useState({
    current_age: 55,
    retirement_age: 65,
    target_end_age: 90,
    pretax_balance: 500000,
    roth_balance: 100000,
    taxable_balance: 0,
    annual_return: 0.07,
    expected_retirement_income: 50000,
    target_bracket_rate: 0.22,
    annual_contribution_pretax: 0,
    annual_contribution_roth: 0,
  });

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

  function handleChange(key, value) {
    const num = value === '' ? 0 : parseFloat(value);
    setForm((prev) => ({ ...prev, [key]: isNaN(num) ? 0 : num }));
  }

  async function handleSubmit(e) {
    e.preventDefault();
    setLoading(true);
    try {
      const result = await api.rothProjection(scenarioId, form);
      setResults(result);
    } catch (err) {
      notify(err.message, 'error');
    } finally {
      setLoading(false);
    }
  }

  if (fetching) {
    return (
      <div className="flex items-center justify-center py-12">
        <p className="text-gray-500 text-sm">Loading...</p>
      </div>
    );
  }

  const inputFields = [
    { key: 'current_age', label: 'Current Age', step: '1' },
    { key: 'retirement_age', label: 'Retirement Age', step: '1' },
    { key: 'target_end_age', label: 'Target End Age', step: '1' },
    { key: 'pretax_balance', label: 'Pre-Tax Balance' },
    { key: 'roth_balance', label: 'Roth Balance' },
    { key: 'taxable_balance', label: 'Taxable Balance' },
    { key: 'annual_return', label: 'Annual Return (decimal)', step: '0.01' },
    { key: 'expected_retirement_income', label: 'Expected Retirement Income' },
    { key: 'target_bracket_rate', label: 'Target Bracket Rate (decimal)', step: '0.01' },
    { key: 'annual_contribution_pretax', label: 'Annual Pre-Tax Contribution' },
    { key: 'annual_contribution_roth', label: 'Annual Roth Contribution' },
  ];

  return (
    <div className="max-w-4xl">
      <div className="mb-6">
        <button
          onClick={() => navigate(`/households/${householdId}`)}
          className="text-sm text-navy-600 hover:text-navy-800 mb-2 inline-block"
        >
          &larr; Back to {household?.name || 'Household'}
        </button>
        <h1 className="page-title">Roth Conversion Projection</h1>
        <p className="text-gray-500 text-sm mt-1">
          Scenario: {scenario?.name} ({scenario?.tax_year})
        </p>
      </div>

      <form onSubmit={handleSubmit} className="card space-y-4 mb-6">
        <div className="grid grid-cols-3 gap-4">
          {inputFields.map((f) => (
            <div key={f.key}>
              <label className="label-text">{f.label}</label>
              <input
                type="number"
                step={f.step || 'any'}
                className="input-field"
                value={form[f.key]}
                onChange={(e) => handleChange(f.key, e.target.value)}
              />
            </div>
          ))}
        </div>
        <button type="submit" className="btn-primary" disabled={loading}>
          {loading ? 'Projecting...' : 'Run Projection'}
        </button>
      </form>

      {results && (
        <div className="card space-y-4">
          <h2 className="text-lg font-semibold text-navy-800">Projection Results</h2>

          {results.summary && (
            <div className="grid grid-cols-3 gap-4 mb-4">
              {Object.entries(results.summary).map(([key, val]) => (
                <div key={key} className="bg-gray-50 rounded-lg p-3">
                  <p className="text-xs text-gray-500 capitalize">{key.replace(/_/g, ' ')}</p>
                  <p className="text-lg font-semibold text-navy-800">
                    {typeof val === 'number' ? (val < 1 ? formatPct(val * 100) : formatMoney(val)) : String(val)}
                  </p>
                </div>
              ))}
            </div>
          )}

          {results.yearly_data && (
            <div className="overflow-x-auto">
              <table className="w-full text-sm">
                <thead>
                  <tr className="border-b border-gray-200">
                    <th className="text-left py-2 px-3 text-navy-800 font-semibold">Age</th>
                    <th className="text-right py-2 px-3 text-navy-800 font-semibold">Pre-Tax</th>
                    <th className="text-right py-2 px-3 text-navy-800 font-semibold">Roth</th>
                    <th className="text-right py-2 px-3 text-navy-800 font-semibold">Conversion</th>
                    <th className="text-right py-2 px-3 text-navy-800 font-semibold">Tax Cost</th>
                  </tr>
                </thead>
                <tbody>
                  {results.yearly_data.map((row, i) => (
                    <tr key={i} className="border-b border-gray-100 hover:bg-gray-50">
                      <td className="py-2 px-3">{row.age}</td>
                      <td className="py-2 px-3 text-right font-mono">{formatMoney(row.pretax_balance)}</td>
                      <td className="py-2 px-3 text-right font-mono">{formatMoney(row.roth_balance)}</td>
                      <td className="py-2 px-3 text-right font-mono">{formatMoney(row.conversion_amount)}</td>
                      <td className="py-2 px-3 text-right font-mono">{formatMoney(row.tax_cost)}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </div>
      )}
    </div>
  );
}
