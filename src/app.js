import express from 'express';
import swaggerJsdoc from 'swagger-jsdoc';
import swaggerUi from 'swagger-ui-express';
import { setupSecurity } from './middleware/security.js';
import aiRoutes from './routes/aiRoutes.js';
import authRoutes from './routes/authRoutes.js';
import storyRoutes from './routes/storyRoutes.js';
import { swaggerOptions } from './swagger/swaggerOptions.js';
import logger from './utils/logger.js';

const app = express();
setupSecurity(app);

const specs = swaggerJsdoc(swaggerOptions);
app.use('/api-docs', swaggerUi.serve, swaggerUi.setup(specs));

app.use('/api/auth', authRoutes);
app.use('/api/stories', storyRoutes);
app.use('/api/ai', aiRoutes);

app.use((err, req, res, next) => {
    logger.error('Unhandled error:', err);
    res.status(500).json({ error: 'Something went wrong!' });
});

export default app;