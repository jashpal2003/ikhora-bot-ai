/**
 * Microsoft Teams Channel Adapter using M365 Agents SDK (ADR 010)
 * Translates Teams activities into Relay MessageEnvelope and forwards to relay-gateway.
 */

import http from "http";

const PORT = process.env.PORT || 3978;
const GATEWAY_URL = process.env.GATEWAY_URL || "http://localhost:8001/webhooks/teams";

const server = http.createServer(async (req, res) => {
  if (req.method === "POST" && req.url === "/api/messages") {
    let body = "";
    req.on("data", chunk => { body += chunk; });
    req.on("end", async () => {
      try {
        const activity = JSON.parse(body);
        console.log(`[TeamsAdapter] Ingested message from Entra OID: ${activity.from?.id}`);

        // Forward normalized activity to Relay Channel Gateway
        await fetch(GATEWAY_URL, {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify(activity),
        });

        res.writeHead(200, { "Content-Type": "application/json" });
        res.end(JSON.stringify({ status: "forwarded" }));
      } catch (err) {
        console.error("[TeamsAdapter] Processing error:", err);
        res.writeHead(500);
        res.end();
      }
    });
  } else {
    res.writeHead(404);
    res.end();
  }
});

server.listen(PORT, () => {
  console.log(`[TeamsAdapter] Running on port ${PORT}`);
});
