'use client';

import { useEffect, useState } from 'react';
import { useParams, useRouter } from 'next/navigation';
import { getTemplate, updateFields, getStandardKeys, Template, Field } from '@/lib/api';

export default function TemplateDetailPage() {
  const { id } = useParams<{ id: string }>();
  const router = useRouter();

  const [template, setTemplate] = useState<Template | null>(null);
  const [fields, setFields] = useState<Field[]>([]);
  const [standardKeys, setStandardKeys] = useState<string[]>([]);
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [saved, setSaved] = useState(false);
  const [error, setError] = useState('');

  useEffect(() => {
    Promise.all([getTemplate(Number(id)), getStandardKeys()])
      .then(([t, keys]) => {
        setTemplate(t);
        setFields(t.fields || []);
        setStandardKeys(keys);
      })
      .catch(() => setError('无法加载模板，请检查后端服务'))
      .finally(() => setLoading(false));
  }, [id]);

  const handleFieldChange = (fieldId: number, key: keyof Field, value: string | number) => {
    setFields(prev => prev.map(f => f.id === fieldId ? { ...f, [key]: value } : f));
  };

  const handleSave = async () => {
    setSaving(true);
    setSaved(false);
    try {
      const updates = fields.map(f => ({
        id: f.id,
        standard_key: f.standard_key,
        align: f.align,
        font_size_max: f.font_size_max,
        font_size_min: f.font_size_min,
        is_confirmed: 1,
      }));
      await updateFields(Number(id), updates);
      setSaved(true);
      setTimeout(() => setSaved(false), 2000);
    } catch {
      setError('保存失败');
    } finally {
      setSaving(false);
    }
  };

  if (loading) return (
    <div className="card text-center" style={{ padding: 48, marginTop: 24 }}>
      <div className="loading-spinner" style={{ margin: '0 auto 12px' }} />
      <p className="caption">Loading template...</p>
    </div>
  );

  if (!template) return (
    <div className="card text-center" style={{ padding: 48, marginTop: 24 }}>
      <p className="text-danger">模板不存在或无法加载</p>
    </div>
  );

  return (
    <>
      <div className="page-header">
        <div className="flex items-center justify-between">
          <div>
            <h1 className="page-title">{template.name}</h1>
            <p className="page-subtitle">
              {template.institution && `${template.institution} · `}
              {template.page_count} page(s) · {fields.length} fields
            </p>
          </div>
          <div className="flex gap-2">
            <button
              className="btn btn--secondary"
              onClick={() => router.back()}
            >
              ← Back
            </button>
            <button
              className="btn btn--primary"
              onClick={handleSave}
              disabled={saving}
            >
              {saving ? 'Saving...' : saved ? '✓ Saved' : 'Save & Confirm'}
            </button>
          </div>
        </div>
      </div>

      {error && (
        <div className="mb-4" style={{
          background: 'rgba(217,79,79,0.08)', border: '1px solid var(--danger)',
          borderRadius: 'var(--radius)', padding: '10px 14px', fontSize: 12, color: 'var(--danger)'
        }}>
          {error}
        </div>
      )}

      {/* Template info */}
      <div className="card mb-4">
        <div className="grid-4">
          <div><span className="form-label">ID</span><p>#{template.id}</p></div>
          <div><span className="form-label">Status</span>
            <span className={`badge badge--${template.status === 'active' ? 'success' : template.status === 'confirmed' ? 'info' : 'muted'}`}>
              {template.status}
            </span>
          </div>
          <div><span className="form-label">Pages</span><p>{template.page_count}</p></div>
          <div><span className="form-label">Created</span><p>{template.created_at?.slice(0, 10)}</p></div>
        </div>
      </div>

      {/* Fields table */}
      <div className="card" style={{ padding: 0, overflow: 'hidden' }}>
        <div className="preview-panel__header">
          <span className="section-title">Field Mapping</span>
          <span className="caption">{fields.filter(f => f.is_confirmed).length} / {fields.length} confirmed</span>
        </div>

        {fields.length === 0 ? (
          <div className="empty-state" style={{ padding: 32 }}>
            <p>此模板尚无字段记录，可能分析失败。请重新上传或手动添加。</p>
          </div>
        ) : (
          <div style={{ overflowX: 'auto' }}>
            <table className="data-table">
              <thead>
                <tr>
                  <th>Page</th>
                  <th>Raw Label</th>
                  <th>Standard Key</th>
                  <th>Align</th>
                  <th>Font Max</th>
                  <th>Font Min</th>
                  <th>Cell Size</th>
                  <th>Status</th>
                </tr>
              </thead>
              <tbody>
                {fields.map(f => (
                  <tr key={f.id}>
                    <td>{f.page_number}</td>
                    <td style={{ minWidth: 120 }}>
                      <input
                        className="form-input"
                        style={{ padding: '4px 6px', fontSize: 11 }}
                        value={f.raw_label || ''}
                        onChange={e => handleFieldChange(f.id, 'raw_label', e.target.value)}
                      />
                    </td>
                    <td style={{ minWidth: 200 }}>
                      <select
                        className="form-select"
                        style={{ padding: '4px 6px', fontSize: 11 }}
                        value={f.standard_key || ''}
                        onChange={e => handleFieldChange(f.id, 'standard_key', e.target.value)}
                      >
                        <option value="">— Unassigned —</option>
                        {standardKeys.map(k => (
                          <option key={k} value={k}>{k}</option>
                        ))}
                      </select>
                    </td>
                    <td style={{ minWidth: 90 }}>
                      <select
                        className="form-select"
                        style={{ padding: '4px 6px', fontSize: 11 }}
                        value={f.align || 'left'}
                        onChange={e => handleFieldChange(f.id, 'align', e.target.value)}
                      >
                        <option value="left">Left</option>
                        <option value="center">Center</option>
                        <option value="right">Right</option>
                      </select>
                    </td>
                    <td style={{ minWidth: 70 }}>
                      <input
                        type="number"
                        className="form-input"
                        style={{ padding: '4px 6px', fontSize: 11, width: 60 }}
                        value={f.font_size_max || 10}
                        step={0.5}
                        min={4}
                        max={20}
                        onChange={e => handleFieldChange(f.id, 'font_size_max', parseFloat(e.target.value))}
                      />
                    </td>
                    <td style={{ minWidth: 70 }}>
                      <input
                        type="number"
                        className="form-input"
                        style={{ padding: '4px 6px', fontSize: 11, width: 60 }}
                        value={f.font_size_min || 6}
                        step={0.5}
                        min={4}
                        max={12}
                        onChange={e => handleFieldChange(f.id, 'font_size_min', parseFloat(e.target.value))}
                      />
                    </td>
                    <td className="text-muted" style={{ whiteSpace: 'nowrap', fontSize: 11 }}>
                      {f.cell_width?.toFixed(0)}×{f.cell_height?.toFixed(0)} pt
                    </td>
                    <td>
                      {f.needs_manual
                        ? <span className="badge badge--warning">Manual</span>
                        : f.is_confirmed
                        ? <span className="badge badge--success">✓</span>
                        : <span className="badge badge--muted">Draft</span>}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>

      <div className="flex justify-end mt-4 gap-3">
        <button className="btn btn--primary btn--lg" onClick={handleSave} disabled={saving}>
          {saving ? 'Saving...' : 'Save & Confirm All Fields'}
        </button>
        <button className="btn btn--secondary btn--lg" onClick={() => router.push(`/fill?template=${id}`)}>
          Proceed to Fill Form →
        </button>
      </div>
    </>
  );
}
