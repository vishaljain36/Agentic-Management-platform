import { PrismaClient } from "@prisma/client";

const prisma = new PrismaClient();

async function main() {
  console.log("🔍 Verifying database connection and schema tables...");

  const user = await prisma.user.create({
    data: {
      email: `admin-${Date.now()}@agentic.ai`,
      name: "Super Admin",
      role: "SUPER_ADMIN"
    }
  });
  console.log("✅ Created User:", user.id, user.email, user.role);

  const workspace = await prisma.workspace.create({
    data: {
      name: "Default Enterprise Workspace",
      slug: `enterprise-${Date.now()}`,
      plan: "enterprise",
      credits: 500000
    }
  });
  console.log("✅ Created Workspace:", workspace.id, workspace.slug);

  const member = await prisma.workspaceMember.create({
    data: {
      userId: user.id,
      workspaceId: workspace.id,
      role: "SUPER_ADMIN"
    }
  });
  console.log("✅ Created WorkspaceMember link:", member.id);

  const agent = await prisma.agent.create({
    data: {
      workspaceId: workspace.id,
      name: "Researcher Agent",
      description: "Autonomous research and analysis agent",
      systemPrompt: "You are an expert researcher agent.",
      modelProvider: "openai",
      modelName: "gpt-4o",
      tools: ["web_search", "document_retrieval"]
    }
  });
  console.log("✅ Created Agent:", agent.id, agent.name);

  const run = await prisma.agentRun.create({
    data: {
      workspaceId: workspace.id,
      prompt: "Analyze Q3 revenue",
      status: "COMPLETED",
      totalTokens: 1250,
      costUsd: 0.015
    }
  });
  console.log("✅ Created AgentRun:", run.id, run.status, run.costUsd);

  // Clean up test data
  await prisma.agentRun.delete({ where: { id: run.id } });
  await prisma.agent.delete({ where: { id: agent.id } });
  await prisma.workspaceMember.delete({ where: { id: member.id } });
  await prisma.workspace.delete({ where: { id: workspace.id } });
  await prisma.user.delete({ where: { id: user.id } });

  console.log("🎉 ALL PHASE 1 DATABASE AND PRISMA CHECKS PASSED WITH 100% SUCCESS!");
}

main()
  .catch((e) => {
    console.error("❌ Verification failed:", e);
    process.exit(1);
  })
  .finally(async () => {
    await prisma.$disconnect();
  });

