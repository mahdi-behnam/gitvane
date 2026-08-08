"use client";

import * as ToastPrimitive from "@radix-ui/react-toast";
import { createContext, useCallback, useContext, useMemo, useState } from "react";
import { cn } from "@/lib/utils";

export type ToastVariant = "default" | "success" | "destructive" | "warning" | "info";

export type ToastMessage = {
  description?: string;
  id: string;
  title: string;
  variant?: ToastVariant;
};

type ToastContextValue = {
  notify: (message: Omit<ToastMessage, "id">) => void;
};

const ToastContext = createContext<ToastContextValue | null>(null);

export function ToastProvider({ children }: { children: React.ReactNode }) {
  const [messages, setMessages] = useState<ToastMessage[]>([]);

  const notify = useCallback((message: Omit<ToastMessage, "id">) => {
    setMessages((current) => [
      ...current,
      { ...message, id: window.crypto.randomUUID() },
    ]);
  }, []);

  const value = useMemo(() => ({ notify }), [notify]);

  return (
    <ToastContext.Provider value={value}>
      <ToastPrimitive.Provider swipeDirection="right">
        {children}
        {messages.map((message) => (
          <ToastPrimitive.Root
            className={cn(
              "rounded-lg border p-4 text-sm text-foreground shadow-lg transition-all",
              "data-[state=open]:animate-in data-[state=closed]:animate-out",
              message.variant === "destructive" && "border-danger/40 bg-panel border-l-4 border-l-danger",
              message.variant === "success" && "border-success/40 bg-panel border-l-4 border-l-success",
              message.variant === "warning" && "border-warning/40 bg-panel border-l-4 border-l-warning",
              message.variant === "info" && "border-primary/40 bg-panel border-l-4 border-l-primary",
              (!message.variant || message.variant === "default") && "border-border bg-panel"
            )}
            key={message.id}
            onOpenChange={(open) => {
              if (!open) {
                setMessages((current) =>
                  current.filter((item) => item.id !== message.id),
                );
              }
            }}
          >
            <ToastPrimitive.Title className="font-medium">
              {message.title}
            </ToastPrimitive.Title>
            {message.description ? (
              <ToastPrimitive.Description className="mt-1 text-muted">
                {message.description}
              </ToastPrimitive.Description>
            ) : null}
          </ToastPrimitive.Root>
        ))}
        <ToastPrimitive.Viewport className="fixed bottom-4 right-4 z-50 flex w-[min(360px,calc(100vw-32px))] flex-col gap-2 outline-none" />
      </ToastPrimitive.Provider>
    </ToastContext.Provider>
  );
}

const fallbackToastContext: ToastContextValue = {
  notify: (message: Omit<ToastMessage, "id">) => {
    console.warn("useToast notify called outside of ToastProvider:", message);
  },
};

export function useToast() {
  const context = useContext(ToastContext);

  if (!context) {
    return fallbackToastContext;
  }

  return context;
}
