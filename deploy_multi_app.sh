#!/bin/bash

# Multi-App Ubuntu Server Deployment Script for Speech-to-Text Django Application
# This script is designed to work with multiple Django applications on the same server
# Use with Nginx Proxy Manager for external domain management

set -e

# Configuration - Change these values for your deployment
APP_NAME="speechtotext"
APP_PORT="8001"  # Unique port for this app
DOMAIN_NAME="speechtotext.ehost.com.tr"  # Your domain for NPM
DB_NAME="speechtotext_db"
DB_USER="speechtotext_user"
DB_PASSWORD="your_strong_password_here"  # Change this!

echo "🚀 Starting deployment of $APP_NAME application on port $APP_PORT..."

# Update system (only if first deployment)
echo "📦 Checking system packages..."
if ! command -v nginx &> /dev/null; then
    echo "Installing required system packages..."
    apt update && apt upgrade -y
    apt install -y python3 python3-pip python3-venv python3-dev \
        postgresql postgresql-contrib \
        nginx \
        ffmpeg \
        libasound2-dev portaudio19-dev libportaudio2 libportaudiocpp0 \
        build-essential \
        git \
        supervisor

    # Install additional audio libraries
    apt install -y libsndfile1-dev libsamplerate0-dev \
        libasound2-dev portaudio19-dev libfftw3-dev \
        pkg-config
fi

# Create application directory
echo "📁 Creating application directory..."
mkdir -p /var/www/$APP_NAME
cd /var/www/$APP_NAME

# Check if application files exist
if [ ! -f "manage.py" ]; then
    echo "❌ Application files not found! Please upload your Django project files to /var/www/$APP_NAME/"
    echo "You can use: scp -r /path/to/your/project/* user@server:/var/www/$APP_NAME/"
    exit 1
fi

# Create virtual environment
echo "🐍 Creating Python virtual environment..."
python3 -m venv venv
source venv/bin/activate

# Install Python dependencies
echo "📦 Installing Python packages..."
if [ -f "requirements.txt" ]; then
    pip install --upgrade pip
    pip install -r requirements.txt
else
    echo "❌ requirements.txt not found!"
    exit 1
fi

# Set up PostgreSQL database
echo "🗄️ Setting up PostgreSQL database..."
if ! sudo -u postgres psql -lqt | cut -d \| -f 1 | grep -qw $DB_NAME; then
    sudo -u postgres psql -c "CREATE DATABASE $DB_NAME;"
    sudo -u postgres psql -c "CREATE USER $DB_USER WITH ENCRYPTED PASSWORD '$DB_PASSWORD';"
    sudo -u postgres psql -c "GRANT ALL PRIVILEGES ON DATABASE $DB_NAME TO $DB_USER;"
    sudo -u postgres psql -c "ALTER USER $DB_USER CREATEDB;"
    echo "✅ Database created successfully"
else
    echo "ℹ️ Database already exists, skipping creation"
fi

# Set up environment variables
echo "⚙️ Setting up environment variables..."
if [ ! -f ".env" ]; then
    cp .env.production .env
    
    # Generate a random secret key
    SECRET_KEY=$(python -c 'from django.core.management.utils import get_random_secret_key; print(get_random_secret_key())')
    
    # Update .env file with actual values
    sed -i "s/your-secret-key-here-change-this-in-production/$SECRET_KEY/" .env
    sed -i "s/your-domain.com/$DOMAIN_NAME/" .env
    sed -i "s/your-server-ip/127.0.0.1/" .env
    sed -i "s/your-db-password/$DB_PASSWORD/" .env
    sed -i "s/speechtotext_db/$DB_NAME/" .env
    sed -i "s/speechtotext_user/$DB_USER/" .env
    
    echo "🔧 .env file created. Please review and update if needed:"
    echo "  - Domain: $DOMAIN_NAME"
    echo "  - Database: $DB_NAME"
    echo "  - Port: $APP_PORT"
fi

# Set proper permissions
echo "🔒 Setting file permissions..."
chown -R www-data:www-data /var/www/$APP_NAME
chmod -R 755 /var/www/$APP_NAME
chmod +x gunicorn_start

# Create media and static directories
echo "📁 Creating media and static directories..."
mkdir -p /var/www/$APP_NAME/media
mkdir -p /var/www/$APP_NAME/static
chown -R www-data:www-data /var/www/$APP_NAME/media
chown -R www-data:www-data /var/www/$APP_NAME/static

# Run Django migrations
echo "🔄 Running Django migrations..."
source venv/bin/activate
python manage.py collectstatic --noinput
python manage.py migrate

# Create superuser if not exists
echo "👤 Creating admin user..."
echo "from django.contrib.auth.models import User; User.objects.filter(username='admin').exists() or User.objects.create_superuser('admin', 'admin@$DOMAIN_NAME', 'admin123')" | python manage.py shell

# Update systemd service file with app-specific settings
echo "⚙️ Updating systemd service files..."
sed -i "s/speechtotext/$APP_NAME/g" $APP_NAME.service
sed -i "s/speechtotext/$APP_NAME/g" $APP_NAME.socket

# Set up systemd services
echo "⚙️ Setting up systemd services..."
cp $APP_NAME.socket /etc/systemd/system/
cp $APP_NAME.service /etc/systemd/system/
systemctl daemon-reload
systemctl enable $APP_NAME.socket
systemctl enable $APP_NAME.service

# Update Nginx configuration with app-specific port
echo "🌐 Setting up Nginx..."
sed -i "s/8001/$APP_PORT/" nginx_$APP_NAME.conf
cp nginx_$APP_NAME.conf /etc/nginx/sites-available/$APP_NAME

# Enable site
ln -sf /etc/nginx/sites-available/$APP_NAME /etc/nginx/sites-enabled/

# Test Nginx configuration
nginx -t

# Start services
echo "🚀 Starting services..."
systemctl start $APP_NAME.socket
systemctl start $APP_NAME.service
systemctl restart nginx

# Configure firewall for the specific port
echo "🔥 Configuring firewall..."
ufw allow $APP_PORT
ufw allow 'Nginx Full'
ufw allow ssh

echo "✅ Deployment completed successfully!"
echo ""
echo "📋 Application Details:"
echo "  - Name: $APP_NAME"
echo "  - Internal Port: $APP_PORT"
echo "  - Domain: $DOMAIN_NAME"
echo "  - Database: $DB_NAME"
echo "  - Location: /var/www/$APP_NAME"
echo ""
echo "🌐 Nginx Proxy Manager Setup:"
echo "  1. Add a new proxy host in NPM"
echo "  2. Domain: $DOMAIN_NAME"
echo "  3. Forward Hostname/IP: 127.0.0.1"
echo "  4. Forward Port: $APP_PORT"
echo "  5. Enable 'Block Common Exploits'"
echo "  6. Enable 'Websockets Support' if needed"
echo "  7. Add SSL certificate (Let's Encrypt)"
echo ""
echo "🔧 Useful commands:"
echo "  - Check service: systemctl status $APP_NAME"
echo "  - Check logs: journalctl -u $APP_NAME -f"
echo "  - Restart app: systemctl restart $APP_NAME"
echo ""
echo "🔒 Security reminders:"
echo "  - Admin user: admin / admin123 (change password!)"
echo "  - Database password: $DB_PASSWORD"
echo "  - Review .env file settings"
echo "  - Configure SSL in Nginx Proxy Manager"
