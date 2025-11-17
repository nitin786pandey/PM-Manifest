# Execute Cursor Cloud Agent via Vercel (Next.js App Router)

## Overview

This adds:
- `/api/execute-agent` — serverless route that proxies to `${CURSOR_CLOUD_BASE_URL}/agents/{agentId}/execute`
- `/api/slack/execute-agent` — Slack slash-command handler that runs the agent and posts results back to Slack

## Environment Variables

- `CURSOR_CLOUD_BASE_URL` — e.g. `https://api.cursor.sh`
- `CURSOR_CLOUD_API_KEY` — Bearer token to call Cursor Cloud
- `SLACK_SIGNING_SECRET` — Slack app signing secret (for slash command verification)
- `SLACK_BOT_TOKEN` — optional, only if you later use `chat.postMessage`

## API: POST /api/execute-agent

Request body:
```json
{
  "agentId": "agent_123",
  "input": "Summarize this text...",
  "params": {
    "temperature": 0.2
  }
}
```

Example curl:
```bash
curl -X POST https://<your-vercel-domain>/api/execute-agent \
  -H 'Content-Type: application/json' \
  -d '{"agentId":"agent_123","input":"Summarize: ...","params": {"temperature": 0.2}}'
```

Responses:
- `200` on success (body mirrors upstream result)
- `400` validation error
- `502` upstream error
- `500` misconfiguration

## Slack Slash Command: POST /api/slack/execute-agent

Configure a Slack Slash Command (e.g., `/cursor`) to POST to:
```
https://<your-vercel-domain>/api/slack/execute-agent
```

Command text formats supported:
- `agentId=<id> input="your prompt here"`
- `<id> your prompt here`

Flow:
1. Verifies Slack signature with `SLACK_SIGNING_SECRET`
2. ACKs within 3s (ephemeral message)
3. Executes the agent
4. Posts result to the `response_url` (visible in channel)

Note: If you prefer threading and richer formatting, swap `response_url` for `chat.postMessage` using `SLACK_BOT_TOKEN`.

## Slack App Setup (Step-by-Step)

### Step 1: Create a Slack App

1. Go to https://api.slack.com/apps
2. Click **"Create New App"**
3. Choose **"From scratch"**
4. Enter:
   - **App Name**: `Cursor Agent` (or your preferred name)
   - **Pick a workspace**: Select your workspace
5. Click **"Create App"**

### Step 2: Configure Slash Command

1. In the left sidebar, click **"Slash Commands"**
2. Click **"Create New Command"**
3. Fill in:
   - **Command**: `/cursor` (or your preferred command name)
   - **Request URL**: `https://<your-vercel-domain>/api/slack/execute-agent`
     - Replace `<your-vercel-domain>` with your actual Vercel domain (e.g., `your-app.vercel.app`)
   - **Short Description**: `Execute Cursor Cloud Agent`
   - **Usage Hint**: `agentId=<id> input="your prompt"` or `<id> your prompt`
4. Click **"Save"**

### Step 3: Get Your Signing Secret

1. In the left sidebar, click **"Basic Information"**
2. Scroll down to **"App Credentials"**
3. Find **"Signing Secret"**
4. Click **"Show"** and copy the value (starts with something like `a1b2c3d4e5f6...`)
5. **Save this** - you'll need it for Vercel environment variables

### Step 4: Install App to Your Workspace

