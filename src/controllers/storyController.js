import ProjectStory from '../models/ProjectStory.js';
import logger from '../utils/logger.js';

export const createStory = async (req, res) => {
    try {
        const { title, description, status = 'todo' } = req.body;
        const story = await ProjectStory.create({ title, description, status, tenant_id: req.tenantId });
        res.status(201).json(story);
    } catch (err) {
        logger.error('Create story error:', err);
        res.status(500).json({ error: 'Failed to create story' });
    }
};

export const getAllStories = async (req, res) => {
    try {
        const stories = await ProjectStory.findAll({
            where: { tenant_id: req.tenantId },
            attributes: ['id', 'title', 'description', 'status', 'created_at', 'updated_at'],
        });
        res.json(stories);
    } catch (err) {
        logger.error('Fetch stories error:', err);
        res.status(500).json({ error: 'Failed to fetch stories' });
    }
};

export const updateStory = async (req, res) => {
    try {
        const { id } = req.params;
        const { title, description, status } = req.body;
        const story = await ProjectStory.findOne({ where: { id, tenant_id: req.tenantId } });
        if (!story) return res.status(404).json({ error: 'Story not found' });
        await story.update({ title, description, status });
        res.json(story);
    } catch (err) {
        logger.error('Update story error:', err);
        res.status(500).json({ error: 'Failed to update story' });
    }
};

export const deleteStory = async (req, res) => {
    try {
        const { id } = req.params;
        const result = await ProjectStory.destroy({ where: { id, tenant_id: req.tenantId } });
        if (result === 0) return res.status(404).json({ error: 'Story not found' });
        res.json({ message: 'Story deleted successfully' });
    } catch (err) {
        logger.error('Delete story error:', err);
        res.status(500).json({ error: 'Failed to delete story' });
    }
};