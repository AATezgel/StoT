from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.contrib.auth import login, logout
from django.contrib.auth.decorators import login_required
from django.contrib.auth.forms import AuthenticationForm
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.core.files.storage import default_storage
from django.db.models import Q
import speech_recognition as sr
import os
import time
import numpy as np
import librosa
import noisereduce as nr
from scipy.io import wavfile
from pydub import AudioSegment
from .models import AudioUpload
from .forms import CustomUserCreationForm, CustomAuthenticationForm
import tempfile
import logging

# Logging konfigürasyonu
logging.basicConfig(level=logging.INFO)

def home(request):
    """Ana sayfa view'i"""
    if request.user.is_authenticated:
        if request.user.is_staff:
            # Admin kullanıcı tüm transcriptions'ları görebilir
            recent_transcriptions = AudioUpload.objects.filter(status='completed')[:5]
        else:
            # Normal kullanıcı sadece kendi transcriptions'larını görebilir
            recent_transcriptions = AudioUpload.objects.filter(
                user=request.user, 
                status='completed'
            )[:5]
    else:
        recent_transcriptions = []
    
    return render(request, 'speech_app/home.html', {
        'recent_transcriptions': recent_transcriptions
    })

def user_login(request):
    """Kullanıcı giriş view'i"""
    if request.user.is_authenticated:
        return redirect('home')
    
    if request.method == 'POST':
        form = CustomAuthenticationForm(request, data=request.POST)
        if form.is_valid():
            user = form.get_user()
            login(request, user)
            messages.success(request, f'Hoş geldiniz, {user.get_full_name() or user.username}!')
            next_url = request.GET.get('next', 'home')
            return redirect(next_url)
        else:
            messages.error(request, 'Kullanıcı adı veya şifre hatalı.')
    else:
        form = CustomAuthenticationForm()
    
    return render(request, 'speech_app/login.html', {'form': form})

def user_register(request):
    """Kullanıcı kayıt view'i"""
    if request.user.is_authenticated:
        return redirect('home')
    
    if request.method == 'POST':
        form = CustomUserCreationForm(request.POST)
        if form.is_valid():
            user = form.save()
            login(request, user)
            messages.success(request, f'Hesabınız başarıyla oluşturuldu! Hoş geldiniz, {user.get_full_name()}!')
            return redirect('home')
        else:
            messages.error(request, 'Kayıt sırasında bir hata oluştu. Lütfen formu kontrol edin.')
    else:
        form = CustomUserCreationForm()
    
    return render(request, 'speech_app/register.html', {'form': form})

def user_logout(request):
    """Kullanıcı çıkış view'i"""
    logout(request)
    messages.success(request, 'Başarıyla çıkış yaptınız.')
    return redirect('home')

@login_required
def upload_audio(request):
    """Ses dosyası yükleme view'i - Sadece giriş yapmış kullanıcılar"""
    if request.method == 'POST':
        try:
            audio_file = request.FILES.get('audio_file')
            title = request.POST.get('title', '')
            language = request.POST.get('language', 'tr-TR')
            
            if not audio_file:
                messages.error(request, 'Lütfen bir ses dosyası seçin.')
                return redirect('upload_audio')
            
            # Dosya türü kontrolü
            allowed_formats = ['.wav', '.mp3', '.m4a', '.flac', '.ogg']
            file_extension = os.path.splitext(audio_file.name)[1].lower()
            
            if file_extension not in allowed_formats:
                messages.error(request, f'Desteklenmeyen dosya türü. İzin verilen türler: {", ".join(allowed_formats)}')
                return redirect('upload_audio')
            
            # Dosya boyutu kontrolü (200MB limit)
            max_file_size = 200 * 1024 * 1024  # 200MB
            if audio_file.size > max_file_size:
                messages.error(request, f'Dosya boyutu çok büyük. Maksimum {max_file_size // (1024*1024)}MB olmalıdır.')
                return redirect('upload_audio')
            
            # AudioUpload objesi oluştur
            audio_upload = AudioUpload.objects.create(
                user=request.user,  # Kullanıcıyı ekle
                title=title or audio_file.name,
                audio_file=audio_file,
                language=language,
                file_size=audio_file.size,
                status='processing'
            )
            
            # Dosya boyutu uyarısı
            file_size_mb = audio_file.size / (1024 * 1024)
            if file_size_mb > 10:
                messages.info(request, f'Büyük dosya ({file_size_mb:.1f}MB) yüklendi. İşlem birkaç dakika sürebilir.')
            
            # Transkripsiyon işlemini başlat
            transcription_result = process_audio_transcription(audio_upload)
            
            if transcription_result['success']:
                audio_upload.transcription = transcription_result['text']
                audio_upload.status = 'completed'
                
                # İstatistikleri kullanıcıya göster
                if 'stats' in transcription_result:
                    stats = transcription_result['stats']
                    success_rate = stats.get('success_rate', 0)
                    if success_rate >= 90:
                        messages.success(request, f'Ses dosyası mükemmel kalitede işlendi! (Başarı oranı: %{success_rate:.1f})')
                    elif success_rate >= 70:
                        messages.success(request, f'Ses dosyası başarıyla işlendi! (Başarı oranı: %{success_rate:.1f})')
                    else:
                        messages.warning(request, f'Ses dosyası işlendi ancak kalite orta seviyede. (Başarı oranı: %{success_rate:.1f})')
                else:
                    messages.success(request, 'Ses dosyası başarıyla işlendi!')
            else:
                audio_upload.status = 'error'
                messages.error(request, f'Transkripsiyon hatası: {transcription_result["error"]}')
            
            audio_upload.save()
            return redirect('transcription_detail', pk=audio_upload.pk)
            
        except Exception as e:
            messages.error(request, f'Bir hata oluştu: {str(e)}')
            return redirect('upload_audio')
    
    return render(request, 'speech_app/upload.html')

