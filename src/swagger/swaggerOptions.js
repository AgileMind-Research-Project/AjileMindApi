export const swaggerOptions = {
    definition: {
        openapi: '3.0.0',
        info: {
            title: 'AgileMind API',
            version: '1.0.0',
            description: 'AI-powered Agile Project Management Platform - Multi-tenant SaaS',
        },
        servers: [{ url: process.env.API_BASE_URL || 'http://localhost:5000' }],
        components: {
            securitySchemes: {
                bearerAuth: { type: 'http', scheme: 'bearer', bearerFormat: 'JWT' },
                cookieAuth: { type: 'apiKey', in: 'cookie', name: 'refreshToken' },
            },
        },
        security: [{ bearerAuth: [] }],
    },
    apis: ['./src/routes/*.js', './src/controllers/*.js'],
};