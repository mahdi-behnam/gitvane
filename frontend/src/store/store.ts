import { configureStore } from "@reduxjs/toolkit";
import { repolensApi } from "@/store/api/repolensApi";
import { appPreferencesReducer } from "@/store/slices/appPreferencesSlice";
import { repositorySelectionReducer } from "@/store/slices/repositorySelectionSlice";
import { authReducer } from "@/store/slices/authSlice";

export function makeStore() {
  return configureStore({
    reducer: {
      appPreferences: appPreferencesReducer,
      auth: authReducer,
      [repolensApi.reducerPath]: repolensApi.reducer,
      repositorySelection: repositorySelectionReducer,
    },
    middleware: (getDefaultMiddleware) =>
      getDefaultMiddleware().concat(repolensApi.middleware),
  });
}

export type AppStore = ReturnType<typeof makeStore>;
export type RootState = ReturnType<AppStore["getState"]>;
export type AppDispatch = AppStore["dispatch"];
