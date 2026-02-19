import React, { useState, useEffect, useRef } from 'react';
import { useParams, useNavigate, Link } from 'react-router-dom';
import { api, formatMoney } from '../utils/api';
import useStore from '../hooks/useStore';

const TABS = ['Tax Returns', 'Scenarios', 'Tax Letters'];

export default function HouseholdDetail() {
  const { id } = useParams();
  const navigate = useNavigate();
  const notify = useStore((s) => s.notify);
  const setCurrentHousehold = useStore((s) => s.setCurrentHousehold);

  const [summary, setSummary] = useState(null);
  const [loading, setLoading] = useState(true);
  const [activeTab, setActiveTab] = useState('Tax Returns');
  const [uploading, setUploading] = useState(false);

  const fileInputRef = useRef(null);

  useEffect(() => {
    loadSummary();
  }, [id]);

  async function loadSummary() {
    setLoading(true);
    try {
      const data = await api.getHouseholdSummary(id);
      setSummary(data);
      setCurrentHousehold(data.household || data);
    } catch (err) {
      notify(err.message, 'error');
    } finally {
      setLoading(false);
    }
  }

  async function handleDelete() {
    if (!window.confirm(`Are you sure you want to delete this household? This action cannot be undone.`)) {
      return;
    }
    try {
      await api.deleteHousehold(id);
      notify('Household deleted successfully', 'success');
      navigate('/households');
    } catch (err) {
      notify(err.message, 'error');
    }
  }

  async function handleUploadPdf(e) {
    const file = e.target.files?.[0];
    if (!file) return;

    const yearStr = window.prompt('Enter the tax year for this return:', new Date().getFullYear() - 1);
    if (!yearStr) return;

    const taxYear = parseInt(yearStr, 10);
    if (isNaN(taxYear)) {
      notify('Invalid tax year', 'error');
      return;
    }

    setUploading(true);
    try {
      await api.uploadReturn(id, taxYear, file);
      notify('Return uploaded successfully', 'success');
      await loadSummary();
    } catch (err) {
      notify(err.message, 'error');
    } finally {
      setUploading(false);
      if (fileInputRef.current) fileInputRef.current.value = '';
    }
  }

  if (loading) {
    return (
      <div className="flex items-center justify-center py-20">
        <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-navy-800"></div>
        <span className="ml-3 text-gray-500 text-sm">Loading household...</span>
      </div>
    );
  }

  if (!summary) {
    return (
      <div className="text-center py-20">
        <p className="text-gray-500">Household not found.</p>
        <Link to="/households" className="text-navy-700 hover:underline text-sm mt-2 inline-block">
          Back to Households
        </Link>
      </div>
    );
  }

  const household = summary.household || summary;
  const returns = summary.returns || [];
  const scenarios = summary.scenarios || [];
  const letters = summary.letters || [];

  return (
    <div>
      {/* Breadcrumb */}
      <div className="mb-4">
        <Link to="/households" className="text-navy-600 hover:text-navy-800 text-sm">
          Households
        </Link>
        <span className="text-gray-400 mx-2">/</span>
        <span className="text-gray-600 text-sm">{household.name}</span>
      </div>

      {/* Header */}
      <div className="flex items-start justify-between mb-8">
        <div>
          <h1 className="page-title">{household.name}</h1>
          <div className="mt-2 flex flex-wrap items-center gap-x-6 gap-y-1 text-sm text-gray-600">
            {household.primary_taxpayer && (
              <span>
                <span className="font-medium text-gray-700">Primary:</span> {household.primary_taxpayer}
              </span>
            )}
            {household.secondary_taxpayer && (
              <span>
                <span className="font-medium text-gray-700">Secondary:</span> {household.secondary_taxpayer}
              </span>
            )}
            {household.filing_status && (
              <span className="inline-flex items-center gap-1.5">
                <span className="font-medium text-gray-700">Filing:</span>
                <span className="bg-navy-50 text-navy-700 px-2 py-0.5 rounded text-xs font-medium">
                  {household.filing_status}
                </span>
              </span>
            )}
            {household.state && (
              <span>
                <span className="font-medium text-gray-700">State:</span> {household.state}
              </span>
            )}
          </div>
        </div>
        <div className="flex items-center gap-2 flex-shrink-0">
          <Link to={`/households/${id}/edit`} className="btn-secondary">
            Edit
          </Link>
          <button onClick={handleDelete} className="btn-danger">
            Delete
          </button>
        </div>
      </div>

      {/* Tab Navigation */}
      <div className="border-b border-gray-200 mb-6">
        <nav className="flex gap-6">
          {TABS.map((tab) => (
            <button
              key={tab}
              onClick={() => setActiveTab(tab)}
              className={`pb-3 text-sm font-medium border-b-2 transition-colors ${
                activeTab === tab
                  ? 'border-navy-800 text-navy-800'
                  : 'border-transparent text-gray-500 hover:text-gray-700 hover:border-gray-300'
              }`}
            >
              {tab}
              <span className="ml-1.5 text-xs bg-gray-100 text-gray-600 px-1.5 py-0.5 rounded-full">
                {tab === 'Tax Returns' && returns.length}
                {tab === 'Scenarios' && scenarios.length}
                {tab === 'Tax Letters' && letters.length}
              </span>
            </button>
          ))}
        </nav>
      </div>

      {/* Tab Content */}
      {activeTab === 'Tax Returns' && (
        <TaxReturnsSection
          householdId={id}
          returns={returns}
          uploading={uploading}
          fileInputRef={fileInputRef}
          onUpload={handleUploadPdf}
        />
      )}
      {activeTab === 'Scenarios' && (
        <ScenariosSection householdId={id} scenarios={scenarios} />
      )}
      {activeTab === 'Tax Letters' && (
        <TaxLettersSection householdId={id} letters={letters} />
      )}
    </div>
  );
}

