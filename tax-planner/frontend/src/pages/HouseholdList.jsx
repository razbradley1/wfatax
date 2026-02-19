import React, { useState, useEffect } from 'react';
import { Link, useNavigate } from 'react-router-dom';
import { api, formatMoney, formatPct } from '../utils/api';
import useStore from '../hooks/useStore';

const FILING_STATUSES = [
  { value: '', label: 'All Statuses' },
  { value: 'single', label: 'Single' },
  { value: 'married_filing_jointly', label: 'Married Filing Jointly' },
  { value: 'married_filing_separately', label: 'Married Filing Separately' },
  { value: 'head_of_household', label: 'Head of Household' },
  { value: 'qualifying_widow', label: 'Qualifying Surviving Spouse' },
];

function formatFilingStatus(status) {
  if (!status) return '--';
  const found = FILING_STATUSES.find((s) => s.value === status);
  if (found) return found.label;
  return status
    .replace(/_/g, ' ')
    .replace(/\b\w/g, (c) => c.toUpperCase());
}

function formatDate(dateStr) {
  if (!dateStr) return '--';
  const d = new Date(dateStr);
  return d.toLocaleDateString('en-US', {
    month: 'short',
    day: 'numeric',
    year: 'numeric',
  });
}

export default function HouseholdList() {
  const navigate = useNavigate();
  const { setHouseholds, notify } = useStore();

  const [households, setLocalHouseholds] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [search, setSearch] = useState('');
  const [statusFilter, setStatusFilter] = useState('');

  useEffect(() => {
    fetchHouseholds();
  }, []);

  async function fetchHouseholds() {
    setLoading(true);
    setError(null);
    try {
      const data = await api.getHouseholds();
      const list = Array.isArray(data) ? data : data.households || [];
      setLocalHouseholds(list);
      setHouseholds(list);
    } catch (err) {
      setError(err.message || 'Failed to load households');
      notify(err.message || 'Failed to load households', 'error');
    } finally {
      setLoading(false);
    }
  }

  const filtered = households.filter((h) => {
    const nameMatch =
      !search ||
      (h.name || '').toLowerCase().includes(search.toLowerCase());
    const statusMatch =
      !statusFilter || h.filing_status === statusFilter;
    return nameMatch && statusMatch;
  });

  return (
    <div>
      {/* Header */}
      <div className="flex items-center justify-between mb-6">
        <div>
          <h1 className="page-title">Households</h1>
          <p className="text-sm text-slate-500 mt-1">
            Manage client households and tax planning
          </p>
        </div>
        <Link to="/households/new" className="btn-primary inline-flex items-center gap-2">
          <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 4v16m8-8H4" />
          </svg>
          New Household
        </Link>
      </div>

      {/* Filters */}
      <div className="card mb-6">
        <div className="flex flex-col sm:flex-row gap-4">
          <div className="flex-1">
            <label htmlFor="search" className="sr-only">Search households</label>
            <div className="relative">
              <svg
                className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-slate-400"
                fill="none"
                stroke="currentColor"
                viewBox="0 0 24 24"
              >
                <path
                  strokeLinecap="round"
                  strokeLinejoin="round"
                  strokeWidth={2}
                  d="M21 21l-6-6m2-5a7 7 0 11-14 0 7 7 0 0114 0z"
                />
              </svg>
              <input
                id="search"
                type="text"
                placeholder="Search by name..."
                value={search}
                onChange={(e) => setSearch(e.target.value)}
                className="input-field pl-10"
              />
            </div>
          </div>
          <div className="sm:w-64">
            <label htmlFor="status-filter" className="sr-only">Filter by filing status</label>
            <select
              id="status-filter"
              value={statusFilter}
              onChange={(e) => setStatusFilter(e.target.value)}
              className="input-field"
            >
              {FILING_STATUSES.map((s) => (
                <option key={s.value} value={s.value}>
                  {s.label}
                </option>
              ))}
            </select>
          </div>
        </div>
      </div>

      {/* Loading State */}
      {loading && (
        <div className="card text-center py-12">
          <div className="inline-block w-8 h-8 border-4 border-navy-200 border-t-navy-800 rounded-full animate-spin" />
          <p className="mt-3 text-sm text-slate-500">Loading households...</p>
        </div>
      )}

      {/* Error State */}
      {error && !loading && (
        <div className="card border-red-200 bg-red-50 text-center py-8">
          <p className="text-red-700 font-medium">{error}</p>
          <button
            onClick={fetchHouseholds}
            className="mt-3 text-sm text-red-600 underline hover:text-red-800"
          >
            Retry
          </button>
        </div>
      )}

      {/* Empty State */}
      {!loading && !error && households.length === 0 && (
        <div className="card text-center py-12">
          <svg
            className="mx-auto w-12 h-12 text-slate-300"
            fill="none"
            stroke="currentColor"
            viewBox="0 0 24 24"
          >
            <path
              strokeLinecap="round"
              strokeLinejoin="round"
              strokeWidth={1.5}
              d="M17 20h5v-2a3 3 0 00-5.356-1.857M17 20H7m10 0v-2c0-.656-.126-1.283-.356-1.857M7 20H2v-2a3 3 0 015.356-1.857M7 20v-2c0-.656.126-1.283.356-1.857m0 0a5.002 5.002 0 019.288 0M15 7a3 3 0 11-6 0 3 3 0 016 0z"
            />
          </svg>
          <h3 className="mt-4 text-lg font-semibold text-navy-800">No households yet</h3>
          <p className="mt-1 text-sm text-slate-500">
            Get started by creating your first household.
          </p>
          <Link to="/households/new" className="btn-primary inline-block mt-4">
            Create Household
          </Link>
        </div>
      )}

      {/* No Results from Filter */}
      {!loading && !error && households.length > 0 && filtered.length === 0 && (
        <div className="card text-center py-8">
          <p className="text-slate-500 text-sm">
            No households match your search criteria.
          </p>
          <button
            onClick={() => {
              setSearch('');
              setStatusFilter('');
            }}
            className="mt-2 text-sm text-navy-600 underline hover:text-navy-800"
          >
            Clear filters
          </button>
        </div>
      )}

      {/* Table */}
      {!loading && !error && filtered.length > 0 && (
        <div className="card p-0 overflow-hidden">
          <div className="overflow-x-auto">
            <table className="w-full text-sm">
              <thead>
                <tr className="bg-slate-50 border-b border-gray-200">
                  <th className="text-left px-6 py-3 font-semibold text-navy-800">Name</th>
                  <th className="text-left px-6 py-3 font-semibold text-navy-800">Filing Status</th>
                  <th className="text-left px-6 py-3 font-semibold text-navy-800">Tax Year</th>
                  <th className="text-right px-6 py-3 font-semibold text-navy-800">AGI</th>
                  <th className="text-right px-6 py-3 font-semibold text-navy-800">Marginal Bracket</th>
                  <th className="text-right px-6 py-3 font-semibold text-navy-800">Effective Rate</th>
                  <th className="text-right px-6 py-3 font-semibold text-navy-800">Carryforward Loss</th>
                  <th className="text-left px-6 py-3 font-semibold text-navy-800">Last Updated</th>
                  <th className="text-center px-6 py-3 font-semibold text-navy-800">Actions</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-gray-100">
                {filtered.map((h) => (
                  <tr
                    key={h.id}
                    onClick={() => navigate(`/households/${h.id}`)}
                    className="hover:bg-navy-50/50 cursor-pointer transition-colors"
                  >
                    <td className="px-6 py-4 font-medium text-navy-900 whitespace-nowrap">
                      {h.name || '--'}
                    </td>
                    <td className="px-6 py-4 text-slate-600 whitespace-nowrap">
                      {formatFilingStatus(h.filing_status)}
                    </td>
                    <td className="px-6 py-4 text-slate-600 whitespace-nowrap">
                      {h.tax_year || '--'}
                    </td>
                    <td className="px-6 py-4 money whitespace-nowrap">
                      {formatMoney(h.agi)}
                    </td>
                    <td className="px-6 py-4 money whitespace-nowrap">
                      {h.marginal_bracket != null ? formatPct(h.marginal_bracket) : '--'}
                    </td>
                    <td className="px-6 py-4 money whitespace-nowrap">
                      {h.effective_rate != null ? formatPct(h.effective_rate) : '--'}
                    </td>
                    <td className="px-6 py-4 money whitespace-nowrap">
                      {h.carryforward_loss != null ? formatMoney(h.carryforward_loss) : '--'}
                    </td>
                    <td className="px-6 py-4 text-slate-500 whitespace-nowrap">
                      {formatDate(h.updated_at)}
                    </td>
                    <td className="px-6 py-4 whitespace-nowrap text-center">
                      <div
                        className="inline-flex items-center gap-2"
                        onClick={(e) => e.stopPropagation()}
                      >
                        <Link
                          to={`/households/${h.id}/report/${h.latest_scenario_id || ''}`}
                          className="text-xs font-medium text-navy-600 hover:text-navy-800 px-2 py-1 rounded hover:bg-navy-50"
                        >
                          Report
                        </Link>
                        <Link
                          to={`/households/${h.id}/scenarios`}
                          className="text-xs font-medium text-navy-600 hover:text-navy-800 px-2 py-1 rounded hover:bg-navy-50"
                        >
                          Scenarios
                        </Link>
                        <Link
                          to={`/households/${h.id}/letters/${h.latest_letter_id || 'new'}`}
                          className="text-xs font-medium text-navy-600 hover:text-navy-800 px-2 py-1 rounded hover:bg-navy-50"
                        >
                          Letter
                        </Link>
                      </div>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>

          {/* Result count */}
          <div className="px-6 py-3 border-t border-gray-100 bg-slate-50 text-xs text-slate-500">
            Showing {filtered.length} of {households.length} household{households.length !== 1 ? 's' : ''}
          </div>
        </div>
      )}
    </div>
  );
}
