# Start Python Backend Service

## Quick Start Guide for AgileMind Backend

---

## Prerequisites

Before starting the backend service, ensure you have:

1. **Python 3.9+** installed
   ```bash
   python --version
   ```

2. **MySQL Server** running
   - Default port: 3306
   - Database: `agile_mind_db`

3. **Environment Variables** configured (`.env` file)

---

## Step-by-Step Instructions

### 1. Navigate to Backend Directory

```powershell
# Windows PowerShell
cd f:/research/Research_Final/agile-mind-backend

# Or using cmd
cd f:\research\Research_Final\agile-mind-backend
```

```bash
# Linux/Mac
cd /path/to/Research_Final/agile-mind-backend
```

---

### 2. Create Virtual Environment (First Time Only)

```powershell
# Windows
python -m venv venv
```

```bash
# Linux/Mac
python3 -m venv venv
```

---

### 3. Activate Virtual Environment

```powershell
# Windows PowerShell
.\venv\Scripts\Activate.ps1

# Windows CMD
.\venv\Scripts\activate.bat
```

```bash
# Linux/Mac
source venv/bin/activate
```

**You should see `(venv)` prefix in your terminal**

---

### 4. Install Dependencies (First Time Only)

```bash
pip install -r requirements.txt
```

**Or install manually:**
```bash
pip install fastapi uvicorn python-dotenv pymysql bcrypt pyjwt python-multipart email-validator
```

---

### 5. Configure Environment Variables

Create or update `.env` file in the backend directory:

```env
# Database Configuration
DB_HOST=localhost
DB_PORT=3306
DB_USER=root
DB_PASSWORD=your_mysql_password
DB_NAME=agile_mind_db

# JWT Configuration
JWT_SECRET_KEY=your-super-secret-jwt-key-change-in-production
JWT_ALGORITHM=HS256
ACCESS_TOKEN_EXPIRE_MINUTES=1440
REFRESH_TOKEN_EXPIRE_DAYS=30

# Email Configuration (Optional for now)
SMTP_HOST=smtp.gmail.com
SMTP_PORT=587
SMTP_USERNAME=your-email@gmail.com
SMTP_PASSWORD=your-app-password
SMTP_FROM_EMAIL=noreply@agilemind.com
SMTP_FROM_NAME=AgileMind Platform

# Application Configuration
API_V1_PREFIX=/api/v1
BACKEND_CORS_ORIGINS=["http://localhost:3008","http://localhost:3000"]
PROJECT_NAME=AgileMind API
DEBUG=True
```

---

### 6. Setup Database (First Time Only)

```bash
# Login to MySQL
mysql -u root -p

# Run the schema
mysql -u root -p agile_mind_db < database_schema.sql
```

**Or run from MySQL command line:**
```sql
SOURCE database_schema.sql;
```

---

### 7. Start the Server

```bash
python main.py
```

**Server will start on:**
- **API**: http://localhost:5000
- **API Docs**: http://localhost:5000/api/docs
- **ReDoc**: http://localhost:5000/api/redoc

---

## Development Mode Commands

### Start with Auto-Reload
```bash
uvicorn main:app --reload --host 0.0.0.0 --port 5000
```

### Start with Specific Port
```bash
python main.py --port 5001
```

### Start in Debug Mode
```bash
DEBUG=True python main.py
```

---

## Troubleshooting

### Issue 1: Virtual Environment Not Activating

**Windows PowerShell Execution Policy Error:**
```powershell
Set-ExecutionPolicy -ExecutionPolicy RemoteSigned -Scope CurrentUser
```

### Issue 2: Module Not Found

```bash
# Ensure venv is activated, then:
pip install -r requirements.txt --force-reinstall
```

### Issue 3: Database Connection Error

**Check MySQL is running:**
```bash
# Windows
net start MySQL80

# Linux/Mac
sudo systemctl start mysql
```

**Verify credentials in `.env` file**

### Issue 4: Port Already in Use

