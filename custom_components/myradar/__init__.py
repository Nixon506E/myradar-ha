"""The myRadar component."""
from __future__ import annotations

import logging
from typing import Any

import voluptuous as vol
import homeassistant.helpers.config_validation as cv
from homeassistant.helpers.entity_registry import EntityRegistry

from datetime import timedelta
import forecastio

from homeassistant.config_entries import SOURCE_IMPORT, ConfigEntry


from homeassistant.const import (
    CONF_API_KEY,
    CONF_LATITUDE,
    CONF_LONGITUDE,
    CONF_MODE,
    CONF_NAME,
    CONF_MONITORED_CONDITIONS,
    CONF_SCAN_INTERVAL,
)
from homeassistant.core import HomeAssistant

from .const import (
    CONF_LANGUAGE,
    CONFIG_FLOW_VERSION,
    DOMAIN,
    DEFAULT_FORECAST_MODE,
    ENTRY_NAME,
    ENTRY_WEATHER_COORDINATOR,
    FORECAST_MODES,
    PLATFORMS,
    UPDATE_LISTENER,
    CONF_UNITS,
    DEFAULT_UNITS,
    DEFAULT_NAME,
    FORECASTS_HOURLY,
    FORECASTS_DAILY,
    MR_PLATFORMS,
    MR_PLATFORM, 
    MR_PREVPLATFORM,   
    MR_ROUND,
)

CONF_FORECAST = "forecast"
CONF_HOURLY_FORECAST = "hourly_forecast"

#from .weather_update_coordinator import WeatherUpdateCoordinator, DarkSkyData
from .weather_update_coordinator import WeatherUpdateCoordinator

_LOGGER = logging.getLogger(__name__)
ATTRIBUTION = "Powered by myRadar"


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up myRadar as config entry."""
    name = entry.data[CONF_NAME]
    api_key = entry.data[CONF_API_KEY]
    latitude = entry.data.get(CONF_LATITUDE, hass.config.latitude)
    longitude = entry.data.get(CONF_LONGITUDE, hass.config.longitude)
    forecast_mode = _get_config_value(entry, CONF_MODE)
    language = _get_config_value(entry, CONF_LANGUAGE)
    conditions = _get_config_value(entry, CONF_MONITORED_CONDITIONS)
    units = _get_config_value(entry, CONF_UNITS)
    forecast_days = _get_config_value(entry, CONF_FORECAST)
    forecast_hours = _get_config_value(entry, CONF_HOURLY_FORECAST)
    mr_entity_platform = _get_config_value(entry, MR_PLATFORM)
    mr_entity_rounding = _get_config_value(entry, MR_ROUND)
    mr_scan_Int = entry.data[CONF_SCAN_INTERVAL]
    
    
    # Extract list of int from forecast days/ hours string if present
    #_LOGGER.warning('forecast_days_type: ' + str(type(forecast_days)))
    
    #_LOGGER.warning(forecast_days)
    if type(forecast_days) == str:
      # If empty, set to none
      if forecast_days  == "" or forecast_days  == "None":
        forecast_days = None
      else:
        if forecast_days[0] == '[':
          forecast_days = forecast_days[1:-1].split(",")
        else:    
          forecast_days = forecast_days.split(",")
        forecast_days = [int(i) for i in forecast_days]
        
    if type(forecast_hours) == str:
    # If empty, set to none
      if forecast_hours == "" or forecast_hours  == "None":
        forecast_hours = None
      else:
        if forecast_hours[0] == '[':
          forecast_hours = forecast_hours[1:-1].split(",")
        else:    
          forecast_hours = forecast_hours.split(",")
        forecast_hours = [int(i) for i in forecast_hours]
      
    unique_location = (f"myradar-{latitude}-{longitude}")
    
    hass.data.setdefault(DOMAIN, {})
    # If coordinator already exists for this API key, we'll use that, otherwise
    # we have to create a new one
    if unique_location in hass.data[DOMAIN]:
      weather_coordinator = hass.data[DOMAIN].get(unique_location)
      _LOGGER.info('An existing weather coordinator already exists for this location. Using that one instead')  
    else:
      weather_coordinator = WeatherUpdateCoordinator(api_key, latitude, longitude, timedelta(seconds=mr_scan_Int), hass)
      hass.data[DOMAIN][unique_location] = weather_coordinator    
      #_LOGGER.warning('New Coordinator') 

    #await weather_coordinator.async_refresh()
    await weather_coordinator.async_config_entry_first_refresh()
    
    
    hass.data[DOMAIN][entry.entry_id] = {
        ENTRY_NAME: name,
        ENTRY_WEATHER_COORDINATOR: weather_coordinator,
        CONF_API_KEY: api_key,
        CONF_LATITUDE: latitude,
        CONF_LONGITUDE: longitude,
        CONF_UNITS: units,
        CONF_MONITORED_CONDITIONS: conditions,
        CONF_MODE: forecast_mode,
        CONF_FORECAST: forecast_days,
        CONF_HOURLY_FORECAST: forecast_hours,
        MR_PLATFORM: mr_entity_platform,
        MR_ROUND: mr_entity_rounding,
        CONF_SCAN_INTERVAL: mr_scan_Int,
    }

    # If both platforms
    if  (MR_PLATFORMS[0] in mr_entity_platform) and (MR_PLATFORMS[1] in mr_entity_platform):
      await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    # If only sensor  
    elif MR_PLATFORMS[0] in mr_entity_platform:
      await hass.config_entries.async_forward_entry_setup(entry, PLATFORMS[0])
    # If only weather
    elif MR_PLATFORMS[1] in mr_entity_platform:
      await hass.config_entries.async_forward_entry_setup(entry, PLATFORMS[1])
    
    
    update_listener = entry.add_update_listener(async_update_options)
    hass.data[DOMAIN][entry.entry_id][UPDATE_LISTENER] = update_listener
    return True


async def async_update_options(hass: HomeAssistant, entry: ConfigEntry) -> None:
    """Update options."""
    await hass.config_entries.async_reload(entry.entry_id)

  

async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Unload a config entry."""
    
    mr_entity_prevplatform = hass.data[DOMAIN][entry.entry_id][MR_PLATFORM]

    
    # If both
    if (MR_PLATFORMS[0] in mr_entity_prevplatform) and (MR_PLATFORMS[1] in mr_entity_prevplatform):
      unload_ok = await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
    # If only sensor
    elif MR_PLATFORMS[0] in mr_entity_prevplatform:
      unload_ok = await hass.config_entries.async_unload_platforms(entry, [PLATFORMS[0]])
    # If only Weather
    elif MR_PLATFORMS[1] in mr_entity_prevplatform:
      unload_ok = await hass.config_entries.async_unload_platforms(entry, [PLATFORMS[1]])
    
    _LOGGER.info('Unloading myRadar')
    
    if unload_ok:
        update_listener = hass.data[DOMAIN][entry.entry_id][UPDATE_LISTENER]
        update_listener()
         
        hass.data[DOMAIN].pop(entry.entry_id)
    
    
    return unload_ok


def _get_config_value(config_entry: ConfigEntry, key: str) -> Any:
    if config_entry.options:
        return config_entry.options[key]
    return config_entry.data[key]


def _filter_domain_configs(elements, domain):
    return list(filter(lambda elem: elem["platform"] == domain, elements))
