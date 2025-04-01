import os
from dotenv import load_dotenv
from supabase import create_client, Client
import requests
from datetime import datetime, timedelta
import pytz
import time
from dateutil import parser

# Загружаем переменные окружения из .env файла
load_dotenv()

# Инициализация Supabase клиента
SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_SERVICE_ROLE_KEY")

if not SUPABASE_URL or not SUPABASE_KEY:
    raise Exception("Необходимо указать SUPABASE_URL и SUPABASE_SERVICE_ROLE_KEY в .env файле")

supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)

def get_users_with_spotify():
    """Получает всех пользователей, у которых есть подключение к Spotify"""
    try:
        response = supabase.table("users").select(
            "id", 
            "spotify_access_token", 
            "spotify_refresh_token",
            "spotify_token_expires_at"
        ).filter("spotify_connected", "eq", True).execute()
        
        if not response.data:
            print("Пользователи с подключенным Spotify не найдены")
            return []
            
        return response.data
    except Exception as e:
        print(f"Ошибка при получении пользователей с Spotify: {e}")
        return []

def refresh_spotify_token(user_id: str, refresh_token: str):
    """Обновляет access token для Spotify"""
    try:
        SPOTIFY_CLIENT_ID = os.getenv("SPOTIFY_CLIENT_ID")
        SPOTIFY_CLIENT_SECRET = os.getenv("SPOTIFY_CLIENT_SECRET")
        
        response = requests.post(
            "https://accounts.spotify.com/api/token",
            data={
                "grant_type": "refresh_token",
                "refresh_token": refresh_token,
                "client_id": SPOTIFY_CLIENT_ID,
                "client_secret": SPOTIFY_CLIENT_SECRET
            }
        )
        
        response.raise_for_status()
        token_data = response.json()
        
        # Обновляем данные в Supabase
        expires_at = datetime.now() + timedelta(seconds=token_data["expires_in"])
        supabase.table("users").update({
            "spotify_access_token": token_data["access_token"],
            "spotify_token_expires_at": expires_at.isoformat(),
            "spotify_last_updated": datetime.now().isoformat()
        }).eq("id", user_id).execute()
        
        print(f"Токен для пользователя {user_id} успешно обновлен.")
        return token_data["access_token"]
        
    except requests.exceptions.HTTPError as http_err:
        print(f"HTTP ошибка при обновлении токена для пользователя {user_id}: {http_err}")
    except Exception as e:
        print(f"Ошибка при обновлении токена Spotify для пользователя {user_id}: {e}")
    return None

def get_current_track(access_token: str):
    """Получает текущий трек пользователя из Spotify API"""
    try:
        print(f"Используемый access token: {access_token}")  # Логируем токен
        headers = {
            "Authorization": f"Bearer {access_token}"
        }
        
        response = requests.get(
            "https://api.spotify.com/v1/me/player/currently-playing",
            headers=headers
        )
        
        if response.status_code == 204:
            return None
            
        response.raise_for_status()
        return response.json()
        
    except Exception as e:
        print(f"Ошибка при получении текущего трека: {e}")
        return None

def update_user_track_info(user):
    """Обновляет информацию о текущем треке для одного пользователя"""
    user_id = user["id"]
    
    # Проверяем, есть ли access token
    if not user.get("spotify_access_token"):
        print(f"У пользователя {user_id} нет access token для Spotify")
        return
    
    # Проверяем, не истек ли access token
    token_expires_at = user.get("spotify_token_expires_at")
    if token_expires_at:
        try:
            # Преобразуем строку в datetime объект, используя dateutil.parser
            expires_at = parser.isoparse(token_expires_at)
            # Создаем timezone-aware объект для текущего времени в UTC
            current_time = datetime.now(pytz.UTC)
            if current_time >= expires_at:
                print(f"Access token пользователя {user_id} истек, обновляем...")
                new_token = refresh_spotify_token(user_id, user["spotify_refresh_token"])
                if not new_token:
                    return
                user["spotify_access_token"] = new_token
            else:
                print(f"Access token пользователя {user_id} действителен.")
        except ValueError as e:
            print(f"Ошибка при обработке даты истечения токена для пользователя {user_id}: {e}")
    
    # Получаем текущий трек
    current_track = get_current_track(user["spotify_access_token"])
    
    # Определяем, слушает ли пользователь что-то в данный момент
    is_listening = current_track is not None
    
    # Обновляем базовую информацию о статусе прослушивания
    update_data = {
        "is_listening": is_listening,
        "spotify_last_updated": datetime.now(pytz.UTC).isoformat()
    }
    
    if current_track:
        artist_names = ', '.join([artist['name'] for artist in current_track['item']['artists']])
        track_name = current_track['item']['name']
        album_name = current_track['item']['album']['name']
        
        print(f"Пользователь {user_id} слушает:")
        print(f"Исполнитель: {artist_names}")
        print(f"Трек: {track_name}")
        print(f"Альбом: {album_name}")
        
        album_image_url = current_track['item']['album']['images'][0]['url'] if current_track['item']['album']['images'] else None
        
        # Добавляем информацию о треке в данные для обновления
        update_data.update({
            "current_track_name": track_name,
            "current_track_artist": artist_names,
            "current_track_album_url": album_image_url,
            "current_track_progress_ms": current_track['progress_ms'],
            "current_track_duration_ms": current_track['item']['duration_ms']
        })
    else:
        print(f"Пользователь {user_id} ничего не слушает в данный момент")
    
    # Удаляем None значения
    update_data = {k: v for k, v in update_data.items() if v is not None}
    
    try:
        response = supabase.table("users").update(update_data).eq("id", user_id).execute()
        if response.data:
            print(f"Данные пользователя {user_id} успешно обновлены")
        else:
            print(f"Проблема при обновлении данных пользователя {user_id}")
    except Exception as e:
        print(f"Ошибка при обновлении данных пользователя {user_id}: {str(e)}")

def main(loop_interval=60):
    """
    Основная функция, которая в цикле обновляет данные всех пользователей с Spotify
    
    Args:
        loop_interval: Интервал между циклами обновления в секундах
    """
    print(f"Запуск сервиса обновления данных Spotify. Интервал обновления: {loop_interval} секунд")
    
    try:
        while True:
            print("\n" + "="*50)
            print(f"Запуск цикла обновления: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
            
            # Получаем всех пользователей с подключенным Spotify
            users = get_users_with_spotify()
            print(f"Найдено {len(users)} пользователей с подключенным Spotify")
            
            # Обновляем данные для каждого пользователя
            for user in users:
                print("-"*40)
                print(f"Обработка пользователя: {user['id']}")
                update_user_track_info(user)
            
            print("="*50)
            print(f"Цикл обновления завершен. Следующее обновление через {loop_interval} секунд")
            
            # Ждем до следующего обновления
            time.sleep(loop_interval)
            
    except KeyboardInterrupt:
        print("\nПрограмма остановлена пользователем")
    except Exception as e:
        print(f"Критическая ошибка: {str(e)}")

if __name__ == "__main__":
    # Запускаем основной цикл с интервалом 60 секунд
    main(60)