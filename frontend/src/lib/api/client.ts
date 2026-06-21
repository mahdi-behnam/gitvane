import { env } from "@/lib/env";

export const apiBaseUrl = env.NEXT_PUBLIC_API_BASE_URL.replace(/\/$/, "");
