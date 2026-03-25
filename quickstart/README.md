# Quick Start Installer Assets

This folder contains the installer templates for the public one-line installation flow.

## Files
- `install.sh` for macOS/Linux
- `install.ps1` for Windows PowerShell

These committed files are templates and intentionally contain the placeholder `__LICENSE_SERVER_ADMIN_TOKEN__`.

## Hosted Installer Flow
Before publishing the installers on the marketing website, render them with the shared billing token:

```bash
QUICKSTART_LICENSE_SERVER_ADMIN_TOKEN='<shared-token>' bash scripts/render-quickstart-installers.sh
```

That creates:
- `dist/hosted-installers/install.sh`
- `dist/hosted-installers/install.ps1`

Host those rendered files at:
- `https://knowledgebaseai.de/knowledgebase-ai/install.sh`
- `https://knowledgebaseai.de/knowledgebase-ai/install.ps1`

## Website Commands
Use these commands on the marketing website:

```bash
curl -fsSL https://knowledgebaseai.de/knowledgebase-ai/install.sh | bash
```

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -Command "irm https://knowledgebaseai.de/knowledgebase-ai/install.ps1 | iex"
```

## Release Requirements
The one-line installers expect the latest GitHub release to publish these assets:
- `knowledgebase-ai.tar.gz`
- `knowledgebase-ai.zip`

They also assume the GitHub repository `Tim-M-83/knowledgebase-ai` is public.

## Workspace Restore Behavior
- The installer now generates a stable `LICENSE_WORKSPACE_ID` and writes it into the installed `.env`.
- It also prints the Workspace ID at the end of the install.
- Keep that value if you ever reinstall and want to reuse the same purchased Polar license.
- Reinstalling with a different or empty `LICENSE_WORKSPACE_ID` creates a new workspace identity, so an old Polar key will no longer match.
