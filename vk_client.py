import requests
from datetime import datetime
from typing import Dict, List, Tuple

class VKClient:
    """Класс для взаимодействия с API ВКонтакте от лица пользователя."""
    
    def __init__(self, user_token: str, version: str = '5.131'):
        self.token = user_token
        self.version = version
        self.base_url = 'https://api.vk.com/method/'

    def _get_headers(self) -> Dict[str, str]:
        return {
            'Authorization': f'Bearer {self.token}'
        }

    def get_user_info(self, vk_id: int) -> Dict:
        """
        Получает информацию о пользователе (имя, пол, город, возраст),
        которому бот будет искать пару.
        """
        url = f'{self.base_url}users.get'
        params = {
            'user_ids': vk_id,
            'fields': 'bdate, sex, city',
            'v': self.version
        }
        response = requests.get(url, headers=self._get_headers(), params=params).json()
        
        if 'error' in response:
            print(f"Ошибка получения данных пользователя: {response['error']}")
            return {}

        user_data = response['response'][0]
        
        # Вычисляем возраст, если указана полная дата рождения
        age = None
        if 'bdate' in user_data and len(user_data['bdate'].split('.')) == 3:
            bdate = datetime.strptime(user_data['bdate'], '%d.%m.%Y')
            age = (datetime.now() - bdate).days // 365

        return {
            'vk_id': user_data['id'],
            'first_name': user_data['first_name'],
            'last_name': user_data['last_name'],
            'sex': user_data.get('sex', 0),  # 1 - жен, 2 - муж, 0 - не указан
            'city_id': user_data.get('city', {}).get('id', None),
            'age': age
        }

    def search_users(self, city_id: int, sex: int, age: int, offset: int = 0) -> List[Dict]:
        """
        Ищет людей противоположного пола в том же городе и того же возраста.
        Использует offset для обхода лимита в 1000 пользователей.
        """
        url = f'{self.base_url}users.search'
        opposite_sex = 1 if sex == 2 else 2 if sex == 1 else 0
        
        params = {
            'city': city_id,
            'sex': opposite_sex,
            'age_from': age - 2 if age else None, # Ищем ровесников +/- 2 года
            'age_to': age + 2 if age else None,
            'has_photo': 1, # Только с фото
            'status': 1,    # 1 - Не женат/Не замужем, 6 - В активном поиске
            'count': 50,    # Берем пачками по 50
            'offset': offset,
            'fields': 'screen_name',
            'v': self.version
        }
        
        response = requests.get(url, headers=self._get_headers(), params=params).json()
        if 'error' in response:
            return []
            
        return response['response']['items']

    def get_top_photos(self, owner_id: int) -> Tuple[List[str], bool]:
        """
        Получает 3 самые популярные фотографии профиля пользователя.
        Возвращает список attachment-строк и флаг успешности.
        """
        url = f'{self.base_url}photos.get'
        params = {
            'owner_id': owner_id,
            'album_id': 'profile',
            'extended': 1, # Чтобы получить количество лайков
            'photo_sizes': 0,
            'v': self.version
        }
        
        response = requests.get(url, headers=self._get_headers(), params=params).json()
        
        if 'error' in response:
            # Ошибка 30 - профиль закрыт настройками приватности
            return [], False
            
        photos = response['response']['items']
        
        # Сортируем фотографии по количеству лайков по убыванию
        photos.sort(key=lambda x: x['likes']['count'], reverse=True)
        
        # Берем топ-3 фото и формируем строки для attachment в формате photo{owner_id}_{photo_id}
        top_3 = photos[:3]
        attachments = [f"photo{photo['owner_id']}_{photo['id']}" for photo in top_3]
        
        return attachments, True