import { Activity, Home, Plane, Radar, Repeat2, Route, SearchCheck, Settings, Sparkles, Table2 } from "lucide-react";
import { NavLink } from "react-router-dom";
import { cn } from "@/lib/utils";

const items = [
  { to: "/results", label: "扫描结果", icon: SearchCheck },
  { to: "/overview", label: "今日雷达", icon: Home },
  { to: "/monitors", label: "关注路线", icon: Route },
  { to: "/scans", label: "扫描记录", icon: Activity },
  { to: "/tasks", label: "查询任务", icon: Radar },
  { to: "/prices", label: "价格快照", icon: Table2 },
  { to: "/round-trips", label: "往返结果", icon: Repeat2 },
  { to: "/plans", label: "候选方案", icon: Plane },
  { to: "/best", label: "今日机会", icon: Sparkles },
  { to: "/settings", label: "设置", icon: Settings },
];

export function SidebarNav() {
  return (
    <aside className="fixed inset-y-0 left-0 hidden w-64 border-r border-border bg-[#fffaf5]/90 backdrop-blur xl:block">
      <div className="flex h-16 items-center gap-3 px-6">
        <div className="flex h-10 w-10 items-center justify-center rounded-xl bg-coral text-white">
          <Plane className="h-5 w-5" />
        </div>
        <div>
          <div className="text-base font-semibold text-ink">FlightScan</div>
          <div className="text-xs text-stone-500">Personal Flight Scanner</div>
        </div>
      </div>
      <nav className="space-y-1 px-3 py-5">
        {items.map((item) => (
          <NavLink
            key={item.to}
            to={item.to}
            className={({ isActive }) =>
              cn(
                "flex items-center gap-3 rounded-xl px-3 py-2.5 text-sm text-stone-600 transition hover:bg-muted hover:text-ink",
                isActive && "bg-white text-ink shadow-sm",
              )
            }
          >
            <item.icon className="h-4 w-4" />
            {item.label}
          </NavLink>
        ))}
      </nav>
    </aside>
  );
}
