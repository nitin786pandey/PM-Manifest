export type ExecuteAgentArgs = {
	agentId: string;
	input: string;
	params?: Record<string, unknown>;
};

function getBaseUrl(): string {
	const base = process.env.CURSOR_CLOUD_BASE_URL;
	if (!base) {
		throw new Error('Missing CURSOR_CLOUD_BASE_URL');
	}
	return base.replace(/\/$/, '');
}

function getApiKey(): string {
	const key = process.env.CURSOR_CLOUD_API_KEY;
	if (!key) {
		throw new Error('Missing CURSOR_CLOUD_API_KEY');
	}
	return key;
}

export async function executeAgent(args: ExecuteAgentArgs): Promise<Response> {
	const base = getBaseUrl();
	const apiKey = getApiKey();
	const url = `${base}/agents/${encodeURIComponent(args.agentId)}/execute`;
	return fetch(url, {
		method: 'POST',
		headers: {
			Authorization: `Bearer ${apiKey}`,
			'Content-Type': 'application/json'
		},
		body: JSON.stringify({ input: args.input, params: args.params ?? undefined }),
		cache: 'no-store'
	});
}


