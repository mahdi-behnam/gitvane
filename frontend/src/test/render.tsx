import { render, type RenderOptions } from "@testing-library/react";
import type { ReactElement } from "react";
import { Provider } from "react-redux";
import { makeStore, type AppStore } from "@/store/store";

type ExtendedRenderOptions = RenderOptions & {
  store?: AppStore;
};

export function renderWithProviders(
  ui: ReactElement,
  { store = makeStore(), ...renderOptions }: ExtendedRenderOptions = {},
) {
  return {
    store,
    ...render(<Provider store={store}>{ui}</Provider>, renderOptions),
  };
}
