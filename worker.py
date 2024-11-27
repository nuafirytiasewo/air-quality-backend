from air_quality import get_air_pollution_data
from sqlalchemy.orm import Session
from app.db.database import get_db
from datetime import datetime
from config import MAP_DATA_UPDATE_INTERVAL
from app.db import crud
import asyncio
import logging

async def update_database():
    while True:
        logging.info(f"Обновление данных таблицы map")
        with get_db() as db:
            locations = crud.get_all_locations(db)
            for location in locations:
                coordinates = {"lat": location.latitude, "lon": location.longitude}
                location_info = await get_air_pollution_data(coordinates['lat'], coordinates['lon'])
                crud.update_map_cache(db, location_info, location)
                crud.update_location_aqi(db, coordinates, location_info['list'][0]['main']['aqi'])

        # Задержка перед следующим обновлением
        await asyncio.sleep(MAP_DATA_UPDATE_INTERVAL)

async def force_update_database():
    logging.info(f"Запущено обновление данных таблицы map")
    with get_db() as db:
        locations = crud.get_all_locations(db)
        for location in locations:
            coordinates = {"lat": location.latitude, "lon": location.longitude}
            location_info = await get_air_pollution_data(coordinates['lat'], coordinates['lon'])
            crud.update_map_cache(db, location_info, location)
            crud.update_location_aqi(db, coordinates, location_info['list'][0]['main']['aqi'])
