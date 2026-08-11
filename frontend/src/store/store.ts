import { configureStore } from "@reduxjs/toolkit";
import { gitvaneApi } from "@/store/api/gitvaneApi";
import { appPreferencesReducer } from "@/store/slices/appPreferencesSlice";
import { repositorySelectionReducer } from "@/store/slices/repositorySelectionSlice";
import { authReducer } from "@/store/slices/authSlice";

export function makeStore() {
  return configureStore({
    reducer: {
      appPreferences: appPreferencesReducer,
      auth: authReducer,
      [gitvaneApi.reducerPath]: gitvaneApi.reducer,
      repositorySelection: repositorySelectionReducer,
    },
    middleware: (getDefaultMiddleware) =>
      getDefaultMiddleware().concat(gitvaneApi.middleware),
  });
}

export type AppStore = ReturnType<typeof makeStore>;
export type RootState = ReturnType<AppStore["getState"]>;
export type AppDispatch = AppStore["dispatch"];
