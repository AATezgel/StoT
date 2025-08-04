# Multi-App Ubuntu Server Speech-to-Text Deployment Rehberi

## 🎯 Yeni Özellikler

### 🔐 Authentication Sistemi
- **Kullanıcı Kayıt/Giriş**: Güvenli authentication sistemi
- **User-based Access**: Her kullanıcı sadece kendi dosyalarını görür
- **Admin Panel**: Admin kullanıcılar tüm dosyaları yönetebilir
- **Session Management**: Güvenli oturum yönetimi

### 🌐 Multi-App Deployment
- **Nginx Proxy Manager Desteği**: Kolay domain yönetimi
- **Port-based Separation**: Her uygulama farklı port kullanır
- **SSL Termination**: NPM üzerinden SSL yönetimi
- **Isolated Services**: Her uygulama bağımsız çalışır

## 🚀 Hızlı Deployment

### 1. Önkoşullar
```bash
# Ubuntu 20.04+ sunucu
# Root veya sudo erişimi
# Nginx Proxy Manager kurulu (opsiyonel)
```

### 2. Dosyaları Sunucuya Yükle
```bash
# Method 1: SCP ile
scp -r speechtotext/ user@server-ip:/tmp/

# Method 2: Git ile
git clone your-repo-url /tmp/speechtotext
```

### 3. Otomatik Multi-App Deployment
```bash
# Sunucuda
sudo cp -r /tmp/speechtotext /var/www/
cd /var/www/speechtotext
sudo chmod +x deploy_multi_app.sh

# Konfigürasyonu düzenle
sudo nano deploy_multi_app.sh
# APP_NAME="speechtotext"
# APP_PORT="8001"
# DOMAIN_NAME="speechtotext.yourdomain.com"
# DB_PASSWORD="güçlü_şifre_buraya"

# Deploy et
sudo ./deploy_multi_app.sh
```

## 🐳 Docker Deployment (Alternatif)

### 1. Docker Compose ile
```bash
cd /var/www/speechtotext

# Environment variables düzenle
nano docker-compose.yml

# Başlat
docker-compose up -d

# Logs kontrol et
docker-compose logs -f web
```

### 2. Docker Build
```bash
# Image oluştur
docker build -t speechtotext-app .

# Çalıştır
docker run -d -p 8001:8000 \
  -e DEBUG=False \
  -e SECRET_KEY=your-secret-key \
  speechtotext-app
```

## 🔧 Nginx Proxy Manager Konfigürasyonu

### 1. NPM'de Yeni Proxy Host Ekle
```
Domain Names: speechtotext.yourdomain.com
Scheme: http
Forward Hostname/IP: 127.0.0.1
Forward Port: 8001
Block Common Exploits: ✅
Websockets Support: ✅
```

### 2. SSL Sertifikası
```
SSL: Let's Encrypt
Email: admin@yourdomain.com
Domain: speechtotext.yourdomain.com
```

### 3. Advanced Konfigürasyon
```nginx
# Custom Nginx Configuration
client_max_body_size 100M;

location /static/ {
    proxy_pass http://127.0.0.1:8001;
    proxy_cache_valid 200 30d;
}

location /media/ {
    proxy_pass http://127.0.0.1:8001;
    proxy_cache_valid 200 7d;
}
```

## 🔐 Authentication Kullanımı

### 1. İlk Admin Kullanıcısı
```bash
# Deployment sırasında otomatik oluşturulur:
# Username: admin
# Password: admin123
# Email: admin@yourdomain.com

# Şifreyi değiştir!
cd /var/www/speechtotext
source venv/bin/activate
python manage.py changepassword admin
```

### 2. User Permissions
```python
# Admin users (is_staff=True):
- Tüm ses dosyalarını görebilir
- Tüm kullanıcıları yönetebilir
- Admin paneline erişebilir

# Normal users (is_staff=False):
- Sadece kendi ses dosyalarını görebilir
- Kendi transkriptlerini yönetebilir
- Upload/download yapabilir
```

### 3. Template Changes
```html
<!-- Navigation menü kullanıcı durumuna göre değişir -->
{% if user.is_authenticated %}
    <!-- Upload ve liste menüleri görünür -->
{% else %}
    <!-- Login/register menüleri görünür -->
{% endif %}
```

## 📱 Multi-App Portları

