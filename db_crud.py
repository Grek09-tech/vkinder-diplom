from db_models import Session, User, Candidate, Interaction, InteractionStatus
from typing import List, Tuple

def get_or_create_user(session, vk_id: int) -> User:
    """Получает пользователя из БД или создает нового."""
    user = session.query(User).filter_by(vk_id=vk_id).first()
    if not user:
        user = User(vk_id=vk_id)
        session.add(user)
        session.commit()
    return user

def add_candidate_interaction(user_vk_id: int, candidate_data: dict, status: InteractionStatus):
    """Добавляет кандидата в БД и записывает действие пользователя (лайк/чс/пропуск)."""
    with Session() as session:
        user = get_or_create_user(session, user_vk_id)
        
        # Ищем кандидата, если нет - создаем
        candidate = session.query(Candidate).filter_by(vk_id=candidate_data['vk_id']).first()
        if not candidate:
            candidate = Candidate(
                vk_id=candidate_data['vk_id'],
                first_name=candidate_data['first_name'],
                last_name=candidate_data['last_name'],
                profile_link=candidate_data['link']
            )
            session.add(candidate)
            session.flush() # Получаем id кандидата до коммита
            
        # Записываем взаимодействие
        interaction = Interaction(user_id=user.id, candidate_id=candidate.id, status=status)
        session.add(interaction)
        session.commit()

def get_viewed_vk_ids(user_vk_id: int) -> List[int]:
    """Возвращает список vk_id кандидатов, которых пользователь уже видел."""
    with Session() as session:
        user = session.query(User).filter_by(vk_id=user_vk_id).first()
        if not user:
            return []
            
        viewed = session.query(Candidate.vk_id).join(Interaction).filter(
            Interaction.user_id == user.id
        ).all()
        
        return [item[0] for item in viewed]

def get_favorites(user_vk_id: int) -> List[Tuple[str, str, str]]:
    """Возвращает список избранных кандидатов для вывода в чат."""
    with Session() as session:
        user = session.query(User).filter_by(vk_id=user_vk_id).first()
        if not user:
            return []
            
        favorites = session.query(Candidate).join(Interaction).filter(
            Interaction.user_id == user.id,
            Interaction.status == InteractionStatus.FAVORITE
        ).all()
        
        return [(f.first_name, f.last_name, f.profile_link) for f in favorites]