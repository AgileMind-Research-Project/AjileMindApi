import axios from 'axios';

const AI_SERVICE_URL = process.env.AI_SERVICE_URL || 'http://ai-engine:8000';

export const analyzeStandup = async (transcript, tenantId) => {
    try {
        const response = await axios.post(`${AI_SERVICE_URL}/analyze/standup`, {
            transcript,
            tenant_id: tenantId,
        }, { timeout: 10000 });
        return response.data;
    } catch (error) {
        console.error('AI Proxy Error:', error.message);
        throw new Error('Failed to process with AI engine');
    }
};