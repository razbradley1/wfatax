import React, { useState, useEffect } from 'react';
import { useParams, Link } from 'react-router-dom';
import { api, formatMoney, formatPct } from '../utils/api';
import {
  BarChart, Bar, XAxis, YAxis, Tooltip, ResponsiveContainer,
  PieChart, Pie, Cell, Legend
} from 'recharts';

const BRACKET_COLORS = ['#22c55e', '#84cc16', '#eab308', '#f97316', '#ef4444', '#dc2626', '#991b1b'];
const PIE_COLORS = ['#1e3a5f', '#2563eb', '#3b82f6', '#60a5fa', '#93c5fd', '#bfdbfe', '#6366f1', '#a78bfa'];

function StatCard({ label, value, subtext }) {
  return (
    <div className="stat-card">
      <div className="text-xs text-gray-500 uppercase tracking-wide font-medium">{label}</div>
      <div className="text-2xl font-bold text-navy-900 mt-1">{value}</div>
      {subtext && <div className="text-xs text-gray-400 mt-1">{subtext}</div>}
    </div>
  );
}

function ObservationCard({ obs }) {
  const colors = {
    info: 'bg-blue-50 border-blue-300 text-blue-800',
    warning: 'bg-yellow-50 border-yellow-300 text-yellow-800',
    alert: 'bg-red-50 border-red-300 text-red-800',
    opportunity: 'bg-green-50 border-green-300 text-green-800',
  };
  return (
    <div className={`border-l-4 px-4 py-3 rounded-r-lg text-sm ${colors[obs.severity] || colors.info}`}>
      {obs.text}
    </div>
  );
}

