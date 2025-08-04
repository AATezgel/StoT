# Ubuntu Server'a Speech-to-Text Uygulaması Deployment Rehberi

## 🚀 Hızlı Başlangıç

### 1. Sunucu Hazırlığı

```bash
# Sistemi güncelle
sudo apt update && sudo apt upgrade -y

# Gerekli paketleri yükle
sudo apt install -y python3 python3-pip python3-venv python3-dev \
    postgresql postgresql-contrib \
    nginx \
    ffmpeg \
    libasound2-dev portaudio19-dev libportaudio2 libportaudiocpp0 \
    build-essential git supervisor

# Audio işleme kütüphaneleri
sudo apt install -y libsndfile1-dev libsamplerate0-dev \
    libasound2-dev portaudio19-dev libfftw3-dev pkg-config
```

### 2. Uygulama Dosyalarını Yükle

```bash
# Uygulama dizini oluştur
sudo mkdir -p /var/www/speechtotext
cd /var/www/speechtotext

# Proje dosyalarını bu dizine kopyala/upload et
# SCP ile: scp -r * user@server:/var/www/speechtotext/
# Git ile: git clone your-repo-url .
```

### 3. Python Ortamını Hazırla

```bash
# Virtual environment oluştur
sudo python3 -m venv venv
sudo chown -R $USER:$USER venv
source venv/bin/activate

# Python paketlerini yükle
pip install --upgrade pip
pip install -r requirements.txt
```

### 4. PostgreSQL Veritabanını Hazırla

```bash
# PostgreSQL'e bağlan
sudo -u postgres psql

# Veritabanı ve kullanıcı oluştur
CREATE DATABASE speechtotext_db;
CREATE USER speechtotext_user WITH ENCRYPTED PASSWORD 'your_strong_password_here';
GRANT ALL PRIVILEGES ON DATABASE speechtotext_db TO speechtotext_user;
ALTER USER speechtotext_user CREATEDB;
\q
```

### 5. Environment Variables Ayarla

```bash
# .env dosyasını düzenle
sudo cp .env.production .env
sudo nano .env
```

**Önemli ayarlar:**
```
DEBUG=False
SECRET_KEY=your-very-long-random-secret-key-here
ALLOWED_HOSTS=your-domain.com,your-server-ip,localhost
DB_PASSWORD=your_strong_password_here
```

### 6. Django Uygulamasını Hazırla

```bash
# Sanal ortamı aktifleştir
source venv/bin/activate

# Static dosyaları topla
python manage.py collectstatic --noinput

# Veritabanı migrations
python manage.py migrate

# Admin kullanıcısı oluştur (opsiyonel)
python manage.py createsuperuser
```

### 7. Dosya İzinlerini Ayarla

```bash
# Sahiplik ve izinleri ayarla
sudo chown -R www-data:www-data /var/www/speechtotext
sudo chmod -R 755 /var/www/speechtotext
sudo chmod +x /var/www/speechtotext/gunicorn_start

# Media ve static dizinleri
sudo mkdir -p /var/www/speechtotext/media
sudo mkdir -p /var/www/speechtotext/static
sudo chown -R www-data:www-data /var/www/speechtotext/media
sudo chown -R www-data:www-data /var/www/speechtotext/static
```

### 8. Systemd Servisleri Ayarla

```bash
# Systemd dosyalarını kopyala
sudo cp speechtotext.socket /etc/systemd/system/
sudo cp speechtotext.service /etc/systemd/system/

# Servisleri etkinleştir
sudo systemctl daemon-reload
sudo systemctl enable speechtotext.socket
sudo systemctl enable speechtotext.service
sudo systemctl start speechtotext.socket
sudo systemctl start speechtotext.service
```

### 9. Nginx Ayarla

```bash
# Nginx konfigürasyonunu kopyala
sudo cp nginx_speechtotext.conf /etc/nginx/sites-available/speechtotext

# Site'ı etkinleştir
sudo ln -sf /etc/nginx/sites-available/speechtotext /etc/nginx/sites-enabled/
sudo rm -f /etc/nginx/sites-enabled/default

# Nginx konfigürasyonunu test et
sudo nginx -t

# Nginx'i yeniden başlat
sudo systemctl restart nginx
```

