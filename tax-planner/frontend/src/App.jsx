import React from 'react';
import { Routes, Route, NavLink, Navigate } from 'react-router-dom';
import useStore from './hooks/useStore';

import HouseholdList from './pages/HouseholdList';
import HouseholdCreate from './pages/HouseholdCreate';
import HouseholdDetail from './pages/HouseholdDetail';
import TaxReturnEntry from './pages/TaxReturnEntry';
import TaxReport from './pages/TaxReport';
import ScenarioList from './pages/ScenarioList';
import ScenarioEditor from './pages/ScenarioEditor';
import ScenarioCompare from './pages/ScenarioCompare';
import RangeCalc from './pages/RangeCalc';
import RothProjection from './pages/RothProjection';
import TaxLetterEditor from './pages/TaxLetterEditor';
import Explainers from './pages/Explainers';
import SettingsPage from './pages/SettingsPage';

function Notification() {
  const notification = useStore((s) => s.notification);
  if (!notification) return null;
  const colors = {
    info: 'bg-blue-50 text-blue-800 border-blue-200',
    success: 'bg-green-50 text-green-800 border-green-200',
    error: 'bg-red-50 text-red-800 border-red-200',
    warning: 'bg-yellow-50 text-yellow-800 border-yellow-200',
  };
  return (
    <div className={`fixed top-4 right-4 z-50 px-4 py-3 rounded-lg border ${colors[notification.type] || colors.info} shadow-lg max-w-md`}>
      {notification.message}
    </div>
  );
}

function Sidebar() {
  const linkClass = ({ isActive }) =>
    `flex items-center gap-3 px-4 py-2.5 rounded-lg text-sm font-medium transition-colors ${
      isActive ? 'bg-navy-800 text-white' : 'text-navy-200 hover:bg-navy-800/50 hover:text-white'
    }`;

  return (
    <aside className="w-64 bg-navy-900 min-h-screen flex flex-col">
      <div className="p-6">
        <h1 className="text-xl font-bold text-white tracking-tight">Tax Planner</h1>
        <p className="text-navy-400 text-xs mt-1">Financial Planning Tool</p>
      </div>
      <nav className="flex-1 px-3 space-y-1">
        <NavLink to="/households" className={linkClass}>
          <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M17 20h5v-2a3 3 0 00-5.356-1.857M17 20H7m10 0v-2c0-.656-.126-1.283-.356-1.857M7 20H2v-2a3 3 0 015.356-1.857M7 20v-2c0-.656.126-1.283.356-1.857m0 0a5.002 5.002 0 019.288 0M15 7a3 3 0 11-6 0 3 3 0 016 0z" /></svg>
          Households
        </NavLink>
        <NavLink to="/settings" className={linkClass}>
          <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M10.325 4.317c.426-1.756 2.924-1.756 3.35 0a1.724 1.724 0 002.573 1.066c1.543-.94 3.31.826 2.37 2.37a1.724 1.724 0 001.066 2.573c1.756.426 1.756 2.924 0 3.35a1.724 1.724 0 00-1.066 2.573c.94 1.543-.826 3.31-2.37 2.37a1.724 1.724 0 00-2.573 1.066c-.426 1.756-2.924 1.756-3.35 0a1.724 1.724 0 00-2.573-1.066c-1.543.94-3.31-.826-2.37-2.37a1.724 1.724 0 00-1.066-2.573c-1.756-.426-1.756-2.924 0-3.35a1.724 1.724 0 001.066-2.573c-.94-1.543.826-3.31 2.37-2.37.996.608 2.296.07 2.572-1.065z" /><path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15 12a3 3 0 11-6 0 3 3 0 016 0z" /></svg>
          Settings
        </NavLink>
      </nav>
      <div className="p-4 text-navy-500 text-xs">v1.0.0</div>
    </aside>
  );
}

export default function App() {
  return (
    <div className="flex min-h-screen">
      <Sidebar />
      <main className="flex-1 overflow-auto">
        <Notification />
        <div className="p-8">
          <Routes>
            <Route path="/" element={<Navigate to="/households" replace />} />
            <Route path="/households" element={<HouseholdList />} />
            <Route path="/households/new" element={<HouseholdCreate />} />
            <Route path="/households/:id" element={<HouseholdDetail />} />
            <Route path="/households/:id/edit" element={<HouseholdCreate />} />
            <Route path="/households/:householdId/returns/new" element={<TaxReturnEntry />} />
            <Route path="/households/:householdId/returns/:returnId" element={<TaxReturnEntry />} />
            <Route path="/households/:householdId/report/:scenarioId" element={<TaxReport />} />
            <Route path="/households/:householdId/scenarios" element={<ScenarioList />} />
            <Route path="/households/:householdId/scenarios/:scenarioId" element={<ScenarioEditor />} />
            <Route path="/households/:householdId/compare" element={<ScenarioCompare />} />
            <Route path="/households/:householdId/range-calc/:scenarioId" element={<RangeCalc />} />
            <Route path="/households/:householdId/roth-projection/:scenarioId" element={<RothProjection />} />
            <Route path="/households/:householdId/letters/:letterId" element={<TaxLetterEditor />} />
            <Route path="/households/:householdId/explainers/:scenarioId" element={<Explainers />} />
            <Route path="/settings" element={<SettingsPage />} />
          </Routes>
        </div>
      </main>
    </div>
  );
}
