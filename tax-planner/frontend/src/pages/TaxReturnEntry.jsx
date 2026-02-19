import React, { useState, useEffect } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import { api, formatMoney } from '../utils/api';
import useStore from '../hooks/useStore';

const FILING_STATUSES = [
  { value: 'single', label: 'Single' },
  { value: 'mfj', label: 'Married Filing Jointly' },
  { value: 'mfs', label: 'Married Filing Separately' },
  { value: 'hoh', label: 'Head of Household' },
  { value: 'qw', label: 'Qualifying Widow(er)' },
];

const INCOME_FIELDS = [
  { key: 'wages_salaries', label: 'Wages & Salaries' },
  { key: 'interest_income_taxable', label: 'Taxable Interest' },
  { key: 'interest_income_exempt', label: 'Tax-Exempt Interest' },
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
  { key: 'business_income', label: 'Business Income (Sched C)' },
  { key: 'rental_income', label: 'Rental Income (Sched E)' },
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
  { key: 'state_local_taxes', label: 'State & Local Taxes (SALT)' },
  { key: 'mortgage_interest', label: 'Mortgage Interest' },
  { key: 'charitable_contributions', label: 'Charitable Contributions' },
  { key: 'other_itemized', label: 'Other Itemized' },
];

const PAYMENT_FIELDS = [
  { key: 'federal_withholding', label: 'Federal Withholding' },
  { key: 'estimated_tax_payments', label: 'Estimated Tax Payments' },
  { key: 'other_payments', label: 'Other Payments' },
];

export default function TaxReturnEntry() {
  const { householdId, returnId } = useParams();
  const navigate = useNavigate();
  const notify = useStore((s) => s.notify);

  const isEdit = Boolean(returnId);
  const [household, setHousehold] = useState(null);
  const [loading, setLoading] = useState(false);
  const [fetching, setFetching] = useState(true);
  const [needsReview, setNeedsReview] = useState([]);

  const [filingStatus, setFilingStatus] = useState('single');
  const [taxYear, setTaxYear] = useState(2024);
  const [data, setData] = useState({});

  useEffect(() => {
    async function load() {
      try {
        const hh = await api.getHousehold(householdId);
        setHousehold(hh);
        if (isEdit) {
          const ret = await api.getReturn(returnId);
          setFilingStatus(ret.filing_status || 'single');
          setTaxYear(ret.tax_year);
          setData(ret.extracted_data || {});
          setNeedsReview(ret.needs_review_fields || []);
        } else if (hh.filing_status) {
          setFilingStatus(hh.filing_status);
        }
      } catch (err) {
        notify(err.message, 'error');
      } finally {
        setFetching(false);
      }
    }
    load();
  }, [householdId, returnId, isEdit, notify]);

  function handleFieldChange(key, value) {
    const num = value === '' ? 0 : parseFloat(value);
    setData((prev) => ({ ...prev, [key]: isNaN(num) ? 0 : num }));
  }

  async function handleSubmit(e) {
    e.preventDefault();
    setLoading(true);
    try {
      if (isEdit) {
        await api.updateReturn(returnId, { filing_status: filingStatus, extracted_data: data });
        notify('Tax return updated', 'success');
      } else {
        await api.createReturn({
          household_id: parseInt(householdId),
          tax_year: taxYear,
          filing_status: filingStatus,
          extracted_data: data,
        });
        notify('Tax return created', 'success');
      }
      navigate(`/households/${householdId}`);
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
              <label htmlFor={f.key} className="label-text flex items-center gap-2">
                {f.label}
                {needsReview.includes(f.key) && (
                  <span className="text-xs bg-yellow-100 text-yellow-800 px-1.5 py-0.5 rounded">Review</span>
                )}
              </label>
              <input
                id={f.key}
                type="number"
                step="any"
                className="input-field"
                value={data[f.key] || ''}
                onChange={(e) => handleFieldChange(f.key, e.target.value)}
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
        <p className="text-gray-500 text-sm">Loading...</p>
      </div>
    );
  }

  return (
    <div className="max-w-3xl">
      <div className="mb-6">
        <button
          onClick={() => navigate(`/households/${householdId}`)}
          className="text-sm text-navy-600 hover:text-navy-800 mb-2 inline-block"
        >
          &larr; Back to {household?.name || 'Household'}
        </button>
        <h1 className="page-title">
          {isEdit ? 'Edit Tax Return' : 'New Tax Return'}
        </h1>
      </div>

      <form onSubmit={handleSubmit} className="card space-y-6">
        <div className="grid grid-cols-2 gap-4">
          <div>
            <label htmlFor="tax_year" className="label-text">Tax Year</label>
            <select
              id="tax_year"
              className="input-field"
              value={taxYear}
              onChange={(e) => setTaxYear(parseInt(e.target.value))}
              disabled={isEdit}
            >
              <option value={2023}>2023</option>
              <option value={2024}>2024</option>
              <option value={2025}>2025</option>
            </select>
          </div>
          <div>
            <label htmlFor="filing_status" className="label-text">Filing Status</label>
            <select
              id="filing_status"
              className="input-field"
              value={filingStatus}
              onChange={(e) => setFilingStatus(e.target.value)}
            >
              {FILING_STATUSES.map((s) => (
                <option key={s.value} value={s.value}>{s.label}</option>
              ))}
            </select>
          </div>
        </div>

        {renderFieldGroup('Income', INCOME_FIELDS)}
        {renderFieldGroup('Adjustments', ADJUSTMENT_FIELDS)}

        <fieldset className="space-y-3">
          <legend className="text-lg font-semibold text-navy-800 border-b border-gray-200 pb-2 mb-4">
            Deductions
          </legend>
          <div className="mb-3">
            <label className="label-text flex items-center gap-2">
              <input
                type="checkbox"
                checked={data.use_itemized || false}
                onChange={(e) => setData((prev) => ({ ...prev, use_itemized: e.target.checked }))}
              />
              Use Itemized Deductions
            </label>
          </div>
          {data.use_itemized && (
            <div className="grid grid-cols-2 gap-4">
              {DEDUCTION_FIELDS.map((f) => (
                <div key={f.key}>
                  <label htmlFor={f.key} className="label-text">{f.label}</label>
                  <input
                    id={f.key}
                    type="number"
                    step="any"
                    className="input-field"
                    value={data[f.key] || ''}
                    onChange={(e) => handleFieldChange(f.key, e.target.value)}
                    placeholder="0"
                  />
                </div>
              ))}
            </div>
          )}
        </fieldset>

        {renderFieldGroup('Payments & Withholding', PAYMENT_FIELDS)}

        <div className="flex items-center gap-3 pt-2">
          <button type="submit" className="btn-primary" disabled={loading}>
            {loading ? 'Saving...' : isEdit ? 'Update Return' : 'Create Return'}
          </button>
          <button
            type="button"
            className="btn-secondary"
            onClick={() => navigate(`/households/${householdId}`)}
          >
            Cancel
          </button>
        </div>
      </form>
    </div>
  );
}
