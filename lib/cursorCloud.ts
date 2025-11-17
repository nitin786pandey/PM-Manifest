export type ExecuteAgentContext = {
	storeName?: string;
	storeId?: string;
};

export type ExecuteAgentArgs = {
	agentId: string;
	input: string;
	params?: Record<string, unknown>;
	context?: ExecuteAgentContext;
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
	
	// Build request body with input, params, and context
	const body: Record<string, unknown> = {
		input: args.input,
	};
	
	if (args.params) {
		body.params = args.params;
	}
	
	// Include context in the request body (agent can use this for store name resolution)
	if (args.context) {
		body.context = args.context;
	}
	
	return fetch(url, {
		method: 'POST',
		headers: {
			Authorization: `Bearer ${apiKey}`,
			'Content-Type': 'application/json'
		},
		body: JSON.stringify(body),
		cache: 'no-store'
	});
}


