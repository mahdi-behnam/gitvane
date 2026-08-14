import { z } from "zod";

const envSchema = z.object({
  NEXT_PUBLIC_API_BASE_URL: z
    .string()
    .url()
    .or(z.string().startsWith("/"))
    .default("http://localhost:8000/api/v1"),
  INTERNAL_API_BASE_URL: z
    .string()
    .url()
    .optional()
    .default("http://backend:8000/api/v1"),
});

export const env = envSchema.parse({
  NEXT_PUBLIC_API_BASE_URL: process.env.NEXT_PUBLIC_API_BASE_URL,
  INTERNAL_API_BASE_URL: process.env.INTERNAL_API_BASE_URL,
});

