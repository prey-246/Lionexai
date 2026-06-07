'use client';

import { useState, useEffect } from 'react';
import { systemAPI } from '@/lib/api';
import type { RiskMandate } from '@/lib/types';
import { PageHeader } from '@/components/ui/PageHeader';
import { Loader2, Edit2, Save, X, Shield, Zap, Target, History } from 'lucide-react';
import { useUser } from '@/contexts/UserContext';

export default function MandatesPage() {
  const { user } = useUser();
  const [mandates, setMandates] = useState<RiskMandate[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  
  const [editingId, setEditingId] = useState<number | null>(null);
  const [editForm, setEditForm] = useState<Partial<RiskMandate>>({});
  const [saving, setSaving] = useState(false);

  const fetchMandates = async () => {
    try {
      setLoading(true);
      const data = await systemAPI.getMandates();
      setMandates(data || []);
    } catch (err: any) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchMandates();
  }, []);

  const handleEditClick = (mandate: RiskMandate) => {
    setEditingId(mandate.pk_id);
    setEditForm(mandate);
  };

  const handleCancel = () => {
    setEditingId(null);
    setEditForm({});
  };

  const handleSave = async (pkId: number) => {
    try {
      setSaving(true);
      // We exclude fields that shouldn't be manually updated
      const { pk_id, id, version, is_active, created_at, updated_at, kill_switch_active, ...updatePayload } = editForm as any;
      
      await systemAPI.updateMandate(pkId, updatePayload);
      await fetchMandates();
      setEditingId(null);
    } catch (err: any) {
      alert(`Failed to update mandate: ${err.message}`);
    } finally {
      setSaving(false);
    }
  };

  const getTierIcon = (tier: string) => {
    if (tier === 'Low') return <Shield className="w-5 h-5 text-primary-teal" />;
    if (tier === 'Medium') return <Target className="w-5 h-5 text-primary-blue" />;
    return <Zap className="w-5 h-5 text-primary-gold" />;
  };

  if (loading) return <div className="flex justify-center items-center h-64"><Loader2 className="w-8 h-8 animate-spin text-primary-gold" /></div>;
  if (error) return <div className="text-center text-danger">{error}</div>;

  const canEdit = user?.role_tier === 'admin' || user?.role_tier === 'risk_manager';

  return (
    <div className="space-y-8">
      <PageHeader title="Risk Mandates" subtitle="Configure and govern institutional risk limits and execution parameters." />

      <div className="grid grid-cols-1 xl:grid-cols-2 gap-6">
        {mandates.map((mandate) => {
          const isEditing = editingId === mandate.pk_id;
          
          return (
            <div key={mandate.pk_id} className="bg-background-panel-1 border border-border-secondary rounded-lg overflow-hidden flex flex-col">
              
              {/* Header */}
              <div className="p-5 border-b border-border-secondary bg-background-panel-2/50 flex justify-between items-start">
                <div>
                  <div className="flex items-center gap-3 mb-1">
                    {getTierIcon(mandate.risk_tier)}
                    <h3 className="text-lg font-bold text-text-primary">{mandate.name}</h3>
                    <span className="bg-background-panel-2 px-2 py-0.5 rounded text-xs font-mono text-text-muted border border-border-secondary">
                      {mandate.id}
                    </span>
                  </div>
                  <p className="text-sm text-text-muted flex items-center gap-2">
                    <History className="w-3 h-3" /> v{mandate.version} (Active)
                  </p>
                </div>
                
                {canEdit && !isEditing && (
                  <button 
                    onClick={() => handleEditClick(mandate)}
                    className="flex items-center gap-2 px-3 py-1.5 bg-primary-blue/10 hover:bg-primary-blue/20 text-primary-blue rounded-md text-sm font-semibold transition-colors"
                  >
                    <Edit2 className="w-4 h-4" /> Edit
                  </button>
                )}
              </div>

              {/* Body */}
              <div className="p-6 flex-grow">
                {isEditing ? (
                  <div className="space-y-4 animate-in fade-in">
                    <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                      <div className="md:col-span-2">
                        <label className="block text-xs font-medium text-text-muted mb-1">Mandate Name</label>
                        <input type="text" className="w-full bg-background-panel-2 border border-border-secondary rounded-md px-3 py-2 text-sm text-white focus:outline-none focus:border-primary-blue" value={editForm.name} onChange={e => setEditForm({...editForm, name: e.target.value})} />
                      </div>
                      <div className="md:col-span-2">
                        <label className="block text-xs font-medium text-text-muted mb-1">Description</label>
                        <textarea className="w-full bg-background-panel-2 border border-border-secondary rounded-md px-3 py-2 text-sm text-white focus:outline-none focus:border-primary-blue" value={editForm.description} onChange={e => setEditForm({...editForm, description: e.target.value})} rows={2} />
                      </div>
                      <div>
                        <label className="block text-xs font-medium text-text-muted mb-1">Risk Tier</label>
                        <select className="w-full bg-background-panel-2 border border-border-secondary rounded-md px-3 py-2 text-sm text-white focus:outline-none focus:border-primary-blue" value={editForm.risk_tier} onChange={e => setEditForm({...editForm, risk_tier: e.target.value})}>
                          <option value="Low">Low</option>
                          <option value="Medium">Medium</option>
                          <option value="High">High</option>
                        </select>
                      </div>
                      <div>
                        <label className="block text-xs font-medium text-text-muted mb-1">Max Leverage (x)</label>
                        <input type="number" step="0.1" className="w-full bg-background-panel-2 border border-border-secondary rounded-md px-3 py-2 text-sm text-white focus:outline-none focus:border-primary-blue" value={editForm.max_leverage} onChange={e => setEditForm({...editForm, max_leverage: parseFloat(e.target.value)})} />
                      </div>
                      <div>
                        <label className="block text-xs font-medium text-text-muted mb-1">Daily Loss Limit (%)</label>
                        <input type="number" step="0.1" className="w-full bg-background-panel-2 border border-border-secondary rounded-md px-3 py-2 text-sm text-white focus:outline-none focus:border-primary-blue" value={editForm.daily_loss_limit_pct} onChange={e => setEditForm({...editForm, daily_loss_limit_pct: parseFloat(e.target.value)})} />
                      </div>
                      <div>
                        <label className="block text-xs font-medium text-text-muted mb-1">Max Drawdown (%)</label>
                        <input type="number" step="0.1" className="w-full bg-background-panel-2 border border-border-secondary rounded-md px-3 py-2 text-sm text-white focus:outline-none focus:border-primary-blue" value={editForm.max_drawdown_pct} onChange={e => setEditForm({...editForm, max_drawdown_pct: parseFloat(e.target.value)})} />
                      </div>
                      <div>
                        <label className="block text-xs font-medium text-text-muted mb-1">Max Position Size (%)</label>
                        <input type="number" step="0.1" className="w-full bg-background-panel-2 border border-border-secondary rounded-md px-3 py-2 text-sm text-white focus:outline-none focus:border-primary-blue" value={editForm.max_position_size_pct} onChange={e => setEditForm({...editForm, max_position_size_pct: parseFloat(e.target.value)})} />
                      </div>
                    </div>
                    
                    <div className="flex justify-end gap-3 pt-4 mt-4 border-t border-border-secondary">
                      <button onClick={handleCancel} disabled={saving} className="px-4 py-2 bg-background-panel-2 hover:bg-white/10 rounded-md text-sm font-semibold transition-colors disabled:opacity-50 flex items-center gap-2">
                        <X className="w-4 h-4" /> Cancel
                      </button>
                      <button onClick={() => handleSave(mandate.pk_id)} disabled={saving} className="px-4 py-2 bg-primary-teal hover:bg-primary-teal/80 text-[#050816] rounded-md text-sm font-bold transition-colors disabled:opacity-50 flex items-center gap-2 shadow-lg">
                        {saving ? <Loader2 className="w-4 h-4 animate-spin" /> : <Save className="w-4 h-4" />}
                        Save New Version
                      </button>
                    </div>
                  </div>
                ) : (
                  <div className="space-y-6">
                    <p className="text-sm text-text-muted italic">{mandate.description}</p>
                    
                    <div className="grid grid-cols-2 md:grid-cols-3 gap-y-6 gap-x-4">
                      <div><p className="text-xs text-text-muted mb-1 uppercase tracking-wider">Max Leverage</p><p className="font-mono font-semibold text-text-primary text-lg">{mandate.max_leverage.toFixed(1)}x</p></div>
                      <div><p className="text-xs text-text-muted mb-1 uppercase tracking-wider">Daily Loss Limit</p><p className="font-mono font-semibold text-danger text-lg">{mandate.daily_loss_limit_pct.toFixed(1)}%</p></div>
                      <div><p className="text-xs text-text-muted mb-1 uppercase tracking-wider">Max Drawdown</p><p className="font-mono font-semibold text-danger text-lg">{mandate.max_drawdown_pct.toFixed(1)}%</p></div>
                      <div><p className="text-xs text-text-muted mb-1 uppercase tracking-wider">Position Limit</p><p className="font-mono font-semibold text-text-primary text-lg">{mandate.max_position_size_pct.toFixed(1)}%</p></div>
                      <div><p className="text-xs text-text-muted mb-1 uppercase tracking-wider">Open Positions</p><p className="font-mono font-semibold text-text-primary text-lg">{mandate.max_open_positions}</p></div>
                    </div>
                  </div>
                )}
              </div>
            </div>
          );
        })}
      </div>
    </div>
  );
}