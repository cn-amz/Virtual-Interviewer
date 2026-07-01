import { useState } from "react";
import { login, type UserPublic } from "../api/client";

type LoginPageProps = {
  onLogin: (user: UserPublic) => void;
};

export function LoginPage({ onLogin }: LoginPageProps) {
  const [username, setUsername] = useState("demo");
  const [password, setPassword] = useState("demo123456");
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(false);

  async function handleSubmit(event: React.FormEvent) {
    event.preventDefault();
    setError("");
    setLoading(true);
    try {
      const result = await login(username, password);
      onLogin(result.user);
    } catch (err) {
      setError(err instanceof Error ? err.message : "登录失败");
    } finally {
      setLoading(false);
    }
  }

  return (
    <section className="panel login-panel">
      <p className="eyebrow">Virtual Interviewer</p>
      <h1>登录</h1>
      <p>使用演示账号进入第二阶段工作台。</p>
      <form className="login-form" onSubmit={handleSubmit}>
        <label>
          <span>用户名</span>
          <input
            type="text"
            value={username}
            onChange={(event) => setUsername(event.target.value)}
            autoComplete="username"
          />
        </label>
        <label>
          <span>密码</span>
          <input
            type="password"
            value={password}
            onChange={(event) => setPassword(event.target.value)}
            autoComplete="current-password"
          />
        </label>
        {error && <p className="login-error">{error}</p>}
        <button className="primary-button" type="submit" disabled={loading}>
          {loading ? "登录中..." : "登录"}
        </button>
      </form>
    </section>
  );
}