@login_required
def transcription_detail(request, pk):
    """Kullanıcı bazlı transkripsiyon detay view'i"""
    if request.user.is_staff:
        # Admin kullanıcı tüm transcriptions'ları görebilir
        audio_upload = get_object_or_404(AudioUpload, pk=pk)
    else:
        # Normal kullanıcı sadece kendi transcriptions'larını görebilir
        audio_upload = get_object_or_404(AudioUpload, pk=pk, user=request.user)
    
    return render(request, 'speech_app/detail.html', {
        'audio_upload': audio_upload
    })

@login_required
def transcription_list(request):
    """Kullanıcıya göre transkripsiyonları listele"""
    if request.user.is_staff:
        # Admin kullanıcı tüm transcriptions'ları görebilir
        transcriptions = AudioUpload.objects.all()
    else:
        # Normal kullanıcı sadece kendi transcriptions'larını görebilir
        transcriptions = AudioUpload.objects.filter(user=request.user)
    
    return render(request, 'speech_app/list.html', {
        'transcriptions': transcriptions
    })

def enhance_audio_quality(audio_path):
    """
    Ses kalitesini iyileştiren fonksiyon
    """
    try:
        # Ses dosyasını yükle
        y, sr_rate = librosa.load(audio_path, sr=16000)  # 16kHz standardı
        
        # 1. Gürültü azaltma
        reduced_noise = nr.reduce_noise(y=y, sr=sr_rate, prop_decrease=0.8)
        
        # 2. Ses normalizasyonu
        normalized_audio = librosa.util.normalize(reduced_noise)
        
        # 3. Sessizlik temizleme
        trimmed_audio, _ = librosa.effects.trim(normalized_audio, top_db=20)
        
        # 4. Ses seviyesi dengeleme
        # RMS tabanlı ses seviyesi ayarı
        rms = librosa.feature.rms(y=trimmed_audio)[0]
        mean_rms = np.mean(rms)
        if mean_rms > 0:
            trimmed_audio = trimmed_audio / mean_rms * 0.1
        
        # İyileştirilmiş ses dosyasını geçici dosyaya kaydet
        enhanced_path = audio_path.replace('.wav', '_enhanced.wav')
        wavfile.write(enhanced_path, sr_rate, (trimmed_audio * 32767).astype(np.int16))
        
        return enhanced_path, True
        
    except Exception as e:
        logging.error(f"Ses iyileştirme hatası: {str(e)}")
        return audio_path, False

