import { useState, useEffect, useCallback, type FormEvent } from "react";
import { useNavigate, useSearchParams } from "react-router-dom";
import { useMutation } from "@tanstack/react-query";
import { Plane, RefreshCw } from "lucide-react";
import { toast } from "sonner";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { authApi, setToken, type CaptchaData } from "@/api/authApi";

export function LoginPage() {
  const navigate = useNavigate();
  const [searchParams] = useSearchParams();
  const redirect = searchParams.get("redirect") || "/overview";

  const [username, setUsername] = useState("");
  const [password, setPassword] = useState("");
  const [captchaCode, setCaptchaCode] = useState("");
  const [captcha, setCaptcha] = useState<CaptchaData | null>(null);

  const loadCaptcha = useCallback(async () => {
    try {
      const data = await authApi.getCaptcha();
      setCaptcha(data);
      setCaptchaCode("");
    } catch {
      toast.error("加载验证码失败");
    }
  }, []);

  // Load captcha on mount
  useEffect(() => {
    loadCaptcha();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  const loginMutation = useMutation({
    mutationFn: () =>
      authApi.login({
        username: username.trim(),
        password,
        captcha_id: captcha?.captcha_id || "",
        captcha_code: captchaCode,
      }),
    onSuccess: (data) => {
      setToken(data.access_token);
      toast.success("登录成功");
      navigate(redirect, { replace: true });
    },
    onError: (err: Error) => {
      toast.error(err.message || "登录失败");
      loadCaptcha();
    },
  });

  function handleSubmit(e: FormEvent) {
    e.preventDefault();
    if (!username || !password || !captchaCode) {
      toast.error("请填写完整信息");
      return;
    }
    if (!captcha) {
      toast.error("请等待验证码加载");
      return;
    }
    loginMutation.mutate();
  }

  const loading = loginMutation.isPending;

  return (
    <div className="flex min-h-screen items-center justify-center bg-[#fbf8f4] px-4">
      <div className="w-full max-w-md">
        {/* Brand */}
        <div className="mb-8 text-center">
          <div className="mb-3 flex items-center justify-center gap-2">
            <div className="flex h-10 w-10 items-center justify-center rounded-xl bg-[#ea580c] text-white">
              <Plane className="h-5 w-5" />
            </div>
            <h1 className="text-2xl font-bold tracking-tight text-stone-800">FlightScan</h1>
          </div>
          <p className="text-sm text-stone-500">Personal Flight Scanner</p>
        </div>

        <Card className="border-stone-200 shadow-sm">
          <CardHeader>
            <CardTitle className="text-lg">登录</CardTitle>
            <p className="text-sm text-stone-500">登录后管理关注路线、扫描任务和旅行报告。</p>
          </CardHeader>
          <CardContent>
            <form onSubmit={handleSubmit} className="space-y-4">
              <div>
                <label className="mb-1.5 block text-sm font-medium text-stone-700">用户名</label>
                <Input
                  autoComplete="username"
                  value={username}
                  onChange={(e) => setUsername(e.target.value)}
                  placeholder="请输入用户名"
                  disabled={loading}
                />
              </div>

              <div>
                <label className="mb-1.5 block text-sm font-medium text-stone-700">密码</label>
                <Input
                  type="password"
                  autoComplete="current-password"
                  value={password}
                  onChange={(e) => setPassword(e.target.value)}
                  placeholder="请输入密码"
                  disabled={loading}
                />
              </div>

              <div>
                <label className="mb-1.5 block text-sm font-medium text-stone-700">验证码</label>
                <div className="flex gap-3">
                  <Input
                    value={captchaCode}
                    onChange={(e) => setCaptchaCode(e.target.value.toUpperCase())}
                    placeholder="验证码"
                    className="w-28"
                    maxLength={4}
                    disabled={loading}
                  />
                  {captcha ? (
                    <button
                      type="button"
                      onClick={loadCaptcha}
                      className="flex items-center gap-1 shrink-0"
                      disabled={loading}
                    >
                      <img
                        src={captcha.image_base64}
                        alt="验证码"
                        className="h-10 rounded border border-stone-200 cursor-pointer"
                        onClick={loadCaptcha}
                      />
                      <RefreshCw className="h-4 w-4 text-stone-400 hover:text-stone-600" />
                    </button>
                  ) : (
                    <div className="flex h-10 w-[120px] items-center justify-center rounded border border-stone-200 text-xs text-stone-400">
                      加载中...
                    </div>
                  )}
                </div>
                <p className="mt-1 text-xs text-stone-400">点击图片或刷新图标刷新验证码</p>
              </div>

              <Button
                type="submit"
                className="w-full bg-[#ea580c] hover:bg-[#c2410c]"
                disabled={loading}
              >
                {loading ? "登录中..." : "登录"}
              </Button>
            </form>
          </CardContent>
        </Card>

        <p className="mt-6 text-center text-xs text-stone-400">
          登录后即可管理航线监控和扫描任务
        </p>
      </div>
    </div>
  );
}
