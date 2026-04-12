'use client';

import { useState, useEffect } from 'react';
import { addSynonym, getSettings, updateSettings, SystemSettings } from '@/lib/api';

const STANDARD_KEYS = [
  'customer.full_name', 'customer.ic_no', 'customer.date_of_birth',
  'customer.nationality', 'customer.gender', 'customer.marital_status',
  'customer.race', 'customer.religion', 'customer.mobile_no',
  'customer.home_tel', 'customer.email',
  'customer.address_line1', 'customer.address_line2', 'customer.address_line3',
  'customer.postcode', 'customer.city', 'customer.state',
  'customer.employer_name', 'customer.monthly_income',
  'customer.annual_income', 'customer.occupation',
  'customer.employment_type', 'customer.bank_name',
  'customer.loan_amount', 'customer.loan_tenure',
];

// ── 只读标签 ───────────────────────────────────────────────────
function ReadonlyRow({ label, value }: { label: string; value: string }) {
  return (
    <div className="flex items-center justify-between" style={{ paddingBottom: 8, borderBottom: '1px solid #E8E4DE', marginBottom: 8 }}>
      <span className="form-label" style={{ margin: 0 }}>{label}</span>
      <span style={{ fontSize: 12, fontFamily: 'var(--font-mono)', color: 'var(--ink)' }}>{value}</span>
    </div>
  );
}

