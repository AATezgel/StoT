from django.db import models
from django.utils import timezone
from django.contrib.auth.models import User

# Create your models here.

class AudioUpload(models.Model):
    """
    Model for storing uploaded audio files and their transcriptions
    """
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='audio_uploads', default=1)
    title = models.CharField(max_length=200, blank=True, null=True)
    audio_file = models.FileField(upload_to='audio_files/')
    transcription = models.TextField(blank=True, null=True)
    language = models.CharField(max_length=10, default='tr-TR')  # Varsayılan olarak Türkçe
    created_at = models.DateTimeField(default=timezone.now)
    updated_at = models.DateTimeField(auto_now=True)
    file_size = models.IntegerField(blank=True, null=True)  # Bytes cinsinden
    duration = models.FloatField(blank=True, null=True)  # Saniye cinsinden
    
    # Gelişmiş kalite ve istatistik alanları
    quality_score = models.FloatField(blank=True, null=True)  # 0-100 arası kalite skoru
    success_rate = models.FloatField(blank=True, null=True)  # Başarı oranı %
    total_chunks = models.IntegerField(blank=True, null=True)  # Toplam parça sayısı
    successful_chunks = models.IntegerField(blank=True, null=True)  # Başarılı parça sayısı
    processing_method = models.CharField(max_length=50, blank=True, null=True)  # İşleme yöntemi
    
    status = models.CharField(
        max_length=20,
        choices=[
            ('pending', 'Bekliyor'),
            ('processing', 'İşleniyor'),
            ('completed', 'Tamamlandı'),
            ('error', 'Hata')
        ],
        default='pending'
    )

    class Meta:
        ordering = ['-created_at']
        verbose_name = 'Ses Dosyası'
        verbose_name_plural = 'Ses Dosyaları'

    def __str__(self):
        return self.title if self.title else f"Audio {self.id}"

    def get_file_size_mb(self):
        """File size in MB"""
        if self.file_size:
            return round(self.file_size / (1024 * 1024), 2)
        return None

    def get_duration_formatted(self):
        """Duration formatted as MM:SS"""
        if self.duration:
            minutes = int(self.duration // 60)
            seconds = int(self.duration % 60)
            return f"{minutes:02d}:{seconds:02d}"
        return None

    def get_quality_level(self):
        """Get quality level description"""
        if not self.quality_score:
            return "Bilinmiyor"
        
        if self.quality_score >= 90:
            return "Mükemmel"
        elif self.quality_score >= 75:
            return "İyi"
        elif self.quality_score >= 60:
            return "Orta"
        else:
            return "Düşük"

    def get_quality_color(self):
        """Get Bootstrap color class for quality"""
        if not self.quality_score:
            return "secondary"
        
        if self.quality_score >= 90:
            return "success"
        elif self.quality_score >= 75:
            return "info"
        elif self.quality_score >= 60:
            return "warning"
        else:
            return "danger"

    def get_processing_stats(self):
        """Get processing statistics"""
        if self.total_chunks and self.successful_chunks:
            return {
                'total': self.total_chunks,
                'successful': self.successful_chunks,
                'failed': self.total_chunks - self.successful_chunks,
                'success_rate': (self.successful_chunks / self.total_chunks) * 100
            }
        return None
