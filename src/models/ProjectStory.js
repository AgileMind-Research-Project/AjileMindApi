import { DataTypes } from 'sequelize';
import db from '../config/db.js';

const ProjectStory = db.define('project_story', {
    id: {
        type: DataTypes.INTEGER,
        primaryKey: true,
        autoIncrement: true,
    },
    tenant_id: {
        type: DataTypes.UUID,
        allowNull: false,
    },
    title: {
        type: DataTypes.STRING(200),
        allowNull: false,
    },
    description: {
        type: DataTypes.TEXT,
        allowNull: true,
    },
    status: {
        type: DataTypes.ENUM('todo', 'in-progress', 'done'),
        defaultValue: 'todo',
    },
});

export default ProjectStory;