// TODO: typed fetch helpers calling FastAPI (NEXT_PUBLIC_API_URL)

export const apiBaseUrl =
  process.env.NEXT_PUBLIC_API_URL ?? "http://127.0.0.1:8000";
