import React, { useState, useEffect } from 'react';
import { useParams, useNavigate, useSearchParams } from 'react-router-dom';
import { api, formatMoney, formatPct } from '../utils/api';
import useStore from '../hooks/useStore';

export default function ScenarioCompare() {
  const { householdId } = useParams();
  const [searchParams] = useSearchParams();
  const navigate = useNavigate();
  const notify = useStore((s) => s.notify);

  const [household, setHousehold] = useState(null);
  const [comparison, setComparison] = useState(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    async function load() {
      try {
        const ids = searchParams.get('ids');
        if (!ids) {
          notify('No scenario IDs provided', 'error');
          navigate(`/households/${householdId}`);
          return;
        }
        const scenarioIds = ids.split(',').map(Number);
        const [hh, result] = await Promise.all([
          api.getHousehold(householdId),
          api.compareScenarios(scenarioIds),
        ]);
        setHousehold(hh);
        setComparison(result);
      } catch (err) {
        notify(err.message, 'error');
      } finally {
        setLoading(false);
      }
    }
    load();
  }, [householdId, searchParams, navigate, notify]);

  if (loading) {
    return (
      <div className="flex items-center justify-center py-12">
        <p className="text-gray-500 text-sm">Loading comparison...</p>
      </div>
    );
  }

  if (!comparison) return null;

  const { scenarios, comparison_fields } = comparison;

  const DISPLAY_FIELDS = [
    { key: 'total_income', label: 'Total Income', fmt: formatMoney },
    { key: 'agi', label: 'Adjusted Gross Income', fmt: formatMoney },
    { key: 'taxable_income', label: 'Taxable Income', fmt: formatMoney },
    { key: 'deduction_used', label: 'Deduction Used', fmt: formatMoney },
    { key: 'total_tax', label: 'Federal Tax', fmt: formatMoney },
    { key: 'effective_rate', label: 'Effective Rate', fmt: formatPct },
    { key: 'marginal_bracket_pct', label: 'Marginal Bracket', fmt: formatPct },
    { key: 'se_tax', label: 'SE Tax', fmt: formatMoney },
    { key: 'niit', label: 'NIIT', fmt: formatMoney },
    { key: 'amt', label: 'AMT', fmt: formatMoney },
    { key: 'federal_withholding', label: 'Withholding', fmt: formatMoney },
    { key: 'estimated_tax_payments', label: 'Estimated Payments', fmt: formatMoney },
    { key: 'refund_or_owed', label: 'Refund / Owed', fmt: formatMoney },
  ];

  function getDelta(fieldKey) {
    const cf = (comparison_fields || []).find((f) => f.field === fieldKey);
    return cf ? cf.delta : null;
  }

  return (
    <div className="max-w-5xl">
      <div className="mb-6">
        <button
          onClick={() => navigate(`/households/${householdId}`)}
          className="text-sm text-navy-600 hover:text-navy-800 mb-2 inline-block"
        >
          &larr; Back to {household?.name || 'Household'}
        </button>
        <h1 className="page-title">Scenario Comparison</h1>
      </div>

      <div className="card overflow-x-auto">
        <table className="w-full text-sm">
          <thead>
            <tr className="border-b border-gray-200">
              <th className="text-left py-3 px-4 text-navy-800 font-semibold">Field</th>
              {scenarios.map((sc) => (
                <th key={sc.id} className="text-right py-3 px-4 text-navy-800 font-semibold">
                  {sc.name}
                  <span className="block text-xs font-normal text-gray-500">{sc.tax_year}</span>
                </th>
              ))}
              {scenarios.length === 2 && (
                <th className="text-right py-3 px-4 text-navy-800 font-semibold">Difference</th>
              )}
            </tr>
          </thead>
          <tbody>
            {DISPLAY_FIELDS.map((field) => {
              const delta = scenarios.length === 2 ? getDelta(field.key) : null;
              return (
                <tr key={field.key} className="border-b border-gray-100 hover:bg-gray-50">
                  <td className="py-3 px-4 text-gray-700 font-medium">{field.label}</td>
                  {scenarios.map((sc) => {
                    const val = sc.calculated_outputs?.[field.key];
                    return (
                      <td key={sc.id} className="py-3 px-4 text-right font-mono">
                        {val != null ? field.fmt(val) : '—'}
                      </td>
                    );
                  })}
                  {scenarios.length === 2 && (
                    <td className={`py-3 px-4 text-right font-mono font-semibold ${
                      delta > 0 ? 'text-red-600' : delta < 0 ? 'text-green-600' : 'text-gray-500'
                    }`}>
                      {delta != null ? field.fmt(delta) : '—'}
                    </td>
                  )}
                </tr>
              );
            })}
          </tbody>
        </table>
      </div>
    </div>
  );
}
