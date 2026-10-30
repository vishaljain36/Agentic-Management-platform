import { PGlite } from "@electric-sql/pglite";
import { createServer } from "pglite-server";
import path from "node:path";
import fs from "node:fs";

const dataDir = path.resolve(process.cwd(), ".pgdata");
if (!fs.existsSync(dataDir)) {
  fs.mkdirSync(dataDir, { recursive: true });
}

const db = new PGlite(dataDir);
await db.waitReady;

const PORT = 5432;
const server = createServer(db);

server.listen(PORT, "127.0.0.1", () => {
  console.log(`[PGlite Server] Postgres listening on 127.0.0.1:${PORT}`);
});

process.on("SIGINT", () => {
  server.close();
  process.exit(0);
});

process.on("SIGTERM", () => {
  server.close();
  process.exit(0);
});