### 10. Firewall Ayarla

```bash
# UFW'yi ayarla
sudo ufw allow 'Nginx Full'
sudo ufw allow ssh
sudo ufw --force enable
```

## 🔧 Otomatik Deployment

Tüm bu adımları otomatik yapmak için:

```bash
# Deploy script'ini çalıştırılabilir yap
chmod +x deploy.sh

# Script'i root olarak çalıştır
sudo ./deploy.sh
```

## 🛠️ Yararlı Komutlar

### Servis Yönetimi
```bash
# Uygulama durumunu kontrol et
sudo systemctl status speechtotext

# Uygulama loglarını görüntüle
sudo journalctl -u speechtotext -f

# Uygulamayı yeniden başlat
sudo systemctl restart speechtotext

# Nginx durumunu kontrol et
sudo systemctl status nginx
```

### Debugging
```bash
# Gunicorn'u manuel test et
cd /var/www/speechtotext
source venv/bin/activate
gunicorn --bind 0.0.0.0:8000 speechtotext_project.wsgi:application

# Django development server test
python manage.py runserver 0.0.0.0:8000

# Socket dosyası kontrolü
ls -la /run/gunicorn/speechtotext.sock
```

### Güncellemeler
```bash
# Kod güncellemesi sonrası
cd /var/www/speechtotext
git pull  # veya dosyaları yeniden upload et
source venv/bin/activate
pip install -r requirements.txt
python manage.py collectstatic --noinput
python manage.py migrate
sudo systemctl restart speechtotext
```

## 🔒 Güvenlik Önerileri

### SSL Sertifikası (Let's Encrypt)
```bash
# Certbot yükle
sudo apt install certbot python3-certbot-nginx

# SSL sertifikası al
sudo certbot --nginx -d your-domain.com

# Otomatik yenileme test et
sudo certbot renew --dry-run
```

### Güvenlik Güncellemeleri
```bash
# Sistem paketlerini güncelle
sudo apt update && sudo apt upgrade -y

# Python paketlerini güncelle
cd /var/www/speechtotext
source venv/bin/activate
pip list --outdated
pip install --upgrade package-name
```

### Backup
```bash
# Veritabanı backup
sudo -u postgres pg_dump speechtotext_db > backup_$(date +%Y%m%d).sql

# Media dosyaları backup
tar -czf media_backup_$(date +%Y%m%d).tar.gz /var/www/speechtotext/media/
```

## 🚨 Sorun Giderme

### Yaygın Sorunlar

1. **502 Bad Gateway**
   - Gunicorn servisini kontrol et: `sudo systemctl status speechtotext`
   - Socket dosyasını kontrol et: `ls -la /run/gunicorn/speechtotext.sock`

2. **Static Files Yüklenmiyor**
   - `python manage.py collectstatic --noinput` çalıştır
   - Nginx konfigürasyonunu kontrol et

3. **Database Connection Error**
   - PostgreSQL çalışıyor mu: `sudo systemctl status postgresql`
   - .env dosyasındaki database ayarlarını kontrol et

4. **Permission Denied Hataları**
   - Dosya sahipliklerini kontrol et: `sudo chown -R www-data:www-data /var/www/speechtotext`

### Log Dosyaları
```bash
# Nginx logs
sudo tail -f /var/log/nginx/error.log
sudo tail -f /var/log/nginx/access.log

# Gunicorn logs
sudo journalctl -u speechtotext -f

# Django logs (DEBUG=True ise)
tail -f /var/www/speechtotext/django.log
```

## 📊 Performans Optimizasyonu

### Gunicorn Workers
```bash
# CPU sayısını kontrol et
nproc

# Workers sayısını artır (speechtotext.service dosyasında)
--workers 4  # 2 * CPU + 1
```

### Nginx Optimizasyonu
```bash
# Nginx worker processes (nginx.conf'ta)
worker_processes auto;
worker_connections 1024;
```

### Database Optimizasyonu
```bash
# PostgreSQL ayarları (/etc/postgresql/*/main/postgresql.conf)
shared_buffers = 256MB
effective_cache_size = 1GB
```

Bu rehber ile Ubuntu sunucunuzda Speech-to-Text uygulamanızı başarıyla deploy edebilirsiniz! 🎉
