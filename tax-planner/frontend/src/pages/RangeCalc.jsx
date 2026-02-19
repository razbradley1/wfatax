import React, { useState, useEffect } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import { api, formatMoney, formatPct } from '../utils/api';
import useStore from '../hooks/useStore';

const INCOME_TYPES = [
  { value: 'wages_salaries', label: 'Wages & Salaries' },
  { value: 'ira_distributions_taxable', label: 'IRA Distributions (Taxable)' },
  { value: 'capital_gain_loss', label: 'Capital Gain/Loss' },
  { value: 'lt_gains_losses', label: 'Long-Term Gains' },
  { value: 'business_income', label: 'Business Income' },
  { value: 'rental_income', label: 'Rental Income' },
  { value: 'social_security_total', label: 'Social Security' },
  { value: 'other_income', label: 'Other Income' },
];

export default function RangeCalc() {
  const { householdId, scenarioId } = useParams();
  const navigate = useNavigate();
  const notify = useStore((s) => s.notify);

  const [household, setHousehold] = useState(null);
  const [scenario, setScenario] = useState(null);
  const [incomeType, setIncomeType] = useState('ira_distributions_taxable');
  const [startAmount, setStartAmount] = useState(0);
  const [endAmount, setEndAmount] = useState(200000);
  const [step, setStep] = useState(5000);
  const [results, setResults] = useState(null);
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

  async function handleCalculate(e) {
    e.preventDefault();
    setLoading(true);
    try {
      const result = await api.rangeCalc(scenarioId, {
        income_type: incomeType,
        start_amount: startAmount,
        end_amount: endAmount,
        step,
      });
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

  return (
    <div className="max-w-4xl">
      <div className="mb-6">
        <button
          onClick={() => navigate(`/households/${householdId}`)}
          className="text-sm text-navy-600 hover:text-navy-800 mb-2 inline-block"
        >
          &larr; Back to {household?.name || 'Household'}
        </button>
        <h1 className="page-title">Marginal Rate Range Calculator</h1>
        <p className="text-gray-500 text-sm mt-1">
          Scenario: {scenario?.name} ({scenario?.tax_year})
        </p>
      </div>

      <form onSubmit={handleCalculate} className="card space-y-4 mb-6">
        <div className="grid grid-cols-2 gap-4">
          <div>
            <label className="label-text">Income Type</label>
            <select className="input-field" value={incomeType} onChange={(e) => setIncomeType(e.target.value)}>
              {INCOME_TYPES.map((t) => (
                <option key={t.value} value={t.value}>{t.label}</option>
              ))}
            </select>
          </div>
          <div>
            <label className="label-text">Step Size</label>
            <input
              type="number"
              className="input-field"
              value={step}
              onChange={(e) => setStep(parseInt(e.target.value) || 1000)}
            />
          </div>
        </div>
        <div className="grid grid-cols-2 gap-4">
          <div>
            <label className="label-text">Start Amount</label>
            <input
              type="number"
              className="input-field"
              value={startAmount}
              onChange={(e) => setStartAmount(parseInt(e.target.value) || 0)}
            />
          </div>
          <div>
            <label className="label-text">End Amount</label>
            <input
              type="number"
              className="input-field"
              value={endAmount}
              onChange={(e) => setEndAmount(parseInt(e.target.value) || 200000)}
            />
          </div>
        </div>
        <button type="submit" className="btn-primary" disabled={loading}>
          {loading ? 'Calculating...' : 'Calculate Range'}
        </button>
      </form>

      {results && results.data_points && (
        <div className="card overflow-x-auto">
          <h2 className="text-lg font-semibold text-navy-800 mb-4">
            Results: {INCOME_TYPES.find((t) => t.value === (results.income_type || incomeType))?.label}
          </h2>
          <table className="w-full text-sm">
            <thead>
              <tr className="border-b border-gray-200">
                <th className="text-left py-2 px-3 text-navy-800 font-semibold">Additional Income</th>
                <th className="text-right py-2 px-3 text-navy-800 font-semibold">Total Tax</th>
                <th className="text-right py-2 px-3 text-navy-800 font-semibold">Marginal Rate</th>
                <th className="text-right py-2 px-3 text-navy-800 font-semibold">Effective Rate</th>
                <th className="text-right py-2 px-3 text-navy-800 font-semibold">Tax on Additional</th>
              </tr>
            </thead>
            <tbody>
              {results.data_points.map((dp, i) => (
                <tr key={i} className="border-b border-gray-100 hover:bg-gray-50">
                  <td className="py-2 px-3 font-mono">{formatMoney(dp.additional_income)}</td>
                  <td className="py-2 px-3 text-right font-mono">{formatMoney(dp.total_tax)}</td>
                  <td className="py-2 px-3 text-right font-mono">{formatPct(dp.marginal_rate)}</td>
                  <td className="py-2 px-3 text-right font-mono">{formatPct(dp.effective_rate)}</td>
                  <td className="py-2 px-3 text-right font-mono">{formatMoney(dp.tax_on_additional)}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </div>
  );
}
