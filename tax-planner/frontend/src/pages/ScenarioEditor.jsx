import React, { useState, useEffect, useCallback } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import { api, formatMoney, formatPct } from '../utils/api';
import useStore from '../hooks/useStore';

const INCOME_FIELDS = [
  { key: 'wages_salaries', label: 'Wages & Salaries' },
  { key: 'interest_income_taxable', label: 'Taxable Interest' },
  { key: 'ordinary_dividends', label: 'Ordinary Dividends' },
  { key: 'qualified_dividends', label: 'Qualified Dividends' },
  { key: 'ira_distributions_total', label: 'IRA Distributions (Total)' },
  { key: 'ira_distributions_taxable', label: 'IRA Distributions (Taxable)' },
  { key: 'pension_annuity_total', label: 'Pensions/Annuities (Total)' },
  { key: 'pension_annuity_taxable', label: 'Pensions/Annuities (Taxable)' },
  { key: 'social_security_total', label: 'Social Security (Total)' },
  { key: 'capital_gain_loss', label: 'Capital Gain/Loss (Net)' },
  { key: 'st_gains_losses', label: 'Short-Term Gains/Losses' },
  { key: 'lt_gains_losses', label: 'Long-Term Gains/Losses' },
  { key: 'business_income', label: 'Business Income' },
  { key: 'rental_income', label: 'Rental Income' },
  { key: 'k1_income', label: 'K-1 Income' },
  { key: 'other_income', label: 'Other Income' },
];

const ADJUSTMENT_FIELDS = [
  { key: 'se_health_insurance_deduction', label: 'SE Health Insurance' },
  { key: 'ira_deduction', label: 'IRA Deduction' },
  { key: 'student_loan_interest', label: 'Student Loan Interest' },
  { key: 'other_adjustments', label: 'Other Adjustments' },
];

const DEDUCTION_FIELDS = [
  { key: 'medical_expenses', label: 'Medical Expenses' },
  { key: 'state_local_taxes', label: 'SALT' },
  { key: 'mortgage_interest', label: 'Mortgage Interest' },
  { key: 'charitable_contributions', label: 'Charitable Contributions' },
  { key: 'other_itemized', label: 'Other Itemized' },
];

const CREDIT_FIELDS = [
  { key: 'num_qualifying_children', label: 'Qualifying Children', type: 'int' },
  { key: 'education_credits', label: 'Education Credits' },
  { key: 'retirement_contributions_for_credit', label: 'Retirement Contributions Credit' },
  { key: 'other_credits', label: 'Other Credits' },
];

const PAYMENT_FIELDS = [
  { key: 'federal_withholding', label: 'Federal Withholding' },
  { key: 'estimated_tax_payments', label: 'Estimated Tax Payments' },
  { key: 'other_payments', label: 'Other Payments' },
];

