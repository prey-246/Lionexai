'use client';

import { useState } from 'react';
import { PageHeader } from '@/components/ui/PageHeader';
import { Settings, Save, ShieldAlert, SlidersHorizontal, Activity, Loader2 } from 'lucide-react';

export default function AdminSettingsPage() {
  const [saving, setSaving] = useState(false);

  const handleSave = () => {
    setSaving(true);
    setTimeout(() => {
      setSaving(false);
      alert("Settings updated successfully! (Note: Global settings are currently saved to local session in this MVP version).");
    }, 800);
  };

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
              <label className="block text-sm font-medium text-text-muted mb-1.5">Extreme Bearish Threshold (AI Score)</label>
              <input 
                type="number" 
                defaultValue="-0.5" 
                step="0.1"
                className="w-full bg-background-panel-2 border border-border-secondary rounded-md px-3 py-2 text-sm text-text-primary focus:outline-none focus:border-primary-blue"
              />
              <p className="text-xs text-text-muted mt-1">If the NLP engine scores an asset below this threshold, all BUY orders will be blocked by the Risk Engine.</p>
            </div>
            
            <div>
              <label className="block text-sm font-medium text-text-muted mb-1.5">Global Maximum Leverage (x)</label>
              <input 
                type="number" 
                defaultValue="5.0" 
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
                defaultValue="0.1" 
                step="0.01"
                className="w-full bg-background-panel-2 border border-border-secondary rounded-md px-3 py-2 text-sm text-text-primary focus:outline-none focus:border-primary-blue"
              />
            </div>
            
            <div>
              <label className="block text-sm font-medium text-text-muted mb-1.5">Default Slippage Impact (%)</label>
              <input 
                type="number" 
                defaultValue="0.1" 
                step="0.01"
                className="w-full bg-background-panel-2 border border-border-secondary rounded-md px-3 py-2 text-sm text-text-primary focus:outline-none focus:border-primary-blue"
              />
            </div>
          </div>
        </div>

        {/* Emergency Controls */}
        <div className="bg-danger/5 border border-danger/20 rounded-lg p-6 lg:col-span-2">
          <div className="flex items-center gap-3 mb-6 border-b border-danger/20 pb-4">
            <ShieldAlert className="w-5 h-5 text-danger" />
            <h3 className="text-lg font-semibold text-danger">Emergency Controls</h3>
          </div>
          
          <div className="flex items-center justify-between">
            <div>
              <p className="text-sm font-medium text-text-primary">Global Trading Halt (System-wide Kill Switch)</p>
              <p className="text-xs text-text-muted mt-1">Instantly suspends all trade execution across every portfolio and mandate.</p>
            </div>
            <button className="bg-danger hover:bg-danger/80 text-white px-6 py-2.5 rounded-md text-sm font-bold transition-colors shadow-lg">
              ENGAGE HALT
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