```bash
# Kill process on port 5000 (Windows)
netstat -ano | findstr :5000
taskkill /PID <PID> /F

# Kill process on port 5000 (Linux/Mac)
lsof -ti:5000 | xargs kill -9
```

### Issue 5: Import Errors

```bash
# Reinstall dependencies
pip uninstall -r requirements.txt -y
pip install -r requirements.txt
```

---

## Stopping the Server

### In Terminal (Running Server)
- Press `Ctrl + C`

### Force Kill (If Frozen)
```bash
# Windows
taskkill /F /IM python.exe

# Linux/Mac
pkill -9 python
```

---

## Testing the Server

### 1. Health Check
```bash
curl http://localhost:5000/health
```

**Expected Response:**
```json
{
  "status": "healthy",
  "database": "connected",
  "timestamp": "2025-11-11T00:00:00Z"
}
```

### 2. API Status
```bash
curl http://localhost:5000/api/v1/status
```

### 3. Open API Docs
Visit: http://localhost:5000/api/docs

---

## Production Deployment

### Using Gunicorn (Linux)
```bash
pip install gunicorn
gunicorn main:app -w 4 -k uvicorn.workers.UvicornWorker -b 0.0.0.0:5000
```

### Using Docker
```bash
docker build -t agilemind-backend .
docker run -d -p 5000:5000 --env-file .env agilemind-backend
```

---

## Useful Commands

### Check Python Version
```bash
python --version
```

### List Installed Packages
```bash
pip list
```

### Update All Packages
```bash
pip install --upgrade pip
pip list --outdated
```

### Deactivate Virtual Environment
```bash
deactivate
```

### View Server Logs
```bash
# Logs are printed to console by default
# For production, redirect to file:
python main.py > logs/server.log 2>&1
```

---

## Directory Structure

```
agile-mind-backend/
├── app/
│   ├── api/
│   │   └── v1/           # API endpoints
│   ├── core/             # Core configuration
│   ├── db/               # Database connections
│   ├── middleware/       # Custom middleware
│   ├── schemas/          # Pydantic models
│   ├── services/         # Business logic
│   └── utils/            # Helper functions
├── venv/                 # Virtual environment (not in git)
├── .env                  # Environment variables (not in git)
├── .env.example          # Example environment file
├── main.py               # Application entry point
├── requirements.txt      # Python dependencies
└── database_schema.sql   # Database schema
```

---

## Environment Variables Reference

| Variable | Description | Default | Required |
|----------|-------------|---------|----------|
| `DB_HOST` | MySQL host address | localhost | Yes |
| `DB_PORT` | MySQL port | 3306 | Yes |
| `DB_USER` | MySQL username | root | Yes |
| `DB_PASSWORD` | MySQL password | - | Yes |
| `DB_NAME` | Database name | agile_mind_db | Yes |
| `JWT_SECRET_KEY` | Secret key for JWT | - | Yes |
| `JWT_ALGORITHM` | JWT algorithm | HS256 | No |
| `ACCESS_TOKEN_EXPIRE_MINUTES` | Token expiry | 1440 | No |
| `DEBUG` | Debug mode | False | No |

---

## Development Workflow

1. **Start Backend Server** (Port 5000)
   ```bash
   python main.py
   ```

2. **Start Frontend Server** (Port 3008)
   ```bash
   cd ../agile-mind-frontend
   npm run dev
   ```

3. **Open Browser**
   - Frontend: http://localhost:3008
   - Backend API Docs: http://localhost:5000/api/docs

---

## Additional Resources

- **FastAPI Documentation**: https://fastapi.tiangolo.com/
- **Uvicorn Documentation**: https://www.uvicorn.org/
- **Python Virtual Environments**: https://docs.python.org/3/tutorial/venv.html
- **MySQL Documentation**: https://dev.mysql.com/doc/

---

## Support

If you encounter issues:
1. Check this guide's troubleshooting section
2. Review server logs in the terminal
3. Verify `.env` configuration
4. Ensure MySQL is running
5. Check firewall/port settings

---

**Last Updated:** November 11, 2025  
**Python Version:** 3.9+  
**FastAPI Version:** 0.104+
