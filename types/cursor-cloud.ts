export type CursorAgentSuccess = {
	ok: true;
	data: unknown;
	[key: string]: unknown;
};

export type CursorAgentError = {
	ok: false;
	error: string | Record<string, unknown>;
	status?: number;
	[key: string]: unknown;
};

export type CursorAgentResponse = CursorAgentSuccess | CursorAgentError;


