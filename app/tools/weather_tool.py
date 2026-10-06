"""
weather_tool.py — Mock weather tool.

Returns deterministic weather data for known cities.
"""

# Deterministic mock weather data keyed by lowercase city name.
MOCK_WEATHER = {
    "hyderabad": {
        "city": "Hyderabad",
        "temperature_c": 32,
        "feels_like_c": 36,
        "condition": "Partly Cloudy",
        "humidity_pct": 65,
        "wind_kph": 18,
        "visibility_km": 8,
        "uv_index": 7,
        "forecast": "Expect afternoon showers. Carry an umbrella.",
    },
    "delhi": {
        "city": "Delhi",
        "temperature_c": 28,
        "feels_like_c": 31,
        "condition": "Hazy Sunshine",
        "humidity_pct": 55,
        "wind_kph": 12,
        "visibility_km": 5,
        "uv_index": 6,
        "forecast": "Moderate air quality. Haze expected through the evening.",
    },
    "mumbai": {
        "city": "Mumbai",
        "temperature_c": 30,
        "feels_like_c": 35,
        "condition": "Humid and Sunny",
        "humidity_pct": 80,
        "wind_kph": 22,
        "visibility_km": 10,
        "uv_index": 8,
        "forecast": "Hot and humid. Stay hydrated.",
    },
    "bangalore": {
        "city": "Bangalore",
        "temperature_c": 24,
        "feels_like_c": 25,
        "condition": "Pleasant and Cloudy",
        "humidity_pct": 60,
        "wind_kph": 15,
        "visibility_km": 12,
        "uv_index": 5,
        "forecast": "Mild weather expected. Light rain possible in the evening.",
    },
    "chennai": {
        "city": "Chennai",
        "temperature_c": 34,
        "feels_like_c": 40,
        "condition": "Hot and Sunny",
        "humidity_pct": 75,
        "wind_kph": 20,
        "visibility_km": 9,
        "uv_index": 9,
        "forecast": "Very hot day. Avoid outdoor activity between 12–4 PM.",
    },
    "kolkata": {
        "city": "Kolkata",
        "temperature_c": 29,
        "feels_like_c": 33,
        "condition": "Overcast",
        "humidity_pct": 70,
        "wind_kph": 14,
        "visibility_km": 7,
        "uv_index": 4,
        "forecast": "Cloudy skies with a chance of evening thunderstorms.",
    },
}


def weather_tool(city: str) -> dict:
    """
    Get mock current weather for a city.

    Args:
        city: Name of the city (case-insensitive).

    Returns:
        A dict with:
          - status: "success" | "city_not_found"
          - weather data fields (on success)
          - message: human-readable summary
    """
    key = city.strip().lower()
    data = MOCK_WEATHER.get(key)

    if data is None:
        return {
            "status": "city_not_found",
            "city": city,
            "message": (
                f"Weather data not available for '{city}'. "
                "Supported cities: "
                + ", ".join(v["city"] for v in MOCK_WEATHER.values())
                + "."
            ),
        }

    return {
        "status": "success",
        **data,
        "message": (
            f"Current weather in {data['city']}: {data['temperature_c']}°C, "
            f"{data['condition']}. Humidity {data['humidity_pct']}%, "
            f"Wind {data['wind_kph']} kph. {data['forecast']}"
        ),
    }