def transcribe_with_multiple_engines(audio_path, language_code):
    """
    Birden fazla speech recognition engine kullanarak transkripsiyon yapar
    """
    results = []
    recognizer = sr.Recognizer()
    
    # Ses kalitesini iyileştir
    enhanced_path, enhanced = enhance_audio_quality(audio_path)
    final_audio_path = enhanced_path if enhanced else audio_path
    
    try:
        with sr.AudioFile(final_audio_path) as source:
            recognizer.adjust_for_ambient_noise(source, duration=1)
            audio_data = recognizer.record(source)
        
        # 1. Google Speech Recognition (Ana)
        try:
            google_result = recognizer.recognize_google(
                audio_data, 
                language=language_code,
                show_all=False
            )
            if google_result:
                results.append({
                    'engine': 'Google',
                    'text': google_result,
                    'confidence': 0.9  # Google için varsayılan güven skoru
                })
                logging.info(f"Google başarılı: {len(google_result)} karakter")
        except Exception as e:
            logging.warning(f"Google API hatası: {str(e)}")
        
        # 2. Google Speech Recognition (Alternative)
        try:
            google_alt = recognizer.recognize_google(
                audio_data,
                language=language_code,
                show_all=True
            )
            if google_alt and 'alternative' in google_alt:
                for alt in google_alt['alternative'][:2]:  # İlk 2 alternatif
                    if 'transcript' in alt and alt['transcript']:
                        confidence = alt.get('confidence', 0.7)
                        results.append({
                            'engine': 'Google_Alt',
                            'text': alt['transcript'],
                            'confidence': confidence
                        })
        except Exception as e:
            logging.warning(f"Google alternatif API hatası: {str(e)}")
        
        # 3. Sphinx (Offline - fallback)
        try:
            sphinx_result = recognizer.recognize_sphinx(audio_data)
            if sphinx_result:
                results.append({
                    'engine': 'Sphinx',
                    'text': sphinx_result,
                    'confidence': 0.6  # Sphinx için düşük güven skoru
                })
                logging.info(f"Sphinx başarılı: {len(sphinx_result)} karakter")
        except Exception as e:
            logging.warning(f"Sphinx hatası: {str(e)}")
        
        # En iyi sonucu seç
        if results:
            # Güven skoruna ve metin uzunluğuna göre sıralama
            best_result = max(results, key=lambda x: (x['confidence'], len(x['text'])))
            
            # Eğer birden fazla sonuç varsa, en uzun ve güvenilir olanı seç
            filtered_results = [r for r in results if len(r['text']) > 10]  # Çok kısa metinleri filtrele
            if filtered_results:
                best_result = max(filtered_results, key=lambda x: x['confidence'])
            
            logging.info(f"En iyi sonuç: {best_result['engine']} (güven: {best_result['confidence']})")
            return best_result['text'], True
        else:
            return None, False
            
    except Exception as e:
        logging.error(f"Transkripsiyon hatası: {str(e)}")
        return None, False
    
    finally:
        # Geçici enhanced dosyayı temizle
        if enhanced and os.path.exists(enhanced_path):
            try:
                os.unlink(enhanced_path)
            except:
                pass

