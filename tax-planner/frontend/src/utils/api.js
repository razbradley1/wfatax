const API_BASE = '/api';

async function request(path, options = {}) {
  const url = `${API_BASE}${path}`;
  const config = {
    headers: { 'Content-Type': 'application/json' },
    ...options,
  };
  if (config.body && typeof config.body === 'object') {
    config.body = JSON.stringify(config.body);
  }
  const res = await fetch(url, config);
  if (!res.ok) {
    const err = await res.json().catch(() => ({ detail: res.statusText }));
    throw new Error(err.detail || 'Request failed');
  }
  return res.json();
}

export const api = {
  // Households
  getHouseholds: (params = {}) => {
    const qs = new URLSearchParams(params).toString();
    return request(`/households${qs ? '?' + qs : ''}`);
  },
  getHousehold: (id) => request(`/households/${id}`),
  getHouseholdSummary: (id) => request(`/households/${id}/summary`),
  createHousehold: (data) => request('/households', { method: 'POST', body: data }),
  updateHousehold: (id, data) => request(`/households/${id}`, { method: 'PUT', body: data }),
  deleteHousehold: (id) => request(`/households/${id}`, { method: 'DELETE' }),

  // Tax Returns
  getReturn: (id) => request(`/returns/${id}`),
  getReturnsByHousehold: (householdId) => request(`/returns/household/${householdId}`),
  createReturn: (data) => request('/returns', { method: 'POST', body: data }),
  updateReturn: (id, data) => request(`/returns/${id}`, { method: 'PUT', body: data }),
  deleteReturn: (id) => request(`/returns/${id}`, { method: 'DELETE' }),
  uploadReturn: async (householdId, taxYear, file) => {
    const formData = new FormData();
    formData.append('household_id', householdId);
    formData.append('tax_year', taxYear);
    formData.append('file', file);
    const res = await fetch(`${API_BASE}/returns/upload`, { method: 'POST', body: formData });
    if (!res.ok) throw new Error('Upload failed');
    return res.json();
  },

  // Scenarios
  getScenariosByHousehold: (householdId, taxYear) => {
    const params = taxYear ? `?tax_year=${taxYear}` : '';
    return request(`/scenarios/household/${householdId}${params}`);
  },
  getScenario: (id) => request(`/scenarios/${id}`),
  createScenario: (data) => request('/scenarios', { method: 'POST', body: data }),
  updateScenario: (id, data) => request(`/scenarios/${id}`, { method: 'PUT', body: data }),
  deleteScenario: (id) => request(`/scenarios/${id}`, { method: 'DELETE' }),
  compareScenarios: (ids) => request('/scenarios/compare', { method: 'POST', body: { scenario_ids: ids } }),
  rangeCalc: (scenarioId, data) => request(`/scenarios/${scenarioId}/range-calc`, { method: 'POST', body: data }),
  findSpike: (scenarioId, data) => request(`/scenarios/${scenarioId}/find-spike`, { method: 'POST', body: data }),
  rothProjection: (scenarioId, data) => request(`/scenarios/${scenarioId}/roth-projection`, { method: 'POST', body: data }),
  quickCalc: (inputs) => request('/scenarios/quick-calc', { method: 'POST', body: inputs }),

  // Reports
  getTaxReport: (scenarioId) => request(`/reports/tax-report/${scenarioId}`),
  getTaxExplainer: (scenarioId) => request(`/reports/explainer/tax/${scenarioId}`),
  getRothExplainer: (scenarioId) => request(`/reports/explainer/roth/${scenarioId}`),
  getQcdExplainer: (scenarioId) => request(`/reports/explainer/qcd/${scenarioId}`),
  getDafExplainer: (scenarioId) => request(`/reports/explainer/daf/${scenarioId}`),

  // Letters
  getLettersByHousehold: (householdId) => request(`/letters/household/${householdId}`),
  getLetter: (id) => request(`/letters/${id}`),
  createLetter: (data) => request('/letters', { method: 'POST', body: data }),
  updateLetter: (id, data) => request(`/letters/${id}`, { method: 'PUT', body: data }),
  deleteLetter: (id) => request(`/letters/${id}`, { method: 'DELETE' }),
  getLetterTemplates: () => request('/letters/templates'),

  // Settings
  getSettings: () => request('/settings'),
  updateSetting: (key, value) => request(`/settings/${key}`, { method: 'PUT', body: { value } }),
  exportData: () => request('/settings/export'),
  importData: (data) => request('/settings/import', { method: 'POST', body: data }),
  clearAllData: () => request('/settings/clear-all?confirm=yes', { method: 'DELETE' }),

  // PDF export URLs
  exportUrl: {
    taxReport: (scenarioId) => `${API_BASE}/export/tax-report/${scenarioId}`,
    letter: (letterId) => `${API_BASE}/export/letter/${letterId}`,
    explainer: (type, scenarioId) => `${API_BASE}/export/explainer/${type}/${scenarioId}`,
  },
};

export function formatMoney(val) {
  if (val == null || isNaN(val)) return '$0';
  const abs = Math.abs(val);
  const formatted = abs.toLocaleString('en-US', { minimumFractionDigits: 0, maximumFractionDigits: 0 });
  return val < 0 ? `-$${formatted}` : `$${formatted}`;
}

export function formatPct(val) {
  if (val == null || isNaN(val)) return '0.0%';
  return `${val.toFixed(1)}%`;
}

export function formatMoneyInput(val) {
  if (!val && val !== 0) return '';
  return Number(val).toString();
}
