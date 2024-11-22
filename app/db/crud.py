# crud.py
from sqlalchemy.orm import Session
from app.db.models import User, Subscription, Location
from sqlalchemy.exc import NoResultFound


def create_or_update_subscription(
    db: Session, tg_user: dict, coordinates: dict, city: str, current_aqi: int
) -> Subscription:
    # Проверяем, существует ли пользователь с указанным telegram_id
    user = db.query(User).filter(User.id == tg_user.id).first()

    if not user:
        # Если пользователя нет, создаем его
        user = User(
            id=tg_user.id, 
            username=tg_user.username, 
            first_name=tg_user.first_name, 
            last_name=tg_user.last_name
            )
        db.add(user)
        db.commit()
        db.refresh(user)

    # Проверяем, существует ли локация с указанными данными
    location = (
        db.query(Location)
        .filter(
            Location.city == city, 
            Location.longitude == coordinates['lon'], 
            Location.latitude == coordinates['lat'])
        .first()
    )

    if not location:
        # Если локации нет, создаем новую
        location = Location(
            city=city, 
            longitude=coordinates['lon'], 
            latitude=coordinates['lat'], 
            aqi=current_aqi,
            created_by="telegram_user"
        )
        db.add(location)
        db.commit()
        db.refresh(location)

    # Проверяем, существует ли подписка для данного пользователя и локации
    subscription = (
        db.query(Subscription)
        .filter(
            Subscription.user_id == user.id, 
            Subscription.location_id == location.id)
        .first()
    )

    if subscription:
        # Если подписка существует, обновляем её
        subscription.location.aqi = current_aqi  # Обновляем AQI локации
        db.commit()
        db.refresh(subscription)
        return subscription

    # Если подписки нет, создаем новую
    new_subscription = Subscription(
        user_id=user.id, 
        location_id=location.id
        )
    db.add(new_subscription)
    db.commit()
    db.refresh(new_subscription)

    return new_subscription


def get_all_users(db: Session) -> list[Subscription]:
    return db.query(User).all()

def update_location_aqi(db: Session, coordinates: dict, current_aqi: int) -> Subscription:
    location = (
        db.query(Location)
        .filter(
            Location.longitude == coordinates['lon'], 
            Location.latitude == coordinates['lat'])
        .first()
    )
    location.aqi = current_aqi
    db.commit()
    db.refresh(location)
    return location

# Delete
def delete_subscription(db: Session, telegram_id: int) -> bool:
    subscription = db.query(Subscription).filter(Subscription.user_id == telegram_id).first()
    if not Subscription:
        return False

    location = db.query(Location).filter(Location.id == subscription.location_id).first()

    if location.created_by == "telegram_user":
        db.delete(location)
    db.delete(subscription)
    db.commit()
    return True



# Получение подписки по telegram_id
def get_subscription_by_telegram_id(db: Session, telegram_id: int) -> User:
    user = db.query(User).filter(User.id == telegram_id).first()    
    if not user:
        return None

    # Обновляем объект, чтобы он снова был привязан к сессии
    db.refresh(user)  # Это позволяет убедиться, что атрибуты объекта доступны

    return user