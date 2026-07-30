import { describe, expect, it } from "vitest";
import {
  setDependencyDepth,
  setThemePreference,
} from "@/store/slices/appPreferencesSlice";
import { setActiveRepositoryId } from "@/store/slices/repositorySelectionSlice";
import { makeStore } from "@/store/store";

describe("store", () => {
  it("tracks app preferences and active repository selection", () => {
    const store = makeStore();

    store.dispatch(setThemePreference("dark"));
    store.dispatch(setDependencyDepth(3));
    store.dispatch(setActiveRepositoryId("77777777-7777-7777-7777-777777777777"));

    expect(store.getState().appPreferences.theme).toBe("dark");
    expect(store.getState().appPreferences.dependencyDepth).toBe(3);
    expect(store.getState().repositorySelection.activeRepositoryId).toBe("77777777-7777-7777-7777-777777777777");
  });
});
