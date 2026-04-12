'use client';

import Link from 'next/link';
import { useEffect, useState } from 'react';
import { getTemplates, getCustomers, getJobs, Template, Customer, FillJob } from '@/lib/api';

// ── 工具：裁定颜色 ────────────────────────────────────────────
function verdictColor(v?: string) {
  if (v === 'pass')    return 'var(--success)';
  if (v === 'warning') return 'var(--warning)';
  if (v === 'fail')    return 'var(--danger)';
  return 'var(--dg)';
}

function VerdictBadge({ verdict }: { verdict?: string }) {
  if (!verdict || verdict === 'pending') return <span className="badge badge--muted">—</span>;
  const map: Record<string, string> = {
    pass:    'badge--success',
    warning: 'badge--warning',
    fail:    'badge--danger',
  };
  return <span className={`badge ${map[verdict] ?? 'badge--muted'}`}>{verdict.toUpperCase()}</span>;
}

export default function DashboardPage() {
  const [templates, setTemplates] = useState<Template[]>([]);
  const [customers, setCustomers] = useState<Customer[]>([]);
  const [jobs,      setJobs     ] = useState<FillJob[]>([]);
  const [loading,   setLoading  ] = useState(true);

  useEffect(() => {
    Promise.all([getTemplates(), getCustomers(), getJobs(10)])
      .then(([t, c, j]) => { setTemplates(t); setCustomers(c); setJobs(j); })
      .catch(() => {})
      .finally(() => setLoading(false));
  }, []);

  const confirmed  = templates.filter(t => t.status === 'confirmed' || t.status === 'active').length;
  const failedJobs = jobs.filter(j => j.final_verdict === 'fail' || j.status === 'failed').length;

  return (
    <>
      <div className="page-header">
        <h1 className="page-title">Dashboard</h1>
        <p className="page-subtitle">Smart Form Filler 系统概览 — 原件叠字，严格保留原件内容</p>
      </div>

      {/* KPI 卡片 */}
      <div className="grid-4 mb-6">
        <div className="kpi-card">
          <div className="kpi-card__label">Total Templates</div>
          <div className="kpi-card__value">{loading ? '—' : templates.length}</div>
          <div className="kpi-card__sub">已上传模板</div>
        </div>
        <div className="kpi-card">
          <div className="kpi-card__label">Confirmed</div>
          <div className="kpi-card__value">{loading ? '—' : confirmed}</div>
          <div className="kpi-card__sub">已确认模板</div>
        </div>
        <div className="kpi-card">
          <div className="kpi-card__label">Customers</div>
          <div className="kpi-card__value">{loading ? '—' : customers.length}</div>
          <div className="kpi-card__sub">客户主资料</div>
        </div>
        <div className="kpi-card">
          <div className="kpi-card__label">Total Jobs</div>
          <div className="kpi-card__value">{loading ? '—' : jobs.length}</div>
          <div className="kpi-card__sub">最近填表任务</div>
        </div>
      </div>

      {/* 异常摘要（若有）*/}
      {!loading && failedJobs > 0 && (
        <div style={{
          background: 'rgba(217,79,79,0.06)', border: '1px solid var(--danger)',
          borderRadius: 'var(--radius)', padding: '10px 16px', marginBottom: 20,
          display: 'flex', gap: 24, alignItems: 'center',
        }}>
          <span style={{ fontSize: 16 }}>⚠</span>
          {failedJobs > 0 && (
            <span style={{ fontSize: 12, color: 'var(--danger)', fontWeight: 600 }}>
              {failedJobs} 个任务验证失败
            </span>
          )}
          <Link href="/fill" className="btn btn--secondary btn--sm" style={{ marginLeft: 'auto' }}>
            查看填表页
          </Link>
        </div>
      )}

      {/* 快速操作 */}
      <div className="grid-3 mb-6">
        <Link href="/upload" style={{ textDecoration: 'none' }}>
          <div className="card card--hoverable" style={{ borderColor: 'var(--vm)' }}>
            <div style={{ color: 'var(--vm)', marginBottom: 10 }}>
              <svg width={28} height={28} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth={2}>
                <path d="M21 15v4a2 2 0 01-2 2H5a2 2 0 01-2-2v-4"/>
                <polyline points="17 8 12 3 7 8"/>
                <line x1="12" y1="3" x2="12" y2="15"/>
              </svg>
            </div>
            <div className="section-title mb-2">Upload New Form</div>
            <p className="caption">上传原件 PDF，系统自动分析字段位置，保存为可复用模板</p>
          </div>
        </Link>

        <Link href="/fill" style={{ textDecoration: 'none' }}>
          <div className="card card--hoverable">
            <div style={{ color: 'var(--vd)', marginBottom: 10 }}>
              <svg width={28} height={28} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth={2}>
                <path d="M11 4H4a2 2 0 00-2 2v14a2 2 0 002 2h14a2 2 0 002-2v-7"/>
                <path d="M18.5 2.5a2.121 2.121 0 013 3L12 15l-4 1 1-4 9.5-9.5z"/>
              </svg>
            </div>
            <div className="section-title mb-2">Fill Form</div>
            <p className="caption">选择模板与客户，在原件上叠字，验证并下载成品 PDF</p>
          </div>
        </Link>

        <Link href="/templates" style={{ textDecoration: 'none' }}>
          <div className="card card--hoverable">
            <div style={{ color: 'var(--dg)', marginBottom: 10 }}>
              <svg width={28} height={28} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth={2}>
                <path d="M14 2H6a2 2 0 00-2 2v16a2 2 0 002 2h12a2 2 0 002-2V8z"/>
                <polyline points="14 2 14 8 20 8"/>
              </svg>
            </div>
            <div className="section-title mb-2">Manage Templates</div>
            <p className="caption">查看、编辑和确认已上传的表格模板及字段映射</p>
          </div>
        </Link>
      </div>

      {/* 最近填表任务 */}
      {jobs.length > 0 && (
        <div className="card mb-6">
          <div className="flex items-center justify-between mb-4">
            <span className="section-title">Recent Fill Jobs</span>
            <Link href="/fill" className="btn btn--secondary btn--sm">Fill New</Link>
          </div>
          <table className="data-table">
            <thead>
              <tr>
                <th>Job #</th>
                <th>Template</th>
                <th>Customer</th>
                <th>Pass / Total</th>
                <th>Fail</th>
                <th>Verdict</th>
                <th>Status</th>
                <th>Time</th>
              </tr>
            </thead>
            <tbody>
              {jobs.map(j => (
                <tr key={j.id}>
                  <td style={{ fontFamily: 'var(--font-mono)', fontSize: 11, color: 'var(--dg)' }}>#{j.id}</td>
                  <td style={{ fontWeight: 600, maxWidth: 160, overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>
                    {j.template_name || `Template #${j.template_id}`}
                  </td>
                  <td>
                    <span style={{ fontWeight: 600 }}>{j.customer_name || j.customer_ref}</span>
                    <span className="text-muted" style={{ fontSize: 10, marginLeft: 4 }}>{j.customer_ref}</span>
                  </td>
                  <td>
                    <span style={{ color: 'var(--success)', fontWeight: 600 }}>{j.total_pass}</span>
                    <span className="text-muted"> / {j.total_fields}</span>
                  </td>
                  <td>
                    {(j.total_fail ?? 0) > 0
                      ? <span style={{ color: 'var(--danger)', fontWeight: 600 }}>{j.total_fail}</span>
                      : <span className="text-muted">0</span>}
                  </td>
                  <td><VerdictBadge verdict={j.final_verdict ?? ''} /></td>
                  <td>
                    <span className={`badge badge--${j.status === 'done' ? 'success' : j.status === 'failed' ? 'danger' : 'muted'}`}>
                      {j.status}
                    </span>
                  </td>
                  <td className="text-muted" style={{ fontSize: 10 }}>{j.created_at?.slice(0, 16)}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}

      {/* 最近模板 */}
      {templates.length > 0 && (
        <div className="card">
          <div className="flex items-center justify-between mb-4">
            <span className="section-title">Recent Templates</span>
            <Link href="/templates" className="btn btn--secondary btn--sm">View All</Link>
          </div>
          <table className="data-table">
            <thead>
              <tr>
                <th>Template Name</th>
                <th>Institution</th>
                <th>Pages</th>
                <th>Status</th>
                <th>Created</th>
              </tr>
            </thead>
            <tbody>
              {templates.slice(0, 5).map(t => (
                <tr key={t.id}>
                  <td>
                    <Link href={`/templates/${t.id}`} style={{ color: 'var(--vd)', fontWeight: 600 }}>
                      {t.name}
                    </Link>
                  </td>
                  <td className="text-muted">{t.institution || '—'}</td>
                  <td>{t.page_count}</td>
                  <td>
                    <span className={`badge badge--${
                      t.status === 'active'    ? 'success' :
                      t.status === 'confirmed' ? 'info'    : 'muted'
                    }`}>{t.status}</span>
                  </td>
                  <td className="text-muted">{t.created_at?.slice(0, 10)}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}

      {templates.length === 0 && !loading && (
        <div className="card">
          <div className="empty-state">
            <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth={1.5}>
              <path d="M14 2H6a2 2 0 00-2 2v16a2 2 0 002 2h12a2 2 0 002-2V8z"/>
              <polyline points="14 2 14 8 20 8"/>
            </svg>
            <p>还没有任何模板，先上传一张表格开始吧</p>
            <Link href="/upload" className="btn btn--primary mt-3">Upload First Form</Link>
          </div>
        </div>
      )}
    </>
  );
}
