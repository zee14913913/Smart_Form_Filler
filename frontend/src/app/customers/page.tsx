'use client';

import { useCallback, useEffect, useMemo, useRef, useState } from 'react';
import { useRouter } from 'next/navigation';
import { AgGridReact } from 'ag-grid-react';
import type { ColDef, GridApi, GridReadyEvent, CellValueChangedEvent, RowSelectedEvent } from 'ag-grid-community';
import {
  Customer,
  getCustomers,
  bulkCustomers,
  importCustomersXlsx,
  getCustomerExportUrl,
} from '@/lib/api';

// ── AG Grid CSS (Community) ──────────────────────────────────
import 'ag-grid-community/styles/ag-grid.css';
import 'ag-grid-community/styles/ag-theme-alpine.css';
// Morandi Violet 主题覆盖（独立 CSS 文件，避免 hydration mismatch）
import '@/styles/customers-grid.css';

// ── Toast 辅助 ───────────────────────────────────────────────

type ToastType = 'success' | 'error' | 'info';

interface Toast {
  id: number;
  type: ToastType;
  message: string;
}

let _toastId = 0;

function useToast() {
  const [toasts, setToasts] = useState<Toast[]>([]);

  const show = useCallback((message: string, type: ToastType = 'info') => {
    const id = ++_toastId;
    setToasts(prev => [...prev, { id, type, message }]);
    setTimeout(() => setToasts(prev => prev.filter(t => t.id !== id)), 4000);
  }, []);

  return { toasts, show };
}

// ── 行扩展类型（带脏标记）────────────────────────────────────

interface CustomerRow extends Customer {
  _isNew?: boolean;     // 前端新增行（尚未保存）
  _isDirty?: boolean;   // 已修改但未保存
  _isDeleted?: boolean; // 标记删除
}

// ── 确认对话框 ───────────────────────────────────────────────

function ConfirmDialog({
  message,
  onConfirm,
  onCancel,
}: {
  message: string;
  onConfirm: () => void;
  onCancel: () => void;
}) {
  return (
    <div
      style={{
        position: 'fixed', inset: 0, background: 'rgba(30,26,46,0.55)',
        display: 'flex', alignItems: 'center', justifyContent: 'center',
        zIndex: 9999, backdropFilter: 'blur(2px)',
      }}
    >
      <div
        className="card"
        style={{ minWidth: 340, maxWidth: 440, padding: '28px 28px 24px' }}
      >
        <p style={{ fontSize: 13, fontWeight: 600, color: 'var(--ink)', marginBottom: 20 }}>
          {message}
        </p>
        <div className="flex justify-end gap-2">
          <button className="btn btn--secondary btn--sm" onClick={onCancel}>
            取消
          </button>
          <button className="btn btn--danger btn--sm" onClick={onConfirm}>
            确认删除
          </button>
        </div>
      </div>
    </div>
  );
}

// ── 新增客户表单 ──────────────────────────────────────────────

const EMPTY_NEW: Partial<CustomerRow> = {
  customer_id: '', full_name: '', ic_no: '', mobile_no: '',
  email: '', date_of_birth: '', nationality: '', gender: '',
  marital_status: '', race: '', religion: '', home_tel: '',
  address_line1: '', address_line2: '', address_line3: '',
  postcode: '', city: '', state: '', country: 'Malaysia',
  employer_name: '', monthly_income: '', occupation: '',
};

