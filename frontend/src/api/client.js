const API_BASE = '/api';

async function handleResponse(response) {
  if (!response.ok) {
    let errorDetail = 'An error occurred';
    try {
      const data = await response.json();
      errorDetail = data.detail || JSON.stringify(data);
    } catch {
      errorDetail = await response.text() || response.statusText;
    }
    const error = new Error(errorDetail);
    error.status = response.status;
    throw error;
  }
  return response.json();
}

export const api = {
  // Practical Files
  async getPracticalFiles() {
    const res = await fetch(`${API_BASE}/practical-files`);
    return handleResponse(res);
  },

  async getPracticalFile(id) {
    const res = await fetch(`${API_BASE}/practical-files/${id}`);
    return handleResponse(res);
  },

  async createPracticalFile(data) {
    const res = await fetch(`${API_BASE}/practical-files`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(data),
    });
    return handleResponse(res);
  },

  async updateCoverPageCount(id, cover_page_count) {
    const res = await fetch(`${API_BASE}/practical-files/${id}`, {
      method: 'PATCH',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ cover_page_count: Number(cover_page_count) }),
    });
    return handleResponse(res);
  },

  // Tasks
  async createTask(practicalFileId, data) {
    const res = await fetch(`${API_BASE}/practical-files/${practicalFileId}/tasks`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(data),
    });
    return handleResponse(res);
  },

  async getTasks(practicalFileId) {
    const res = await fetch(`${API_BASE}/practical-files/${practicalFileId}/tasks`);
    return handleResponse(res);
  },

  async reorderTasks(practicalFileId, taskIds) {
    const res = await fetch(`${API_BASE}/practical-files/${practicalFileId}/tasks/reorder`, {
      method: 'PATCH',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ task_ids: taskIds }),
    });
    return handleResponse(res);
  },

  async getTask(taskId) {
    const res = await fetch(`${API_BASE}/tasks/${taskId}`);
    return handleResponse(res);
  },

  // Markdown
  async submitMarkdown(taskId, rawMarkdown) {
    const res = await fetch(`${API_BASE}/tasks/${taskId}/markdown`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ raw_markdown: rawMarkdown }),
    });
    return handleResponse(res);
  },

  // Placeholders
  async getPlaceholders(taskId) {
    const res = await fetch(`${API_BASE}/tasks/${taskId}/placeholders`);
    return handleResponse(res);
  },

  async updatePlaceholder(placeholderId, data) {
    const res = await fetch(`${API_BASE}/placeholders/${placeholderId}`, {
      method: 'PATCH',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(data),
    });
    return handleResponse(res);
  },

  async uploadPlaceholderImage(placeholderId, file) {
    const formData = new FormData();
    formData.append('file', file);
    const res = await fetch(`${API_BASE}/placeholders/${placeholderId}/upload`, {
      method: 'POST',
      body: formData,
    });
    return handleResponse(res);
  },

  async retryPlaceholder(placeholderId) {
    const res = await fetch(`${API_BASE}/placeholders/${placeholderId}/retry`, {
      method: 'POST',
    });
    return handleResponse(res);
  },

  getPlaceholderImageUrl(placeholderId) {
    return `${API_BASE}/placeholders/${placeholderId}/image`;
  },

  // Generation
  async getStartingPage(taskId) {
    const res = await fetch(`${API_BASE}/tasks/${taskId}/starting-page`);
    return handleResponse(res);
  },

  async generatePdf(taskId, startingPage = null) {
    const res = await fetch(`${API_BASE}/tasks/${taskId}/generate`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ starting_page: startingPage ? Number(startingPage) : null }),
    });
    return handleResponse(res);
  },

  getPdfDownloadUrl(taskId) {
    return `${API_BASE}/tasks/${taskId}/pdf`;
  },
};
