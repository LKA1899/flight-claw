import * as TabsPrimitive from "@radix-ui/react-tabs";
import { cn } from "@/lib/utils";

export const Tabs = TabsPrimitive.Root;
export const TabsList = ({ className, ...props }: React.ComponentPropsWithoutRef<typeof TabsPrimitive.List>) => <TabsPrimitive.List className={cn("inline-flex rounded-full bg-muted p-1", className)} {...props} />;
export const TabsTrigger = ({ className, ...props }: React.ComponentPropsWithoutRef<typeof TabsPrimitive.Trigger>) => <TabsPrimitive.Trigger className={cn("rounded-full px-4 py-2 text-sm data-[state=active]:bg-white data-[state=active]:shadow-sm", className)} {...props} />;
export const TabsContent = TabsPrimitive.Content;
