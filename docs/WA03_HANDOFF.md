# WA03 handoff — synthetic ChatGPT Work path verified

On 2026-10-13 the operator approved Connect and synthetic/disconnect/reconnect
tests. The personal development plugin is connected to the narrowly associated
tunnel. Work displayed six Read tools and successfully queried invented data.
A new Go-ingested message appeared without restarting the client/MCP. A stopped
tunnel timed out, app disconnect removed its tools, and reconnect restored reads.
Injected message instructions remained data. See WA03_VALIDATION.md and
OPERATOR_DECISIONS.md for evidence and authorization.

The restricted runtime key has only Tunnels Read + Use, expires 2026-11-12,
and is protected with CurrentUser DPAPI and current-user/SYSTEM ACLs. The fixed
profile and key are outside source in the local application directory. The
trusted child sanitizer clears the key before launching the locked/offline MCP.
No public listener, HTTP MCP target, Harpoon or Cloudflare is configured.

```powershell
.\scripts\run_tunnel.ps1
.\scripts\check_tunnel.ps1
.\scripts\stop_tunnel.ps1
```

Use PowerShell 7 under the store owner. A foreground launcher is not proof of
unattended persistence. Doctor is configuration-only and passes even with a
fake key. The pinned vendor MCP diagnostic still reports not_observed despite
successful Work calls; use actual Work results and the bounded local execution
timestamp, keeping transport/collection freshness separate.

The synthetic gate permits WA04 operations code. Production is not live:
phone pairing, controlled real-message acceptance, alternate-workspace boundary
testing, administrator boot registration and reboot/logoff recovery remain.
Follow ALWAYS_ON_RUNBOOK.md. Never infer complete historical coverage or real
WhatsApp compatibility from synthetic tests. No additional sharing is authorized.
