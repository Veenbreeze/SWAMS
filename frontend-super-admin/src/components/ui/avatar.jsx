import * as React from "react"

import { cn } from "@/lib/utils"

function initialsFor(name) {
  return (name ?? "")
    .trim()
    .split(/\s+/)
    .filter(Boolean)
    .slice(0, 2)
    .map((part) => part[0]?.toUpperCase())
    .join("");
}

function Avatar({ src, name, className, ...props }) {
  const [failed, setFailed] = React.useState(false);

  if (src && !failed) {
    return (
      <img
        data-slot="avatar"
        src={src}
        alt={name ?? ""}
        onError={() => setFailed(true)}
        className={cn("size-8 shrink-0 rounded-full object-cover", className)}
        {...props}
      />
    );
  }

  return (
    <span
      data-slot="avatar"
      className={cn(
        "flex size-8 shrink-0 items-center justify-center rounded-full bg-muted text-xs font-medium text-muted-foreground",
        className
      )}
      {...props}
    >
      {initialsFor(name) || "—"}
    </span>
  );
}

export { Avatar }
