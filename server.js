import app from './src/app.js';
import db from './src/config/db.js';
import logger from './src/utils/logger.js';

const PORT = process.env.PORT || 5000;

db.authenticate()
    .then(() => {
        logger.info('✅ Connected to MySQL database');
        app.listen(PORT, () => {
            logger.info(`🚀 Server running on port ${PORT}`);
            logger.info(`📘 Swagger docs: http://localhost:${PORT}/api-docs`);
        });
    })
    .catch((err) => {
        logger.error('❌ Unable to connect to database:', err);
        process.exit(1);
    });