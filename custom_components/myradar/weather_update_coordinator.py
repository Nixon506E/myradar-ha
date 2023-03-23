"""Weather data coordinator for the myRadar service."""
from datetime import timedelta
import logging

import async_timeout
import forecastio
from forecastio.models import Forecast
import json
import aiohttp
import asyncio

from requests.exceptions import ConnectionError as ConnectError, HTTPError, Timeout
import voluptuous as vol

from homeassistant.helpers import sun
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed
from homeassistant.util import dt


from .const import (
    DOMAIN,
)

_LOGGER = logging.getLogger(__name__)

ATTRIBUTION = "Powered by myRadar"

        
class WeatherUpdateCoordinator(DataUpdateCoordinator):
    """Weather data update coordinator."""

    def __init__(self, api_key, latitude, longitude, mr_scan_Int, hass):
        """Initialize coordinator."""
        self._api_key = api_key
        self.latitude = latitude
        self.longitude = longitude
        self.mr_scan_Int = mr_scan_Int
        self.requested_units = "si"
        self.language = "en"
        self.extend_forecast = True
        
        self.data = None
        self.currently = None
        self.hourly = None
        self.daily = None
        self._connect_error = False

        super().__init__(
            hass, _LOGGER, name=DOMAIN, update_interval=mr_scan_Int
        )
               
                 
                        
    async def _async_update_data(self):
        """Update the data."""
        data = {}
        async with async_timeout.timeout(30):
            try:
                data = await self._get_myradar_weather()
            except Exception as error:
                raise UpdateFailed(error) from error
        return data


    async def _get_myradar_weather(self):
        """Poll weather data from myRadar."""   
        
        headers={
            "Cache-Control": "no-cache",
            "Subscription-Key": self._api_key,
        }
             
        forecastString = "https://api.myradar.dev/forecast/" + str(self.latitude) + "," + str(self.longitude) + "?units=" + self.requested_units + "&lang=" + self.language
        if self.extend_forecast:
            forecastString += "&extend=hourly"
        
        async with aiohttp.ClientSession(headers=headers, raise_for_status=True) as session:
          async with session.get(forecastString) as resp:
            resptext = await resp.text()
            jsonText = json.loads(resptext)
            headers = resp.headers
            status = resp.raise_for_status()
            
            data = Forecast(jsonText, status, headers)
                
        return data

