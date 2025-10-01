import { Router } from 'express';
import { createStory, deleteStory, getAllStories, updateStory } from '../controllers/storyController.js';
import { authenticateToken } from '../middleware/auth.js';
import { tenantMiddleware } from '../middleware/tenant.js';

const router = Router();
router.use(authenticateToken, tenantMiddleware);
router.post('/', createStory);
router.get('/', getAllStories);
router.put('/:id', updateStory);
router.delete('/:id', deleteStory);
export default router;