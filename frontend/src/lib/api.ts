/**
 * api.ts — 前端 API 调用封装
 * 所有请求都指向后端 FastAPI 服务（默认 http://localhost:8000）
 */

import axios from 'axios';

const BASE_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';

const api = axios.create({
  baseURL: BASE_URL,
  timeout: 60000,  // 60s（PDF 分析可能耗时较长）
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
  cell_width: number;
  cell_height: number;
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

export interface FillFormResponse {
  success: boolean;
  output_path: string;
  download_url: string;
  output_filename: string;
  filled_count: number;
  manual_count: number;
  skipped_count: number;
  manual_fields: string[];
}

// ── API 函数 ───────────────────────────────────────────────────

// 上传表格 PDF，分析字段
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

// 获取模板列表
export async function getTemplates(): Promise<Template[]> {
  const res = await api.get<Template[]>('/templates');
  return res.data;
}

// 获取单个模板（含字段列表）
export async function getTemplate(id: number): Promise<Template> {
  const res = await api.get<Template>(`/templates/${id}`);
  return res.data;
}

// 批量更新字段
export async function updateFields(
  templateId: number,
  fields: Partial<Field & { id: number }>[],
): Promise<void> {
  await api.put(`/templates/${templateId}/fields`, { fields });
}

// 获取客户列表
export async function getCustomers(): Promise<Customer[]> {
  const res = await api.get<Customer[]>('/customers');
  return res.data;
}

// 获取单个客户完整数据
export async function getCustomer(id: string): Promise<Record<string, string>> {
  const res = await api.get<Record<string, string>>(`/customers/${id}`);
  return res.data;
}

// 执行填表
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

// 获取所有标准字段键
export async function getStandardKeys(): Promise<string[]> {
  const res = await api.get<{ keys: string[] }>('/standard-keys');
  return res.data.keys;
}

// 添加同义词
export async function addSynonym(
  standardKey: string,
  synonym: string,
): Promise<void> {
  await api.post('/synonyms', { standard_key: standardKey, synonym });
}

// 获取文件下载 URL
export function getDownloadUrl(filename: string): string {
  return `${BASE_URL}/download/${filename}`;
}
