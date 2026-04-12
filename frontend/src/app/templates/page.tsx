'use client';

import Link from 'next/link';
import { useEffect, useState } from 'react';
import { getTemplates, Template } from '@/lib/api';

export default function TemplatesPage() {
  const [templates, setTemplates] = useState<Template[]>([]);
  const [loading, setLoading] = useState(true);
  const [search, setSearch] = useState('');

  useEffect(() => {
    getTemplates()
      .then(setTemplates)
      .catch(() => {})
      .finally(() => setLoading(false));
  }, []);

  const filtered = templates.filter(t =>
    t.name.toLowerCase().includes(search.toLowerCase()) ||
    (t.institution || '').toLowerCase().includes(search.toLowerCase())
  );

  return (
    <>
      <div className="page-header">
        <div className="flex items-center justify-between">
          <div>
            <h1 className="page-title">Templates</h1>
            <p className="page-subtitle">所有已上传的表格模板</p>
          </div>
          <Link href="/upload" className="btn btn--primary">
            <svg width={14} height={14} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth={2.5}>
              <path d="M12 2v20M2 12h20"/>
            </svg>
            Upload New
          </Link>
        </div>
      </div>

      {/* 搜索框 */}
      <div className="mb-4" style={{ maxWidth: 320 }}>
        <input
          className="form-input"
          placeholder="Search by name or institution..."
          value={search}
          onChange={e => setSearch(e.target.value)}
        />
      </div>

      {loading ? (
        <div className="card text-center" style={{ padding: 48 }}>
          <div className="loading-spinner" style={{ margin: '0 auto 12px' }} />
          <p className="caption">Loading templates...</p>
        </div>
      ) : filtered.length === 0 ? (
        <div className="card">
          <div className="empty-state">
            <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth={1.5}>
              <path d="M14 2H6a2 2 0 00-2 2v16a2 2 0 002 2h12a2 2 0 002-2V8z"/>
              <polyline points="14 2 14 8 20 8"/>
            </svg>
            <p>{search ? 'No matching templates' : 'No templates yet — upload your first form'}</p>
            {!search && <Link href="/upload" className="btn btn--primary mt-3">Upload First Form</Link>}
          </div>
        </div>
      ) : (
        <div className="card" style={{ padding: 0, overflow: 'hidden' }}>
          <table className="data-table">
            <thead>
              <tr>
                <th>Template Name</th>
                <th>Institution</th>
                <th>Pages</th>
                <th>Status</th>
                <th>Created At</th>
                <th>Actions</th>
              </tr>
            </thead>
            <tbody>
              {filtered.map(t => (
                <tr key={t.id}>
                  <td>
                    <Link href={`/templates/${t.id}`} style={{ color: 'var(--vd)', fontWeight: 600, textDecoration: 'none' }}>
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
                  <td>
                    <div className="flex gap-2">
                      <Link href={`/templates/${t.id}`} className="btn btn--secondary btn--sm">
                        Edit Fields
                      </Link>
                      <Link href={`/fill?template=${t.id}`} className="btn btn--primary btn--sm">
                        Fill →
                      </Link>
                    </div>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </>
  );
}
