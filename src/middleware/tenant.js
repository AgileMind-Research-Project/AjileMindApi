export const tenantMiddleware = (req, res, next) => {
    const tenantId = req.headers['x-tenant-id'];
    const uuidRegex = /^[0-9a-f]{8}-[0-9a-f]{4}-[0-5][0-9a-f]{3}-[089ab][0-9a-f]{3}-[0-9a-f]{12}$/i;

    if (!tenantId || !uuidRegex.test(tenantId)) {
        return res.status(400).json({ error: 'Valid X-Tenant-ID (UUID) required' });
    }
    req.tenantId = tenantId;
    next();
};