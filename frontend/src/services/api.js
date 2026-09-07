const API_BASE_URL =
  import.meta.env.VITE_API_BASE_URL ?? "";

export async function request(path, options = {}) {
  const response = await fetch(`${API_BASE_URL}/api${path}`, {
    ...options,
    signal: AbortSignal.timeout(15000),
    headers: { 'Content-Type': 'application/json', ...options.headers },
  });
  const data = await response.json();
  if (!response.ok) throw new Error(typeof data.detail === 'string' ? data.detail : '요청을 처리하지 못했습니다.');
  return data;
}

export async function getHealth() {
  const response = await fetch(`${API_BASE_URL}/api/health`);

  if (!response.ok) {
    throw new Error("API 서버 상태를 확인할 수 없습니다.");
  }

  return response.json();
}
