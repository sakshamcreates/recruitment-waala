import type { ComponentProps } from "react";
import { cn } from "@/lib/utils";

export const buttonStyle = {
  primary: "button button-primary",
  secondary: "button button-secondary",
  quiet: "button button-quiet",
} as const;

export function Button({
  className,
  variant = "primary",
  ...props
}: ComponentProps<"button"> & { variant?: keyof typeof buttonStyle }) {
  return <button className={cn(buttonStyle[variant], className)} {...props} />;
}

// Adapted from the shadcn/ui Card registry component.
export function Card({ className, ...props }: ComponentProps<"div">) {
  return (
    <div data-slot="card" className={cn("surface", className)} {...props} />
  );
}

export function Input({ className, ...props }: ComponentProps<"input">) {
  return <input className={cn("field", className)} {...props} />;
}

export function PageContainer({ className, ...props }: ComponentProps<"div">) {
  return <div className={cn("page-container", className)} {...props} />;
}
