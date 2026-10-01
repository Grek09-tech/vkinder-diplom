import os
import vk_api
from vk_api.longpoll import VkLongPoll, VkEventType
from vk_api.keyboard import VkKeyboard, VkKeyboardColor
from dotenv import load_dotenv
# Импортируем наши модули
from vk_client import VKClient
from db_models import InteractionStatus
from db_crud import add_candidate_interaction, get_viewed_vk_ids, get_favorites

# Загружаем переменные из .env
load_dotenv()

# Получаем токены
GROUP_TOKEN = os.getenv('GROUP_TOKEN', 'твой_токен_группы')
USER_TOKEN = os.getenv('USER_TOKEN', 'твой_токен_пользователя')

# Инициализация API
vk_group = vk_api.VkApi(token=GROUP_TOKEN)
longpoll = VkLongPoll(vk_group)
vk_user_client = VKClient(user_token=USER_TOKEN)

# Словарь для хранения текущего просматриваемого кандидата для каждого пользователя
# Формат: {user_vk_id: candidate_dict}
current_view = {}

def create_keyboard() -> str:
    """Генерирует клавиатуру с кнопками для взаимодействия."""
    keyboard = VkKeyboard(one_time=False)
    
    keyboard.add_button('Поиск', color=VkKeyboardColor.PRIMARY)
    keyboard.add_button('Дальше', color=VkKeyboardColor.SECONDARY)
    keyboard.add_line()  # Переход на новую строку
    keyboard.add_button('Лайк', color=VkKeyboardColor.POSITIVE)
    keyboard.add_button('В ЧС', color=VkKeyboardColor.NEGATIVE)
    keyboard.add_line()
    keyboard.add_button('Список избранных', color=VkKeyboardColor.PRIMARY)
    
    return keyboard.get_keyboard()

def send_message(user_id: int, message: str, attachment: str = None):
    """Функция для отправки сообщений от лица группы."""
    vk_group.method('messages.send', {
        'user_id': user_id,
        'message': message,
        'attachment': attachment,
        'random_id': 0,
        'keyboard': create_keyboard()
    })

def find_next_candidate(user_id: int):
    """Ищет следующего кандидата, которого еще не было в БД."""
    send_message(user_id, "Ищу подходящего кандидата... ⏳")
    
    user_info = vk_user_client.get_user_info(user_id)
    if not user_info.get('city_id') or not user_info.get('age'):
        send_message(user_id, "У вас в профиле не указан город или возраст. "
                              "Пожалуйста, заполните их для корректного поиска.")
        return

    viewed_ids = set(get_viewed_vk_ids(user_id))
    offset = 0
    
    while True:
        candidates = vk_user_client.search_users(
            city_id=user_info['city_id'],
            sex=user_info['sex'],
            age=user_info['age'],
            offset=offset
        )
        
        if not candidates:
            send_message(user_id, "Кандидаты закончились или произошла ошибка поиска.")
            return

        for candidate in candidates:
            # Пропускаем закрытые профили и тех, кого уже видели
            if candidate['is_closed'] or candidate['id'] in viewed_ids:
                continue

            # Пытаемся получить фото
            photos, success = vk_user_client.get_top_photos(candidate['id'])
            if success and len(photos) > 0:
                # Кандидат найден!
                cand_data = {
                    'vk_id': candidate['id'],
                    'first_name': candidate['first_name'],
                    'last_name': candidate['last_name'],
                    'link': f"https://vk.com/id{candidate['id']}"
                }
                
                # Сохраняем в память бота, чтобы знать, кого лайкаем
                current_view[user_id] = cand_data
                
                msg = f"{cand_data['first_name']} {cand_data['last_name']}\n{cand_data['link']}"
                attachment = ','.join(photos)
                
                send_message(user_id, msg, attachment)
                return

        offset += 50  # Если в пачке из 50 человек все просмотрены, берем следующих

def main():
    """Основной цикл бота."""
    print("Бот запущен и готов к работе...")
    
    for event in longpoll.listen():
        if event.type == VkEventType.MESSAGE_NEW and event.to_me:
            text = event.text.lower()
            user_id = event.user_id

            if text in ['привет', 'поиск', 'дальше']:
                # Если человек нажал "Дальше", заносим предыдущего в статус VIEWED
                if text == 'дальше' and user_id in current_view:
                    add_candidate_interaction(user_id, current_view[user_id], InteractionStatus.VIEWED)
                find_next_candidate(user_id)

            elif text == 'лайк':
                if user_id in current_view:
                    add_candidate_interaction(user_id, current_view[user_id], InteractionStatus.FAVORITE)
                    send_message(user_id, "Кандидат добавлен в избранное! ❤️")
                    find_next_candidate(user_id)
                else:
                    send_message(user_id, "Сначала нажмите 'Поиск'.")

            elif text == 'в чс':
                if user_id in current_view:
                    add_candidate_interaction(user_id, current_view[user_id], InteractionStatus.BLACKLISTED)
                    send_message(user_id, "Кандидат скрыт и больше не появится. 🚫")
                    find_next_candidate(user_id)
                else:
                    send_message(user_id, "Сначала нажмите 'Поиск'.")

            elif text == 'список избранных':
                favorites = get_favorites(user_id)
                if not favorites:
                    send_message(user_id, "Ваш список избранного пока пуст.")
                else:
                    msg = "Ваши избранные кандидаты:\n\n"
                    for fname, lname, link in favorites:
                        msg += f"• {fname} {lname} - {link}\n"
                    send_message(user_id, msg)
            
            else:
                send_message(user_id, "Неизвестная команда. Воспользуйтесь кнопками ниже.")

if __name__ == '__main__':
    main()