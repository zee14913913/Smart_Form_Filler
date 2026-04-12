/**
 * api.ts — 前端 API 调用封装 (v3 — PRD Master Prompt 严格版)
 * 所有请求指向后端 FastAPI（默认 http://localhost:8000）
 *
 * PRD 严格约束：
 *   - 结果只允许 pass / fail，无 warning / manual
 *   - VerificationSummary 只有 total_pass / total_fail
 *   - FillJob 只有 total_pass / total_fail / final_verdict
 *   - SystemSettings 使用 fail_threshold，无 overflow_policy / manual_threshold
 */

import axios from 'axios';

const BASE_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';

const api = axios.create({
  baseURL: BASE_URL,
  timeout: 60000,
});

// ── 类型定义 ───────────────────────────────────────────────────

export interface Field {
  id: number;
  template_id: number;
  page_number: number;
  raw_label: string;
  standard_key: string;
  field_type: 'text' | 'checkbox' | 'date' | 'phone' | 'signature';
  cell_x0: number;
  cell_top: number;
  cell_x1: number;
  cell_bottom: number;
  font_size_max: number;
  font_size_min: number;
  font_size_step: number;
  text_align: 'left' | 'center' | 'right';
  padding_left_px: number;
  padding_vertical_strategy: string;
  multiline: number;
  max_chars: number;
  is_confirmed: number;
  match_confidence?: number;
}

export interface Template {
  id: number;
  name: string;
  institution: string;
  source_filename: string;
  original_pdf_path?: string;
  page_count: number;
  status: 'draft' | 'confirmed' | 'active';
  created_at: string;
  updated_at: string;
  fields?: Field[];
}

export interface UploadFormResponse {
  template_id: number;
  template_name: string;
  institution: string;
  page_count: number;
  field_count: number;
  fields: Field[];
}

/** 数据库客户记录（完整字段） */
export interface Customer {
  id: number;            // DB 主键
  customer_id: string;   // 业务编号，如 C001
  full_name: string;
  ic_no: string;
  date_of_birth?: string;
  nationality?: string;
  gender?: string;
  marital_status?: string;
  race?: string;
  religion?: string;
  mobile_no?: string;
  home_tel?: string;
  email?: string;
  address_line1?: string;
  address_line2?: string;
  address_line3?: string;
  postcode?: string;
  city?: string;
  state?: string;
  country?: string;
  employer_name?: string;
  employer_address?: string;
  monthly_income?: string;
  annual_income?: string;
  occupation?: string;
  employment_type?: string;
  years_with_employer?: string;
  bank_name?: string;
  bank_account_no?: string;
  loan_amount?: string;
  loan_tenure?: string;
  created_at?: string;
  updated_at?: string;
}

export interface CustomerListResponse {
  success: boolean;
  data: {
    items: Customer[];
    total: number;
    page: number;
    page_size: number;
  };
}

export interface CustomerBulkPayload {
  create: Partial<Customer>[];
  update: Partial<Customer>[];
  delete: number[];
}

/** PRD v3：只有 pass / fail，无 warning / manual */
export interface VerificationSummary {
  total_fields: number;
  total_pass: number;
  total_fail: number;
  final_verdict: 'pass' | 'fail';
  image_diff_available: boolean;
  image_diff_verdict: 'pass' | 'fail';
}

/** PRD v3：fill_status = write | fail；verify_status = pass | fail */
export interface FieldVerdict {
  field_id: number;
  raw_label: string;
  standard_key: string;
  fill_status: 'write' | 'fail';
  verify_status: 'pass' | 'fail';
  verify_reason: string;
}

export interface FillFormResponse {
  job_id: number;
  download_url: string;
  output_filename: string;
  write_count: number;
  fail_count: number;
  fail_fields: string[];
  verification: VerificationSummary;
  field_verdicts: FieldVerdict[];
}

/** PRD v3：只有 total_pass / total_fail / final_verdict */
export interface FillJob {
  id: number;
  template_id: number;
  template_name?: string;
  customer_ref: string;
  customer_name: string;
  original_pdf_path: string;
  output_path: string;
  output_filename: string;
  status: 'pending' | 'running' | 'done' | 'failed';
  total_fields: number;
  total_pass: number;
  total_fail: number;
  verification_status: string;
  final_verdict: 'pass' | 'fail' | null;
  created_at: string;
  updated_at: string;
}

/** PRD v3：fail_threshold 替代 overflow_policy + manual_threshold */
export interface SystemSettings {
  // 字体
  default_font_name: string;
  default_font_size_max: number;
  default_font_size_min: number;
  default_font_size_step: number;
  // Padding
  default_left_padding_px: number;
  default_vertical_strategy: string;
  default_custom_offset: number;
  // 对齐
  default_text_align: string;
  // 失败阈值（PRD v3）
  fail_threshold: number;
  // 验证
  verify_pixel_diff_threshold: number;
  // 只读
  render_base: string;
  allow_custom_drawn_templates: number;
  allow_modify_original_content: number;
  updated_at: string;
}

