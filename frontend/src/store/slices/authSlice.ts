import { createSlice, type PayloadAction } from "@reduxjs/toolkit";

type User = {
  id: number;
  email: string;
  full_name: string;
  oauth_provider?: string | null;
  picture?: string | null;
};

type AuthState = {
  accessToken: string | null;
  user: User | null;
};

const initialState: AuthState = {
  accessToken: null,
  user: null,
};

const authSlice = createSlice({
  name: "auth",
  initialState,
  reducers: {
    setCredentials(
      state,
      action: PayloadAction<{ accessToken?: string | null; user?: User | null }>
    ) {
      if (action.payload.accessToken !== undefined) {
        state.accessToken = action.payload.accessToken;
      }
      if (action.payload.user !== undefined) {
        state.user = action.payload.user;
      }
    },
    setUser(state, action: PayloadAction<User | null>) {
      state.user = action.payload;
    },
    clearCredentials(state) {
      state.accessToken = null;
      state.user = null;
    },
  },
});

export const { setCredentials, setUser, clearCredentials } = authSlice.actions;
export const authReducer = authSlice.reducer;
