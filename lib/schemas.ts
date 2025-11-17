import { z } from 'zod';

export const ExecuteAgentRequest = z.object({
	agentId: z.string().min(1, 'agentId is required'),
	input: z.string().min(1, 'input is required'),
	params: z.record(z.any()).optional(),
	context: z.object({
		storeName: z.string().optional(),
		storeId: z.string().optional(),
	}).optional(),
});

export type ExecuteAgentRequestType = z.infer<typeof ExecuteAgentRequest>;