def process_audio_transcription(audio_upload):
    """
    Gelişmiş ses dosyası transkripsiyon fonksiyonu
    - Ses kalitesi iyileştirme
    - Birden fazla recognition engine
    - Akıllı parçalama ve birleştirme
    """
    try:
        logging.info(f"Transkripsiyon başlatıldı: {audio_upload.title}")
        
        # Dosya yolunu al
        audio_path = audio_upload.audio_file.path
        
        # Audio dosyasını yükle
        audio = AudioSegment.from_file(audio_path)
        
        # Ses dosyasının süresini hesapla
        duration_seconds = len(audio) / 1000.0
        audio_upload.duration = duration_seconds
        audio_upload.save()
        
        logging.info(f"Dosya süresi: {duration_seconds:.2f} saniye")
        
        # Ses kalitesi ön kontrolü ve düzeltme
        if audio.frame_rate < 16000:
            audio = audio.set_frame_rate(16000)
            logging.info("Ses dosyası 16kHz'e çevrildi")
        
        if audio.channels > 1:
            audio = audio.set_channels(1)  # Mono'ya çevir
            logging.info("Ses dosyası mono'ya çevrildi")
        
        # Adaptif parçalama - ses kalitesine göre parça boyutu ayarla
        base_chunk_length = 45 if duration_seconds > 300 else 60  # 5dk+ dosyalar için daha kısa parçalar
        chunk_length_ms = base_chunk_length * 1000
        
        # Overlap ekle - parçalar arası bilgi kaybını engelle
        overlap_ms = 5 * 1000  # 5 saniye overlap
        
        chunks = []
        for i in range(0, len(audio), chunk_length_ms - overlap_ms):
            end_pos = min(i + chunk_length_ms, len(audio))
            chunk = audio[i:end_pos]
            if len(chunk) > 10000:  # 10 saniyeden uzun parçaları al
                chunks.append(chunk)
        
        logging.info(f"Ses dosyası {len(chunks)} parçaya bölündü (parça boyutu: {base_chunk_length}s)")
        
        # Her parçayı gelişmiş transkripsiyon ile işle
        transcriptions = []
        temp_files = []
        successful_chunks = 0
        
        try:
            for i, chunk in enumerate(chunks):
                logging.info(f"Parça {i+1}/{len(chunks)} işleniyor...")
                
                # Geçici WAV dosyası oluştur
                with tempfile.NamedTemporaryFile(suffix=f'_chunk_{i}.wav', delete=False) as temp_wav:
                    # Ses kalitesini optimize et
                    optimized_chunk = chunk
                    
                    # Ses seviyesi çok düşükse yükselt
                    if chunk.dBFS < -30:
                        optimized_chunk = chunk + (abs(chunk.dBFS) - 20)
                        logging.info(f"Parça {i+1} ses seviyesi yükseltildi")
                    
                    # Çok yüksek ses seviyesini düşür
                    elif chunk.dBFS > -6:
                        optimized_chunk = chunk - (chunk.dBFS + 10)
                        logging.info(f"Parça {i+1} ses seviyesi düşürüldü")
                    
                    optimized_chunk.export(temp_wav.name, format='wav')
                    temp_wav_path = temp_wav.name
                    temp_files.append(temp_wav_path)
                
                # Gelişmiş transkripsiyon uygula
                try:
                    text, success = transcribe_with_multiple_engines(temp_wav_path, audio_upload.language)
                    
                    if success and text and len(text.strip()) > 0:
                        # Metin temizleme ve iyileştirme
                        cleaned_text = clean_and_improve_text(text.strip())
                        transcriptions.append(cleaned_text)
                        successful_chunks += 1
                        logging.info(f"Parça {i+1} başarılı: {len(cleaned_text)} karakter")
                    else:
                        logging.warning(f"Parça {i+1} sessiz veya tanınamadı")
                        
                except Exception as e:
                    logging.error(f"Parça {i+1} transkripsiyon hatası: {str(e)}")
                    continue
                
                # Çok büyük dosyalar için kısa bir mola
                if i > 0 and i % 10 == 0:
                    time.sleep(1)
            
            # Sonuçları değerlendir ve birleştir
            if transcriptions:
                # Akıllı metin birleştirme
                full_text = intelligent_text_joining(transcriptions)
                
                success_rate = (successful_chunks / len(chunks)) * 100
                quality_score = calculate_quality_score(full_text, success_rate, duration_seconds)
                
                # İstatistikleri veritabanına kaydet
                audio_upload.success_rate = success_rate
                audio_upload.quality_score = quality_score
                audio_upload.total_chunks = len(chunks)
                audio_upload.successful_chunks = successful_chunks
                audio_upload.processing_method = "Enhanced Multi-Engine"
                audio_upload.save()
                
                logging.info(f"Transkripsiyon tamamlandı. Başarı oranı: {success_rate:.1f}%, Kalite: {quality_score:.1f}")
                logging.info(f"Toplam metin uzunluğu: {len(full_text)} karakter")
                
                return {
                    'success': True,
                    'text': full_text,
                    'stats': {
                        'total_chunks': len(chunks),
                        'successful_chunks': successful_chunks,
                        'success_rate': success_rate,
                        'text_length': len(full_text)
                    }
                }
            else:
                return {
                    'success': False,
                    'error': 'Ses dosyasında hiç metin tespit edilemedi. Lütfen dosyanın konuşma içerdiğinden ve ses kalitesinin yeterli olduğundan emin olun.'
                }
                
        finally:
            # Tüm geçici dosyaları temizle
            for temp_file in temp_files:
                if os.path.exists(temp_file):
                    try:
                        os.unlink(temp_file)
                    except Exception as e:
                        logging.warning(f"Geçici dosya silinemedi {temp_file}: {str(e)}")
    
    except Exception as e:
        logging.error(f"Ana transkripsiyon hatası: {str(e)}")
        return {
            'success': False,
            'error': f'Ses dosyası işlenirken beklenmeyen hata oluştu: {str(e)}'
        }

