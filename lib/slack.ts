import crypto from 'crypto';

export function verifySlackSignature(opts: {
	signingSecret: string;
	timestamp: string | null;
	signature: string | null;
	rawBody: string;
}): boolean {
	const { signingSecret, timestamp, signature, rawBody } = opts;
	if (!timestamp || !signature) return false;
	// Replay attack window: 5 minutes
	const fiveMinutes = 60 * 5;
	const now = Math.floor(Date.now() / 1000);
	const ts = Number(timestamp);
	if (Number.isFinite(ts) && Math.abs(now - ts) > fiveMinutes) {
		return false;
	}
	const base = `v0:${timestamp}:${rawBody}`;
	const hmac = crypto.createHmac('sha256', signingSecret);
	hmac.update(base);
	const mySig = `v0=${hmac.digest('hex')}`;
	// constant-time compare
	return crypto.timingSafeEqual(Buffer.from(mySig), Buffer.from(signature));
}

export async function postToResponseUrl(responseUrl: string, payload: unknown) {
	const res = await fetch(responseUrl, {
		method: 'POST',
		headers: { 'Content-Type': 'application/json' },
		body: JSON.stringify(payload)
	});
	return res.ok;
}

export async function chatPostMessage(token: string, payload: {
	channel: string;
	text?: string;
	thread_ts?: string;
	blocks?: unknown[];
	mrkdwn?: boolean;
}) {
	const res = await fetch('https://slack.com/api/chat.postMessage', {
		method: 'POST',
		headers: {
			'Content-Type': 'application/json; charset=utf-8',
			Authorization: `Bearer ${token}`
		},
		body: JSON.stringify(payload)
	});
	const json = await res.json().catch(() => ({}));
	return { ok: res.ok, json };
}