/* ─── Tax Returns Section ─────────────────────────────── */

function TaxReturnsSection({ householdId, returns, uploading, fileInputRef, onUpload }) {
  return (
    <div>
      <div className="flex items-center justify-between mb-4">
        <h2 className="text-lg font-semibold text-navy-800">Tax Returns</h2>
        <div className="flex items-center gap-2">
          <label className={`btn-secondary cursor-pointer inline-flex items-center gap-1.5 ${uploading ? 'opacity-50 pointer-events-none' : ''}`}>
            <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 16v1a3 3 0 003 3h10a3 3 0 003-3v-1m-4-8l-4-4m0 0L8 8m4-4v12" />
            </svg>
            {uploading ? 'Uploading...' : 'Upload PDF'}
            <input
              ref={fileInputRef}
              type="file"
              accept=".pdf"
              className="hidden"
              onChange={onUpload}
              disabled={uploading}
            />
          </label>
          <Link to={`/households/${householdId}/returns/new`} className="btn-primary inline-flex items-center gap-1.5">
            <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 4v16m8-8H4" />
            </svg>
            Add Return
          </Link>
        </div>
      </div>

      {returns.length === 0 ? (
        <div className="card text-center py-10">
          <svg className="w-12 h-12 mx-auto text-gray-300 mb-3" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" />
          </svg>
          <p className="text-gray-500 text-sm">No tax returns yet.</p>
          <p className="text-gray-400 text-xs mt-1">Add a return manually or upload a PDF to get started.</p>
        </div>
      ) : (
        <div className="space-y-3">
          {returns.map((ret) => (
            <div key={ret.id} className="card flex items-center justify-between">
              <div className="flex items-center gap-4">
                <div className="text-lg font-bold text-navy-800">{ret.tax_year || ret.year}</div>
                <div className="flex items-center gap-2">
                  {ret.filing_status && (
                    <span className="text-sm text-gray-600">{ret.filing_status}</span>
                  )}
                  {ret.has_pdf && (
                    <span className="inline-flex items-center gap-1 bg-blue-50 text-blue-700 text-xs font-medium px-2 py-0.5 rounded-full">
                      <svg className="w-3 h-3" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M7 21h10a2 2 0 002-2V9.414a1 1 0 00-.293-.707l-5.414-5.414A1 1 0 0012.586 3H7a2 2 0 00-2 2v14a2 2 0 002 2z" />
                      </svg>
                      PDF
                    </span>
                  )}
                  {ret.needs_review && (
                    <span className="inline-flex items-center gap-1 bg-amber-50 text-amber-700 text-xs font-medium px-2 py-0.5 rounded-full">
                      <svg className="w-3 h-3" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 9v2m0 4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
                      </svg>
                      Needs Review
                    </span>
                  )}
                </div>
              </div>
              <div className="flex items-center gap-2">
                <Link
                  to={`/households/${householdId}/returns/${ret.id}`}
                  className="text-sm text-navy-700 hover:text-navy-900 font-medium hover:underline"
                >
                  View / Edit
                </Link>
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}

/* ─── Scenarios Section ───────────────────────────────── */

function ScenariosSection({ householdId, scenarios }) {
  return (
    <div>
      <div className="flex items-center justify-between mb-4">
        <h2 className="text-lg font-semibold text-navy-800">Scenarios</h2>
        <div className="flex items-center gap-2">
          {scenarios.length >= 2 && (
            <Link to={`/households/${householdId}/compare`} className="btn-secondary inline-flex items-center gap-1.5">
              <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 19v-6a2 2 0 00-2-2H5a2 2 0 00-2 2v6a2 2 0 002 2h2a2 2 0 002-2zm0 0V9a2 2 0 012-2h2a2 2 0 012 2v10m-6 0a2 2 0 002 2h2a2 2 0 002-2m0 0V5a2 2 0 012-2h2a2 2 0 012 2v14a2 2 0 01-2 2h-2a2 2 0 01-2-2z" />
              </svg>
              Compare
            </Link>
          )}
          <Link to={`/households/${householdId}/scenarios`} className="btn-primary inline-flex items-center gap-1.5">
            <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 4v16m8-8H4" />
            </svg>
            New Scenario
          </Link>
        </div>
      </div>

      {scenarios.length === 0 ? (
        <div className="card text-center py-10">
          <svg className="w-12 h-12 mx-auto text-gray-300 mb-3" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M8 7v8a2 2 0 002 2h6M8 7V5a2 2 0 012-2h4.586a1 1 0 01.707.293l4.414 4.414a1 1 0 01.293.707V15a2 2 0 01-2 2h-2M8 7H6a2 2 0 00-2 2v10a2 2 0 002 2h8a2 2 0 002-2v-2" />
          </svg>
          <p className="text-gray-500 text-sm">No scenarios yet.</p>
          <p className="text-gray-400 text-xs mt-1">Create a scenario to start planning.</p>
        </div>
      ) : (
        <div className="space-y-3">
          {scenarios.map((sc) => (
            <div key={sc.id} className="card flex items-center justify-between">
              <div className="flex items-center gap-4">
                <div>
                  <div className="font-medium text-navy-800">{sc.name}</div>
                  <div className="text-xs text-gray-500 mt-0.5">Tax Year {sc.tax_year || sc.year}</div>
                </div>
                <div className="flex items-center gap-2">
                  {sc.is_readonly && (
                    <span className="inline-flex items-center gap-1 bg-gray-100 text-gray-600 text-xs font-medium px-2 py-0.5 rounded-full">
                      <svg className="w-3 h-3" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 15v2m-6 4h12a2 2 0 002-2v-6a2 2 0 00-2-2H6a2 2 0 00-2 2v6a2 2 0 002 2zm10-10V7a4 4 0 00-8 0v4h8z" />
                      </svg>
                      Read Only
                    </span>
                  )}
                </div>
              </div>
              <div className="flex items-center gap-3">
                <Link
                  to={`/households/${householdId}/report/${sc.id}`}
                  className="text-sm text-gray-500 hover:text-navy-700 font-medium hover:underline"
                >
                  Report
                </Link>
                <Link
                  to={`/households/${householdId}/scenarios/${sc.id}`}
                  className="text-sm text-navy-700 hover:text-navy-900 font-medium hover:underline"
                >
                  View / Edit
                </Link>
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}

/* ─── Tax Letters Section ─────────────────────────────── */

function TaxLettersSection({ householdId, letters }) {
  const navigate = useNavigate();
  const notify = useStore((s) => s.notify);

  async function handleCreateLetter() {
    try {
      const letter = await api.createLetter({ household_id: parseInt(householdId, 10) });
      notify('Letter created', 'success');
      navigate(`/households/${householdId}/letters/${letter.id}`);
    } catch (err) {
      notify(err.message, 'error');
    }
  }

  function statusBadge(status) {
    const styles = {
      draft: 'bg-gray-100 text-gray-600',
      in_progress: 'bg-blue-50 text-blue-700',
      review: 'bg-amber-50 text-amber-700',
      final: 'bg-green-50 text-green-700',
    };
    const cls = styles[status] || styles.draft;
    const label = (status || 'draft').replace(/_/g, ' ');
    return (
      <span className={`inline-flex items-center text-xs font-medium px-2 py-0.5 rounded-full capitalize ${cls}`}>
        {label}
      </span>
    );
  }

  return (
    <div>
      <div className="flex items-center justify-between mb-4">
        <h2 className="text-lg font-semibold text-navy-800">Tax Letters</h2>
        <button onClick={handleCreateLetter} className="btn-primary inline-flex items-center gap-1.5">
          <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 4v16m8-8H4" />
          </svg>
          New Letter
        </button>
      </div>

      {letters.length === 0 ? (
        <div className="card text-center py-10">
          <svg className="w-12 h-12 mx-auto text-gray-300 mb-3" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M3 8l7.89 5.26a2 2 0 002.22 0L21 8M5 19h14a2 2 0 002-2V7a2 2 0 00-2-2H5a2 2 0 00-2 2v10a2 2 0 002 2z" />
          </svg>
          <p className="text-gray-500 text-sm">No tax letters yet.</p>
          <p className="text-gray-400 text-xs mt-1">Create a letter to communicate tax planning recommendations.</p>
        </div>
      ) : (
        <div className="space-y-3">
          {letters.map((letter) => (
            <div key={letter.id} className="card flex items-center justify-between">
              <div className="flex items-center gap-4">
                <div className="text-lg font-bold text-navy-800">{letter.tax_year || letter.year || '--'}</div>
                <div className="flex items-center gap-2">
                  {statusBadge(letter.status)}
                  {letter.section_count != null && (
                    <span className="text-xs text-gray-500">
                      {letter.section_count} {letter.section_count === 1 ? 'section' : 'sections'}
                    </span>
                  )}
                </div>
              </div>
              <Link
                to={`/households/${householdId}/letters/${letter.id}`}
                className="text-sm text-navy-700 hover:text-navy-900 font-medium hover:underline"
              >
                View / Edit
              </Link>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
