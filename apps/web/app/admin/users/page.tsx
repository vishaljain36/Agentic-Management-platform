"use client";

import React, { useState } from "react";
import { GlassCard } from "@/components/ui/glass-card";
import { Button } from "@/components/ui/button";
import {
  Users,
  Search,
  Shield,
  Key,
  Plus,
  Trash2,
  CheckCircle2,
  Sliders,
  DollarSign,
} from "lucide-react";

interface UserRow {
  id: string;
  name: string;
  email: string;
  role: "SUPER_ADMIN" | "WORKSPACE_ADMIN" | "MEMBER" | "VIEWER";
  workspace: string;
  creditsRemaining: number;
  creditsMax: number;
  apiKeysActive: number;
  status: "active" | "suspended";
}

export default function UserManagementPage() {
  const [searchTerm, setSearchTerm] = useState("");
  const [users, setUsers] = useState<UserRow[]>([
    {
      id: "usr-001",
      name: "Alex Vance",
      email: "alex@void.io",
      role: "SUPER_ADMIN",
      workspace: "Global Void Core",
      creditsRemaining: 980_000,
      creditsMax: 1_000_000,
      apiKeysActive: 3,
      status: "active",
    },
    {
      id: "usr-002",
      name: "Devon Miles",
      email: "devon@quantum-ai.net",
      role: "WORKSPACE_ADMIN",
      workspace: "Quantum Labs",
      creditsRemaining: 412_500,
      creditsMax: 500_000,
      apiKeysActive: 2,
      status: "active",
    },
    {
      id: "usr-003",
      name: "Elena Rostova",
      email: "elena@apexfin.com",
      role: "WORKSPACE_ADMIN",
      workspace: "Apex Finance Workspace",
      creditsRemaining: 48_100,
      creditsMax: 500_000,
      apiKeysActive: 1,
      status: "active",
    },
    {
      id: "usr-004",
      name: "Marcus Brody",
      email: "marcus@brody-robotics.org",
      role: "MEMBER",
      workspace: "Robotics Core",
      creditsRemaining: 2_100,
      creditsMax: 100_000,
      apiKeysActive: 1,
      status: "suspended",
    },
    {
      id: "usr-005",
      name: "Sarah Chen",
      email: "sarah@cyberdyne.co",
      role: "MEMBER",
      workspace: "Cyberdyne Systems",
      creditsRemaining: 890_200,
      creditsMax: 2_500_000,
      apiKeysActive: 4,
      status: "active",
    },
  ]);

  const toggleStatus = (id: string) => {
    setUsers((prev) =>
      prev.map((u) =>
        u.id === id
          ? { ...u, status: u.status === "active" ? "suspended" : "active" }
          : u
      )
    );
  };

  const addCredits = (id: string, amount: number) => {
    setUsers((prev) =>
      prev.map((u) =>
        u.id === id ? { ...u, creditsRemaining: u.creditsRemaining + amount } : u
      )
    );
  };

  const filteredUsers = users.filter(
    (u) =>
      u.name.toLowerCase().includes(searchTerm.toLowerCase()) ||
      u.email.toLowerCase().includes(searchTerm.toLowerCase()) ||
      u.workspace.toLowerCase().includes(searchTerm.toLowerCase())
  );

  return (
    <div className="space-y-8">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold tracking-tight text-white flex items-center gap-2">
            User Directory & Quota Administration
          </h1>
          <p className="text-sm text-zinc-400 mt-1">
            Tenant membership roles, token quotas, and cryptographic API key revocation
          </p>
        </div>

        <Button variant="primary" size="sm" className="gap-1.5 text-xs font-mono">
          <Plus size={14} />
          <span>Provision Tenant</span>
        </Button>
      </div>

      {/* Filter and Search Bar */}
      <div className="flex items-center gap-4">
        <div className="relative flex-1">
          <Search size={16} className="absolute left-3.5 top-1/2 -translate-y-1/2 text-zinc-500" />
          <input
            type="text"
            placeholder="Search users by name, email, or workspace..."
            value={searchTerm}
            onChange={(e) => setSearchTerm(e.target.value)}
            className="w-full bg-[#111827]/70 border border-white/10 rounded-lg pl-10 pr-4 py-2 text-sm text-white placeholder-zinc-500 focus:outline-none focus:border-[#8B5CF6]/50 font-sans"
          />
        </div>
      </div>

      {/* User Table */}
      <GlassCard className="p-0 overflow-hidden">
        <div className="overflow-x-auto">
          <table className="w-full text-left text-sm">
            <thead>
              <tr className="border-b border-white/10 bg-white/[0.02] text-xs font-mono uppercase text-zinc-400">
                <th className="py-3 px-4 font-medium">User / Email</th>
                <th className="py-3 px-4 font-medium">Role</th>
                <th className="py-3 px-4 font-medium">Workspace</th>
                <th className="py-3 px-4 font-medium">Token Credits</th>
                <th className="py-3 px-4 font-medium">Keys</th>
                <th className="py-3 px-4 font-medium">Status</th>
                <th className="py-3 px-4 font-medium text-right">Actions</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-white/5 font-mono text-xs">
              {filteredUsers.map((u) => {
                const creditPct = Math.min(100, (u.creditsRemaining / u.creditsMax) * 100);
                return (
                  <tr key={u.id} className="hover:bg-white/[0.02] transition-colors">
                    {/* User */}
                    <td className="py-3.5 px-4 font-sans">
                      <div className="font-medium text-white">{u.name}</div>
                      <div className="text-zinc-500 text-xs font-mono">{u.email}</div>
                    </td>

                    {/* Role */}
                    <td className="py-3.5 px-4">
                      <span
                        className={`inline-flex items-center gap-1 px-2 py-0.5 rounded text-[10px] font-mono font-medium ${
                          u.role === "SUPER_ADMIN"
                            ? "bg-red-500/20 text-red-300 border border-red-500/30"
                            : u.role === "WORKSPACE_ADMIN"
                            ? "bg-[#8B5CF6]/20 text-[#8B5CF6] border border-[#8B5CF6]/30"
                            : "bg-white/5 text-zinc-400 border border-white/10"
                        }`}
                      >
                        <Shield size={10} />
                        {u.role}
                      </span>
                    </td>

                    {/* Workspace */}
                    <td className="py-3.5 px-4 font-sans text-zinc-300">{u.workspace}</td>

                    {/* Credits */}
                    <td className="py-3.5 px-4">
                      <div className="flex justify-between text-[11px] text-zinc-400 mb-1">
                        <span>{u.creditsRemaining.toLocaleString()}</span>
                        <span>/ {u.creditsMax.toLocaleString()}</span>
                      </div>
                      <div className="w-28 bg-white/10 rounded-full h-1.5 overflow-hidden">
                        <div
                          className={`h-full rounded-full ${
                            creditPct < 15
                              ? "bg-red-500"
                              : creditPct < 40
                              ? "bg-amber-400"
                              : "bg-[#06B6D4]"
                          }`}
                          style={{ width: `${creditPct}%` }}
                        />
                      </div>
                    </td>

                    {/* API Keys */}
                    <td className="py-3.5 px-4">
                      <span className="flex items-center gap-1 text-zinc-400">
                        <Key size={12} className="text-[#8B5CF6]" />
                        {u.apiKeysActive} active
                      </span>
                    </td>

                    {/* Status */}
                    <td className="py-3.5 px-4">
                      <span
                        className={`inline-block px-2 py-0.5 rounded text-[10px] font-mono ${
                          u.status === "active"
                            ? "bg-emerald-500/10 text-emerald-400 border border-emerald-500/20"
                            : "bg-red-500/10 text-red-400 border border-red-500/20"
                        }`}
                      >
                        {u.status.toUpperCase()}
                      </span>
                    </td>

                    {/* Actions */}
                    <td className="py-3.5 px-4 text-right">
                      <div className="inline-flex items-center gap-1.5">
                        <Button
                          onClick={() => addCredits(u.id, 100_000)}
                          variant="ghost"
                          size="sm"
                          className="text-[11px] py-0.5 px-2 text-[#06B6D4] hover:bg-[#06B6D4]/10"
                        >
                          +100k
                        </Button>
                        <Button
                          onClick={() => toggleStatus(u.id)}
                          variant={u.status === "active" ? "danger" : "ghost"}
                          size="sm"
                          className="text-[11px] py-0.5 px-2"
                        >
                          {u.status === "active" ? "Suspend" : "Activate"}
                        </Button>
                      </div>
                    </td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        </div>
      </GlassCard>
    </div>
  );
}