// ── API 函数 ───────────────────────────────────────────────────

export async function uploadForm(
  file: File,
  templateName?: string,
  institution?: string,
): Promise<UploadFormResponse> {
  const formData = new FormData();
  formData.append('file', file);
  formData.append('template_name', templateName || '');
  formData.append('institution', institution || '');
  const res = await api.post<UploadFormResponse>('/upload-form', formData);
  return res.data;
}

export async function getTemplates(): Promise<Template[]> {
  const res = await api.get<Template[]>('/templates');
  return res.data;
}

export async function getTemplate(id: number): Promise<Template> {
  const res = await api.get<Template>(`/templates/${id}`);
  return res.data;
}

export async function updateFields(
  templateId: number,
  fields: Partial<Field & { id: number }>[],
): Promise<{ success: boolean; updated_count: number; template_status?: string }> {
  const res = await api.put<{ success: boolean; updated_count: number; template_status?: string }>(`/templates/${templateId}/fields`, { fields });
  return res.data;
}

export async function confirmTemplate(templateId: number): Promise<{ success: boolean; status: string }> {
  const res = await api.post<{ success: boolean; status: string }>(`/templates/${templateId}/confirm`, {});
  return res.data;
}

export async function getCustomers(
  page = 1,
  pageSize = 200,
  q?: string,
): Promise<CustomerListResponse> {
  const params: Record<string, string | number> = { page, page_size: pageSize };
  if (q) params.q = q;
  const res = await api.get<CustomerListResponse>('/customers', { params });
  return res.data;
}

export async function getCustomer(id: string): Promise<Record<string, string>> {
  const res = await api.get<Record<string, string>>(`/customers/${id}`);
  return res.data;
}

export async function createCustomer(data: Partial<Customer>): Promise<Customer> {
  const res = await api.post<{ success: boolean; data: Customer }>('/customers', data);
  return res.data.data;
}

export async function updateCustomer(id: number, data: Partial<Customer>): Promise<Customer> {
  const res = await api.put<{ success: boolean; data: Customer }>(`/customers/${id}`, data);
  return res.data.data;
}

export async function deleteCustomer(id: number): Promise<void> {
  await api.delete(`/customers/${id}`);
}

export async function bulkCustomers(payload: CustomerBulkPayload): Promise<{
  created: number; updated: number; deleted: number; errors: unknown[];
}> {
  const res = await api.post<{ success: boolean; data: { created: number; updated: number; deleted: number; errors: unknown[] } }>('/customers/bulk', payload);
  return res.data.data;
}

export async function importCustomersXlsx(file: File): Promise<{
  imported: number; skipped: number; errors: unknown[];
}> {
  const formData = new FormData();
  formData.append('file', file);
  const res = await api.post<{ success: boolean; data: { imported: number; skipped: number; errors: unknown[] } }>('/customers/import-xlsx', formData);
  return res.data.data;
}

export function getCustomerExportUrl(): string {
  return `${BASE_URL}/customers/export-xlsx`;
}

export async function fillForm(
  templateId: number,
  customerId: string,
): Promise<FillFormResponse> {
  const res = await api.post<FillFormResponse>('/fill-form', {
    template_id: templateId,
    customer_id: customerId,
  });
  return res.data;
}

export async function getJobs(limit = 20): Promise<FillJob[]> {
  const res = await api.get<FillJob[]>(`/jobs?limit=${limit}`);
  return res.data;
}

export async function getJob(jobId: number): Promise<FillJob & { field_results: unknown[] }> {
  const res = await api.get(`/jobs/${jobId}`);
  return res.data;
}

export async function getSettings(): Promise<SystemSettings> {
  const res = await api.get<SystemSettings>('/settings');
  return res.data;
}

export async function updateSettings(
  patch: Partial<Omit<SystemSettings, 'render_base' | 'allow_custom_drawn_templates' | 'allow_modify_original_content' | 'updated_at'>>,
): Promise<SystemSettings> {
  const res = await api.post<SystemSettings>('/settings', patch);
  return res.data;
}

export async function getStandardKeys(): Promise<string[]> {
  const res = await api.get<{ keys: string[] }>('/standard-keys');
  return res.data.keys;
}

export async function addSynonym(
  standardKey: string,
  synonym: string,
): Promise<void> {
  await api.post('/synonyms', { standard_key: standardKey, synonym });
}

export function getDownloadUrl(filename: string): string {
  return `${BASE_URL}/download/${filename}`;
}
