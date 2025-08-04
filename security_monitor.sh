# Security monitoring script
#!/bin/bash

LOG_FILE="/var/log/speechtotext_security.log"
EMAIL="admin@yourdomain.com"

# Function to log events
log_event() {
    echo "$(date): $1" >> $LOG_FILE
}

# Check for failed login attempts
failed_logins=$(grep "Failed password" /var/log/auth.log | wc -l)
if [ $failed_logins -gt 10 ]; then
    log_event "HIGH: $failed_logins failed login attempts detected"
    echo "Security Alert: $failed_logins failed login attempts on $(hostname)" | mail -s "Security Alert" $EMAIL
fi

# Check disk usage
disk_usage=$(df /var/www/speechtotext | awk 'NR==2 {print $5}' | sed 's/%//')
if [ $disk_usage -gt 80 ]; then
    log_event "WARNING: Disk usage is $disk_usage%"
    echo "Disk usage warning: $disk_usage% on $(hostname)" | mail -s "Disk Usage Warning" $EMAIL
fi

# Check service status
if ! systemctl is-active --quiet speechtotext; then
    log_event "ERROR: speechtotext service is down"
    echo "Service Alert: speechtotext service is down on $(hostname)" | mail -s "Service Down Alert" $EMAIL
fi

if ! systemctl is-active --quiet nginx; then
    log_event "ERROR: nginx service is down"
    echo "Service Alert: nginx service is down on $(hostname)" | mail -s "Service Down Alert" $EMAIL
fi

# Check for unusual traffic patterns
nginx_errors=$(grep "$(date +%d/%b/%Y)" /var/log/nginx/error.log | wc -l)
if [ $nginx_errors -gt 50 ]; then
    log_event "WARNING: $nginx_errors nginx errors today"
fi

log_event "Security check completed"
