import { z } from 'zod';

export const ExecuteAgentRequest = z.object({
	agentId: z.string().min(1, 'agentId is required'),
	input: z.string().min(1, 'input is required'),
	params: z.record(z.any()).optional(),
});

export type ExecuteAgentRequestType = z.infer<typeof ExecuteAgentRequest>;


