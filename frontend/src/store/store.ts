import { configureStore } from "@reduxjs/toolkit";
import { appPreferencesReducer } from "@/store/slices/appPreferencesSlice";
import { repositorySelectionReducer } from "@/store/slices/repositorySelectionSlice";

export function makeStore() {
  return configureStore({
    reducer: {
      appPreferences: appPreferencesReducer,
      repositorySelection: repositorySelectionReducer,
    },
  });
}

export type AppStore = ReturnType<typeof makeStore>;
export type RootState = ReturnType<AppStore["getState"]>;
export type AppDispatch = AppStore["dispatch"];
