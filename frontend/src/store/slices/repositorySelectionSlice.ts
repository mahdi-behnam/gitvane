import { createSlice, type PayloadAction } from "@reduxjs/toolkit";

type RepositorySelectionState = {
  activeRepositoryId: string | null;
  recentAnalysisRunId: number | null;
  recentEvaluationRunId: number | null;
};

const initialState: RepositorySelectionState = {
  activeRepositoryId: null,
  recentAnalysisRunId: null,
  recentEvaluationRunId: null,
};

const repositorySelectionSlice = createSlice({
  name: "repositorySelection",
  initialState,
  reducers: {
    clearActiveRepository(state) {
      state.activeRepositoryId = null;
    },
    setActiveRepositoryId(state, action: PayloadAction<string | null>) {
      state.activeRepositoryId = action.payload;
    },
    setRecentAnalysisRunId(state, action: PayloadAction<number | null>) {
      state.recentAnalysisRunId = action.payload;
    },
    setRecentEvaluationRunId(state, action: PayloadAction<number | null>) {
      state.recentEvaluationRunId = action.payload;
    },
  },
});

export const {
  clearActiveRepository,
  setActiveRepositoryId,
  setRecentAnalysisRunId,
  setRecentEvaluationRunId,
} = repositorySelectionSlice.actions;

export const repositorySelectionReducer = repositorySelectionSlice.reducer;