export default function ScenarioEditor() {
  const { householdId, scenarioId } = useParams();
  const navigate = useNavigate();
  const notify = useStore((s) => s.notify);

  const [scenario, setScenario] = useState(null);
  const [household, setHousehold] = useState(null);
  const [inputs, setInputs] = useState({});
  const [name, setName] = useState('');
  const [notes, setNotes] = useState('');
  const [preview, setPreview] = useState(null);
  const [loading, setLoading] = useState(false);
  const [fetching, setFetching] = useState(true);
  const [previewTimer, setPreviewTimer] = useState(null);

  useEffect(() => {
    async function load() {
      try {
        const [hh, sc] = await Promise.all([
          api.getHousehold(householdId),
          api.getScenario(scenarioId),
        ]);
        setHousehold(hh);
        setScenario(sc);
        setInputs(sc.inputs || {});
        setName(sc.name);
        setNotes(sc.notes || '');
        setPreview(sc.calculated_outputs || null);
      } catch (err) {
        notify(err.message, 'error');
      } finally {
        setFetching(false);
      }
    }
    load();
  }, [householdId, scenarioId, notify]);

  const runPreview = useCallback(
    (currentInputs) => {
      if (previewTimer) clearTimeout(previewTimer);
      const timer = setTimeout(async () => {
        try {
          const result = await api.quickCalc(currentInputs);
          setPreview(result);
        } catch {}
      }, 600);
      setPreviewTimer(timer);
    },
    [previewTimer],
  );

  function handleFieldChange(key, value, isInt) {
    const num = value === '' ? 0 : isInt ? parseInt(value) : parseFloat(value);
    const newInputs = { ...inputs, [key]: isNaN(num) ? 0 : num };
    setInputs(newInputs);
    if (!scenario?.is_readonly) runPreview(newInputs);
  }

  async function handleSave() {
    if (scenario?.is_readonly) return;
    setLoading(true);
    try {
      const updated = await api.updateScenario(scenarioId, { name, inputs, notes });
      setScenario(updated);
      setPreview(updated.calculated_outputs || null);
      notify('Scenario saved', 'success');
    } catch (err) {
      notify(err.message, 'error');
    } finally {
      setLoading(false);
    }
  }

  function renderFieldGroup(title, fields) {
    return (
      <fieldset className="space-y-3">
        <legend className="text-lg font-semibold text-navy-800 border-b border-gray-200 pb-2 mb-4">
          {title}
        </legend>
        <div className="grid grid-cols-2 gap-4">
          {fields.map((f) => (
            <div key={f.key}>
              <label htmlFor={f.key} className="label-text">{f.label}</label>
              <input
                id={f.key}
                type="number"
                step={f.type === 'int' ? '1' : 'any'}
                className="input-field"
                value={inputs[f.key] || ''}
                onChange={(e) => handleFieldChange(f.key, e.target.value, f.type === 'int')}
                disabled={scenario?.is_readonly}
                placeholder="0"
              />
            </div>
          ))}
        </div>
      </fieldset>
    );
  }

  if (fetching) {
    return (
      <div className="flex items-center justify-center py-12">
        <p className="text-gray-500 text-sm">Loading scenario...</p>
      </div>
    );
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
        <div className="flex items-center justify-between">
          <h1 className="page-title">{scenario?.is_readonly ? 'View Scenario (Read-Only)' : 'Edit Scenario'}</h1>
          <div className="flex gap-2">
            <button
              onClick={() => navigate(`/households/${householdId}/report/${scenarioId}`)}
              className="btn-secondary"
            >
              View Report
            </button>
            <button
              onClick={() => navigate(`/households/${householdId}/range-calc/${scenarioId}`)}
              className="btn-secondary"
            >
              Range Calc
            </button>
          </div>
        </div>
      </div>

      <div className="grid grid-cols-3 gap-6">
        <div className="col-span-2 space-y-6">
          <div className="card space-y-4">
            <div className="grid grid-cols-2 gap-4">
              <div>
                <label className="label-text">Scenario Name</label>
                <input
                  type="text"
                  className="input-field"
                  value={name}
                  onChange={(e) => setName(e.target.value)}
                  disabled={scenario?.is_readonly}
                />
              </div>
              <div>
                <label className="label-text">Tax Year</label>
                <input type="text" className="input-field" value={scenario?.tax_year || ''} disabled />
              </div>
            </div>
          </div>

          <div className="card space-y-6">
            {renderFieldGroup('Income', INCOME_FIELDS)}
            {renderFieldGroup('Adjustments', ADJUSTMENT_FIELDS)}

            <fieldset className="space-y-3">
              <legend className="text-lg font-semibold text-navy-800 border-b border-gray-200 pb-2 mb-4">
                Deductions
              </legend>
              <label className="label-text flex items-center gap-2 mb-3">
                <input
                  type="checkbox"
                  checked={inputs.use_itemized || false}
                  onChange={(e) => {
                    const newInputs = { ...inputs, use_itemized: e.target.checked };
                    setInputs(newInputs);
                    if (!scenario?.is_readonly) runPreview(newInputs);
                  }}
                  disabled={scenario?.is_readonly}
                />
                Use Itemized Deductions
              </label>
              {inputs.use_itemized && (
                <div className="grid grid-cols-2 gap-4">
                  {DEDUCTION_FIELDS.map((f) => (
                    <div key={f.key}>
                      <label htmlFor={f.key} className="label-text">{f.label}</label>
                      <input
                        id={f.key}
                        type="number"
                        step="any"
                        className="input-field"
                        value={inputs[f.key] || ''}
                        onChange={(e) => handleFieldChange(f.key, e.target.value)}
                        disabled={scenario?.is_readonly}
                        placeholder="0"
                      />
                    </div>
                  ))}
                </div>
              )}
            </fieldset>

            {renderFieldGroup('Credits', CREDIT_FIELDS)}
            {renderFieldGroup('Payments & Withholding', PAYMENT_FIELDS)}

            <div>
              <label className="label-text">Notes</label>
              <textarea
                className="input-field"
                rows={3}
                value={notes}
                onChange={(e) => setNotes(e.target.value)}
                disabled={scenario?.is_readonly}
                placeholder="Scenario notes..."
              />
            </div>
          </div>

          {!scenario?.is_readonly && (
            <div className="flex gap-3">
              <button onClick={handleSave} className="btn-primary" disabled={loading}>
                {loading ? 'Saving...' : 'Save Scenario'}
              </button>
              <button
                type="button"
                className="btn-secondary"
                onClick={() => navigate(`/households/${householdId}`)}
              >
                Cancel
              </button>
            </div>
          )}
        </div>

        <div className="col-span-1">
          <div className="card sticky top-8 space-y-4">
            <h2 className="text-lg font-semibold text-navy-800">Live Preview</h2>
            {preview ? (
              <div className="space-y-3 text-sm">
                <div className="flex justify-between">
                  <span className="text-gray-600">Total Income</span>
                  <span className="font-medium">{formatMoney(preview.total_income)}</span>
                </div>
                <div className="flex justify-between">
                  <span className="text-gray-600">AGI</span>
                  <span className="font-medium">{formatMoney(preview.agi)}</span>
                </div>
                <div className="flex justify-between">
                  <span className="text-gray-600">Taxable Income</span>
                  <span className="font-medium">{formatMoney(preview.taxable_income)}</span>
                </div>
                <hr className="border-gray-200" />
                <div className="flex justify-between">
                  <span className="text-gray-600">Federal Tax</span>
                  <span className="font-semibold text-red-600">{formatMoney(preview.total_tax)}</span>
                </div>
                <div className="flex justify-between">
                  <span className="text-gray-600">Effective Rate</span>
                  <span className="font-medium">{formatPct(preview.effective_rate)}</span>
                </div>
                <div className="flex justify-between">
                  <span className="text-gray-600">Marginal Bracket</span>
                  <span className="font-medium">{formatPct(preview.marginal_bracket_pct)}</span>
                </div>
                <hr className="border-gray-200" />
                <div className="flex justify-between">
                  <span className="text-gray-600">Withholding</span>
                  <span className="font-medium">{formatMoney(preview.federal_withholding)}</span>
                </div>
                <div className={`flex justify-between font-semibold ${(preview.refund_or_owed || 0) >= 0 ? 'text-green-700' : 'text-red-700'}`}>
                  <span>{(preview.refund_or_owed || 0) >= 0 ? 'Refund' : 'Owed'}</span>
                  <span>{formatMoney(Math.abs(preview.refund_or_owed || 0))}</span>
                </div>
              </div>
            ) : (
              <p className="text-gray-400 text-sm">Enter values to see a live tax preview.</p>
            )}
          </div>
        </div>
      </div>
    </div>
  );
}
