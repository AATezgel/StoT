# Backup script for Speech-to-Text application
#!/bin/bash

BACKUP_DIR="/backup/speechtotext"
DATE=$(date +%Y%m%d_%H%M%S)
APP_DIR="/var/www/speechtotext"

# Create backup directory
mkdir -p $BACKUP_DIR

echo "🔄 Starting backup process..."

# Backup database
echo "📊 Backing up PostgreSQL database..."
sudo -u postgres pg_dump speechtotext_db | gzip > $BACKUP_DIR/db_backup_$DATE.sql.gz

# Backup media files
echo "📁 Backing up media files..."
tar -czf $BACKUP_DIR/media_backup_$DATE.tar.gz -C $APP_DIR media/

# Backup application files (excluding venv and cache)
echo "💾 Backing up application files..."
tar --exclude='venv' --exclude='__pycache__' --exclude='*.pyc' \
    -czf $BACKUP_DIR/app_backup_$DATE.tar.gz -C /var/www speechtotext/

# Remove old backups (keep last 7 days)
echo "🧹 Cleaning old backups..."
find $BACKUP_DIR -name "*.gz" -mtime +7 -delete

echo "✅ Backup completed successfully!"
echo "📁 Backup location: $BACKUP_DIR"
