'use client';

import Link from 'next/link';
import { useEffect, useState } from 'react';
import { getTemplates, getCustomers, Template, Customer } from '@/lib/api';

export default function DashboardPage() {
  const [templates, setTemplates] = useState<Template[]>([]);
  const [customers, setCustomers] = useState<Customer[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    Promise.all([getTemplates(), getCustomers()])
      .then(([t, c]) => { setTemplates(t); setCustomers(c); })
      .catch(() => {})
      .finally(() => setLoading(false));
  }, []);

  const confirmed = templates.filter(t => t.status === 'confirmed' || t.status === 'active').length;

  return (
    <>
      <div className="page-header">
        <h1 className="page-title">Dashboard</h1>
        <p className="page-subtitle">智能表格自动填写系统概览</p>
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
          <div className="kpi-card__label">Status</div>
          <div className="kpi-card__value" style={{ fontSize: 18, color: 'var(--success)' }}>Online</div>
          <div className="kpi-card__sub">系统运行中</div>
        </div>
      </div>

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
            <p className="caption">上传 PDF 或图片表格，系统自动分析填写字段位置</p>
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
            <p className="caption">选择模板与客户，一键执行精准回填并下载填好的 PDF</p>
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
            <p className="caption">查看、编辑和确认所有已上传的表格模板与字段映射</p>
          </div>
        </Link>
      </div>

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
                      t.status === 'active' ? 'success'
                      : t.status === 'confirmed' ? 'info'
                      : 'muted'
                    }`}>
                      {t.status}
                    </span>
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
