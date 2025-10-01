import { Sequelize } from 'sequelize';

const db = new Sequelize(
    process.env.DB_NAME || 'agilemind_saas',
    process.env.DB_USER || 'root',
    process.env.DB_PASSWORD || 'admin',
    {
        host: process.env.DB_HOST || 'localhost',
        port: parseInt(process.env.DB_PORT, 10) || 3307,
        dialect: 'mysql',
        logging: false,
        define: {
            underscored: true,
            timestamps: true,
        },
        pool: {
            max: 20,
            min: 5,
            acquire: 30000,
            idle: 10000,
        },
    },
);

export default db;