"""
Configuration Test & Connection Monitor
Tests database, SMTP, and other service connections at startup
"""

import pymysql
import smtplib
from email.mime.text import MIMEText
from datetime import datetime
import sys
from pathlib import Path

# Add app directory to path
sys.path.insert(0, str(Path(__file__).parent))

from app.core.config import settings


class ConfigTester:
    """Test and validate configuration settings"""
    
    def __init__(self):
        self.results = {
            "database": {"status": "untested", "message": ""},
            "smtp": {"status": "untested", "message": ""},
            "config": {"status": "untested", "message": ""}
        }
    
    def print_header(self):
        """Print startup header"""
        print("\n" + "="*70)
        print("🔍 CONFIGURATION & CONNECTION MONITORING")
        print("="*70)
        print(f"⏰ Timestamp: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print(f"🌍 Environment: {settings.ENVIRONMENT}")
        print(f"🏷️  Application: {settings.APP_NAME} v{settings.APP_VERSION}")
        print(f"🐛 Debug Mode: {'✅ Enabled' if settings.DEBUG else '❌ Disabled'}")
        print("="*70 + "\n")
    
    def test_config_loading(self):
        """Test if configuration loaded successfully"""
        print("📋 CONFIGURATION SETTINGS")
        print("-" * 70)
        
        try:
            config_items = [
                ("Server Host", settings.HOST),
                ("Server Port", settings.PORT),
                ("API Prefix", settings.API_PREFIX),
                ("CORS Origins", ', '.join(settings.CORS_ORIGINS) if isinstance(settings.CORS_ORIGINS, list) else settings.CORS_ORIGINS),
                ("JWT Algorithm", settings.ALGORITHM),
                ("Access Token Expiry", f"{settings.ACCESS_TOKEN_EXPIRE_MINUTES} minutes"),
                ("Refresh Token Expiry", f"{settings.REFRESH_TOKEN_EXPIRE_DAYS} days"),
            ]
            
            for label, value in config_items:
                print(f"  ✓ {label:<25}: {value}")
            
            self.results["config"]["status"] = "success"
            self.results["config"]["message"] = "Configuration loaded successfully"
            print("  ✅ Status: Configuration Loaded\n")
            return True
            
        except Exception as e:
            self.results["config"]["status"] = "error"
            self.results["config"]["message"] = str(e)
            print(f"  ❌ Error: {str(e)}\n")
            return False
    
    def test_database_connection(self):
        """Test MySQL database connection"""
        print("🗄️  DATABASE CONNECTION TEST")
        print("-" * 70)
        
        try:
            print(f"  📍 Host: {settings.DB_HOST}:{settings.DB_PORT}")
            print(f"  📦 Database: {settings.DB_NAME}")
            print(f"  👤 User: {settings.DB_USER}")
            print(f"  🔧 Pool Size: {settings.DB_POOL_SIZE}")
            print(f"  ⚡ Max Overflow: {settings.DB_MAX_OVERFLOW}")
            
            # Attempt connection
            print("  ⏳ Connecting...")
            
            connection = pymysql.connect(
                host=settings.DB_HOST,
                port=settings.DB_PORT,
                user=settings.DB_USER,
                password=settings.DB_PASSWORD,
                database=settings.DB_NAME,
                connect_timeout=5,
                charset='utf8mb4'
            )
            
            # Test query
            with connection.cursor() as cursor:
                cursor.execute("SELECT VERSION()")
                version = cursor.fetchone()[0]
                print(f"  🔢 MySQL Version: {version}")
                
                cursor.execute("SELECT DATABASE()")
                db_name = cursor.fetchone()[0]
                print(f"  ✓ Connected to: {db_name}")
                
                # Check tables
                cursor.execute("SHOW TABLES")
                tables = cursor.fetchall()
                print(f"  📊 Tables Found: {len(tables)}")
                if tables:
                    table_names = [table[0] for table in tables[:5]]
                    print(f"     └─ {', '.join(table_names)}{'...' if len(tables) > 5 else ''}")
            
            connection.close()
            
            self.results["database"]["status"] = "success"
            self.results["database"]["message"] = f"Connected to MySQL {version}"
            print("  ✅ Status: Database Connected\n")
            return True
            
        except pymysql.MySQLError as e:
            error_msg = str(e)
            self.results["database"]["status"] = "error"
            self.results["database"]["message"] = error_msg
            print(f"  ❌ Error: {error_msg}")
            print("  ℹ️  Hint: Check database credentials in .env file\n")
            return False
        except Exception as e:
            error_msg = str(e)
            self.results["database"]["status"] = "error"
            self.results["database"]["message"] = error_msg
            print(f"  ❌ Error: {error_msg}\n")
            return False
    
    def test_smtp_connection(self):
        """Test SMTP email connection"""
        print("📧 SMTP EMAIL CONNECTION TEST")
        print("-" * 70)
        
        try:
            print(f"  📍 Host: {settings.SMTP_HOST}:{settings.SMTP_PORT}")
            print(f"  📧 From: {settings.SMTP_FROM_EMAIL} ({settings.SMTP_FROM_NAME})")
            print(f"  👤 User: {settings.SMTP_USER}")
            print(f"  🔒 Secure: {settings.SMTP_SECURE}")
            print("  ⏳ Connecting...")
            
            # Create SMTP connection
            if settings.SMTP_SECURE:
                server = smtplib.SMTP_SSL(settings.SMTP_HOST, settings.SMTP_PORT, timeout=10)
            else:
                server = smtplib.SMTP(settings.SMTP_HOST, settings.SMTP_PORT, timeout=10)
                server.starttls()
            
            # Login
            server.login(settings.SMTP_USER, settings.SMTP_APP_PASSWORD)
            
            # Get server info
            print(f"  ✓ Connected to {settings.SMTP_HOST}")
            
            server.quit()
            
            self.results["smtp"]["status"] = "success"
            self.results["smtp"]["message"] = "SMTP connection successful"
            print("  ✅ Status: SMTP Connected\n")
            return True
            
        except smtplib.SMTPAuthenticationError:
            error_msg = "Authentication failed - check username/password"
            self.results["smtp"]["status"] = "error"
            self.results["smtp"]["message"] = error_msg
            print(f"  ❌ Error: {error_msg}")
            print("  ℹ️  Hint: Use App Password for Gmail (not regular password)\n")
            return False
        except smtplib.SMTPException as e:
            error_msg = str(e)
            self.results["smtp"]["status"] = "error"
            self.results["smtp"]["message"] = error_msg
            print(f"  ❌ Error: {error_msg}")
            print("  ℹ️  Hint: Check SMTP settings in .env file\n")
            return False
        except Exception as e:
            error_msg = str(e)
            self.results["smtp"]["status"] = "warning"
            self.results["smtp"]["message"] = error_msg
            print(f"  ⚠️  Warning: {error_msg}")
            print("  ℹ️  Note: Email functionality may not be configured yet\n")
            return False
    
    def print_summary(self):
        """Print test summary"""
        print("="*70)
        print("📊 CONNECTION STATUS SUMMARY")
        print("="*70)
        
        status_icons = {
            "success": "✅",
            "error": "❌",
            "warning": "⚠️",
            "untested": "⏸️"
        }
        
        for service, result in self.results.items():
            icon = status_icons.get(result["status"], "❓")
            status_text = result["status"].upper()
            print(f"  {icon} {service.upper():<15}: {status_text}")
            if result["message"]:
                print(f"     └─ {result['message']}")
        
        print("="*70)
        
        # Overall status
        all_success = all(r["status"] == "success" for r in self.results.values())
        has_error = any(r["status"] == "error" for r in self.results.values())
        
        if all_success:
            print("🎉 All systems operational!\n")
            return True
        elif has_error:
            print("⚠️  Some services have errors. Check configuration.\n")
            return False
        else:
            print("ℹ️  System partially configured.\n")
            return True
    
    def run_all_tests(self):
        """Run all configuration tests"""
        self.print_header()
        
        # Run tests
        self.test_config_loading()
        self.test_database_connection()
        self.test_smtp_connection()
        
        # Print summary
        return self.print_summary()


def run_config_test():
    """Main function to run configuration tests"""
    tester = ConfigTester()
    return tester.run_all_tests()


if __name__ == "__main__":
    # Run tests when executed directly
    success = run_config_test()
    sys.exit(0 if success else 1)
