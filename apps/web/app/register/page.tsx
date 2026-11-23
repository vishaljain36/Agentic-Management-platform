"use client";

import React, { useState, Suspense } from "react";
import Link from "next/link";
import { useRouter, useSearchParams } from "next/navigation";
import {
  Layers,
  Lock,
  Mail,
  User,
  Building,
  ArrowRight,
  Shield,
  Zap,
  AlertCircle,
  Loader2,
} from "lucide-react";

function RegisterForm() {
  const router = useRouter();
  const searchParams = useSearchParams();
  const callbackUrl = searchParams.get("callbackUrl") || "/workspace/default/canvas";

  const [name, setName] = useState("");
  const [org, setOrg] = useState("");
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const applyAuthCookieAndRedirect = (token: string) => {
    document.cookie = `session_token=${token}; path=/; max-age=86400; SameSite=Lax`;
    if (typeof window !== "undefined") {
      try {
        localStorage.setItem("session_token", token);
      } catch {
        // ignore storage errors
      }
    }
    router.push(callbackUrl);
  };

  const handleDevBypass = () => {
    setLoading(true);
    setTimeout(() => {
      applyAuthCookieAndRedirect("jwt_mock_valid_999");
    }, 150);
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!email || !password) {
      setError("Please provide an email and password.");
      return;
    }

    setLoading(true);
    setError(null);

    try {
      // Simulate account provisioning and immediately set session token
      await new Promise((resolve) => setTimeout(resolve, 300));
      applyAuthCookieAndRedirect("jwt_mock_valid_999");
    } catch {
      applyAuthCookieAndRedirect("jwt_mock_valid_999");
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="relative z-10 w-full max-w-md rounded-2xl border border-white/10 bg-[#0B0F19]/85 p-8 shadow-2xl backdrop-blur-cyber">
      {/* Brand Header */}
      <div className="text-center">
        <div className="inline-flex h-12 w-12 items-center justify-center rounded-2xl bg-gradient-to-tr from-[#8B5CF6] to-[#06B6D4] shadow-neon-violet mb-4">
          <Layers className="h-6 w-6 text-white" />
        </div>
        <h1 className="text-2xl font-bold tracking-tight text-white">
          Create Workspace Account
        </h1>
        <p className="mt-2 text-xs text-zinc-400">
          Provision your tenant space on the Cyber-Glass agent network
        </p>
      </div>

      {/* Dev Bypass Option */}
      <div className="mt-5 rounded-xl border border-[#8B5CF6]/40 bg-[#8B5CF6]/10 p-3 text-center">
        <button
          type="button"
          onClick={handleDevBypass}
          disabled={loading}
          data-testid="register-dev-bypass-btn"
          className="w-full flex items-center justify-center gap-2 rounded-lg bg-[#8B5CF6] px-3.5 py-2 text-xs font-semibold text-white shadow-neon-violet hover:bg-[#7C3AED] transition-all disabled:opacity-50"
        >
          <Zap className="h-4 w-4" />
          ⚡ Quick Dev Bypass (Auto Provision)
        </button>
      </div>

      {/* Divider */}
      <div className="my-5 flex items-center gap-3">
        <div className="h-[1px] flex-1 bg-white/10" />
        <span className="text-[10px] uppercase tracking-wider text-zinc-500 font-mono">
          Registration Details
        </span>
        <div className="h-[1px] flex-1 bg-white/10" />
      </div>

      {/* Error Alert */}
      {error && (
        <div className="mb-4 flex items-center gap-2 rounded-lg border border-red-500/30 bg-red-500/10 p-3 text-xs text-red-400">
          <AlertCircle className="h-4 w-4 shrink-0" />
          <span>{error}</span>
        </div>
      )}

      {/* Form */}
      <form onSubmit={handleSubmit} className="space-y-3.5">
        <div>
          <label className="block text-xs font-medium text-zinc-300 mb-1">
            Full Name
          </label>
          <div className="relative">
            <User className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-zinc-500" />
            <input
              type="text"
              value={name}
              onChange={(e) => setName(e.target.value)}
              placeholder="Dr. Jordan Hayes"
              className="w-full rounded-xl border border-white/10 bg-black/50 pl-10 pr-4 py-2 text-sm text-zinc-100 placeholder:text-zinc-600 focus:border-[#8B5CF6] focus:outline-none focus:ring-1 focus:ring-[#8B5CF6] transition-all"
            />
          </div>
        </div>

        <div>
          <label className="block text-xs font-medium text-zinc-300 mb-1">
            Organization / Tenant
          </label>
          <div className="relative">
            <Building className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-zinc-500" />
            <input
              type="text"
              value={org}
              onChange={(e) => setOrg(e.target.value)}
              placeholder="Acme Autonomous Corp"
              className="w-full rounded-xl border border-white/10 bg-black/50 pl-10 pr-4 py-2 text-sm text-zinc-100 placeholder:text-zinc-600 focus:border-[#8B5CF6] focus:outline-none focus:ring-1 focus:ring-[#8B5CF6] transition-all"
            />
          </div>
        </div>

        <div>
          <label className="block text-xs font-medium text-zinc-300 mb-1">
            Work Email
          </label>
          <div className="relative">
            <Mail className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-zinc-500" />
            <input
              type="email"
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              placeholder="jordan@acme.ai"
              required
              className="w-full rounded-xl border border-white/10 bg-black/50 pl-10 pr-4 py-2 text-sm text-zinc-100 placeholder:text-zinc-600 focus:border-[#8B5CF6] focus:outline-none focus:ring-1 focus:ring-[#8B5CF6] transition-all"
            />
          </div>
        </div>

        <div>
          <label className="block text-xs font-medium text-zinc-300 mb-1">
            Master Password
          </label>
          <div className="relative">
            <Lock className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-zinc-500" />
            <input
              type="password"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              placeholder="••••••••••••"
              required
              className="w-full rounded-xl border border-white/10 bg-black/50 pl-10 pr-4 py-2 text-sm text-zinc-100 placeholder:text-zinc-600 focus:border-[#8B5CF6] focus:outline-none focus:ring-1 focus:ring-[#8B5CF6] transition-all"
            />
          </div>
        </div>

        <button
          type="submit"
          disabled={loading}
          data-testid="submit-register-btn"
          className="mt-2 w-full flex items-center justify-center gap-2 rounded-xl bg-gradient-to-r from-[#8B5CF6] to-[#06B6D4] px-4 py-2.5 text-sm font-semibold text-white shadow-neon-violet hover:opacity-90 active:scale-[0.99] transition-all disabled:opacity-50"
        >
          {loading ? (
            <Loader2 className="h-4 w-4 animate-spin text-white" />
          ) : (
            <>
              Create Enterprise Account
              <ArrowRight className="h-4 w-4" />
            </>
          )}
        </button>
      </form>

      {/* Footer Links */}
      <div className="mt-6 flex items-center justify-between text-xs text-zinc-400 pt-4 border-t border-white/5">
        <Link
          href="/login"
          className="hover:text-zinc-200 text-[#8B5CF6] transition-colors"
        >
          Already have an account? Sign In
        </Link>
        <Link href="/" className="hover:text-zinc-200 transition-colors">
          ← Back to Home
        </Link>
      </div>
    </div>
  );
}

export default function RegisterPage() {
  return (
    <div className="relative min-h-screen bg-void flex items-center justify-center p-4 overflow-hidden">
      {/* Background cyber glow spheres */}
      <div className="absolute top-1/3 left-1/4 -translate-x-1/2 -translate-y-1/2 w-[500px] h-[500px] bg-[#8B5CF6]/15 rounded-full blur-[140px] pointer-events-none" />
      <div className="absolute bottom-1/3 right-1/4 w-[400px] h-[400px] bg-[#06B6D4]/15 rounded-full blur-[120px] pointer-events-none" />

      <Suspense
        fallback={
          <div className="rounded-2xl border border-white/10 bg-[#0B0F19]/80 p-8 text-center text-zinc-400 backdrop-blur-cyber">
            <Loader2 className="h-6 w-6 animate-spin mx-auto text-[#8B5CF6] mb-2" />
            <span>Loading Registration Portal...</span>
          </div>
        }
      >
        <RegisterForm />
      </Suspense>
    </div>
  );
}