def clean_and_improve_text(text):
    """
    Transkripsiyon metnini temizler ve iyileştirir
    """
    if not text:
        return ""
    
    # Temel temizlik
    cleaned = text.strip()
    
    # Çoklu boşlukları tek boşluğa çevir
    import re
    cleaned = re.sub(r'\s+', ' ', cleaned)
    
    # Türkçe karakterleri düzelt
    replacements = {
        'ğ': 'ğ', 'Ğ': 'Ğ',
        'ü': 'ü', 'Ü': 'Ü',
        'ş': 'ş', 'Ş': 'Ş',
        'ı': 'ı', 'İ': 'İ',
        'ö': 'ö', 'Ö': 'Ö',
        'ç': 'ç', 'Ç': 'Ç'
    }
    
    for old, new in replacements.items():
        cleaned = cleaned.replace(old, new)
    
    # İlk harfi büyük yap
    if cleaned:
        cleaned = cleaned[0].upper() + cleaned[1:] if len(cleaned) > 1 else cleaned.upper()
    
    return cleaned

def calculate_quality_score(text, success_rate, duration):
    """
    Transkripsiyon kalite skorunu hesaplar
    """
    if not text:
        return 0.0
    
    # Temel skor başarı oranından
    base_score = success_rate
    
    # Metin uzunluğu bonusu (daha uzun metin genellikle daha iyi)
    text_length_bonus = min(len(text) / 1000 * 10, 20)  # Max 20 puan
    
    # Kelime sayısı ve çeşitliliği
    words = text.split()
    word_count = len(words)
    unique_words = len(set(words))
    
    if word_count > 0:
        word_diversity = (unique_words / word_count) * 100
        diversity_bonus = min(word_diversity / 10, 15)  # Max 15 puan
    else:
        diversity_bonus = 0
    
    # Cümle yapısı kontrolü
    sentence_count = text.count('.') + text.count('!') + text.count('?')
    if sentence_count > 0:
        avg_sentence_length = word_count / sentence_count
        # İdeal cümle uzunluğu 10-20 kelime
        if 10 <= avg_sentence_length <= 20:
            sentence_bonus = 10
        elif 5 <= avg_sentence_length <= 30:
            sentence_bonus = 5
        else:
            sentence_bonus = 0
    else:
        sentence_bonus = 0
    
    # Süre bazında kalite (dakika başına kelime sayısı)
    if duration > 0:
        words_per_minute = (word_count / duration) * 60
        # Normal konuşma hızı 150-160 kelime/dakika
        if 120 <= words_per_minute <= 200:
            pace_bonus = 10
        elif 80 <= words_per_minute <= 250:
            pace_bonus = 5
        else:
            pace_bonus = 0
    else:
        pace_bonus = 0
    
    # Toplam skoru hesapla (max 100)
    total_score = min(
        base_score + text_length_bonus + diversity_bonus + sentence_bonus + pace_bonus,
        100.0
    )
    
    return round(total_score, 1)

def intelligent_text_joining(text_segments):
    """
    Metin parçalarını akıllıca birleştirir
    """
    if not text_segments:
        return ""
    
    if len(text_segments) == 1:
        return text_segments[0]
    
    result = []
    
    for i, segment in enumerate(text_segments):
        if not segment:
            continue
            
        if i == 0:
            result.append(segment)
        else:
            # Önceki segmentle overlap kontrolü
            prev_segment = result[-1] if result else ""
            
            # Son kelimeler benzer mi kontrol et
            prev_words = prev_segment.split()[-3:] if prev_segment else []
            curr_words = segment.split()[:3] if segment else []
            
            # Overlap varsa tekrarı kaldır
            overlap_found = False
            if prev_words and curr_words:
                for j in range(1, min(len(prev_words), len(curr_words)) + 1):
                    if prev_words[-j:] == curr_words[:j]:
                        # Overlap bulundu, tekrarı kaldır
                        segment = ' '.join(curr_words[j:])
                        overlap_found = True
                        break
            
            if segment.strip():
                # Cümle sonu kontrolü
                if result and not result[-1].endswith(('.', '!', '?')):
                    if not segment[0].isupper():
                        result.append(' ' + segment)
                    else:
                        result.append('. ' + segment)
                else:
                    result.append(' ' + segment)
    
    return ''.join(result).strip()

@csrf_exempt
def live_transcription(request):
    """Canlı mikrofon kaydı için API endpoint"""
    if request.method == 'POST':
        try:
            # Bu endpoint gelecekte canlı transkripsiyon için kullanılabilir
            return JsonResponse({'status': 'success', 'message': 'Canlı transkripsiyon özelliği geliştirme aşamasında'})
        except Exception as e:
            return JsonResponse({'status': 'error', 'message': str(e)})
    
    return JsonResponse({'status': 'error', 'message': 'Sadece POST istekleri kabul edilir'})