### Önerilen Port Dağılımı
```bash
# Ana uygulamalar
8001: speechtotext
8002: app2
8003: app3
8004: app4

# Database ve servisler
5432: PostgreSQL
6379: Redis
3306: MySQL (isteğe bağlı)
```

### Port Management
```bash
# Aktif portları kontrol et
sudo netstat -tlnp | grep :8001

# Firewall ayarla
sudo ufw allow 8001
sudo ufw allow 8002
# etc.

# Nginx upstream konfig
upstream speechtotext {
    server 127.0.0.1:8001;
}
```

## 🔄 Güncellemeler

### 1. Code Update
```bash
cd /var/www/speechtotext
git pull origin main
source venv/bin/activate
pip install -r requirements.txt
python manage.py collectstatic --noinput
python manage.py migrate
sudo systemctl restart speechtotext
```

### 2. Database Migration
```bash
source venv/bin/activate
python manage.py makemigrations
python manage.py migrate
sudo systemctl restart speechtotext
```

### 3. Environment Update
```bash
# .env dosyasını düzenle
nano .env

# Service'i restart et
sudo systemctl restart speechtotext
```

## 🎮 Management Commands

### Service Management
```bash
# Status kontrol
sudo systemctl status speechtotext

# Restart
sudo systemctl restart speechtotext

# Logs
sudo journalctl -u speechtotext -f

# Stop/Start
sudo systemctl stop speechtotext
sudo systemctl start speechtotext
```

### Database Management
```bash
# Backup
sudo -u postgres pg_dump speechtotext_db > backup.sql

# Restore
sudo -u postgres psql speechtotext_db < backup.sql

# Reset database
sudo -u postgres dropdb speechtotext_db
sudo -u postgres createdb speechtotext_db
python manage.py migrate
```

### User Management
```bash
# Django shell
python manage.py shell

# Kullanıcı oluştur
python manage.py createsuperuser

# Kullanıcı listesi
echo "from django.contrib.auth.models import User; [print(f'{u.username}: {u.email} - Admin: {u.is_staff}') for u in User.objects.all()]" | python manage.py shell
```

## 🚨 Troubleshooting

### Yaygın Sorunlar

1. **502 Bad Gateway**
```bash
# Service durumu kontrol et
sudo systemctl status speechtotext
# Socket dosyası kontrol et
ls -la /run/gunicorn/speechtotext.sock
# Nginx config test
sudo nginx -t
```

2. **Permission Denied**
```bash
# File permissions
sudo chown -R www-data:www-data /var/www/speechtotext
sudo chmod -R 755 /var/www/speechtotext
```

3. **Database Connection Error**
```bash
# PostgreSQL status
sudo systemctl status postgresql
# Test connection
sudo -u postgres psql -d speechtotext_db -c "SELECT 1;"
```

4. **Static Files Not Loading**
```bash
# Collect static files
python manage.py collectstatic --noinput
# Check nginx config
sudo nginx -t && sudo systemctl restart nginx
```

5. **Authentication Issues**
```bash
# CSRF errors
# .env dosyasında CSRF_TRUSTED_ORIGINS kontrol et
# Session cleanup
python manage.py clearsessions
```

## 📊 Monitoring

### Log Locations
```bash
# Application logs
sudo journalctl -u speechtotext -f

# Nginx logs
sudo tail -f /var/log/nginx/error.log
sudo tail -f /var/log/nginx/access.log

# PostgreSQL logs
sudo tail -f /var/log/postgresql/postgresql-*.log
```

### Performance Monitoring
```bash
# System resources
htop
iotop
nethogs

# Database queries
# Django Debug Toolbar (development)
pip install django-debug-toolbar
```

## 🔒 Security Checklist

- [ ] Admin şifresi değiştirildi
- [ ] Strong SECRET_KEY kullanılıyor
- [ ] Database şifresi güçlü
- [ ] ALLOWED_HOSTS doğru ayarlandı
- [ ] CSRF_TRUSTED_ORIGINS doğru ayarlandı
- [ ] SSL sertifikası yüklü (NPM'de)
- [ ] Firewall aktif ve yapılandırılmış
- [ ] Regular backups planlandı
- [ ] Security updates düzenli yapılıyor

Bu rehber ile Ubuntu sunucunuzda güvenli, ölçeklenebilir ve yönetilebilir bir Speech-to-Text servisi çalıştırabilirsiniz! 🎉
