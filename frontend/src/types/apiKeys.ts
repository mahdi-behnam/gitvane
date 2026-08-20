export interface ApiKeyItem {
  id: string;
  name: string;
  key_prefix: string;
  created_at: string;
  expires_at: string | null;
  last_used_at: string | null;
  is_revoked: boolean;
}

export interface ApiKeyCreateRequest {
  name: string;
  expires_in_days?: number;
}

export interface ApiKeyCreatedResponse extends ApiKeyItem {
  raw_key: string;
}
