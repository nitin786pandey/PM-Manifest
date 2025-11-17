import { NextRequest } from 'next/server';
import { verifySlackSignature, postToResponseUrl } from '../../../../lib/slack';
import { executeAgent } from '../../../../lib/cursorCloud';

export const runtime = 'nodejs';

function parseSlashText(text: string): { agentId: string; input: string } | null {
	// Expected: agentId=<id> input="your prompt here"
	// Fallback: first token agentId, rest is input
	const idMatch = text.match(/(?:^|\s)agentId=([^\s]+)(?:\s|$)/);
	const inputMatch = text.match(/input=(?:"([^"]+)"|(.+))/);
	if (idMatch && inputMatch) {
		const agentId = idMatch[1];
		const input = (inputMatch[1] || inputMatch[2] || '').trim();
		return agentId && input ? { agentId, input } : null;
	}
	const [first, ...rest] = text.trim().split(/\s+/);
	if (first && rest.length) {
		return { agentId: first, input: rest.join(' ') };
	}
	return null;
}

export async function POST(req: NextRequest) {
	// Always return 200 with valid Slack response format, even on errors
	// Slack requires 200 status within 3 seconds, otherwise shows "dispatch_failed"
	const errorResponse = (text: string) => {
		return new Response(
			JSON.stringify({
				response_type: 'ephemeral',
				text
			}),
			{ status: 200, headers: { 'Content-Type': 'application/json' } }
		);
	};

	try {
		const signingSecret = process.env.SLACK_SIGNING_SECRET;
		if (!signingSecret) {
			return errorResponse('Error: SLACK_SIGNING_SECRET not configured. Please check Vercel environment variables.');
		}

		// Slack sends x-www-form-urlencoded
		const rawBody = await req.text();
		const timestamp = req.headers.get('x-slack-request-timestamp');
		const signature = req.headers.get('x-slack-signature');
		
		const verified = verifySlackSignature({
			signingSecret,
			timestamp,
			signature,
			rawBody
		});
		
		if (!verified) {
			return errorResponse('Error: Signature verification failed. Please check SLACK_SIGNING_SECRET matches your Slack app settings.');
		}

		const form = new URLSearchParams(rawBody);
		const text = form.get('text') ?? '';
		const response_url = form.get('response_url');
		const user_name = form.get('user_name') ?? 'user';
		
		if (!response_url) {
			return errorResponse('Error: Missing response_url from Slack. This may be a Slack configuration issue.');
		}

		const parsed = parseSlashText(text);
		if (!parsed) {
			return errorResponse('Usage: /elastic agentId=<id> input="your prompt" or /elastic <id> your prompt');
		}

		// Acknowledge quickly (within 3 seconds)
		const ack = {
			response_type: 'ephemeral',
			text: `Got it, ${user_name}. Running agent ${parsed.agentId}...`
		};

		// Fire and forget background task
		(async () => {
			try {
				const upstream = await executeAgent({
					agentId: parsed.agentId,
					input: parsed.input
				});
				
				if (!upstream.ok) {
					const errorText = await upstream.text().catch(() => 'Unknown error');
					await postToResponseUrl(response_url, {
						response_type: 'ephemeral',
						text: `Agent execution failed (${upstream.status}): ${errorText}`
					});
					return;
				}
				
				const contentType = upstream.headers.get('content-type') ?? 'application/json';
				let message = '';
				if (contentType.includes('application/json')) {
					const data = await upstream.json().catch(() => ({}));
					message = '```json\n' + JSON.stringify(data, null, 2) + '\n```';
				} else {
					message = await upstream.text();
				}
				
				await postToResponseUrl(response_url, {
					response_type: 'in_channel',
					text: message
				});
			} catch (e) {
				const errorMsg = e instanceof Error ? e.message : String(e);
				await postToResponseUrl(response_url, {
					response_type: 'ephemeral',
					text: `Agent execution failed: ${errorMsg}`
				});
			}
		})().catch(() => {});

		return new Response(JSON.stringify(ack), {
			status: 200,
			headers: { 'Content-Type': 'application/json' }
		});
	} catch (e) {
		// Catch any unexpected errors
		const errorMsg = e instanceof Error ? e.message : String(e);
		return errorResponse(`Unexpected error: ${errorMsg}`);
	}
}


