"use client";

import { Avatar } from "@/components/ui/avatar";
import { Button } from "@/components/ui/button";

interface UserMenuProps {
  email?: string | null;
  fullName?: string | null;
  oauthProvider?: string | null;
  onLogout: () => void;
  picture?: string | null;
}

export function UserMenu({
  email,
  fullName,
  oauthProvider,
  onLogout,
  picture,
}: UserMenuProps) {
  const userName = fullName || "Guest User";
  const userInitials = userName
    .split(" ")
    .map((n) => n[0])
    .join("")
    .slice(0, 2)
    .toUpperCase();

  let userHue = 0;
  for (let i = 0; i < userName.length; i++) {
    userHue = userName.charCodeAt(i) + ((userHue << 5) - userHue);
  }
  const avatarHue = Math.abs(userHue % 360);

  const showPhoto = oauthProvider === "google" && Boolean(picture);

  return (
    <div className="border-t border-border/70 pt-4 mt-auto">
      <div className="flex items-center gap-3">
        <Avatar
          alt={userName}
          fallback={userInitials}
          hue={avatarHue}
          src={showPhoto ? picture : undefined}
        />
        <div className="min-w-0 flex-1">
          <p className="truncate text-xs font-semibold text-foreground">{userName}</p>
          <p className="truncate text-[10px] font-medium text-muted">{email || ""}</p>
        </div>
      </div>
      <Button
        className="mt-3 w-full justify-start text-xs font-medium text-muted hover:bg-danger/10 hover:text-danger"
        onClick={onLogout}
        size="sm"
        variant="ghost"
      >
        Logout
      </Button>
    </div>
  );
}
