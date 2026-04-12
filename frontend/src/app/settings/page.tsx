'use client';

import { useState } from 'react';
import { addSynonym } from '@/lib/api';

export default function SettingsPage() {
  const [synKey, setSynKey] = useState('');
  const [synValue, setSynValue] = useState('');
  const [synSaving, setSynSaving] = useState(false);
  const [synMsg, setSynMsg] = useState('');

  const handleAddSynonym = async () => {
    if (!synKey || !synValue) return;
    setSynSaving(true);
    setSynMsg('');
    try {
      await addSynonym(synKey, synValue);
      setSynMsg('✓ Synonym added successfully');
      setSynValue('');
    } catch {
      setSynMsg('✕ Failed to add synonym');
    } finally {
      setSynSaving(false);
      setTimeout(() => setSynMsg(''), 3000);
    }
  };

  return (
    <div className="page-settings">
      <div className="page-header">
        <h1 className="page-title">Settings</h1>
        <p className="page-subtitle">系统配置、字段字典管理、同义词设置</p>
      </div>

      <div className="settings-grid">

        {/* ── 系统信息 ── */}
        <div className="settings-card settings-card--focus">
          <div className="settings-card__title">System Info</div>
          <div style={{ display: 'flex', flexDirection: 'column', gap: 12 }}>
            {[
              ['Backend', 'FastAPI (Python 3.10+)'],
              ['Frontend', 'Next.js 14 (TypeScript)'],
              ['Database', 'SQLite (templates.db)'],
              ['PDF Engine', 'pdfplumber + ReportLab + pypdf'],
              ['OCR Engine', 'pytesseract + OpenCV'],
              ['API Port', 'http://localhost:8000'],
              ['Frontend Port', 'http://localhost:3000'],
            ].map(([label, value]) => (
              <div key={label} className="flex items-center justify-between">
                <span className="form-label" style={{ margin: 0 }}>{label}</span>
                <span style={{ fontSize: 12, fontFamily: 'var(--font-mono)', color: 'var(--ink)' }}>{value}</span>
              </div>
            ))}
          </div>
        </div>

        {/* ── 字段同义词 ── */}
        <div className="settings-card">
          <div className="settings-card__title">Field Synonyms</div>
          <p className="caption mb-4">
            添加自定义字段同义词，帮助系统更准确地识别表格标签与标准字段的对应关系。
          </p>
          <div className="form-group">
            <label className="form-label">Standard Key</label>
            <select
              className="form-select"
              value={synKey}
              onChange={e => setSynKey(e.target.value)}
            >
              <option value="">— Select standard key —</option>
              {[
                'customer.full_name', 'customer.ic_no', 'customer.date_of_birth',
                'customer.nationality', 'customer.gender', 'customer.marital_status',
                'customer.race', 'customer.religion', 'customer.mobile_no',
                'customer.home_tel', 'customer.email',
                'customer.address_line1', 'customer.address_line2',
                'customer.postcode', 'customer.city', 'customer.state',
                'customer.employer_name', 'customer.monthly_income',
                'customer.annual_income', 'customer.occupation',
                'customer.employment_type', 'customer.bank_name',
                'customer.loan_amount', 'customer.loan_tenure',
              ].map(k => <option key={k} value={k}>{k}</option>)}
            </select>
          </div>
          <div className="form-group">
            <label className="form-label">Synonym / Alias</label>
            <input
              className="form-input"
              placeholder="例如：Nama Pemohon / 申请人全名"
              value={synValue}
              onChange={e => setSynValue(e.target.value)}
            />
          </div>
          {synMsg && (
            <p style={{
              fontSize: 11, marginBottom: 10,
              color: synMsg.startsWith('✓') ? 'var(--success)' : 'var(--danger)'
            }}>{synMsg}</p>
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

        {/* ── 填表规则 ── */}
        <div className="settings-card">
          <div className="settings-card__title">Fill Rules (Read-only)</div>
          <p className="caption mb-4">当前系统采用的精准回填规则（按蓝图设计）</p>
          {[
            ['Left Padding', '1 × font_size (一个字宽)'],
            ['Vertical Align', 'Centered within cell'],
            ['Font Range', '10pt → 6pt (step: 0.5pt)'],
            ['Right Margin', '2 pt safety margin'],
            ['Overflow Action', 'Mark as "needs_manual"'],
            ['Text Align', 'Left (default), Center, Right'],
            ['Overlay Method', 'ReportLab → merge via pypdf'],
          ].map(([label, value]) => (
            <div key={label} className="flex items-center justify-between" style={{ paddingBottom: 8, borderBottom: '1px solid #E8E4DE', marginBottom: 8 }}>
              <span className="form-label" style={{ margin: 0 }}>{label}</span>
              <span style={{ fontSize: 11, color: 'var(--ink)' }}>{value}</span>
            </div>
          ))}
        </div>

        {/* ── 快速导航 ── */}
        <div className="settings-card">
          <div className="settings-card__title">Quick Links</div>
          <div style={{ display: 'flex', flexDirection: 'column', gap: 10 }}>
            <a href="http://localhost:8000/docs" target="_blank" rel="noreferrer"
              className="btn btn--secondary w-full" style={{ justifyContent: 'center' }}>
              <svg width={14} height={14} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth={2}>
                <path d="M18 13v6a2 2 0 01-2 2H5a2 2 0 01-2-2V8a2 2 0 012-2h6"/>
                <polyline points="15 3 21 3 21 9"/>
                <line x1="10" y1="14" x2="21" y2="3"/>
              </svg>
              FastAPI Swagger Docs
            </a>
            <a href="http://localhost:8000/redoc" target="_blank" rel="noreferrer"
              className="btn btn--secondary w-full" style={{ justifyContent: 'center' }}>
              API ReDoc
            </a>
            <a href="/templates" className="btn btn--secondary w-full" style={{ justifyContent: 'center' }}>
              Manage Templates
            </a>
            <a href="/customers" className="btn btn--secondary w-full" style={{ justifyContent: 'center' }}>
              View Customers
            </a>
          </div>
        </div>

        {/* ── 文件目录 ── */}
        <div className="settings-card" style={{ gridColumn: '1 / -1' }}>
          <div className="settings-card__title">Project Directory Structure</div>
          <pre style={{
            fontFamily: 'var(--font-mono)',
            fontSize: 11,
            lineHeight: 1.8,
            color: 'var(--ink)',
            background: '#F8F6F2',
            padding: 16,
            borderRadius: 'var(--radius)',
            border: '1px solid #E8E4DE',
            overflow: 'auto',
          }}>{`Smart_Form_Filler/
├── backend/
│   ├── main.py                  # FastAPI 入口
│   ├── requirements.txt         # Python 依赖
│   ├── modules/
│   │   ├── analyzer.py          # PDF/图片字段分析
│   │   ├── field_normalizer.py  # 字段标准化 (rapidfuzz)
│   │   ├── template_store.py    # SQLite CRUD
│   │   ├── excel_reader.py      # 客户 Excel 读取
│   │   └── filler.py            # PDF 精准回填
│   ├── database/
│   │   ├── templates.db         # SQLite 模板库
│   │   └── init_db.sql          # 初始化脚本
│   ├── uploads/                 # 上传的原始 PDF
│   └── outputs/                 # 生成的填写 PDF
├── frontend/                    # Next.js 前端
├── customer_master.xlsx         # 客户主资料
└── README.md`}</pre>
        </div>

      </div>
    </div>
  );
}
