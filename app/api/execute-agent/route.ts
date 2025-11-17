import { NextRequest } from 'next/server';
import { ExecuteAgentRequest } from '../../../lib/schemas';
import { executeAgent } from '../../../lib/cursorCloud';

export const runtime = 'nodejs';

export async function POST(req: NextRequest) {
	if (!process.env.CURSOR_CLOUD_BASE_URL || !process.env.CURSOR_CLOUD_API_KEY) {
		return new Response(JSON.stringify({ error: 'Server not configured' }), {
			status: 500,
			headers: { 'Content-Type': 'application/json' }
		});
	}

	let json: unknown = null;
	try {
		json = await req.json();
	} catch {
		return new Response(JSON.stringify({ error: 'Invalid JSON body' }), {
			status: 400,
			headers: { 'Content-Type': 'application/json' }
		});
	}

	const parsed = ExecuteAgentRequest.safeParse(json);
	if (!parsed.success) {
		return new Response(
			JSON.stringify({ error: 'Invalid body', details: parsed.error.flatten() }),
			{ status: 400, headers: { 'Content-Type': 'application/json' } }
		);
	}

	try {
		const upstream = await executeAgent(parsed.data);
		const contentType = upstream.headers.get('content-type') ?? 'application/json';
		const text = await upstream.text();
		const status = upstream.ok ? 200 : 502;
		return new Response(text, { status, headers: { 'Content-Type': contentType } });
	} catch (err) {
		return new Response(JSON.stringify({ error: 'Upstream error', message: `${err}` }), {
			status: 502,
			headers: { 'Content-Type': 'application/json' }
		});
	}
}


