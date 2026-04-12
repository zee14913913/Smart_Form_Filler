'use client';

import { useState, useRef, DragEvent, ChangeEvent } from 'react';
import { useRouter } from 'next/navigation';
import { uploadForm, UploadFormResponse } from '@/lib/api';

type Step = 'upload' | 'analyzing' | 'done';

export default function UploadPage() {
  const router = useRouter();
  const fileRef = useRef<HTMLInputElement>(null);

  const [step, setStep] = useState<Step>('upload');
  const [dragOver, setDragOver] = useState(false);
  const [file, setFile] = useState<File | null>(null);
  const [templateName, setTemplateName] = useState('');
  const [institution, setInstitution] = useState('');
  const [result, setResult] = useState<UploadFormResponse | null>(null);
  const [error, setError] = useState('');

  // ── 文件选择 ──────────────────────────────────────────────────

  const handleDrop = (e: DragEvent<HTMLDivElement>) => {
    e.preventDefault();
    setDragOver(false);
    const f = e.dataTransfer.files[0];
    if (f) selectFile(f);
  };

  const handleFileChange = (e: ChangeEvent<HTMLInputElement>) => {
    const f = e.target.files?.[0];
    if (f) selectFile(f);
  };

  const selectFile = (f: File) => {
    const allowed = ['application/pdf', 'image/jpeg', 'image/png', 'image/tiff'];
    if (!allowed.includes(f.type) && !f.name.match(/\.(pdf|jpg|jpeg|png|tiff?)$/i)) {
      setError('仅支持 PDF、JPG、PNG、TIFF 格式');
      return;
    }
    setFile(f);
    setError('');
    if (!templateName) setTemplateName(f.name.replace(/\.[^.]+$/, ''));
  };

  // ── 提交分析 ──────────────────────────────────────────────────

  const handleSubmit = async () => {
    if (!file) return;
    setStep('analyzing');
    setError('');
    try {
      const res = await uploadForm(file, templateName, institution);
      setResult(res);
      setStep('done');
    } catch (e: any) {
      setError(e?.response?.data?.detail || '上传失败，请检查后端服务是否运行');
      setStep('upload');
    }
  };

  // ── 渲染 ──────────────────────────────────────────────────────

  return (
    <>
      <div className="page-header">
        <h1 className="page-title">Upload New Form</h1>
        <p className="page-subtitle">上传 PDF 或图片表格，系统自动分析填写字段</p>
      </div>

      {/* 步骤指示 */}
      <div className="steps mb-6">
        <div className={`step ${step !== 'upload' ? 'done' : 'active'}`}>
          <div className="step-circle">{step !== 'upload' ? '✓' : '1'}</div>
          <span className="step-label">选择文件</span>
        </div>
        <div className="step-line" />
        <div className={`step ${step === 'analyzing' ? 'active' : step === 'done' ? 'done' : ''}`}>
          <div className="step-circle">{step === 'done' ? '✓' : '2'}</div>
          <span className="step-label">分析字段</span>
        </div>
        <div className="step-line" />
        <div className={`step ${step === 'done' ? 'active' : ''}`}>
          <div className="step-circle">3</div>
          <span className="step-label">确认映射</span>
        </div>
      </div>

      {/* 分析中 */}
      {step === 'analyzing' && (
        <div className="card text-center" style={{ padding: 48 }}>
          <div className="loading-spinner" style={{ width: 36, height: 36, margin: '0 auto 16px', borderWidth: 3 }} />
          <p className="section-title" style={{ marginBottom: 8 }}>正在分析表格...</p>
          <p className="caption">系统正在识别填写字段的位置与类型，大型 PDF 可能需要数秒</p>
        </div>
      )}

      {/* 上传步骤 */}
      {step === 'upload' && (
        <div style={{ maxWidth: 640 }}>
          {/* 拖拽上传区 */}
          <div
            className={`upload-card mb-4${dragOver ? ' drag-over' : ''}`}
            onDragOver={(e) => { e.preventDefault(); setDragOver(true); }}
            onDragLeave={() => setDragOver(false)}
            onDrop={handleDrop}
            onClick={() => fileRef.current?.click()}
          >
            <svg className="upload-card__icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth={1.5}>
              <path d="M21 15v4a2 2 0 01-2 2H5a2 2 0 01-2-2v-4"/>
              <polyline points="17 8 12 3 7 8"/>
              <line x1="12" y1="3" x2="12" y2="15"/>
            </svg>
            <div className="upload-card__title">
              {file ? file.name : '点击或拖拽上传表格'}
            </div>
            <div className="upload-card__hint">
              {file
                ? `${(file.size / 1024).toFixed(1)} KB · ${file.type}`
                : '支持 PDF、JPG、PNG、TIFF 格式'}
            </div>
            <input
              ref={fileRef}
              type="file"
              accept=".pdf,.jpg,.jpeg,.png,.tiff,.tif"
              style={{ display: 'none' }}
              onChange={handleFileChange}
            />
          </div>

          {/* 模板信息 */}
          <div className="card mb-4">
            <div className="section-title mb-4">Template Info</div>
            <div className="form-group">
              <label className="form-label">Template Name</label>
              <input
                className="form-input"
                placeholder="例如：CIMB 信用卡申请表"
                value={templateName}
                onChange={e => setTemplateName(e.target.value)}
              />
            </div>
            <div className="form-group">
              <label className="form-label">Institution / Bank</label>
              <input
                className="form-input"
                placeholder="例如：CIMB Bank"
                value={institution}
                onChange={e => setInstitution(e.target.value)}
              />
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

          <button
            className="btn btn--primary btn--lg w-full"
            onClick={handleSubmit}
            disabled={!file}
          >
            <svg width={16} height={16} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth={2.5}>
              <path d="M12 2v20M2 12h20"/>
            </svg>
            Start Analysis
          </button>
        </div>
      )}

      {/* 分析结果 */}
      {step === 'done' && result && (
        <div style={{ maxWidth: 900 }}>
          {/* 摘要 */}
          <div className="card mb-4">
            <div className="flex items-center justify-between mb-3">
              <span className="section-title">Analysis Complete</span>
              <span className="badge badge--success">✓ Done</span>
            </div>
            <div className="grid-3">
              <div><span className="form-label">Template Name</span><p>{result.template_name}</p></div>
              <div><span className="form-label">Pages</span><p>{result.page_count}</p></div>
              <div><span className="form-label">Fields Found</span><p>{result.field_count}</p></div>
            </div>
          </div>

          {/* 字段列表 */}
          <div className="card mb-4">
            <div className="section-title mb-4">Detected Fields ({result.fields.length})</div>
            {result.fields.length === 0 ? (
              <div className="empty-state" style={{ padding: 24 }}>
                <p>未检测到字段，可能是扫描质量不足或 PDF 格式不支持。<br/>请前往模板详情页手动配置。</p>
              </div>
            ) : (
              <div style={{ overflowX: 'auto' }}>
                <table className="data-table">
                  <thead>
                    <tr>
                      <th>Page</th>
                      <th>Raw Label</th>
                      <th>Standard Key</th>
                      <th>Confidence</th>
                      <th>Cell Size (w×h)</th>
                    </tr>
                  </thead>
                  <tbody>
                    {result.fields.map((f, i) => (
                      <tr key={i}>
                        <td>{f.page_number}</td>
                        <td>{f.raw_label || <span className="text-muted">—</span>}</td>
                        <td>
                          {f.standard_key
                            ? <code style={{ fontSize: 10, background: 'var(--vp)', padding: '2px 5px', borderRadius: 4 }}>{f.standard_key}</code>
                            : <span className="badge badge--warning">Unmatched</span>}
                        </td>
                        <td>
                          {f.match_confidence !== undefined && (
                            <span className={`badge badge--${f.match_confidence >= 0.9 ? 'success' : f.match_confidence >= 0.7 ? 'warning' : 'danger'}`}>
                              {Math.round((f.match_confidence || 0) * 100)}%
                            </span>
                          )}
                        </td>
                        <td className="text-muted">
                          {f.cell_width?.toFixed(0) || '?'} × {f.cell_height?.toFixed(0) || '?'} pt
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            )}
          </div>

          <div className="flex gap-3">
            <button
              className="btn btn--primary"
              onClick={() => router.push(`/templates/${result.template_id}`)}
            >
              Confirm Field Mapping →
            </button>
            <button className="btn btn--secondary" onClick={() => {
              setStep('upload'); setFile(null); setResult(null); setTemplateName(''); setInstitution('');
            }}>
              Upload Another
            </button>
          </div>
        </div>
      )}
    </>
  );
}
