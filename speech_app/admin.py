from django.contrib import admin
from .models import AudioUpload

@admin.register(AudioUpload)
class AudioUploadAdmin(admin.ModelAdmin):
    list_display = ['title', 'language', 'status', 'get_file_size_mb', 'created_at']
    list_filter = ['status', 'language', 'created_at']
    search_fields = ['title', 'transcription']
    readonly_fields = ['created_at', 'updated_at', 'file_size']
    
    fieldsets = (
        ('Genel Bilgiler', {
            'fields': ('title', 'language', 'status')
        }),
        ('Dosya Bilgileri', {
            'fields': ('audio_file', 'file_size', 'duration')
        }),
        ('Transkripsiyon', {
            'fields': ('transcription',)
        }),
        ('Zaman Bilgileri', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )
    
    def get_file_size_mb(self, obj):
        return f"{obj.get_file_size_mb()} MB" if obj.get_file_size_mb() else "Bilinmiyor"
    get_file_size_mb.short_description = "Dosya Boyutu"
