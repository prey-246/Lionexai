'use client';

import { useState, useEffect } from 'react';
import { systemAPI, tradeAPI } from '@/lib/api';
import type { RiskMandate } from '@/lib/types';
import { PageHeader } from '@/components/ui/PageHeader';
import { Loader2, Edit2, Save, X, Shield, Zap, Target, History, ShieldAlert } from 'lucide-react';
import { useUser } from '@/contexts/UserContext';

export default function MandatesPage() {
  const { user } = useUser();
  const [mandates, setMandates] = useState<RiskMandate[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  
  const [editingId, setEditingId] = useState<number | null>(null);
  const [editForm, setEditForm] = useState<Partial<RiskMandate>>({});
  const [saving, setSaving] = useState(false);
  
  const [historyOpen, setHistoryOpen] = useState<string | null>(null);
  const [mandateHistory, setMandateHistory] = useState<Record<string, RiskMandate[]>>({});

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

  const toggleHistory = async (mandateId: string) => {
    if (historyOpen === mandateId) {
      setHistoryOpen(null);
      return;
    }
    setHistoryOpen(mandateId);
    if (!mandateHistory[mandateId]) {
      try {
        const history = await systemAPI.getMandateHistory(mandateId);
        setMandateHistory(prev => ({ ...prev, [mandateId]: history }));
      } catch (err: any) {
        console.error(`Failed to fetch history: ${err.message}`);
      }
    }
  };

  const handleCancel = () => {
    setEditingId(null);
    setEditForm({});
  };

  const handleResetKillSwitch = async (mandateId: string) => {
    try {
      await tradeAPI.resetKillSwitch(mandateId);
      await fetchMandates();
    } catch (err: any) {
      alert(`Failed to reset kill switch: ${err.message}`);
    }
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
    if (tier === 'Low') return <Shield className="w-6 h-6 text-primary-emerald" />;
    if (tier === 'Medium') return <Target className="w-6 h-6 text-primary-gold" />;
    return <Zap className="w-6 h-6 text-danger" />;
  };

  if (loading) return <div className="flex justify-center items-center h-64"><Loader2 className="w-8 h-8 animate-spin text-primary-gold" /></div>;
  if (error) return <div className="text-center text-danger">{error}</div>;

  const canEdit = user?.role_tier === 'admin' || user?.role_tier === 'risk_manager';

  return (
    <div className="space-y-8">
      <PageHeader title="Risk Mandates" subtitle="Configure and govern institutional risk limits and execution parameters." />

      <div className="g21">
        {mandates.map((mandate) => {
          const isEditing = editingId === mandate.pk_id;
          
          return (
            <div key={mandate.pk_id} className="card gold overflow-hidden flex flex-col shadow-lg p-0">
              
              {/* Header */}
              <div className="p-6 border-b border-border-default bg-background-base flex justify-between items-start">
                <div>
                  <div className="flex items-center gap-3 mb-1">
                    {getTierIcon(mandate.risk_tier)}
                    <h3 className="font-serif text-[24px] font-light text-text-primary leading-none">{mandate.name}</h3>
                    <span className="tag grey">
                      {mandate.id}
                    </span>
                {mandate.kill_switch_active && (
                  <span className="tag red animate-pulse flex items-center gap-1"><ShieldAlert className="w-3 h-3" /> HALTED</span>
                )}
                  </div>
                  <p className="font-mono text-[9px] text-text-muted uppercase tracking-wider flex items-center gap-2 mt-2">
                    <History className="w-3 h-3" /> v{mandate.version} (Active)
                  </p>
                </div>
                
                <div className="flex items-center gap-2">
                  <button 
                    onClick={() => toggleHistory(mandate.id)}
                    className="btn grey"
                  >
                    <History className="w-4 h-4" /> History
                  </button>
                  {canEdit && !isEditing && (
                    <button 
                      onClick={() => handleEditClick(mandate)}
                      className="btn gold"
                    >
                      <Edit2 className="w-4 h-4" /> Edit
                    </button>
                  )}
                </div>
              </div>

              {/* Body */}
              <div className="p-8 flex-grow">
                {isEditing ? (
                  <div className="space-y-4 animate-in fade-in">
                    <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                      <div className="md:col-span-2">
                        <label className="block font-mono text-[11px] uppercase tracking-wider text-text-muted mb-1">Mandate Name</label>
                        <input type="text" className="w-full border border-border-default rounded-lg px-3 py-2 font-sans text-[13px] focus:outline-none focus:border-primary-gold" value={editForm.name} onChange={e => setEditForm({...editForm, name: e.target.value})} />
                      </div>
                      <div className="md:col-span-2">
                        <label className="block font-mono text-[11px] uppercase tracking-wider text-text-muted mb-1">Description</label>
                        <textarea className="w-full border border-border-default rounded-lg px-3 py-2 font-sans text-[13px] focus:outline-none focus:border-primary-gold" value={editForm.description} onChange={e => setEditForm({...editForm, description: e.target.value})} rows={2} />
                      </div>
                      <div>
                        <label className="block font-mono text-[11px] uppercase tracking-wider text-text-muted mb-1">Risk Tier</label>
                        <select className="w-full border border-border-default rounded-lg px-3 py-2 font-sans text-[13px] focus:outline-none focus:border-primary-blue" value={editForm.risk_tier} onChange={e => setEditForm({...editForm, risk_tier: e.target.value})}>
                          <option value="Low">Low</option>
                          <option value="Medium">Medium</option>
                          <option value="High">High</option>
                        </select>
                      </div>
                      <div>
                        <label className="block font-mono text-[11px] uppercase tracking-wider text-text-muted mb-1">Max Leverage (x)</label>
                        <input type="number" step="0.1" className="w-full border border-border-default rounded-lg px-3 py-2 font-sans text-[13px] focus:outline-none focus:border-primary-blue" value={editForm.max_leverage} onChange={e => setEditForm({...editForm, max_leverage: parseFloat(e.target.value)})} />
                      </div>
                      <div>
                        <label className="block font-mono text-[11px] uppercase tracking-wider text-text-muted mb-1">Daily Loss Limit (%)</label>
                        <input type="number" step="0.1" className="w-full border border-border-default rounded-lg px-3 py-2 font-sans text-[13px] focus:outline-none focus:border-primary-blue" value={editForm.daily_loss_limit_pct} onChange={e => setEditForm({...editForm, daily_loss_limit_pct: parseFloat(e.target.value)})} />
                      </div>
                      <div>
                        <label className="block font-mono text-[11px] uppercase tracking-wider text-text-muted mb-1">Max Drawdown (%)</label>
                        <input type="number" step="0.1" className="w-full border border-border-default rounded-lg px-3 py-2 font-sans text-[13px] focus:outline-none focus:border-primary-blue" value={editForm.max_drawdown_pct} onChange={e => setEditForm({...editForm, max_drawdown_pct: parseFloat(e.target.value)})} />
                      </div>
                      <div>
                        <label className="block font-mono text-[11px] uppercase tracking-wider text-text-muted mb-1">Max Position Size (%)</label>
                        <input type="number" step="0.1" className="w-full border border-border-default rounded-lg px-3 py-2 font-sans text-[13px] focus:outline-none focus:border-primary-blue" value={editForm.max_position_size_pct} onChange={e => setEditForm({...editForm, max_position_size_pct: parseFloat(e.target.value)})} />
                      </div>
                  <div>
                    <label className="block font-mono text-[11px] uppercase tracking-wider text-text-muted mb-1">Max Open Positions</label>
                    <input type="number" className="w-full border border-border-default rounded-lg px-3 py-2 font-sans text-[13px] focus:outline-none focus:border-primary-blue" value={editForm.max_open_positions} onChange={e => setEditForm({...editForm, max_open_positions: parseInt(e.target.value)})} />
                  </div>
                  <div>
                    <label className="block font-mono text-[11px] uppercase tracking-wider text-text-muted mb-1">Max Portfolio Exposure (%)</label>
                    <input type="number" step="0.1" className="w-full border border-border-default rounded-lg px-3 py-2 font-sans text-[13px] focus:outline-none focus:border-primary-blue" value={editForm.max_portfolio_exposure_pct} onChange={e => setEditForm({...editForm, max_portfolio_exposure_pct: parseFloat(e.target.value)})} />
                  </div>
                  <div className="flex items-center gap-2 mt-4">
                    <input type="checkbox" id="kill_switch" className="w-4 h-4 accent-primary-blue" checked={editForm.kill_switch_enabled} onChange={e => setEditForm({...editForm, kill_switch_enabled: e.target.checked})} />
                    <label htmlFor="kill_switch" className="font-mono text-[11px] uppercase tracking-wider text-text-muted cursor-pointer">Enable Automated Kill Switch</label>
                  </div>
                    </div>
                    
                    <div className="flex justify-end gap-3 pt-6 mt-6 border-t border-border-default">
                      <button onClick={handleCancel} disabled={saving} className="btn grey">
                        <X className="w-3 h-3 mr-1" /> Cancel
                      </button>
                      <button onClick={() => handleSave(mandate.pk_id)} disabled={saving} className="btn teal">
                        {saving ? <Loader2 className="w-3 h-3 mr-1 animate-spin" /> : <Save className="w-3 h-3 mr-1" />} Save New Version
                      </button>
                    </div>
                  </div>
                ) : (
                  <div className="space-y-6">
                    <div className="flex items-center gap-6 mb-6 pb-6 border-b border-border-default">
                      <div className="font-mono text-[11px] uppercase tracking-wider text-text-muted"><span className="text-text-secondary font-bold">Created By:</span> {(mandate as any).created_by_id || 'System Genesis'}</div>
                      <div className="font-mono text-[11px] uppercase tracking-wider text-text-muted"><span className="text-text-secondary font-bold">Approved By:</span> {(mandate as any).approved_by_id || 'Auto-Approved'}</div>
                      <div className="font-mono text-[11px] uppercase tracking-wider text-text-muted"><span className="text-text-secondary font-bold">Effective:</span> {(mandate as any).effective_date ? new Date((mandate as any).effective_date).toLocaleDateString() : new Date(mandate.created_at).toLocaleDateString()}</div>
                    </div>
                    
                    <p className="font-sans text-[13px] text-text-muted">{mandate.description}</p>
                    
                    <div className="grid grid-cols-2 md:grid-cols-4 gap-y-6 gap-x-4">
                      <div><p className="font-mono text-[10px] text-text-muted mb-1 uppercase tracking-wider">Max Leverage</p><p className="font-serif text-[26px] font-bold text-text-primary">{mandate.max_leverage.toFixed(1)}x</p></div>
                      <div><p className="font-mono text-[10px] text-text-muted mb-1 uppercase tracking-wider">Daily Loss Limit</p><p className="font-serif text-[26px] font-bold text-danger">{mandate.daily_loss_limit_pct.toFixed(1)}%</p></div>
                      <div><p className="font-mono text-[10px] text-text-muted mb-1 uppercase tracking-wider">Max Drawdown</p><p className="font-serif text-[26px] font-bold text-danger">{mandate.max_drawdown_pct.toFixed(1)}%</p></div>
                      <div><p className="font-mono text-[10px] text-text-muted mb-1 uppercase tracking-wider">Position Limit</p><p className="font-serif text-[26px] font-bold text-text-primary">{mandate.max_position_size_pct.toFixed(1)}%</p></div>
                      <div><p className="font-mono text-[10px] text-text-muted mb-1 uppercase tracking-wider">Open Positions</p><p className="font-serif text-[26px] font-bold text-text-primary">{mandate.max_open_positions}</p></div>
                      <div><p className="font-mono text-[10px] text-text-muted mb-1 uppercase tracking-wider">Max Exposure</p><p className="font-serif text-[26px] font-bold text-text-primary">{mandate.max_portfolio_exposure_pct?.toFixed(1)}%</p></div>
                      <div><p className="font-mono text-[10px] text-text-muted mb-1 uppercase tracking-wider">Auto Kill-Switch</p><p className={`font-serif text-[26px] font-bold ${mandate.kill_switch_enabled ? 'text-success' : 'text-text-muted'}`}>{mandate.kill_switch_enabled ? 'Enabled' : 'Disabled'}</p></div>
                    </div>
                  </div>
                )}

                {/* History Section */}
                {historyOpen === mandate.id && mandateHistory[mandate.id] && (
                  <div className="mt-8 pt-8 border-t border-border-default animate-in fade-in duration-300">
                    <h4 className="sec-head flex items-center gap-2">
                      <History className="w-5 h-5 text-primary-gold" />
                      Version History Archive
                    </h4>
                    <div className="space-y-3 max-h-64 overflow-y-auto pr-2">
                      {mandateHistory[mandate.id].map(hist => (
                        <div key={hist.pk_id} className={`card p-4 ${hist.is_active ? 'gold' : ''}`}>
                          <div className="flex justify-between items-center mb-3">
                            <span className={`font-sans text-[13px] font-semibold ${hist.is_active ? 'text-primary-gold' : 'text-text-primary'}`}>Version {hist.version}</span>
                            <span className={`tag ${hist.is_active ? 'teal' : 'grey'}`}>
                              {hist.is_active ? 'Active' : 'Archived'}
                            </span>
                          </div>
                          <div className="grid grid-cols-2 md:grid-cols-4 gap-3 text-xs mb-2">
                            <div><span className="block font-mono text-[10px] text-text-muted mb-1 uppercase tracking-wider">Max Leverage</span><span className="font-serif text-[16px] font-bold text-text-primary">{hist.max_leverage.toFixed(1)}x</span></div>
                            <div><span className="block font-mono text-[10px] text-text-muted mb-1 uppercase tracking-wider">Daily Loss</span><span className="font-serif text-[16px] font-bold text-danger">{hist.daily_loss_limit_pct.toFixed(1)}%</span></div>
                            <div><span className="block font-mono text-[10px] text-text-muted mb-1 uppercase tracking-wider">Max Drawdown</span><span className="font-serif text-[16px] font-bold text-danger">{hist.max_drawdown_pct.toFixed(1)}%</span></div>
                            <div><span className="block font-mono text-[10px] text-text-muted mb-1 uppercase tracking-wider">Position Limit</span><span className="font-serif text-[16px] font-bold text-text-primary">{hist.max_position_size_pct.toFixed(1)}%</span></div>
                          </div>
                          <div className="text-[10px] text-text-muted flex justify-between">
                            <span className="font-sans text-[11px]">{hist.description}</span>
                            <span>{new Date(hist.created_at).toLocaleDateString()}</span>
                          </div>
                        </div>
                      ))}
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