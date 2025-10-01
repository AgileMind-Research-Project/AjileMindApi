import { Router } from 'express';
import { processStandup } from '../controllers/aiController.js';
import { authenticateToken } from '../middleware/auth.js';
import { tenantMiddleware } from '../middleware/tenant.js';

const router = Router();
router.use(authenticateToken, tenantMiddleware);
router.post('/standup', processStandup);
export default router;