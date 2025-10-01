/**
 * @swagger
 * tags:
 *   name: Authentication
 *   description: User registration, login, and logout
 */

import bcrypt from 'bcrypt';
import jwt from 'jsonwebtoken';
import redisClient from '../config/redis.js';
import User from '../models/User.js';
import logger from '../utils/logger.js';

const JWT_SECRET = process.env.JWT_SECRET || 'agilemind-saas-secret-2025';
const JWT_EXPIRES_IN = '15m';
const REFRESH_SECRET = process.env.REFRESH_SECRET || 'agilemind-refresh-secret';
const REFRESH_EXPIRES_IN = '7d';

/**
 * @swagger
 * /api/auth/register:
 *   post:
 *     summary: Register a new user in a tenant
 *     tags: [Authentication]
 *     security:
 *       - {}
 *     requestBody:
 *       required: true
 *       content:
 *         application/json:
 *           schema:
 *             type: object
 *             required:
 *               - email
 *               - password
 *             properties:
 *               email:
 *                 type: string
 *                 format: email
 *                 example: user@agilemind.com
 *               password:
 *                 type: string
 *                 minLength: 8
 *                 example: securePassword123!
 *     responses:
 *       201:
 *         description: User registered successfully
 *         content:
 *           application/json:
 *             schema:
 *               type: object
 *               properties:
 *                 message:
 *                   type: string
 *                 userId:
 *                   type: integer
 *       400:
 *         description: Email already exists or invalid input
 *       500:
 *         description: Internal server error
 */

export const register = async (req, res) => {
    try {
        const { email, password } = req.body;
        const { tenantId } = req;
        const saltRounds = 12;
        const passwordHash = await bcrypt.hash(password, saltRounds);
        const user = await User.create({ email, password_hash: passwordHash, tenant_id: tenantId });
        logger.info(`New user registered: ${email} in tenant ${tenantId}`);
        res.status(201).json({ message: 'User registered successfully', userId: user.id });
    } catch (err) {
        if (err.name === 'SequelizeUniqueConstraintError') {
            return res.status(400).json({ error: 'Email already exists' });
        }
        logger.error('Registration error:', err);
        res.status(500).json({ error: 'Internal server error' });
    }
};

/**
 * @swagger
 * /api/auth/login:
 *   post:
 *     summary: Login user and get JWT tokens
 *     tags: [Authentication]
 *     security:
 *       - {}
 *     requestBody:
 *       required: true
 *       content:
 *         application/json:
 *           schema:
 *             type: object
 *             required:
 *               - email
 *               - password
 *             properties:
 *               email:
 *                 type: string
 *                 format: email
 *                 example: user@agilemind.com
 *               password:
 *                 type: string
 *                 example: securePassword123!
 *     responses:
 *       200:
 *         description: Login successful
 *         content:
 *           application/json:
 *             schema:
 *               type: object
 *               properties:
 *                 accessToken:
 *                   type: string
 *                 user:
 *                   type: object
 *                   properties:
 *                     id:
 *                       type: integer
 *                     email:
 *                       type: string
 *       401:
 *         description: Invalid credentials
 *       500:
 *         description: Login failed
 */

export const login = async (req, res) => {
    try {
        const { email, password } = req.body;
        const { tenantId } = req;
        const user = await User.findOne({ where: { email, tenant_id: tenantId } });
        if (!user || !(await bcrypt.compare(password, user.password_hash))) {
            return res.status(401).json({ error: 'Invalid credentials' });
        }
        const accessToken = jwt.sign({ userId: user.id, tenantId }, JWT_SECRET, { expiresIn: JWT_EXPIRES_IN });
        const refreshToken = jwt.sign({ userId: user.id, tenantId }, REFRESH_SECRET, { expiresIn: REFRESH_EXPIRES_IN });
        res.cookie('refreshToken', refreshToken, {
            httpOnly: true,
            secure: process.env.NODE_ENV === 'production',
            sameSite: 'strict',
            maxAge: 7 * 24 * 60 * 60 * 1000,
        });
        res.json({ accessToken, user: { id: user.id, email: user.email } });
    } catch (err) {
        logger.error('Login error:', err);
        res.status(500).json({ error: 'Login failed' });
    }
};

/**
 * @swagger
 * /api/auth/logout:
 *   post:
 *     summary: Logout user and invalidate refresh token
 *     tags: [Authentication]
 *     security:
 *       - cookieAuth: []
 *     responses:
 *       200:
 *         description: Logged out successfully
 *         content:
 *           application/json:
 *             schema:
 *               type: object
 *               properties:
 *                 message:
 *                   type: string
 *                   example: Logged out successfully
 */

export const logout = async (req, res) => {
    const refreshToken = req.cookies.refreshToken;
    if (refreshToken) {
        await redisClient.setEx(`blacklist:${refreshToken}`, 7 * 24 * 60 * 60, 'true');
    }
    res.clearCookie('refreshToken');
    res.json({ message: 'Logged out successfully' });
};