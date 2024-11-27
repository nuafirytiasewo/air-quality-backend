# crud.py
from sqlalchemy.orm import Session
from app.db.models import User, Subscription, Location, MapCache
from sqlalchemy.exc import NoResultFound
from config import MAP_DATA_TTL
import datetime
from worker import force_update_database
import logging


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

    # Удаляем существующую подписку если она имеется
    subscription = db.query(Subscription).filter(Subscription.user_id == tg_user.id).first()
    if subscription:
        delete_subscription(db, tg_user.id)

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

def add_locations_from_csv(db: Session, locations_data: list[list[str]]) -> int:
    count = 0
    try:
        for data in locations_data[1:]:
            city, longitude, latitude, radius = data
            location_exists = db.query(Location).filter(Location.city == city).first()
            if location_exists:
                logging.info(f"Город {city} уже существует в таблице Map")
                continue
            location = Location(
                city=city,
                longitude=float(longitude),
                latitude=float(latitude),
                radius=int(radius.rstrip('\r')),
                created_by="default"
            )
            db.add(location)
            count += 1
        db.commit()
        return count
    except Exception as e:
        logging.error(f"Произошла ошибка при добавлении данных в таблицу map: {e}")
        return 0
    force_update_database()


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
    if not subscription:
        return False

    location = db.query(Location).filter(Location.id == subscription.location_id).first()

    if location.created_by == "telegram_user":
        db.query(MapCache).filter(MapCache.location_id == location.id).delete()
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

def get_all_locations(db: Session) -> list[Location]:
    return db.query(Location).all()

def update_map_cache(db: Session, location_info: dict, location: Location) -> Location:
    map_cache = db.query(MapCache).filter(MapCache.location_id == location.id).first()

    if not map_cache:
        map_cache = MapCache(
            location_id=location.id,
            expiration_date=datetime.datetime.utcfromtimestamp(location_info['list'][0]['dt'] + MAP_DATA_TTL),
            co=location_info['list'][0]['components']['co'],
            no=location_info['list'][0]['components']['no'],
            no2=location_info['list'][0]['components']['no2'],
            o3=location_info['list'][0]['components']['o3'],
            so2=location_info['list'][0]['components']['so2'],
            pm2_5=location_info['list'][0]['components']['pm2_5'],
            pm10=location_info['list'][0]['components']['pm10'],
            nh3=location_info['list'][0]['components']['nh3']
        )
        db.add(map_cache)
        db.commit()
        db.refresh(map_cache)
        return location

    map_cache.expiration_date = datetime.datetime.utcfromtimestamp(location_info['list'][0]['dt'] + MAP_DATA_TTL)
    map_cache.co =              location_info['list'][0]['components']['co']
    map_cache.no =              location_info['list'][0]['components']['no']
    map_cache.no2 =             location_info['list'][0]['components']['no2']
    map_cache.o3 =              location_info['list'][0]['components']['o3']
    map_cache.so2 =             location_info['list'][0]['components']['so2']
    map_cache.pm2_5 =           location_info['list'][0]['components']['pm2_5']
    map_cache.pm10 =            location_info['list'][0]['components']['pm10']
    map_cache.nh3 =             location_info['list'][0]['components']['nh3']

    db.commit()
    db.refresh(location)
    return location

def get_map_cache(db: Session) -> list[Location]:
    return db.query(MapCache).all()
