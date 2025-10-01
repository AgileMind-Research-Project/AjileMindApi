import { DataTypes } from 'sequelize';
import db from '../config/db.js';

const User = db.define('user', {
    id: {
        type: DataTypes.INTEGER,
        primaryKey: true,
        autoIncrement: true,
    },
    tenant_id: {
        type: DataTypes.UUID,
        allowNull: false,
    },
    email: {
        type: DataTypes.STRING(100),
        allowNull: false,
        unique: true,
        validate: { isEmail: true },
    },
    password_hash: {
        type: DataTypes.STRING(100),
        allowNull: false,
    },
});

export default User;