1. In the left sidebar, click **"Install App"** (or **"Install to Workspace"**)
2. Review the permissions (you'll see it needs to post messages)
3. Click **"Allow"**
4. You'll see a confirmation page with a **Bot User OAuth Token** (starts with `xoxb-...`)
   - **Note**: You don't need this token for the current implementation, but save it if you want to use `chat.postMessage` later

### Step 5: Add App to a Channel

1. Open Slack and go to any channel where you want to use the command
2. Type `/invite @Cursor Agent` (or whatever you named your app)
3. Or click the channel name → **"Integrations"** → **"Add apps"** → Find your app → **"Add"**

### Step 6: Configure Vercel Environment Variables

1. Go to your Vercel project dashboard
2. Navigate to **Settings** → **Environment Variables**
3. Add these variables:

   | Variable Name | Value | Notes |
   |--------------|-------|-------|
   | `CURSOR_CLOUD_BASE_URL` | `https://api.cursor.sh` | Your Cursor Cloud API base URL |
   | `CURSOR_CLOUD_API_KEY` | `your-api-key` | Your Cursor Cloud API key |
   | `SLACK_SIGNING_SECRET` | `a1b2c3d4...` | The signing secret from Step 3 |

4. Make sure to select the environment (Production, Preview, Development) for each variable
5. Click **"Save"**

### Step 7: Deploy to Vercel

If you haven't deployed yet:

```bash
vercel build && vercel deploy
```

Or if using Git integration, push your changes and Vercel will auto-deploy.

### Step 8: Get Your Cursor Cloud Agent ID

You need your Cursor Cloud Agent ID to use in the slash command. Here's how to find it:

**Option 1: From Cursor Cloud Dashboard (if available)**
1. Log into your Cursor Cloud account
2. Navigate to your Agents/Cloud Agents section
3. Find the agent you want to use
4. The agent ID is typically displayed in the agent details, URL, or settings
   - Format might be: `agent_123`, `ag_abc123`, or a UUID

**Option 2: Via Cursor Cloud API**
If you have API access, you can list your agents:
```bash
curl -X GET https://api.cursor.sh/agents \
  -H "Authorization: Bearer YOUR_CURSOR_CLOUD_API_KEY"
```

**Option 3: Check Agent URL**
- If you access agents via a web interface, the agent ID is often in the URL
- Example: `https://cursor.sh/agents/agent_123` → agent ID is `agent_123`

**Note:** The exact format and location may vary depending on your Cursor Cloud setup. If you're unsure, check your Cursor Cloud documentation or contact support.

### Step 9: Test the Slash Command

1. Go to any Slack channel where you added the app
2. Type: `/cursor agentId=your_agent_id input="Test prompt"`
   - Or shorter: `/cursor your_agent_id Test prompt`
   - Example: `/cursor agentId=agent_abc123 input="Summarize the latest sales data"`
   - Or: `/cursor agent_abc123 Summarize the latest sales data`
3. You should see:
   - An immediate ephemeral message: "Got it, [your name]. Running agent [agentId]..."
   - Then the agent result posted to the channel

### Troubleshooting

**"dispatch_failed" error:**
This means Slack couldn't reach your endpoint or it didn't respond correctly. Check:
1. **URL is correct**: Verify the Request URL in Slack app settings matches: `https://your-app.vercel.app/api/slack/execute-agent`
2. **Endpoint is accessible**: Test with curl:
   ```bash
   curl -X POST https://your-app.vercel.app/api/slack/execute-agent \
     -H 'Content-Type: application/x-www-form-urlencoded' \
     -d 'text=test'
   ```
   Should return JSON (even if it's an error message)
3. **Environment variables**: Ensure `SLACK_SIGNING_SECRET` is set in Vercel and matches your Slack app
4. **Deployment**: Make sure you've deployed the latest code to Vercel
5. **Response time**: The endpoint must respond within 3 seconds with a 200 status code
6. **Check Vercel logs**: Go to Vercel dashboard → Your project → Functions → View logs for errors

**Command not found:**
- Make sure you installed the app to your workspace (Step 4)
- Make sure you added the app to the channel (Step 5)

**Signature verification failed:**
- Double-check `SLACK_SIGNING_SECRET` in Vercel matches the one from Slack
- Make sure you saved and redeployed after adding the env var
- The error message should now appear in Slack (not as dispatch_failed)

**Request URL not working:**
- Verify your Vercel deployment is live
- Check the URL format: `https://your-app.vercel.app/api/slack/execute-agent`
- Test with `curl` first: `curl -X POST https://your-app.vercel.app/api/slack/execute-agent`

**Agent execution fails:**
- Check `CURSOR_CLOUD_BASE_URL` and `CURSOR_CLOUD_API_KEY` are correct
- Verify the agent ID exists in your Cursor Cloud account
- Check Vercel function logs for detailed errors

## Deployment (Vercel)

1. In Vercel Project Settings → Environment Variables, add:
   - `CURSOR_CLOUD_BASE_URL`
   - `CURSOR_CLOUD_API_KEY`
   - `SLACK_SIGNING_SECRET` (and `SLACK_BOT_TOKEN` if needed)
2. Deploy via Git integration or:
   ```bash
   vercel build && vercel deploy
   ```
3. Test:
   - `curl` the `/api/execute-agent` route
   - Run the Slack slash command in your workspace


