import { analyzeStandup } from '../services/aiProxy.js';

export const processStandup = async (req, res) => {
    try {
        const { transcript } = req.body;
        const result = await analyzeStandup(transcript, req.tenantId);
        res.json(result);
    } catch (err) {
        res.status(500).json({ error: err.message });
    }
};