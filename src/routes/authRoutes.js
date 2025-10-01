import { Router } from 'express';
import { login, logout, register } from '../controllers/authController.js';
import { tenantMiddleware } from '../middleware/tenant.js';

const router = Router();
router.post('/register', tenantMiddleware, register);
router.post('/login', tenantMiddleware, login);
router.post('/logout', logout);
export default router;