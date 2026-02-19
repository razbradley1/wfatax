import React, { useState, useEffect } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import { api } from '../utils/api';
import useStore from '../hooks/useStore';

const US_STATES = [
  'AL','AK','AZ','AR','CA','CO','CT','DE','FL','GA',
  'HI','ID','IL','IN','IA','KS','KY','LA','ME','MD',
  'MA','MI','MN','MS','MO','MT','NE','NV','NH','NJ',
  'NM','NY','NC','ND','OH','OK','OR','PA','RI','SC',
  'SD','TN','TX','UT','VT','VA','WA','WV','WI','WY',
  'DC',
];

const FILING_STATUSES = [
  { value: 'single', label: 'Single' },
  { value: 'mfj', label: 'Married Filing Jointly' },
  { value: 'mfs', label: 'Married Filing Separately' },
  { value: 'hoh', label: 'Head of Household' },
  { value: 'qw', label: 'Qualifying Widow(er)' },
];

const EMPTY_FORM = {
  name: '',
  primary_name: '',
  primary_dob: '',
  primary_ssn_last4: '',
  secondary_name: '',
  secondary_dob: '',
  filing_status: 'single',
  state: '',
  notes: '',
};

export default function HouseholdCreate() {
  const { id } = useParams();
  const navigate = useNavigate();
  const notify = useStore((s) => s.notify);

  const isEdit = Boolean(id);

  const [form, setForm] = useState(EMPTY_FORM);
  const [loading, setLoading] = useState(false);
  const [fetching, setFetching] = useState(false);

  useEffect(() => {
    if (isEdit) {
      setFetching(true);
      api
        .getHousehold(id)
        .then((data) => {
          setForm({
            name: data.name || '',
            primary_name: data.primary_name || '',
            primary_dob: data.primary_dob || '',
            primary_ssn_last4: data.primary_ssn_last4 || '',
            secondary_name: data.secondary_name || '',
            secondary_dob: data.secondary_dob || '',
            filing_status: data.filing_status || 'single',
            state: data.state || '',
            notes: data.notes || '',
          });
        })
        .catch((err) => {
          notify(err.message || 'Failed to load household', 'error');
        })
        .finally(() => setFetching(false));
    }
  }, [id, isEdit, notify]);

  function handleChange(e) {
    const { name, value } = e.target;
    setForm((prev) => ({ ...prev, [name]: value }));
  }

  async function handleSubmit(e) {
    e.preventDefault();
    setLoading(true);
    try {
      let result;
      if (isEdit) {
        result = await api.updateHousehold(id, form);
        notify('Household updated successfully', 'success');
      } else {
        result = await api.createHousehold(form);
        notify('Household created successfully', 'success');
      }
      navigate(`/households/${result.id || id}`);
    } catch (err) {
      notify(err.message || 'Failed to save household', 'error');
    } finally {
      setLoading(false);
    }
  }

  if (fetching) {
    return (
      <div className="flex items-center justify-center py-12">
        <p className="text-gray-500 text-sm">Loading household...</p>
      </div>
    );
  }

  return (
    <div className="max-w-2xl">
      <h1 className="page-title mb-6">
        {isEdit ? 'Edit Household' : 'New Household'}
      </h1>

      <form onSubmit={handleSubmit} className="card space-y-6">
        {/* Household Name */}
        <div>
          <label htmlFor="name" className="label-text">
            Household Name
          </label>
          <input
            id="name"
            name="name"
            type="text"
            className="input-field"
            value={form.name}
            onChange={handleChange}
            required
            placeholder="e.g. Smith Family"
          />
        </div>

        {/* Primary Taxpayer */}
        <fieldset className="space-y-4">
          <legend className="text-lg font-semibold text-navy-800 border-b border-gray-200 pb-2 mb-4">
            Primary Taxpayer
          </legend>
          <div>
            <label htmlFor="primary_name" className="label-text">
              Full Name
            </label>
            <input
              id="primary_name"
              name="primary_name"
              type="text"
              className="input-field"
              value={form.primary_name}
              onChange={handleChange}
              placeholder="First and last name"
            />
          </div>
          <div className="grid grid-cols-2 gap-4">
            <div>
              <label htmlFor="primary_dob" className="label-text">
                Date of Birth
              </label>
              <input
                id="primary_dob"
                name="primary_dob"
                type="date"
                className="input-field"
                value={form.primary_dob}
                onChange={handleChange}
              />
            </div>
            <div>
              <label htmlFor="primary_ssn_last4" className="label-text">
                SSN Last 4
              </label>
              <input
                id="primary_ssn_last4"
                name="primary_ssn_last4"
                type="text"
                className="input-field"
                value={form.primary_ssn_last4}
                onChange={handleChange}
                maxLength={4}
                pattern="\d{0,4}"
                placeholder="1234"
              />
            </div>
          </div>
        </fieldset>

        {/* Secondary Taxpayer */}
        <fieldset className="space-y-4">
          <legend className="text-lg font-semibold text-navy-800 border-b border-gray-200 pb-2 mb-4">
            Secondary Taxpayer
          </legend>
          <div>
            <label htmlFor="secondary_name" className="label-text">
              Full Name
            </label>
            <input
              id="secondary_name"
              name="secondary_name"
              type="text"
              className="input-field"
              value={form.secondary_name}
              onChange={handleChange}
              placeholder="First and last name"
            />
          </div>
          <div>
            <label htmlFor="secondary_dob" className="label-text">
              Date of Birth
            </label>
            <input
              id="secondary_dob"
              name="secondary_dob"
              type="date"
              className="input-field"
              value={form.secondary_dob}
              onChange={handleChange}
            />
          </div>
        </fieldset>

        {/* Filing Status & State */}
        <div className="grid grid-cols-2 gap-4">
          <div>
            <label htmlFor="filing_status" className="label-text">
              Filing Status
            </label>
            <select
              id="filing_status"
              name="filing_status"
              className="input-field"
              value={form.filing_status}
              onChange={handleChange}
            >
              {FILING_STATUSES.map((s) => (
                <option key={s.value} value={s.value}>
                  {s.label}
                </option>
              ))}
            </select>
          </div>
          <div>
            <label htmlFor="state" className="label-text">
              State
            </label>
            <select
              id="state"
              name="state"
              className="input-field"
              value={form.state}
              onChange={handleChange}
            >
              <option value="">Select a state</option>
              {US_STATES.map((st) => (
                <option key={st} value={st}>
                  {st}
                </option>
              ))}
            </select>
          </div>
        </div>

        {/* Notes */}
        <div>
          <label htmlFor="notes" className="label-text">
            Notes
          </label>
          <textarea
            id="notes"
            name="notes"
            className="input-field"
            rows={4}
            value={form.notes}
            onChange={handleChange}
            placeholder="Any additional notes about this household..."
          />
        </div>

        {/* Actions */}
        <div className="flex items-center gap-3 pt-2">
          <button type="submit" className="btn-primary" disabled={loading}>
            {loading
              ? 'Saving...'
              : isEdit
                ? 'Update Household'
                : 'Create Household'}
          </button>
          <button
            type="button"
            className="btn-secondary"
            onClick={() => navigate(isEdit ? `/households/${id}` : '/households')}
          >
            Cancel
          </button>
        </div>
      </form>
    </div>
  );
}
