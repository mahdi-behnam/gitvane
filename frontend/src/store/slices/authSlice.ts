import { createSlice, type PayloadAction } from "@reduxjs/toolkit";

type User = {
  id: number;
  email: string;
  full_name: string;
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
      action: PayloadAction<{ accessToken: string; user?: User | null }>
    ) {
      state.accessToken = action.payload.accessToken;
      if (action.payload.user !== undefined) {
        state.user = action.payload.user;
      }
    },
    clearCredentials(state) {
      state.accessToken = null;
      state.user = null;
    },
  },
});

export const { setCredentials, clearCredentials } = authSlice.actions;
export const authReducer = authSlice.reducer;
