import * as DropdownMenuPrimitive from "@radix-ui/react-dropdown-menu";
import { cn } from "@/lib/utils";

export const DropdownMenu = DropdownMenuPrimitive.Root;
export const DropdownMenuTrigger = DropdownMenuPrimitive.Trigger;
export const DropdownMenuContent = ({ className, ...props }: React.ComponentPropsWithoutRef<typeof DropdownMenuPrimitive.Content>) => (
  <DropdownMenuPrimitive.Portal>
    <DropdownMenuPrimitive.Content className={cn("z-50 min-w-40 rounded-xl border border-border bg-white p-1 shadow-soft", className)} sideOffset={8} {...props} />
  </DropdownMenuPrimitive.Portal>
);
export const DropdownMenuItem = ({ className, ...props }: React.ComponentPropsWithoutRef<typeof DropdownMenuPrimitive.Item>) => <DropdownMenuPrimitive.Item className={cn("cursor-pointer rounded-lg px-3 py-2 text-sm outline-none hover:bg-muted", className)} {...props} />;
