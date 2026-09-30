export const API_BASE_URL: string = import.meta.env.VITE_API_BASE_URL ?? 'http://localhost:8006'

export type Health = { status: string; governorates: number }

export async function getHealth(): Promise<Health> {
  const response = await fetch(`${API_BASE_URL}/api/v1/health`)
  if (!response.ok) throw new Error(`HTTP ${response.status}`)
  return response.json()
}
