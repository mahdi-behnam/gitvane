import { createSlice, type PayloadAction } from "@reduxjs/toolkit";

export type ThemePreference = "system" | "light" | "dark";

type AppPreferencesState = {
  dependencyDepth: number;
  includeChangedFilesInImpact: boolean;
  includeExplanations: boolean;
  theme: ThemePreference;
};

const initialState: AppPreferencesState = {
  dependencyDepth: 2,
  includeChangedFilesInImpact: false,
  includeExplanations: true,
  theme: "system",
};

const appPreferencesSlice = createSlice({
  name: "appPreferences",
  initialState,
  reducers: {
    setDependencyDepth(state, action: PayloadAction<number>) {
      state.dependencyDepth = action.payload;
    },
    setIncludeChangedFilesInImpact(state, action: PayloadAction<boolean>) {
      state.includeChangedFilesInImpact = action.payload;
    },
    setIncludeExplanations(state, action: PayloadAction<boolean>) {
      state.includeExplanations = action.payload;
    },
    setThemePreference(state, action: PayloadAction<ThemePreference>) {
      state.theme = action.payload;
    },
  },
});

export const {
  setDependencyDepth,
  setIncludeChangedFilesInImpact,
  setIncludeExplanations,
  setThemePreference,
} = appPreferencesSlice.actions;

export const appPreferencesReducer = appPreferencesSlice.reducer;