function AddCustomerModal({
  onAdd,
  onClose,
}: {
  onAdd: (data: Partial<CustomerRow>) => void;
  onClose: () => void;
}) {
  const [form, setForm] = useState<Partial<CustomerRow>>(EMPTY_NEW);
  const set = (k: keyof CustomerRow, v: string) =>
    setForm(prev => ({ ...prev, [k]: v }));

  const handleSubmit = () => {
    if (!form.customer_id?.trim() || !form.full_name?.trim()) {
      alert('Customer ID 和 Full Name 为必填项');
      return;
    }
    onAdd({ ...form, _isNew: true });
    onClose();
  };

  const Field = ({
    label, field, required,
  }: {
    label: string; field: keyof CustomerRow; required?: boolean;
  }) => (
    <div className="form-group" style={{ marginBottom: 10 }}>
      <label className="form-label">
        {label}{required && <span style={{ color: 'var(--danger)' }}> *</span>}
      </label>
      <input
        className="form-input"
        value={(form[field] as string) || ''}
        onChange={e => set(field, e.target.value)}
      />
    </div>
  );

  return (
    <div
      style={{
        position: 'fixed', inset: 0, background: 'rgba(30,26,46,0.55)',
        display: 'flex', alignItems: 'center', justifyContent: 'center',
        zIndex: 9999, backdropFilter: 'blur(2px)', overflowY: 'auto',
      }}
    >
      <div
        className="card"
        style={{ width: 560, maxHeight: '90vh', overflowY: 'auto', padding: '28px 28px 24px' }}
      >
        <div className="flex items-center justify-between" style={{ marginBottom: 20 }}>
          <h2 style={{ fontSize: 15, fontWeight: 700, color: 'var(--vd)' }}>新增客户</h2>
          <button
            className="btn btn--secondary btn--sm"
            onClick={onClose}
            style={{ padding: '4px 10px' }}
          >
            ✕
          </button>
        </div>

        <div className="grid-2">
          <Field label="Customer ID" field="customer_id" required />
          <Field label="Full Name" field="full_name" required />
          <Field label="IC No" field="ic_no" />
          <Field label="Mobile No" field="mobile_no" />
          <Field label="Date of Birth" field="date_of_birth" />
          <Field label="Email" field="email" />
          <Field label="Nationality" field="nationality" />
          <Field label="Gender" field="gender" />
          <Field label="Marital Status" field="marital_status" />
          <Field label="Race" field="race" />
          <Field label="Occupation" field="occupation" />
          <Field label="Monthly Income" field="monthly_income" />
          <Field label="Employer Name" field="employer_name" />
          <Field label="State" field="state" />
          <Field label="City" field="city" />
          <Field label="Country" field="country" />
        </div>
        <Field label="Address Line 1" field="address_line1" />
        <Field label="Address Line 2" field="address_line2" />

        <div className="flex justify-end gap-2" style={{ marginTop: 16 }}>
          <button className="btn btn--secondary btn--sm" onClick={onClose}>
            取消
          </button>
          <button className="btn btn--primary btn--sm" onClick={handleSubmit}>
            确认新增
          </button>
        </div>
      </div>
    </div>
  );
}

// ── 主页面 ────────────────────────────────────────────────────

