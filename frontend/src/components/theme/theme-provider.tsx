"use client";

import {
  createContext,
  useCallback,
  useContext,
  useEffect,
  useMemo,
  useState,
} from "react";

type ThemeMode = "system" | "light" | "dark";

type ThemeContextValue = {
  mode: ThemeMode;
  resolvedMode: "light" | "dark";
  setMode: (mode: ThemeMode) => void;
  toggleMode: () => void;
};

const storageKey = "repolens-theme";
const ThemeContext = createContext<ThemeContextValue | null>(null);

function getSystemMode() {
  if (typeof window === "undefined") {
    return "light";
  }

  return window.matchMedia("(prefers-color-scheme: dark)").matches ? "dark" : "light";
}

function getStoredMode(): ThemeMode {
  if (typeof window === "undefined") {
    return "system";
  }

  const stored = window.localStorage.getItem(storageKey);
  return stored === "light" || stored === "dark" || stored === "system"
    ? stored
    : "system";
}

export function ThemeProvider({ children }: { children: React.ReactNode }) {
  const [mode, setModeState] = useState<ThemeMode>("system");
  const [resolvedMode, setResolvedMode] = useState<"light" | "dark">("light");

  const applyMode = useCallback((nextMode: ThemeMode) => {
    const nextResolvedMode = nextMode === "system" ? getSystemMode() : nextMode;

    document.documentElement.dataset.theme = nextResolvedMode;
    document.documentElement.style.colorScheme = nextResolvedMode;
    setResolvedMode(nextResolvedMode);
  }, []);

  useEffect(() => {
    const storedMode = getStoredMode();
    setModeState(storedMode);
    applyMode(storedMode);
  }, [applyMode]);

  useEffect(() => {
    const media = window.matchMedia("(prefers-color-scheme: dark)");
    const handleChange = () => {
      if (mode === "system") {
        applyMode("system");
      }
    };

    media.addEventListener("change", handleChange);
    return () => media.removeEventListener("change", handleChange);
  }, [applyMode, mode]);

  const setMode = useCallback(
    (nextMode: ThemeMode) => {
      window.localStorage.setItem(storageKey, nextMode);
      setModeState(nextMode);
      applyMode(nextMode);
    },
    [applyMode],
  );

  const toggleMode = useCallback(() => {
    setMode(resolvedMode === "dark" ? "light" : "dark");
  }, [resolvedMode, setMode]);

  const value = useMemo(
    () => ({ mode, resolvedMode, setMode, toggleMode }),
    [mode, resolvedMode, setMode, toggleMode],
  );

  return <ThemeContext.Provider value={value}>{children}</ThemeContext.Provider>;
}

export function useTheme() {
  const context = useContext(ThemeContext);

  if (!context) {
    throw new Error("useTheme must be used within ThemeProvider");
  }

  return context;
}
