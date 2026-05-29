import { Outlet } from "react-router-dom";
import { SidebarNav } from "@/components/layout/SidebarNav";
import { TopBar } from "@/components/layout/TopBar";

export function AppLayout() {
  return (
    <div className="min-h-screen bg-background">
      <SidebarNav />
      <TopBar />
      <main className="px-5 py-6 xl:pl-[17rem]">
        <div className="mx-auto max-w-screen-2xl">
          <Outlet />
        </div>
      </main>
    </div>
  );
}