export default function SettingsPage() {
  const [settings, setSettings]       = useState<SystemSettings | null>(null);
  const [loadingSettings, setLoading] = useState(true);
  const [saving, setSaving]           = useState(false);
  const [saveMsg, setSaveMsg]         = useState('');

  // 同义词
  const [synKey, setSynKey]           = useState('');
  const [synValue, setSynValue]       = useState('');
  const [synSaving, setSynSaving]     = useState(false);
  const [synMsg, setSynMsg]           = useState('');

  // 本地编辑草稿
  const [draft, setDraft]             = useState<Partial<SystemSettings>>({});

  useEffect(() => {
    getSettings()
      .then(s => { setSettings(s); setDraft({}); })
      .catch(() => {})
      .finally(() => setLoading(false));
  }, []);

  const field = <K extends keyof SystemSettings>(key: K) =>
    ((draft as SystemSettings)[key] ?? settings?.[key]) as SystemSettings[K];

  const setField = <K extends keyof SystemSettings>(key: K, val: SystemSettings[K]) => {
    setDraft(d => ({ ...d, [key]: val }));
  };

  const handleSave = async () => {
    setSaving(true);
    setSaveMsg('');
    try {
      const updated = await updateSettings(draft as Parameters<typeof updateSettings>[0]);
      setSettings(updated);
      setDraft({});
      setSaveMsg('✓ 配置已保存');
    } catch {
      setSaveMsg('✕ 保存失败，请检查后端服务');
    } finally {
      setSaving(false);
      setTimeout(() => setSaveMsg(''), 4000);
    }
  };

  const handleAddSynonym = async () => {
    if (!synKey || !synValue) return;
    setSynSaving(true);
    setSynMsg('');
    try {
      await addSynonym(synKey, synValue);
      setSynMsg('✓ 同义词已添加');
      setSynValue('');
    } catch {
      setSynMsg('✕ 添加失败');
    } finally {
      setSynSaving(false);
      setTimeout(() => setSynMsg(''), 3000);
    }
  };

  const hasDraft = Object.keys(draft).length > 0;

  return (
    <div className="page-settings">
      <div className="page-header">
        <h1 className="page-title">Settings</h1>
        <p className="page-subtitle">全局配置、渲染策略、字段字典、同义词管理</p>
      </div>

      <div className="settings-grid">

        {/* ── 渲染策略（固定只读）─────────────────────────────── */}
        <div className="settings-card settings-card--focus">
          <div className="settings-card__title">渲染策略（Render Strategy）</div>
          <p className="caption mb-4" style={{ color: 'var(--danger)', fontWeight: 600 }}>
            以下为系统硬性约束，不可修改。任何违反此策略的输出均视为严重违例。
          </p>
          <ReadonlyRow label="render_base" value="original_pdf  ✓  固定不可改" />
          <ReadonlyRow label="allow_custom_drawn_templates" value="false  —  禁止自绘表格" />
          <ReadonlyRow label="allow_modify_original_content" value="false  —  禁止修改原件" />
          <ReadonlyRow label="result_states" value="PASS / FAIL 严格两值  —  无 warning / manual" />
          <div style={{ marginTop: 12, background: 'rgba(74,63,107,0.06)', borderRadius: 6, padding: '10px 14px', fontSize: 11, color: 'var(--vd)' }}>
            输出 PDF 必须以上传的原件为底板，仅在空白格子位置叠字。
            严禁用 HTML / CSS / Canvas 重绘表格后导出。
            所有结果只允许 PASS 或 FAIL，绝无灰色中间态。
          </div>
        </div>

        {/* ── 字体与排版（可编辑）─────────────────────────────── */}
        <div className="settings-card">
          <div className="settings-card__title">字体与排版</div>
          {loadingSettings ? (
            <div className="flex items-center gap-2"><div className="loading-spinner" /><span className="caption">加载中...</span></div>
          ) : (
            <>
              <div className="form-group">
                <label className="form-label">默认字体 (default_font_name)</label>
                <select
                  className="form-select"
                  value={field('default_font_name')}
                  onChange={e => setField('default_font_name', e.target.value)}
                >
                  <option value="Helvetica">Helvetica（内置，ASCII）</option>
                  <option value="Times-Roman">Times-Roman（内置）</option>
                  <option value="Courier">Courier（内置，等宽）</option>
                  <option value="NotoSansSC">NotoSansSC（需手动安装 TTF）</option>
                </select>
              </div>

              <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr 1fr', gap: 10 }}>
                <div className="form-group">
                  <label className="form-label">最大字号 (max)</label>
                  <input type="number" className="form-input" step="0.5" min="6" max="24"
                    value={field('default_font_size_max')}
                    onChange={e => setField('default_font_size_max', Number(e.target.value))} />
                </div>
                <div className="form-group">
                  <label className="form-label">最小字号 (min)</label>
                  <input type="number" className="form-input" step="0.5" min="4" max="12"
                    value={field('default_font_size_min')}
                    onChange={e => setField('default_font_size_min', Number(e.target.value))} />
                </div>
                <div className="form-group">
                  <label className="form-label">步进 (step)</label>
                  <input type="number" className="form-input" step="0.5" min="0.5" max="2"
                    value={field('default_font_size_step')}
                    onChange={e => setField('default_font_size_step', Number(e.target.value))} />
                </div>
              </div>
            </>
          )}
        </div>

        {/* ── Padding 与垂直策略 ───────────────────────────────── */}
        <div className="settings-card">
          <div className="settings-card__title">Padding 与垂直策略</div>
          {!loadingSettings && (
            <>
              <div className="form-group">
                <label className="form-label">左侧留白 default_left_padding_px（pt）</label>
                <input type="number" className="form-input" step="0.5" min="0" max="20"
                  value={field('default_left_padding_px')}
                  onChange={e => setField('default_left_padding_px', Number(e.target.value))} />
                <p className="caption mt-1">文字起始 x = cell_x0 + 此值</p>
              </div>

              <div className="form-group">
                <label className="form-label">垂直策略 default_vertical_strategy</label>
                <select className="form-select"
                  value={field('default_vertical_strategy')}
                  onChange={e => setField('default_vertical_strategy', e.target.value)}>
                  <option value="center_baseline">center_baseline（垂直居中，推荐）</option>
                  <option value="top">top（贴格子顶部）</option>
                  <option value="custom_offset">custom_offset（自定义偏移）</option>
                </select>
              </div>

              {field('default_vertical_strategy') === 'custom_offset' && (
                <div className="form-group">
                  <label className="form-label">自定义偏移 (pt)</label>
                  <input type="number" className="form-input" step="1" min="-20" max="20"
                    value={field('default_custom_offset')}
                    onChange={e => setField('default_custom_offset', Number(e.target.value))} />
                </div>
              )}

              <div className="form-group">
                <label className="form-label">默认对齐 default_text_align</label>
                <select className="form-select"
                  value={field('default_text_align')}
                  onChange={e => setField('default_text_align', e.target.value)}>
                  <option value="left">left（左对齐，默认）</option>
                  <option value="center">center（居中）</option>
                  <option value="right">right（右对齐）</option>
                </select>
              </div>
            </>
          )}
        </div>

        {/* ── 失败阈值（PRD v3 — 替代旧版溢出策略）────────────── */}
        <div className="settings-card">
          <div className="settings-card__title">失败阈值（Fail Threshold）</div>
          <p className="caption mb-3" style={{ color: 'var(--ink)' }}>
            PRD 规定：溢出不允许标记为灰色状态。超过字符阈值或字号缩至最小仍溢出，
            字段直接判定为 <strong>FAIL</strong>。
          </p>
          {!loadingSettings && (
            <div className="form-group">
              <label className="form-label">字符数上限 fail_threshold</label>
              <input type="number" className="form-input" step="10" min="10" max="500"
                value={field('fail_threshold')}
                onChange={e => setField('fail_threshold', Number(e.target.value))} />
              <p className="caption mt-1">
                超过此字符数 → 字段直接 fail（不尝试收缩字号）。
                字号缩至最小仍溢出 → 同样直接 fail。
                无任何 manual / warning 灰色中间态。
              </p>
            </div>
          )}
        </div>

        {/* ── 验证阈值 ─────────────────────────────────────────── */}
        <div className="settings-card">
          <div className="settings-card__title">验证阈值（Verification）</div>
          {!loadingSettings && (
            <div className="form-group">
              <label className="form-label">图像差分阈值 verify_pixel_diff_threshold</label>
              <input type="number" className="form-input" step="0.005" min="0.001" max="0.05"
                value={field('verify_pixel_diff_threshold')}
                onChange={e => setField('verify_pixel_diff_threshold', Number(e.target.value))} />
              <p className="caption mt-1">
                非填写区域像素差异超过此比例时，视为原件被篡改 → 整体 FAIL。
                默认 0.01 = 1%（严格模式）。超过即判 fail，无 warning 缓冲。
              </p>
            </div>
          )}
          {!loadingSettings && settings?.updated_at && (
            <p className="caption" style={{ marginTop: 8 }}>
              上次更新：{settings.updated_at}
            </p>
          )}
        </div>

        {/* ── 保存按钮区 ───────────────────────────────────────── */}
        <div className="settings-card" style={{ display: 'flex', flexDirection: 'column', justifyContent: 'flex-end' }}>
          <div className="settings-card__title">保存配置</div>
          <p className="caption mb-4">
            修改以上可编辑项后，点击保存。渲染策略字段固定不接受修改。
          </p>
          {saveMsg && (
            <p style={{
              fontSize: 12, marginBottom: 10,
              color: saveMsg.startsWith('✓') ? 'var(--success)' : 'var(--danger)',
            }}>{saveMsg}</p>
          )}
          <button
            className="btn btn--primary w-full"
            onClick={handleSave}
            disabled={!hasDraft || saving || loadingSettings}
            style={{ justifyContent: 'center' }}
          >
            {saving ? 'Saving...' : hasDraft ? 'Save Settings' : 'No Changes'}
          </button>
        </div>

        {/* ── 同义词管理 ───────────────────────────────────────── */}
        <div className="settings-card">
          <div className="settings-card__title">字段同义词管理</div>
          <p className="caption mb-4">
            添加同义词帮助系统将表格标签自动映射到标准字段键。
          </p>
          <div className="form-group">
            <label className="form-label">Standard Key</label>
            <select className="form-select" value={synKey} onChange={e => setSynKey(e.target.value)}>
              <option value="">— Select standard key —</option>
              {STANDARD_KEYS.map(k => <option key={k} value={k}>{k}</option>)}
            </select>
          </div>
          <div className="form-group">
            <label className="form-label">Synonym / Alias</label>
            <input className="form-input" placeholder="例如：Nama Pemohon / 申请人全名"
              value={synValue} onChange={e => setSynValue(e.target.value)} />
          </div>
          {synMsg && (
            <p style={{ fontSize: 11, marginBottom: 10, color: synMsg.startsWith('✓') ? 'var(--success)' : 'var(--danger)' }}>
              {synMsg}
            </p>
          )}
          <button
            className="btn btn--primary w-full"
            onClick={handleAddSynonym}
            disabled={!synKey || !synValue || synSaving}
            style={{ justifyContent: 'center' }}
          >
            {synSaving ? 'Adding...' : 'Add Synonym'}
          </button>
        </div>

        {/* ── 系统信息 ─────────────────────────────────────────── */}
        <div className="settings-card">
          <div className="settings-card__title">System Info</div>
          <div style={{ display: 'flex', flexDirection: 'column', gap: 10 }}>
            {[
              ['Backend', 'FastAPI v3 (Python 3.10+)'],
              ['Frontend', 'Next.js 14 (TypeScript)'],
              ['Database', 'SQLite (templates.db v3.0)'],
              ['PDF Engine', 'pdfplumber + ReportLab + pypdf'],
              ['Verifier', 'verifier.py — PASS/FAIL strict'],
              ['States', 'write | fail  /  pass | fail  — 无灰色状态'],
              ['API Port', 'http://localhost:8000'],
              ['Frontend Port', 'http://localhost:3000'],
            ].map(([label, value]) => (
              <div key={label} className="flex items-center justify-between">
                <span className="form-label" style={{ margin: 0 }}>{label}</span>
                <span style={{ fontSize: 11, fontFamily: 'var(--font-mono)', color: 'var(--ink)' }}>{value}</span>
              </div>
            ))}
          </div>
          <div style={{ marginTop: 12, display: 'flex', flexDirection: 'column', gap: 8 }}>
            <a href="http://localhost:8000/docs" target="_blank" rel="noreferrer"
              className="btn btn--secondary w-full" style={{ justifyContent: 'center' }}>
              Swagger API Docs
            </a>
            <a href="/templates" className="btn btn--secondary w-full" style={{ justifyContent: 'center' }}>
              Manage Templates
            </a>
          </div>
        </div>

      </div>
    </div>
  );
}