export default function TaxReport() {
  const { householdId, scenarioId } = useParams();
  const [report, setReport] = useState(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    api.getTaxReport(scenarioId).then(setReport).catch(console.error).finally(() => setLoading(false));
  }, [scenarioId]);

  if (loading) return <div className="text-center py-12 text-gray-500">Loading report...</div>;
  if (!report) return <div className="text-center py-12 text-red-500">Failed to load report</div>;

  const { summary, income_breakdown, bracket_details, deductions, capital_gains, observations, magi_thresholds, household, scenario } = report;

  return (
    <div className="max-w-6xl mx-auto space-y-8">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <Link to={`/households/${householdId}`} className="text-sm text-navy-600 hover:underline">&larr; Back to {household?.name}</Link>
          <h1 className="page-title mt-1">Tax Report — {scenario?.tax_year}</h1>
          <p className="text-gray-500 text-sm">{scenario?.name} | {summary?.filing_status?.toUpperCase()}</p>
        </div>
        <a href={api.exportUrl.taxReport(scenarioId)} className="btn-primary" target="_blank" rel="noopener">Export PDF</a>
      </div>

      {/* Summary Cards */}
      <div className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-6 gap-4">
        <StatCard label="Total Income" value={formatMoney(summary?.total_income)} />
        <StatCard label="AGI" value={formatMoney(summary?.agi)} />
        <StatCard label="Taxable Income" value={formatMoney(summary?.taxable_income)} />
        <StatCard label="Federal Tax" value={formatMoney(summary?.total_tax)} />
        <StatCard label="Effective Rate" value={formatPct(summary?.effective_rate)} />
        <StatCard label="Marginal Bracket" value={formatPct(summary?.marginal_bracket_pct)} />
      </div>

      {/* Refund/Owed */}
      {summary?.refund_or_owed != null && (
        <div className={`card text-center ${summary.refund_or_owed >= 0 ? 'bg-green-50 border-green-200' : 'bg-red-50 border-red-200'}`}>
          <div className="text-sm font-medium text-gray-600">{summary.refund_or_owed >= 0 ? 'Refund' : 'Amount Owed'}</div>
          <div className={`text-3xl font-bold ${summary.refund_or_owed >= 0 ? 'text-green-700' : 'text-red-700'}`}>
            {formatMoney(Math.abs(summary.refund_or_owed))}
          </div>
        </div>
      )}

      {/* Income Breakdown */}
      <div className="card">
        <h2 className="section-title">Income Breakdown</h2>
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-8">
          <div className="h-80">
            <ResponsiveContainer width="100%" height="100%">
              <PieChart>
                <Pie data={income_breakdown} dataKey="value" nameKey="label" cx="50%" cy="50%" outerRadius={120} label={({ label, value }) => `${formatMoney(value)}`}>
                  {income_breakdown.map((_, i) => <Cell key={i} fill={PIE_COLORS[i % PIE_COLORS.length]} />)}
                </Pie>
                <Tooltip formatter={(v) => formatMoney(v)} />
                <Legend />
              </PieChart>
            </ResponsiveContainer>
          </div>
          <table className="text-sm">
            <thead><tr><th className="text-left py-2">Source</th><th className="text-right py-2">Amount</th></tr></thead>
            <tbody>
              {income_breakdown.map((item, i) => (
                <tr key={i} className="border-t border-gray-100">
                  <td className="py-2 flex items-center gap-2">
                    <span className="w-3 h-3 rounded-full inline-block" style={{ background: PIE_COLORS[i % PIE_COLORS.length] }} />
                    {item.label}
                  </td>
                  <td className="money py-2">{formatMoney(item.value)}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>

      {/* Bracket Visualization */}
      <div className="card">
        <h2 className="section-title">Tax Bracket Visualization</h2>
        <div className="flex rounded-lg overflow-hidden h-12 mb-4">
          {bracket_details?.filter(b => b.ordinary_income_in_bracket > 0).map((b, i) => {
            const total = bracket_details.reduce((s, x) => s + (x.ordinary_income_in_bracket || 0), 0);
            const pct = total > 0 ? (b.ordinary_income_in_bracket / total) * 100 : 0;
            return (
              <div key={i} className="flex items-center justify-center text-white text-xs font-bold"
                style={{ width: `${Math.max(pct, 5)}%`, background: BRACKET_COLORS[i] }}
                title={`${b.rate_pct}% bracket: ${formatMoney(b.ordinary_income_in_bracket)}`}>
                {b.rate_pct}%
              </div>
            );
          })}
        </div>
        <div className="grid grid-cols-7 gap-2 text-xs">
          {bracket_details?.map((b, i) => (
            <div key={i} className="text-center">
              <div className="w-4 h-4 rounded mx-auto mb-1" style={{ background: BRACKET_COLORS[i] }} />
              <div className="font-semibold">{b.rate_pct}%</div>
              <div className="text-gray-500">{formatMoney(b.ordinary_income_in_bracket)}</div>
              {b.bracket_top && <div className="text-gray-400">up to {formatMoney(b.bracket_top)}</div>}
            </div>
          ))}
        </div>
      </div>

      {/* MAGI Thresholds */}
      <div className="card">
        <h2 className="section-title">MAGI Planning Thresholds</h2>
        <table className="w-full text-sm">
          <thead>
            <tr className="border-b-2 border-gray-200">
              <th className="text-left py-2">Threshold</th>
              <th className="text-right py-2">Start</th>
              <th className="text-right py-2">End</th>
              <th className="text-right py-2">Client MAGI</th>
              <th className="text-center py-2">Status</th>
            </tr>
          </thead>
          <tbody>
            {magi_thresholds?.map((t, i) => (
              <tr key={i} className="border-t border-gray-100">
                <td className="py-2">{t.name}</td>
                <td className="money py-2">{formatMoney(t.start)}</td>
                <td className="money py-2">{t.end ? formatMoney(t.end) : '—'}</td>
                <td className="money py-2">{formatMoney(t.client_magi)}</td>
                <td className="text-center py-2">
                  <span className={`px-2 py-0.5 rounded-full text-xs font-medium ${
                    t.status === 'below' ? 'bg-green-100 text-green-700' :
                    t.status === 'above' ? 'bg-red-100 text-red-700' :
                    'bg-yellow-100 text-yellow-700'
                  }`}>{t.status || '—'}</span>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>

      {/* Deductions */}
      <div className="card">
        <h2 className="section-title">Deductions Summary</h2>
        <div className="grid grid-cols-2 gap-8">
          <div>
            <div className="flex justify-between py-2 border-b"><span>Standard Deduction</span><span className="money">{formatMoney(deductions?.standard_deduction)}</span></div>
            <div className="flex justify-between py-2 border-b"><span>Total Itemized</span><span className="money">{formatMoney(deductions?.total_itemized)}</span></div>
            <div className="flex justify-between py-2 border-b font-semibold">
              <span>Used: {deductions?.deduction_type?.charAt(0).toUpperCase() + deductions?.deduction_type?.slice(1)}</span>
              <span className="money">{formatMoney(deductions?.deduction_used)}</span>
            </div>
            <div className="flex justify-between py-2"><span>QBI Deduction</span><span className="money">{formatMoney(deductions?.qbi_deduction)}</span></div>
          </div>
          {deductions?.deduction_type === 'itemized' && deductions?.itemized_breakdown && (
            <div>
              <h3 className="font-semibold text-sm mb-2">Itemized Breakdown</h3>
              <div className="flex justify-between py-1 text-sm"><span>Medical</span><span className="money">{formatMoney(deductions.itemized_breakdown.medical_deductible)}</span></div>
              <div className="flex justify-between py-1 text-sm"><span>SALT (capped)</span><span className="money">{formatMoney(deductions.itemized_breakdown.salt_capped)}</span></div>
              <div className="flex justify-between py-1 text-sm"><span>Mortgage Interest</span><span className="money">{formatMoney(deductions.itemized_breakdown.mortgage_interest)}</span></div>
              <div className="flex justify-between py-1 text-sm"><span>Charitable</span><span className="money">{formatMoney(deductions.itemized_breakdown.charitable)}</span></div>
            </div>
          )}
        </div>
      </div>

      {/* Capital Gains */}
      <div className="card">
        <h2 className="section-title">Capital Gains Summary</h2>
        <div className="grid grid-cols-2 md:grid-cols-5 gap-4">
          <StatCard label="ST Gains/Losses" value={formatMoney(capital_gains?.st_gains_losses)} />
          <StatCard label="LT Gains/Losses" value={formatMoney(capital_gains?.lt_gains_losses)} />
          <StatCard label="Net Capital" value={formatMoney(capital_gains?.net_capital)} />
          <StatCard label="Loss Carryforward" value={formatMoney(capital_gains?.carryforward)} />
          <StatCard label="Room in 0% LTCG" value={formatMoney(capital_gains?.ltcg_0pct_room)} />
        </div>
      </div>

      {/* Observations */}
      <div className="card">
        <h2 className="section-title">Observations & Planning Notes</h2>
        <div className="space-y-3">
          {observations?.length > 0 ? observations.map((obs, i) => <ObservationCard key={i} obs={obs} />) :
            <p className="text-gray-500 text-sm">No notable observations for this scenario.</p>}
        </div>
      </div>

      {/* Quick Links */}
      <div className="flex gap-3">
        <Link to={`/households/${householdId}/scenarios/${scenarioId}`} className="btn-secondary">Edit Scenario</Link>
        <Link to={`/households/${householdId}/range-calc/${scenarioId}`} className="btn-secondary">Range Calc</Link>
        <Link to={`/households/${householdId}/roth-projection/${scenarioId}`} className="btn-secondary">Roth Projection</Link>
        <Link to={`/households/${householdId}/explainers/${scenarioId}`} className="btn-secondary">Explainers</Link>
      </div>
    </div>
  );
}
