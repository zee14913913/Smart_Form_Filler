'use client';

import { useEffect, useState, Suspense } from 'react';
import { useSearchParams } from 'next/navigation';
import {
  getTemplates, getCustomers, fillForm,
  Template, Customer, FillFormResponse, FieldVerdict,
} from '@/lib/api';

// ── 验证状态标签 ───────────────────────────────────────────────

function VerdictBadge({ verdict }: { verdict: string }) {
  const map: Record<string, { cls: string; label: string }> = {
    pass   : { cls: 'badge--success', label: '✓ PASS' },
    warning: { cls: 'badge--warning', label: '⚠ WARNING' },
    fail   : { cls: 'badge--danger',  label: '✕ FAIL' },
    manual : { cls: 'badge--warning', label: '✎ MANUAL' },
  };
  const { cls, label } = map[verdict] ?? { cls: 'badge--muted', label: verdict };
  return <span className={`badge ${cls}`}>{label}</span>;
}

// ── 验证摘要卡片 ───────────────────────────────────────────────

function VerificationCard({ result }: { result: FillFormResponse }) {
  const v = result.verification;
  const [expanded, setExpanded] = useState(false);

  const verdictColor =
    v.final_verdict === 'pass'    ? 'var(--success)' :
    v.final_verdict === 'warning' ? 'var(--warning)' :
    'var(--danger)';

  return (
    <div style={{
      border: `1px solid ${verdictColor}`,
      borderRadius: 'var(--radius)',
      padding: 16,
      marginBottom: 16,
      background: '#FAFAF9',
    }}>
      {/* 标题行 */}
      <div className="flex items-center justify-between mb-3">
        <span className="section-title" style={{ color: verdictColor }}>
          验证结果 — {v.final_verdict.toUpperCase()}
        </span>
        <VerdictBadge verdict={v.final_verdict} />
      </div>

      {/* 统计格 */}
      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(5, 1fr)', gap: 8, marginBottom: 12 }}>
        {[
          { label: '总字段', val: v.total_fields, color: 'var(--ink)' },
          { label: 'Pass',   val: v.pass_count,    color: 'var(--success)' },
          { label: 'Warning',val: v.warning_count,  color: 'var(--warning)' },
          { label: 'Fail',   val: v.fail_count,     color: 'var(--danger)' },
          { label: 'Manual', val: v.manual_count,   color: '#8A6000' },
        ].map(({ label, val, color }) => (
          <div key={label} style={{ textAlign: 'center', background: 'var(--vp)', borderRadius: 6, padding: '6px 0' }}>
            <div style={{ fontSize: 18, fontWeight: 700, color }}>{val}</div>
            <div style={{ fontSize: 10, color: 'var(--dg)' }}>{label}</div>
          </div>
        ))}
      </div>

      {/* 图像差分行 */}
      {v.image_diff_available && (
        <div style={{ fontSize: 11, color: 'var(--dg)', marginBottom: 8 }}>
          原件图像对比：<VerdictBadge verdict={v.image_diff_verdict} />
          {v.image_diff_verdict === 'pass' && (
            <span style={{ marginLeft: 8 }}>非填写区域与原件 100% 一致 ✓</span>
          )}
        </div>
      )}
      {!v.image_diff_available && (
        <div style={{ fontSize: 11, color: 'var(--dg)', marginBottom: 8 }}>
          图像差分对比：未启用（需安装 pdf2image + Pillow）
        </div>
      )}

      {/* 字段明细（可展开）*/}
      {result.field_verdicts.length > 0 && (
        <>
          <button
            className="btn btn--secondary btn--sm"
            onClick={() => setExpanded(x => !x)}
          >
            {expanded ? '收起字段明细' : `展开字段明细 (${result.field_verdicts.length})`}
          </button>

          {expanded && (
            <div style={{ marginTop: 12, maxHeight: 280, overflowY: 'auto' }}>
              <table className="data-table" style={{ fontSize: 11 }}>
                <thead>
                  <tr>
                    <th>字段标签</th>
                    <th>Standard Key</th>
                    <th>填写状态</th>
                    <th>验证结果</th>
                    <th>原因</th>
                  </tr>
                </thead>
                <tbody>
                  {result.field_verdicts.map((v: FieldVerdict) => (
                    <tr key={v.field_id}>
                      <td>{v.raw_label || '—'}</td>
                      <td style={{ fontFamily: 'var(--font-mono)', fontSize: 10 }}>{v.standard_key}</td>
                      <td><span className={`badge badge--${
                        v.fill_status === 'write' ? 'success' :
                        v.fill_status === 'manual' ? 'warning' : 'muted'
                      }`}>{v.fill_status}</span></td>
                      <td><VerdictBadge verdict={v.verify_status} /></td>
                      <td style={{ color: 'var(--dg)', fontSize: 10 }}>{v.verify_reason}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </>
      )}
    </div>
  );
}

// ── 主页面 ────────────────────────────────────────────────────

function FillFormContent() {
  const searchParams    = useSearchParams();
  const presetTemplate  = searchParams.get('template') || '';
  const presetCustomer  = searchParams.get('customer') || '';

  const [templates, setTemplates]               = useState<Template[]>([]);
  const [customers, setCustomers]               = useState<Customer[]>([]);
  const [loading, setLoading]                   = useState(true);
  const [selectedTemplate, setSelectedTemplate] = useState(presetTemplate);
  const [selectedCustomer, setSelectedCustomer] = useState(presetCustomer);
  const [filling, setFilling]                   = useState(false);
  const [result, setResult]                     = useState<FillFormResponse | null>(null);
  const [error, setError]                       = useState('');

  useEffect(() => {
    Promise.all([getTemplates(), getCustomers()])
      .then(([t, c]) => { setTemplates(t); setCustomers(c); })
      .catch(() => setError('无法连接后端服务，请确认 FastAPI 正在运行'))
      .finally(() => setLoading(false));
  }, []);

  const handleFill = async () => {
    if (!selectedTemplate || !selectedCustomer) return;
    setFilling(true);
    setResult(null);
    setError('');
    try {
      const res = await fillForm(Number(selectedTemplate), selectedCustomer);
      setResult(res);
    } catch (e: unknown) {
      const err = e as { response?: { data?: { detail?: string } } };
      setError(err?.response?.data?.detail || '填表失败，请检查模板字段是否已确认');
    } finally {
      setFilling(false);
    }
  };

  const selectedTemplateObj = templates.find(t => String(t.id) === selectedTemplate);
  const selectedCustomerObj = customers.find(c => c.customer_id === selectedCustomer);

  return (
    <>
      <div className="page-header">
        <h1 className="page-title">Fill Form</h1>
        <p className="page-subtitle">选择模板与客户，在原件 PDF 上精准叠字，验证并下载</p>
      </div>

      <div style={{ maxWidth: 680 }}>
        {/* 步骤指示器 */}
        <div className="steps mb-6">
          <div className={`step ${selectedTemplate ? 'done' : 'active'}`}>
            <div className="step-circle">{selectedTemplate ? '✓' : '1'}</div>
            <span className="step-label">Select Template</span>
          </div>
          <div className="step-line" />
          <div className={`step ${selectedCustomer ? 'done' : selectedTemplate ? 'active' : ''}`}>
            <div className="step-circle">{selectedCustomer ? '✓' : '2'}</div>
            <span className="step-label">Select Customer</span>
          </div>
          <div className="step-line" />
          <div className={`step ${result ? 'done' : selectedCustomer ? 'active' : ''}`}>
            <div className="step-circle">{result ? '✓' : '3'}</div>
            <span className="step-label">Verify &amp; Download</span>
          </div>
        </div>

        {/* 选模板 */}
        <div className="card mb-4">
          <div className="section-title mb-4">Step 1 — Select Template</div>
          {loading ? (
            <div className="flex items-center gap-2">
              <div className="loading-spinner" />
              <span className="caption">Loading...</span>
            </div>
          ) : (
            <>
              <div className="form-group">
                <label className="form-label">Form Template</label>
                <select
                  className="form-select"
                  value={selectedTemplate}
                  onChange={e => setSelectedTemplate(e.target.value)}
                >
                  <option value="">— Select a template —</option>
                  {templates.map(t => (
                    <option key={t.id} value={t.id}>
                      {t.name} {t.institution ? `(${t.institution})` : ''} — {t.page_count}p
                    </option>
                  ))}
                </select>
              </div>
              {selectedTemplateObj && (
                <div style={{ background: 'var(--vp)', borderRadius: 'var(--radius)', padding: '10px 12px' }}>
                  <div className="flex gap-4">
                    <div><span className="form-label">Institution</span><p>{selectedTemplateObj.institution || '—'}</p></div>
                    <div><span className="form-label">Pages</span><p>{selectedTemplateObj.page_count}</p></div>
                    <div><span className="form-label">Status</span>
                      <span className={`badge badge--${
                        selectedTemplateObj.status === 'active'     ? 'success' :
                        selectedTemplateObj.status === 'confirmed'  ? 'info'    : 'warning'
                      }`}>{selectedTemplateObj.status}</span>
                    </div>
                  </div>
                  {selectedTemplateObj.status === 'draft' && (
                    <p style={{ fontSize: 11, color: 'var(--warning)', marginTop: 8 }}>
                      ⚠ 此模板尚未确认字段映射，建议先完成确认再填表
                    </p>
                  )}
                  {selectedTemplateObj.original_pdf_path && (
                    <p style={{ fontSize: 10, color: 'var(--dg)', marginTop: 6 }}>
                      原件路径：data/forms/{selectedTemplateObj.id}/original.pdf ✓
                    </p>
                  )}
                </div>
              )}
            </>
          )}
        </div>

        {/* 选客户 */}
        <div className="card mb-4">
          <div className="section-title mb-4">Step 2 — Select Customer</div>
          {loading ? (
            <div className="flex items-center gap-2">
              <div className="loading-spinner" />
              <span className="caption">Loading...</span>
            </div>
          ) : (
            <>
              <div className="form-group">
                <label className="form-label">Customer</label>
                <select
                  className="form-select"
                  value={selectedCustomer}
                  onChange={e => setSelectedCustomer(e.target.value)}
                >
                  <option value="">— Select a customer —</option>
                  {customers.map(c => (
                    <option key={c.customer_id} value={c.customer_id}>
                      {c.full_name} · {c.ic_no}
                    </option>
                  ))}
                </select>
              </div>
              {selectedCustomerObj && (
                <div style={{ background: 'var(--vp)', borderRadius: 'var(--radius)', padding: '10px 12px' }}>
                  <div className="flex gap-4">
                    <div><span className="form-label">Name</span><p style={{ fontWeight: 600 }}>{selectedCustomerObj.full_name}</p></div>
                    <div><span className="form-label">IC No</span><p>{selectedCustomerObj.ic_no}</p></div>
                    <div><span className="form-label">Mobile</span><p>{selectedCustomerObj.mobile_no}</p></div>
                  </div>
                </div>
              )}
            </>
          )}
        </div>

        {/* 错误提示 */}
        {error && (
          <div className="mb-4" style={{
            background: 'rgba(217,79,79,0.08)', border: '1px solid var(--danger)',
            borderRadius: 'var(--radius)', padding: '10px 14px', fontSize: 12, color: 'var(--danger)',
          }}>
            {error}
          </div>
        )}

        {/* 执行按钮 */}
        {!result ? (
          <button
            className="btn btn--primary btn--lg w-full"
            onClick={handleFill}
            disabled={!selectedTemplate || !selectedCustomer || filling}
            style={{ justifyContent: 'center' }}
          >
            {filling ? (
              <><div className="loading-spinner" style={{ width: 16, height: 16, borderWidth: 2 }} /> Filling PDF on Original...</>
            ) : (
              <>
                <svg width={16} height={16} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth={2.5}>
                  <path d="M11 4H4a2 2 0 00-2 2v14a2 2 0 002 2h14a2 2 0 002-2v-7"/>
                  <path d="M18.5 2.5a2.121 2.121 0 013 3L12 15l-4 1 1-4 9.5-9.5z"/>
                </svg>
                Fill &amp; Generate PDF
              </>
            )}
          </button>
        ) : (
          /* 结果区域 */
          <div>
            {/* 基本统计 */}
            <div className="card mb-4" style={{ border: '1px solid var(--success)' }}>
              <div className="flex items-center gap-2 mb-4">
                <span style={{ fontSize: 20 }}>✅</span>
                <span className="section-title" style={{ color: 'var(--success)' }}>
                  PDF Generated — Job #{result.job_id}
                </span>
              </div>
              <div className="grid-3 mb-4">
                <div>
                  <span className="form-label">Filled Fields</span>
                  <p style={{ fontWeight: 700, color: 'var(--success)', fontSize: 22 }}>{result.filled_count}</p>
                </div>
                <div>
                  <span className="form-label">Skipped</span>
                  <p style={{ color: 'var(--dg)', fontSize: 22 }}>{result.skipped_count}</p>
                </div>
                <div>
                  <span className="form-label">Manual Required</span>
                  <p style={{ fontWeight: 700, color: result.manual_count > 0 ? 'var(--warning)' : 'var(--dg)', fontSize: 22 }}>
                    {result.manual_count}
                  </p>
                </div>
              </div>

              {/* Manual 字段列表 */}
              {result.manual_fields.length > 0 && (
                <div style={{
                  background: 'rgba(240,165,0,0.08)', border: '1px solid var(--warning)',
                  borderRadius: 'var(--radius)', padding: 12, marginBottom: 16,
                }}>
                  <p style={{ fontSize: 11, color: '#8A6000', fontWeight: 600, marginBottom: 6 }}>
                    ⚠ 以下字段需要人工补填（字符太长或无法适配格子）：
                  </p>
                  {result.manual_fields.map((f, i) => (
                    <span key={i} className="badge badge--warning" style={{ marginRight: 6, marginBottom: 4 }}>{f}</span>
                  ))}
                </div>
              )}

              {/* 下载按钮 */}
              <div className="flex gap-3">
                <a
                  href={`http://localhost:8000${result.download_url}`}
                  target="_blank"
                  rel="noreferrer"
                  className="btn btn--primary btn--lg"
                >
                  <svg width={16} height={16} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth={2}>
                    <path d="M21 15v4a2 2 0 01-2 2H5a2 2 0 01-2-2v-4"/>
                    <polyline points="7 10 12 15 17 10"/>
                    <line x1="12" y1="15" x2="12" y2="3"/>
                  </svg>
                  Download Filled PDF
                </a>
                <button className="btn btn--secondary btn--lg" onClick={() => setResult(null)}>
                  Fill Another
                </button>
              </div>
            </div>

            {/* 验证结果卡片 */}
            <VerificationCard result={result} />
          </div>
        )}
      </div>
    </>
  );
}

export default function FillPage() {
  return (
    <Suspense fallback={
      <div className="card text-center" style={{ padding: 48 }}>
        <div className="loading-spinner" style={{ margin: '0 auto' }} />
      </div>
    }>
      <FillFormContent />
    </Suspense>
  );
}
