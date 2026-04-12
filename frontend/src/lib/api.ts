/**
 * api.ts — 前端 API 调用封装 (v2)
 * 所有请求指向后端 FastAPI（默认 http://localhost:8000）
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
  cell_x0: number;
  cell_top: number;
  cell_x1: number;
  cell_bottom: number;
  font_size_max: number;
  font_size_min: number;
  font_size_step: number;
  align: 'left' | 'center' | 'right';
  is_confirmed: number;
  needs_manual: number;
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

export interface Customer {
  customer_id: string;
  full_name: string;
  ic_no: string;
  mobile_no: string;
}

export interface VerificationSummary {
  total_fields: number;
  pass_count: number;
  warning_count: number;
  fail_count: number;
  manual_count: number;
  final_verdict: 'pass' | 'warning' | 'fail';
  image_diff_available: boolean;
  image_diff_verdict: 'pass' | 'warning' | 'fail';
}

export interface FieldVerdict {
  field_id: number;
  raw_label: string;
  standard_key: string;
  fill_status: string;
  verify_status: 'pass' | 'warning' | 'fail' | 'manual';
  verify_reason: string;
}

export interface FillFormResponse {
  job_id: number;
  download_url: string;
  output_filename: string;
  filled_count: number;
  manual_count: number;
  skipped_count: number;
  manual_fields: string[];
  verification: VerificationSummary;
  field_verdicts: FieldVerdict[];
}

export interface FillJob {
  id: number;
  template_id: number;
  template_name?: string;
  customer_ref: string;
  customer_name: string;
  output_filename: string;
  status: 'pending' | 'running' | 'done' | 'failed';
  filled_count: number;
  skipped_count: number;
  manual_count: number;
  total_fields: number;
  verification_status: string;
  verification_verdict: string;
  pass_count: number;
  warning_count: number;
  fail_count: number;
  created_at: string;
}

export interface SystemSettings {
  default_font_name: string;
  default_font_size_max: number;
  default_font_size_min: number;
  default_font_size_step: number;
  default_left_padding_px: number;
  default_vertical_strategy: string;
  default_custom_offset: number;
  default_text_align: string;
  default_multiline_behavior: string;
  overflow_policy: string;
  manual_threshold: number;
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
): Promise<void> {
  await api.put(`/templates/${templateId}/fields`, { fields });
}

export async function getCustomers(): Promise<Customer[]> {
  const res = await api.get<Customer[]>('/customers');
  return res.data;
}

export async function getCustomer(id: string): Promise<Record<string, string>> {
  const res = await api.get<Record<string, string>>(`/customers/${id}`);
  return res.data;
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
  patch: Partial<Omit<SystemSettings, 'render_base' | 'allow_custom_drawn_templates' | 'allow_modify_original_content' | 'updated_at' | 'id'>>,
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
