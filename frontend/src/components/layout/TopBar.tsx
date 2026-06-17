import { useState, type FormEvent } from "react";
import { LogOut, Play, Plus, Search, User } from "lucide-react";
import { Link, useNavigate } from "react-router-dom";
import { useQuery, useQueryClient } from "@tanstack/react-query";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { StatusBadge } from "@/components/common/StatusBadge";
import { authApi } from "@/api/authApi";

export function TopBar() {
  const navigate = useNavigate();
  const queryClient = useQueryClient();
  const [query, setQuery] = useState("");

  const { data: user } = useQuery({
    queryKey: ["auth-me"],
    queryFn: () => authApi.getMe(),
    staleTime: 5 * 60 * 1000,
  });

  function submitSearch(event: FormEvent) {
    event.preventDefault();
    const value = query.trim();
    if (!value) return;
    const upper = value.toUpperCase();
    if (upper.startsWith("SCAN_")) {
      navigate(`/scans?keyword=${encodeURIComponent(value)}`);
    } else if (upper.startsWith("BATCH_")) {
      navigate(`/tasks?batch_no=${encodeURIComponent(value)}`);
    } else if (upper.startsWith("RUN_")) {
      navigate(`/scans?keyword=${encodeURIComponent(value)}`);
    } else {
      navigate(`/monitors?keyword=${encodeURIComponent(value)}`);
    }
  }

  function handleLogout() {
    authApi.logout().finally(() => {
      queryClient.removeQueries({ queryKey: ["auth-me"] });
      navigate("/login", { replace: true });
    });
  }

  return (
    <header className="sticky top-0 z-30 border-b border-border bg-[#fffaf5]/85 backdrop-blur xl:ml-64">
      <div className="flex h-16 items-center justify-between gap-4 px-6">
        <form className="relative hidden min-w-80 max-w-md flex-1 md:block" onSubmit={submitSearch}>
          <Search className="absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-stone-400" />
          <Input value={query} onChange={(event) => setQuery(event.target.value)} placeholder="搜索路线、扫描、批次或任务" className="bg-white/80 pl-9" />
        </form>
        <div className="ml-auto flex items-center gap-2">
          <StatusBadge status="ENABLED" className="hidden md:inline-flex">Local Mode</StatusBadge>
          <span className="hidden rounded-full border border-border bg-white px-2.5 py-1 text-xs text-stone-600 md:inline-flex">SQLite</span>
          <span className="hidden rounded-full border border-border bg-white px-2.5 py-1 text-xs text-stone-600 md:inline-flex">Local Browser</span>
          {user && (
            <span className="hidden items-center gap-1.5 rounded-full border border-border bg-white px-2.5 py-1 text-xs text-stone-600 md:inline-flex">
              <User className="h-3 w-3" />
              {user.display_name || user.username}
            </span>
          )}
          <Button variant="ghost" size="sm" onClick={handleLogout} title="退出登录">
            <LogOut className="h-4 w-4" />
          </Button>
          <Button asChild variant="secondary"><Link to="/monitors/new"><Plus className="h-4 w-4" />新建关注路线</Link></Button>
          <Button asChild><Link to="/monitors"><Play className="h-4 w-4" />选择路线扫描</Link></Button>
        </div>
      </div>
    </header>
  );
}
