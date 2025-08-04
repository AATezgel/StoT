#!/bin/bash

# Ubuntu Server Deployment Script for Speech-to-Text Django Application
# Run this script with sudo privileges

set -e

echo "🚀 Starting deployment of Speech-to-Text application..."

# Update system
echo "📦 Updating system packages..."
apt update && apt upgrade -y

# Install required system packages
echo "📦 Installing system dependencies..."
apt install -y python3 python3-pip python3-venv python3-dev \
    postgresql postgresql-contrib \
    nginx \
    ffmpeg \
    libasound2-dev portaudio19-dev libportaudio2 libportaudiocpp0 \
    build-essential \
    git \
    supervisor

# Install additional audio libraries
echo "📦 Installing audio processing libraries..."
apt install -y libsndfile1-dev libsamplerate0-dev \
    libasound2-dev portaudio19-dev libfftw3-dev \
    pkg-config

# Create application directory
echo "📁 Creating application directory..."
mkdir -p /var/www/speechtotext
cd /var/www/speechtotext

# Copy application files (you need to upload your files here first)
echo "📋 Application files should be uploaded to /var/www/speechtotext/"
echo "Please upload your Django project files before running this script."

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
    echo "❌ requirements.txt not found! Please upload your project files first."
    exit 1
fi

# Set up PostgreSQL database
echo "🗄️ Setting up PostgreSQL database..."
sudo -u postgres psql -c "CREATE DATABASE speechtotext_db;"
sudo -u postgres psql -c "CREATE USER speechtotext_user WITH ENCRYPTED PASSWORD 'your_strong_password_here';"
sudo -u postgres psql -c "GRANT ALL PRIVILEGES ON DATABASE speechtotext_db TO speechtotext_user;"
sudo -u postgres psql -c "ALTER USER speechtotext_user CREATEDB;"

# Set up environment variables
echo "⚙️ Setting up environment variables..."
if [ ! -f ".env" ]; then
    cp .env.production .env
    echo "🔧 Please edit /var/www/speechtotext/.env with your production settings"
    echo "🔧 Especially set SECRET_KEY, DB_PASSWORD, and ALLOWED_HOSTS"
fi

# Set proper permissions
echo "🔒 Setting file permissions..."
chown -R www-data:www-data /var/www/speechtotext
chmod -R 755 /var/www/speechtotext
chmod +x gunicorn_start

# Create media and static directories
echo "📁 Creating media and static directories..."
mkdir -p /var/www/speechtotext/media
mkdir -p /var/www/speechtotext/static
chown -R www-data:www-data /var/www/speechtotext/media
chown -R www-data:www-data /var/www/speechtotext/static

# Run Django migrations
echo "🔄 Running Django migrations..."
source venv/bin/activate
python manage.py collectstatic --noinput
python manage.py migrate

# Set up systemd services
echo "⚙️ Setting up systemd services..."
cp speechtotext.socket /etc/systemd/system/
cp speechtotext.service /etc/systemd/system/
systemctl daemon-reload
systemctl enable speechtotext.socket
systemctl enable speechtotext.service

# Set up Nginx
echo "🌐 Setting up Nginx..."
cp nginx_speechtotext.conf /etc/nginx/sites-available/speechtotext
ln -sf /etc/nginx/sites-available/speechtotext /etc/nginx/sites-enabled/
rm -f /etc/nginx/sites-enabled/default

# Test Nginx configuration
nginx -t

# Start services
echo "🚀 Starting services..."
systemctl start speechtotext.socket
systemctl start speechtotext.service
systemctl restart nginx

# Enable firewall
echo "🔥 Configuring firewall..."
ufw allow 'Nginx Full'
ufw allow ssh
ufw --force enable

echo "✅ Deployment completed successfully!"
echo ""
echo "📋 Next steps:"
echo "1. Edit /var/www/speechtotext/.env with your production settings"
echo "2. Update ALLOWED_HOSTS in .env with your domain/IP"
echo "3. Set a strong SECRET_KEY in .env"
echo "4. Configure SSL certificate (recommended)"
echo "5. Test the application at http://your-server-ip"
echo ""
echo "🔧 Useful commands:"
echo "- Check service status: systemctl status speechtotext"
echo "- Check logs: journalctl -u speechtotext -f"
echo "- Restart application: systemctl restart speechtotext"
echo "- Check Nginx status: systemctl status nginx"
echo ""
echo "🔒 Security reminders:"
echo "- Change default PostgreSQL password"
echo "- Set up SSL certificate (Let's Encrypt recommended)"
echo "- Configure proper firewall rules"
echo "- Regularly update system packages"
