'use client';

import { useState, useEffect } from 'react';
import { PageHeader } from '@/components/ui/PageHeader';
import { Settings, Save, ShieldAlert, SlidersHorizontal, Activity, Loader2 } from 'lucide-react';
import { systemAPI } from '@/lib/api';
import type { GlobalSettings } from '@/lib/types';

export default function AdminSettingsPage() {
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [form, setForm] = useState<Partial<GlobalSettings>>({
    environment_state: 'PAPER',
    extreme_bearish_threshold: -0.5,
    global_max_leverage: 5.0,
    default_commission_pct: 0.1,
    default_slippage_pct: 0.1,
    global_kill_switch_active: false
  });

  useEffect(() => {
    const fetchSettings = async () => {
      try {
        setLoading(true);
        const settings = await systemAPI.getGlobalSettings();
        setForm(settings);
      } catch (err: any) {
        setError(err.message);
      } finally {
        setLoading(false);
      }
    };
    fetchSettings();
  }, []);

  const handleSave = async () => {
    try {
      setSaving(true);
      await systemAPI.updateGlobalSettings(form);
      alert("Global Settings updated successfully!");
    } catch (err: any) {
      alert(`Failed to save settings: ${err.message}`);
    } finally {
      setSaving(false);
    }
  };

  const handleKillSwitch = async () => {
    setForm({ ...form, global_kill_switch_active: !form.global_kill_switch_active });
  };

  if (loading) return <div className="flex justify-center items-center h-64"><Loader2 className="w-8 h-8 animate-spin text-primary-gold" /></div>;
  if (error) return <div className="text-center text-danger">{error}</div>;

  return (
    <div className="space-y-8">
      <PageHeader title="System Settings" subtitle="Configure global platform parameters and AI thresholds." />
      
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-8">
        {/* AI & Risk Engine */}
        <div className="bg-background-panel-1 border border-border-secondary rounded-lg p-6">
          <div className="flex items-center gap-3 mb-6 border-b border-border-secondary pb-4">
            <Settings className="w-5 h-5 text-primary-gold" />
            <h3 className="text-lg font-semibold text-text-primary">AI & Risk Engine Configuration</h3>
          </div>
          
          <div className="space-y-4">
            <div>
              <label className="block text-sm font-medium text-text-muted mb-1.5">Operating Environment</label>
              <select 
                value={form.environment_state}
                onChange={(e) => setForm({ ...form, environment_state: e.target.value as any })}
                className="w-full bg-background-panel-2 border border-border-secondary rounded-md px-3 py-2 text-sm text-text-primary focus:outline-none focus:border-primary-blue"
              >
                <option value="PAPER">PAPER (Simulated Trading)</option>
                <option value="BACKTEST">BACKTEST (Historical Engine)</option>
                <option value="DEMO">DEMO (Client Showcase)</option>
                <option value="LIVE_DISABLED">LIVE (Disabled for MVP)</option>
              </select>
              <p className="text-xs text-text-muted mt-1">Changes the UI state and environment banner across the entire platform.</p>
            </div>
            <div>
              <label className="block text-sm font-medium text-text-muted mb-1.5">Extreme Bearish Threshold (AI Score)</label>
              <input 
                type="number" 
                value={form.extreme_bearish_threshold} 
                onChange={(e) => setForm({ ...form, extreme_bearish_threshold: parseFloat(e.target.value) })}
                step="0.1"
                className="w-full bg-background-panel-2 border border-border-secondary rounded-md px-3 py-2 text-sm text-text-primary focus:outline-none focus:border-primary-blue"
              />
              <p className="text-xs text-text-muted mt-1">If the NLP engine scores an asset below this threshold, all BUY orders will be blocked by the Risk Engine.</p>
            </div>
            
            <div>
              <label className="block text-sm font-medium text-text-muted mb-1.5">Global Maximum Leverage (x)</label>
              <input 
                type="number" 
                value={form.global_max_leverage} 
                onChange={(e) => setForm({ ...form, global_max_leverage: parseFloat(e.target.value) })}
                step="0.5"
                className="w-full bg-background-panel-2 border border-border-secondary rounded-md px-3 py-2 text-sm text-text-primary focus:outline-none focus:border-primary-blue"
              />
              <p className="text-xs text-text-muted mt-1">Absolute ceiling for leverage across all mandates. Individual mandates cannot exceed this value.</p>
            </div>
          </div>
        </div>

        {/* Trading Defaults */}
        <div className="bg-background-panel-1 border border-border-secondary rounded-lg p-6">
          <div className="flex items-center gap-3 mb-6 border-b border-border-secondary pb-4">
            <SlidersHorizontal className="w-5 h-5 text-primary-teal" />
            <h3 className="text-lg font-semibold text-text-primary">Trading & Backtest Defaults</h3>
          </div>
          
          <div className="space-y-4">
            <div>
              <label className="block text-sm font-medium text-text-muted mb-1.5">Default Commission Rate (%)</label>
              <input 
                type="number" 
                value={form.default_commission_pct} 
                onChange={(e) => setForm({ ...form, default_commission_pct: parseFloat(e.target.value) })}
                step="0.01"
                className="w-full bg-background-panel-2 border border-border-secondary rounded-md px-3 py-2 text-sm text-text-primary focus:outline-none focus:border-primary-blue"
              />
            </div>
            
            <div>
              <label className="block text-sm font-medium text-text-muted mb-1.5">Default Slippage Impact (%)</label>
              <input 
                type="number" 
                value={form.default_slippage_pct} 
                onChange={(e) => setForm({ ...form, default_slippage_pct: parseFloat(e.target.value) })}
                step="0.01"
                className="w-full bg-background-panel-2 border border-border-secondary rounded-md px-3 py-2 text-sm text-text-primary focus:outline-none focus:border-primary-blue"
              />
            </div>
          </div>
        </div>

        {/* Emergency Controls */}
        <div className={`${form.global_kill_switch_active ? 'bg-danger/20 border-danger/50' : 'bg-danger/5 border-danger/20'} border rounded-lg p-6 lg:col-span-2 transition-colors`}>
          <div className={`flex items-center gap-3 mb-6 border-b ${form.global_kill_switch_active ? 'border-danger/50' : 'border-danger/20'} pb-4`}>
            <ShieldAlert className={`w-5 h-5 ${form.global_kill_switch_active ? 'text-danger' : 'text-danger/70'}`} />
            <h3 className={`text-lg font-semibold ${form.global_kill_switch_active ? 'text-danger' : 'text-danger/80'}`}>Emergency Controls</h3>
          </div>
          
          <div className="flex items-center justify-between">
            <div>
              <p className="text-sm font-medium text-text-primary">Global Trading Halt (System-wide Kill Switch)</p>
              <p className="text-xs text-text-muted mt-1">Instantly suspends all trade execution across every portfolio and mandate.</p>
            </div>
            <button 
              onClick={handleKillSwitch}
              className={`${form.global_kill_switch_active ? 'bg-background-panel-1 text-danger border-danger' : 'bg-danger hover:bg-danger/80 text-white'} border px-6 py-2.5 rounded-md text-sm font-bold transition-colors shadow-lg`}
            >
              {form.global_kill_switch_active ? 'DISENGAGE HALT' : 'ENGAGE HALT'}
            </button>
          </div>
        </div>
      </div>
      
      {/* Save Button */}
      <div className="flex justify-end pt-4 border-t border-border-secondary">
        <button 
          onClick={handleSave}
          disabled={saving}
          className="flex items-center gap-2 bg-primary-blue hover:bg-primary-blue/90 text-white px-6 py-2.5 rounded-md text-sm font-semibold transition-colors shadow-lg disabled:opacity-50"
        >
          {saving ? <Loader2 className="w-4 h-4 animate-spin" /> : <Save className="w-4 h-4" />}
          {saving ? 'Saving...' : 'Save All Configurations'}
        </button>
      </div>
    </div>
  );
}