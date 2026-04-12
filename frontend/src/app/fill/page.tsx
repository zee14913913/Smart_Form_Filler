'use client';

import { useEffect, useState, Suspense } from 'react';
import { useSearchParams } from 'next/navigation';
import {
  getTemplates, getCustomers, fillForm,
  Template, Customer, FillFormResponse, FieldVerdict,
} from '@/lib/api';

// ── 验证状态标签（PRD v3：严格两值）──────────────────────────

function VerdictBadge({ verdict }: { verdict: string }) {
  const map: Record<string, { cls: string; label: string }> = {
    pass: { cls: 'badge--success', label: '✓ PASS' },
    fail: { cls: 'badge--danger',  label: '✕ FAIL' },
  };
  const { cls, label } = map[verdict] ?? { cls: 'badge--muted', label: verdict };
  return <span className={`badge ${cls}`}>{label}</span>;
}

// ── 不可交付警告横幅 ──────────────────────────────────────────

function FailBanner({ failCount, failFields }: { failCount: number; failFields: string[] }) {
  return (
    <div style={{
      background: 'rgba(217,79,79,0.12)',
      border: '2px solid var(--danger)',
      borderRadius: 'var(--radius)',
      padding: '14px 16px',
      marginBottom: 16,
    }}>
      <div style={{ fontSize: 16, fontWeight: 700, color: 'var(--danger)', marginBottom: 6 }}>
        ✕ 不可交付 — 本次填表结果不合格
      </div>
      <p style={{ fontSize: 12, color: 'var(--danger)', marginBottom: failFields.length > 0 ? 8 : 0 }}>
        共 {failCount} 个字段验证失败。请检查字段映射、字符长度或格子坐标，修正后重新填表。
      </p>
      {failFields.length > 0 && (
        <div>
          <p style={{ fontSize: 11, color: '#8B0000', fontWeight: 600, marginBottom: 4 }}>
            失败字段：
          </p>
          <div style={{ display: 'flex', flexWrap: 'wrap', gap: 4 }}>
            {failFields.map((f, i) => (
              <span key={i} className="badge badge--danger" style={{ fontSize: 10 }}>{f}</span>
            ))}
          </div>
        </div>
      )}
    </div>
  );
}

// ── 验证摘要卡片（PRD v3）────────────────────────────────────

function VerificationCard({ result }: { result: FillFormResponse }) {
  const v = result.verification;
  const [expanded, setExpanded] = useState(false);

  const isFail = v.final_verdict === 'fail';
  const verdictColor = isFail ? 'var(--danger)' : 'var(--success)';

  return (
    <div style={{
      border: `2px solid ${verdictColor}`,
      borderRadius: 'var(--radius)',
      padding: 16,
      marginBottom: 16,
      background: isFail ? 'rgba(217,79,79,0.04)' : '#FAFAF9',
    }}>
      {/* 标题行 */}
      <div className="flex items-center justify-between mb-3">
        <span className="section-title" style={{ color: verdictColor }}>
          验证结果 — {v.final_verdict.toUpperCase()}
        </span>
        <VerdictBadge verdict={v.final_verdict} />
      </div>

      {/* 统计格（PRD v3：只有 pass / fail 计数）*/}
      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(3, 1fr)', gap: 8, marginBottom: 12 }}>
        {[
          { label: '总字段',   val: v.total_fields, color: 'var(--ink)' },
          { label: 'Pass',    val: v.total_pass,   color: 'var(--success)' },
          { label: 'Fail',    val: v.total_fail,   color: 'var(--danger)' },
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
          {v.image_diff_verdict === 'fail' && (
            <span style={{ marginLeft: 8, color: 'var(--danger)', fontWeight: 600 }}>
              非填写区域与原件存在差异 — 原件可能被篡改
            </span>
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
            <div style={{ marginTop: 12, maxHeight: 300, overflowY: 'auto' }}>
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
                    <tr key={v.field_id} style={{
                      background: v.verify_status === 'fail'
                        ? 'rgba(217,79,79,0.06)' : undefined,
                    }}>
                      <td>{v.raw_label || '—'}</td>
                      <td style={{ fontFamily: 'var(--font-mono)', fontSize: 10 }}>{v.standard_key}</td>
                      <td>
                        <span className={`badge badge--${v.fill_status === 'write' ? 'success' : 'danger'}`}>
                          {v.fill_status}
                        </span>
                      </td>
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
      .then(([t, c]) => { setTemplates(t); setCustomers(c.data?.items ?? []); })
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

  const isFinalFail = result?.verification.final_verdict === 'fail';

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
          <div className={`step ${result ? (isFinalFail ? 'fail' : 'done') : selectedCustomer ? 'active' : ''}`}>
            <div className="step-circle">{result ? (isFinalFail ? '✕' : '✓') : '3'}</div>
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
            {/* ── 不可交付警告（fail 时置顶显示）── */}
            {isFinalFail && (
              <FailBanner
                failCount={result.verification.total_fail}
                failFields={result.fail_fields}
              />
            )}

            {/* 基本统计 */}
            <div className="card mb-4" style={{
              border: `1px solid ${isFinalFail ? 'var(--danger)' : 'var(--success)'}`,
            }}>
              <div className="flex items-center gap-2 mb-4">
                <span style={{ fontSize: 20 }}>{isFinalFail ? '❌' : '✅'}</span>
                <span className="section-title" style={{ color: isFinalFail ? 'var(--danger)' : 'var(--success)' }}>
                  PDF Generated — Job #{result.job_id}
                  {isFinalFail && ' — 不可交付'}
                </span>
              </div>
              <div className="grid-3 mb-4">
                <div>
                  <span className="form-label">Written Fields</span>
                  <p style={{ fontWeight: 700, color: 'var(--success)', fontSize: 22 }}>{result.write_count}</p>
                </div>
                <div>
                  <span className="form-label">Failed Fields</span>
                  <p style={{ fontWeight: 700, color: result.fail_count > 0 ? 'var(--danger)' : 'var(--dg)', fontSize: 22 }}>
                    {result.fail_count}
                  </p>
                </div>
                <div>
                  <span className="form-label">Final Verdict</span>
                  <p style={{
                    fontWeight: 700, fontSize: 18,
                    color: isFinalFail ? 'var(--danger)' : 'var(--success)',
                  }}>
                    {result.verification.final_verdict.toUpperCase()}
                  </p>
                </div>
              </div>

              {/* 下载按钮 — 仅在 pass 时显示；fail 时禁用并说明 */}
              <div className="flex gap-3">
                {!isFinalFail ? (
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
                ) : (
                  <div style={{
                    flex: 1, padding: '10px 14px',
                    background: 'rgba(217,79,79,0.08)',
                    border: '1px solid var(--danger)',
                    borderRadius: 'var(--radius)',
                    fontSize: 12, color: 'var(--danger)', fontWeight: 600,
                  }}>
                    ✕ 验证失败 — 此 PDF 不可交付，请修正字段后重新填表
                  </div>
                )}
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
