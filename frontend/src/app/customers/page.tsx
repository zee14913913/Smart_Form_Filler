'use client';

import { useEffect, useState } from 'react';
import { useRouter } from 'next/navigation';
import { getCustomers, Customer } from '@/lib/api';

export default function CustomersPage() {
  const router = useRouter();
  const [customers, setCustomers] = useState<Customer[]>([]);
  const [loading, setLoading] = useState(true);
  const [search, setSearch] = useState('');

  useEffect(() => {
    getCustomers()
      .then(setCustomers)
      .catch(() => {})
      .finally(() => setLoading(false));
  }, []);

  const filtered = customers.filter(c =>
    c.full_name?.toLowerCase().includes(search.toLowerCase()) ||
    c.ic_no?.includes(search) ||
    c.mobile_no?.includes(search) ||
    c.customer_id?.toLowerCase().includes(search.toLowerCase())
  );

  return (
    <>
      <div className="page-header">
        <div className="flex items-center justify-between">
          <div>
            <h1 className="page-title">Customers</h1>
            <p className="page-subtitle">来自 customer_master.xlsx 的客户主资料</p>
          </div>
          <div className="badge badge--info" style={{ fontSize: 12, padding: '6px 12px' }}>
            {customers.length} Records
          </div>
        </div>
      </div>

      <div className="mb-4" style={{ maxWidth: 360 }}>
        <input
          className="form-input"
          placeholder="Search name, IC No, phone..."
          value={search}
          onChange={e => setSearch(e.target.value)}
        />
      </div>

      {loading ? (
        <div className="card text-center" style={{ padding: 48 }}>
          <div className="loading-spinner" style={{ margin: '0 auto 12px' }} />
          <p className="caption">Loading from Excel...</p>
        </div>
      ) : filtered.length === 0 ? (
        <div className="card">
          <div className="empty-state">
            <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth={1.5}>
              <path d="M17 21v-2a4 4 0 00-4-4H5a4 4 0 00-4 4v2"/>
              <circle cx="9" cy="7" r="4"/>
            </svg>
            <p>{search ? 'No matching customers' : 'No customer records found. Check customer_master.xlsx'}</p>
          </div>
        </div>
      ) : (
        <div className="card" style={{ padding: 0, overflow: 'hidden' }}>
          <table className="data-table">
            <thead>
              <tr>
                <th>Customer ID</th>
                <th>Full Name</th>
                <th>IC No</th>
                <th>Mobile</th>
                <th>Actions</th>
              </tr>
            </thead>
            <tbody>
              {filtered.map(c => (
                <tr key={c.customer_id}>
                  <td>
                    <span style={{ fontFamily: 'var(--font-mono)', fontSize: 11, color: 'var(--vm)' }}>
                      {c.customer_id}
                    </span>
                  </td>
                  <td style={{ fontWeight: 600 }}>{c.full_name}</td>
                  <td className="text-muted">{c.ic_no}</td>
                  <td className="text-muted">{c.mobile_no}</td>
                  <td>
                    <button
                      className="btn btn--primary btn--sm"
                      onClick={() => router.push(`/fill?customer=${c.customer_id}`)}
                    >
                      Fill Form →
                    </button>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}

      <div className="mt-4">
        <p className="caption">
          客户资料来自 <code style={{ fontSize: 10, background: 'var(--vp)', padding: '2px 5px', borderRadius: 4 }}>
            customer_master.xlsx
          </code>，请直接编辑 Excel 文件以添加/修改客户信息。
        </p>
      </div>
    </>
  );
}