export default function CustomersPage() {
  const router = useRouter();
  const gridRef = useRef<AgGridReact<CustomerRow>>(null);
  const gridApiRef = useRef<GridApi<CustomerRow> | null>(null);
  const fileInputRef = useRef<HTMLInputElement>(null);

  const [rowData, setRowData] = useState<CustomerRow[]>([]);
  const [total, setTotal] = useState(0);
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [search, setSearch] = useState('');
  const [searchDebounced, setSearchDebounced] = useState('');
  const [pendingDeletes, setPendingDeletes] = useState<Set<number>>(new Set());
  const [dirtyIds, setDirtyIds] = useState<Set<number | string>>(new Set());
  const [newRows, setNewRows] = useState<CustomerRow[]>([]);
  const [showAddModal, setShowAddModal] = useState(false);
  const [confirmDelete, setConfirmDelete] = useState<null | (() => void)>(null);
  const [selectedCount, setSelectedCount] = useState(0);
  const { toasts, show: showToast } = useToast();

  // 搜索防抖
  useEffect(() => {
    const t = setTimeout(() => setSearchDebounced(search), 350);
    return () => clearTimeout(t);
  }, [search]);

  // 加载数据
  const loadData = useCallback(async (q?: string) => {
    setLoading(true);
    try {
      const res = await getCustomers(1, 500, q || undefined);
      const items = res.data?.items ?? [];
      setTotal(res.data?.total ?? items.length);
      setRowData(items as CustomerRow[]);
      setPendingDeletes(new Set());
      setDirtyIds(new Set());
      setNewRows([]);
    } catch {
      showToast('加载客户列表失败，请检查后端连接', 'error');
    } finally {
      setLoading(false);
    }
  }, [showToast]);

  useEffect(() => { loadData(searchDebounced || undefined); }, [searchDebounced, loadData]);

  // Grid 就绪
  const onGridReady = useCallback((e: GridReadyEvent<CustomerRow>) => {
    gridApiRef.current = e.api;
  }, []);

  // 单元格编辑完成 → 标记脏
  const onCellValueChanged = useCallback((e: CellValueChangedEvent<CustomerRow>) => {
    const row = e.data;
    if (!row) return;
    if (row._isNew) {
      // 新行直接在 newRows 中更新
      setNewRows(prev => prev.map(r => r === row ? { ...row } : r));
    } else {
      setDirtyIds(prev => {
        const next = new Set(prev);
        next.add(row.id);
        return next;
      });
    }
  }, []);

  // 选中行变化
  const onSelectionChanged = useCallback(() => {
    const sel = gridApiRef.current?.getSelectedRows() ?? [];
    setSelectedCount(sel.filter(r => !r._isNew).length);
  }, []);

  // 新增一行
  const handleAddRow = useCallback((data: Partial<CustomerRow>) => {
    const newRow: CustomerRow = {
      id: -(Date.now()),   // 临时负数 id
      customer_id: data.customer_id ?? '',
      full_name: data.full_name ?? '',
      ic_no: data.ic_no ?? '',
      ...data,
      _isNew: true,
    } as CustomerRow;
    setNewRows(prev => [...prev, newRow]);
    setRowData(prev => [newRow, ...prev]);
    showToast('新增行已添加，点击"保存所有改动"提交', 'info');
  }, [showToast]);

  // 删除选中行
  const handleDeleteSelected = useCallback(() => {
    const sel = gridApiRef.current?.getSelectedRows() ?? [];
    const existing = sel.filter(r => !r._isNew);
    const newer = sel.filter(r => r._isNew);

    if (newer.length > 0) {
      // 直接从前端移除未保存的新行
      const newIds = new Set(newer.map(r => r.id));
      setRowData(prev => prev.filter(r => !newIds.has(r.id)));
      setNewRows(prev => prev.filter(r => !newIds.has(r.id)));
    }

    if (existing.length === 0) return;

    setConfirmDelete(() => () => {
      const ids = new Set(existing.map(r => r.id));
      setPendingDeletes(prev => {
        const next = new Set(prev);
        ids.forEach(id => next.add(id));
        return next;
      });
      // 标记视觉删除（行变红）
      setRowData(prev => prev.map(r =>
        ids.has(r.id) ? { ...r, _isDeleted: true } : r
      ));
      gridApiRef.current?.deselectAll();
      setSelectedCount(0);
      setConfirmDelete(null);
      showToast(`${existing.length} 条记录已标记删除，点击"保存所有改动"提交`, 'info');
    });
  }, [showToast]);

  // 保存所有改动
  const handleSaveAll = useCallback(async () => {
    const allRows = rowData;
    const createList = allRows
      .filter(r => r._isNew && !r._isDeleted)
      .map(({ _isNew: _, _isDirty: __, _isDeleted: ___, id: ____, ...rest }) => rest);

    const updateList = allRows
      .filter(r => !r._isNew && !r._isDeleted && dirtyIds.has(r.id))
      .map(({ _isNew: _, _isDirty: __, _isDeleted: ___, ...rest }) => rest);

    const deleteIds = Array.from(pendingDeletes);

    if (!createList.length && !updateList.length && !deleteIds.length) {
      showToast('没有待提交的改动', 'info');
      return;
    }

    setSaving(true);
    try {
      const result = await bulkCustomers({
        create: createList,
        update: updateList,
        delete: deleteIds,
      });
      const errCount = result.errors?.length ?? 0;
      if (errCount > 0) {
        showToast(
          `保存完成（新建 ${result.created} / 更新 ${result.updated} / 删除 ${result.deleted}），${errCount} 条出错`,
          'error',
        );
      } else {
        showToast(
          `保存成功：新建 ${result.created}，更新 ${result.updated}，删除 ${result.deleted}`,
          'success',
        );
      }
      // 刷新数据
      await loadData(searchDebounced || undefined);
    } catch (e: unknown) {
      const msg = e instanceof Error ? e.message : '未知错误';
      showToast(`保存失败：${msg}`, 'error');
    } finally {
      setSaving(false);
    }
  }, [rowData, dirtyIds, pendingDeletes, loadData, searchDebounced, showToast]);

  // 导入 Excel
  const handleImportClick = () => fileInputRef.current?.click();

  const handleFileChange = useCallback(async (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (!file) return;
    e.target.value = '';

    setSaving(true);
    try {
      const result = await importCustomersXlsx(file);
      const errCount = result.errors?.length ?? 0;
      if (errCount > 0) {
        showToast(
          `导入完成（${result.imported} 条成功，${result.skipped} 条跳过，${errCount} 条出错）`,
          'error',
        );
      } else {
        showToast(
          `导入成功：${result.imported} 条记录，${result.skipped} 条跳过`,
          'success',
        );
      }
      await loadData(searchDebounced || undefined);
    } catch (e: unknown) {
      const msg = e instanceof Error ? e.message : '未知错误';
      showToast(`导入失败：${msg}`, 'error');
    } finally {
      setSaving(false);
    }
  }, [loadData, searchDebounced, showToast]);

  // 导出 Excel
  const handleExport = useCallback(() => {
    const url = getCustomerExportUrl();
    const a = document.createElement('a');
    a.href = url;
    a.download = 'customer_export.xlsx';
    a.click();
  }, []);

  // ── AG Grid 列定义 ────────────────────────────────────────

  const columnDefs = useMemo<ColDef<CustomerRow>[]>(() => [
    {
      checkboxSelection: true,
      headerCheckboxSelection: true,
      width: 44,
      minWidth: 44,
      maxWidth: 44,
      sortable: false,
      filter: false,
      editable: false,
      pinned: 'left',
      cellStyle: { padding: '0 6px' },
    },
    {
      field: 'customer_id',
      headerName: 'Customer ID',
      width: 110,
      pinned: 'left',
      editable: true,
      cellStyle: (p) => ({
        fontFamily: 'var(--font-mono)',
        fontSize: 11,
        color: p.data?._isDeleted ? '#D94F4F' : 'var(--vm)',
        background: p.data?._isNew ? 'rgba(76,175,130,0.06)' : p.data?._isDeleted ? 'rgba(217,79,79,0.06)' : '',
      }),
    },
    {
      field: 'full_name',
      headerName: 'Full Name',
      width: 180,
      editable: true,
      cellStyle: (p) => ({
        fontWeight: 600,
        background: p.data?._isNew ? 'rgba(76,175,130,0.06)' : p.data?._isDeleted ? 'rgba(217,79,79,0.06)' : '',
      }),
    },
    { field: 'ic_no',        headerName: 'IC No',        width: 145, editable: true },
    { field: 'mobile_no',    headerName: 'Mobile',       width: 120, editable: true },
    { field: 'email',        headerName: 'Email',        width: 180, editable: true },
    { field: 'date_of_birth', headerName: 'Date of Birth', width: 110, editable: true },
    { field: 'nationality',  headerName: 'Nationality',  width: 100, editable: true },
    { field: 'gender',       headerName: 'Gender',       width: 80,  editable: true },
    { field: 'marital_status', headerName: 'Marital',    width: 90,  editable: true },
    { field: 'occupation',   headerName: 'Occupation',   width: 130, editable: true },
    { field: 'employer_name', headerName: 'Employer',    width: 160, editable: true },
    { field: 'monthly_income', headerName: 'Monthly Income', width: 120, editable: true },
    { field: 'address_line1', headerName: 'Address',     width: 200, editable: true },
    { field: 'city',         headerName: 'City',         width: 100, editable: true },
    { field: 'state',        headerName: 'State',        width: 90,  editable: true },
    { field: 'country',      headerName: 'Country',      width: 90,  editable: true },
    {
      headerName: 'Action',
      width: 90,
      sortable: false,
      filter: false,
      editable: false,
      pinned: 'right',
      cellRenderer: (p: { data?: CustomerRow }) => {
        if (!p.data || p.data._isDeleted) return null;
        return (
          <button
            className="btn btn--primary btn--sm"
            style={{ fontSize: 10, padding: '3px 8px', marginTop: 4 }}
            onClick={() => router.push(`/fill?customer=${p.data!.customer_id}`)}
          >
            Fill →
          </button>
        );
      },
    },
  ], [router]);

  // ── AG Grid 默认列设置 ────────────────────────────────────

  const defaultColDef = useMemo<ColDef>(() => ({
    sortable: true,
    resizable: true,
    filter: false,
    editable: false,
    suppressMovable: false,
    cellStyle: { fontSize: 12, fontFamily: 'var(--font-body)', color: 'var(--ink)' },
  }), []);

  // ── 未保存改动数量提示 ────────────────────────────────────

  const pendingCount = newRows.length + dirtyIds.size + pendingDeletes.size;

  // ────────────────────────────────────────────────────────────
  //  Render
  // ────────────────────────────────────────────────────────────

  return (
    <>
      {/* 确认对话框 */}
      {confirmDelete && (
        <ConfirmDialog
          message={`确定要删除选中的 ${selectedCount} 条客户记录吗？此操作将在保存后永久生效。`}
          onConfirm={confirmDelete}
          onCancel={() => setConfirmDelete(null)}
        />
      )}

      {/* 新增客户 Modal */}
      {showAddModal && (
        <AddCustomerModal
          onAdd={handleAddRow}
          onClose={() => setShowAddModal(false)}
        />
      )}

      {/* Toast */}
      {toasts.map(t => (
        <div
          key={t.id}
          className={`toast toast--${t.type === 'success' ? 'success' : t.type === 'error' ? 'error' : 'info'}`}
          style={{ bottom: 24 + toasts.indexOf(t) * 56 }}
        >
          {t.message}
        </div>
      ))}

      {/* 隐藏 file input */}
      <input
        ref={fileInputRef}
        type="file"
        accept=".xlsx,.xls"
        style={{ display: 'none' }}
        onChange={handleFileChange}
      />

      {/* ── 页头 ─────────────────────────────────────────── */}
      <div className="page-header">
        <div className="flex items-center justify-between">
          <div>
            <h1 className="page-title">Customers</h1>
            <p className="page-subtitle">客户主数据库 · 可在页面直接维护；Excel 仅用于导入/导出</p>
          </div>
          <div className="flex items-center gap-2">
            {pendingCount > 0 && (
              <span className="badge badge--warning">
                {pendingCount} 项待保存
              </span>
            )}
            <div className="badge badge--info" style={{ fontSize: 12, padding: '6px 12px' }}>
              {total} Records
            </div>
          </div>
        </div>
      </div>

      {/* ── 搜索 + 按钮区 ─────────────────────────────────── */}
      <div className="flex items-center gap-3 mb-4" style={{ flexWrap: 'wrap' }}>
        <input
          className="form-input"
          style={{ maxWidth: 280 }}
          placeholder="Search name, IC No, phone, ID..."
          value={search}
          onChange={e => setSearch(e.target.value)}
        />

        <div className="flex items-center gap-2" style={{ marginLeft: 'auto', flexWrap: 'wrap' }}>
          {/* 新增 */}
          <button
            className="btn btn--primary btn--sm"
            onClick={() => setShowAddModal(true)}
            disabled={saving}
          >
            <svg viewBox="0 0 20 20" fill="currentColor" width={14} height={14}>
              <path d="M10 3a1 1 0 011 1v5h5a1 1 0 110 2h-5v5a1 1 0 11-2 0v-5H4a1 1 0 110-2h5V4a1 1 0 011-1z"/>
            </svg>
            Add Customer
          </button>

          {/* 删除选中 */}
          <button
            className="btn btn--danger btn--sm"
            onClick={handleDeleteSelected}
            disabled={selectedCount === 0 || saving}
          >
            <svg viewBox="0 0 20 20" fill="currentColor" width={14} height={14}>
              <path fillRule="evenodd" d="M9 2a1 1 0 00-.894.553L7.382 4H4a1 1 0 000 2v10a2 2 0 002 2h8a2 2 0 002-2V6a1 1 0 100-2h-3.382l-.724-1.447A1 1 0 0011 2H9zM7 8a1 1 0 012 0v6a1 1 0 11-2 0V8zm5-1a1 1 0 00-1 1v6a1 1 0 102 0V8a1 1 0 00-1-1z" clipRule="evenodd"/>
            </svg>
            Delete Selected{selectedCount > 0 ? ` (${selectedCount})` : ''}
          </button>

          {/* 保存 */}
          <button
            className="btn btn--success btn--sm"
            onClick={handleSaveAll}
            disabled={saving || pendingCount === 0}
          >
            {saving ? (
              <>
                <span className="loading-spinner" style={{ width: 12, height: 12, borderWidth: 2 }} />
                保存中…
              </>
            ) : (
              <>
                <svg viewBox="0 0 20 20" fill="currentColor" width={14} height={14}>
                  <path d="M17.414 2.586a2 2 0 00-2.828 0L7 10.172V13h2.828l7.586-7.586a2 2 0 000-2.828z"/>
                  <path fillRule="evenodd" d="M2 6a2 2 0 012-2h4a1 1 0 010 2H4v10h10v-4a1 1 0 112 0v4a2 2 0 01-2 2H4a2 2 0 01-2-2V6z" clipRule="evenodd"/>
                </svg>
                Save Changes{pendingCount > 0 ? ` (${pendingCount})` : ''}
              </>
            )}
          </button>

          {/* 导入 Excel */}
          <button
            className="btn btn--secondary btn--sm"
            onClick={handleImportClick}
            disabled={saving}
          >
            <svg viewBox="0 0 20 20" fill="currentColor" width={14} height={14}>
              <path fillRule="evenodd" d="M3 17a1 1 0 011-1h12a1 1 0 110 2H4a1 1 0 01-1-1zM6.293 6.707a1 1 0 010-1.414l3-3a1 1 0 011.414 0l3 3a1 1 0 01-1.414 1.414L11 5.414V13a1 1 0 11-2 0V5.414L7.707 6.707a1 1 0 01-1.414 0z" clipRule="evenodd"/>
            </svg>
            Import Excel
          </button>

          {/* 导出 Excel */}
          <button
            className="btn btn--secondary btn--sm"
            onClick={handleExport}
            disabled={saving}
          >
            <svg viewBox="0 0 20 20" fill="currentColor" width={14} height={14}>
              <path fillRule="evenodd" d="M3 17a1 1 0 011-1h12a1 1 0 110 2H4a1 1 0 01-1-1zm3.293-7.707a1 1 0 011.414 0L9 10.586V3a1 1 0 112 0v7.586l1.293-1.293a1 1 0 111.414 1.414l-3 3a1 1 0 01-1.414 0l-3-3a1 1 0 010-1.414z" clipRule="evenodd"/>
            </svg>
            Export Excel
          </button>
        </div>
      </div>

      {/* ── AG Grid ───────────────────────────────────────── */}
      {loading ? (
        <div className="card text-center" style={{ padding: 48 }}>
          <div className="loading-spinner" style={{ margin: '0 auto 12px' }} />
          <p className="caption">Loading from database...</p>
        </div>
      ) : (
        <div
          className="ag-theme-alpine"
          style={{
            width: '100%',
            height: 'calc(100vh - 300px)',
            minHeight: 400,
            border: '1px solid var(--vl)',
            borderRadius: 'var(--radius)',
            overflow: 'hidden',
            boxShadow: 'var(--shadow)',
          }}
        >
          <AgGridReact<CustomerRow>
            ref={gridRef}
            rowData={rowData}
            columnDefs={columnDefs}
            defaultColDef={defaultColDef}
            rowSelection="multiple"
            suppressRowClickSelection
            onGridReady={onGridReady}
            onCellValueChanged={onCellValueChanged}
            onSelectionChanged={onSelectionChanged}
            stopEditingWhenCellsLoseFocus
            animateRows
            suppressColumnVirtualisation={false}
            rowHeight={36}
            headerHeight={38}
          />
        </div>
      )}

      {/* ── 底部说明 ──────────────────────────────────────── */}
      <div className="mt-4">
        <p className="caption">
          数据来自系统数据库，可通过此页面直接维护；Excel 仅用于导入/导出。
          {pendingCount > 0 && (
            <span style={{ color: 'var(--warning)', fontWeight: 600 }}>
              {' '}当前有 {pendingCount} 项未保存改动，请点击"Save Changes"提交。
            </span>
          )}
        </p>
      </div>

    </>
  );
}
