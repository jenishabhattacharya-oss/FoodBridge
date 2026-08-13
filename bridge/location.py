import json
import ipaddress
import re
from math import asin, cos, radians, sin, sqrt
from urllib.parse import urlencode
from urllib.request import Request, urlopen

from django.conf import settings
from django.core.cache import cache


def _distance_km(latitude, longitude, other_latitude, other_longitude):
    lat1, lon1, lat2, lon2 = map(radians, (float(latitude), float(longitude), float(other_latitude), float(other_longitude)))
    return 6371 * 2 * asin(sqrt(sin((lat2 - lat1) / 2) ** 2 + cos(lat1) * cos(lat2) * sin((lon2 - lon1) / 2) ** 2))


def request_ip_location(request):
    """Get a coarse bias from a public client IP; localhost/private IPs are ignored."""
    address = request.META.get("REMOTE_ADDR", "")
    try:
        if not ipaddress.ip_address(address).is_global:
            return None
    except ValueError:
        return None
    key = f"foodbridge-ip-location:{address}"
    cached = cache.get(key)
    if cached is not None:
        return cached
    try:
        request_url = Request(settings.IP_GEOLOCATION_URL.format(ip=address), headers={"User-Agent": settings.GEOCODING_USER_AGENT, "Accept": "application/json"})
        with urlopen(request_url, timeout=settings.IP_GEOLOCATION_TIMEOUT_SECONDS) as response:
            payload = json.loads(response.read().decode("utf-8"))
        result = (float(payload["latitude"]), float(payload["longitude"]))
    except Exception:
        result = None
    cache.set(key, result, timeout=60 * 60 * 12)
    return result


def search_places(query, *, latitude=None, longitude=None, city=""):
    location_suffix = ", ".join(part for part in (city.strip(), settings.GEOCODING_DEFAULT_COUNTRY) if part)
    street_query = re.sub(r"^\s*\d+[\w/-]*\s*,?\s*", "", query).strip()
    queries = [query]
    if street_query and street_query.casefold() != query.casefold():
        queries.append(street_query)
    if latitude is None or longitude is None:
        queries.append(f"{query}, {location_suffix}")
    key = f"foodbridge-geocode:{'|'.join(queries).lower()}:{latitude or ''}:{longitude or ''}"
    cached = cache.get(key)
    if cached is not None:
        return cached
    results = []
    seen = set()
    for search_query in queries:
        params = {"q": search_query, "limit": 12}
        if latitude is not None and longitude is not None:
            params.update({"lat": latitude, "lon": longitude})
        if settings.GEOCODING_PROVIDER == "photon":
            params["lang"] = "en"
        if settings.GEOCODING_PROVIDER == "nominatim":
            params["format"] = "jsonv2"
        request = Request(f"{settings.GEOCODING_URL}?{urlencode(params)}", headers={"User-Agent": settings.GEOCODING_USER_AGENT, "Accept": "application/json"})
        with urlopen(request, timeout=settings.GEOCODING_TIMEOUT_SECONDS) as response:
            payload = json.loads(response.read().decode("utf-8"))
        if settings.GEOCODING_PROVIDER == "nominatim":
            candidates = [{"label": item["display_name"], "latitude": item["lat"], "longitude": item["lon"]} for item in payload if item.get("display_name") and item.get("lat") and item.get("lon")]
        else:
            candidates = []
            for feature in payload.get("features", []):
                coordinates = feature.get("geometry", {}).get("coordinates", [])
                properties = feature.get("properties", {})
                if properties.get("countrycode", "in").casefold() not in {"in", "india"}:
                    continue
                parts = [properties.get(key) for key in ("name", "housenumber", "street", "district", "city", "state", "country")]
                label = ", ".join(dict.fromkeys(str(part) for part in parts if part))
                if len(coordinates) >= 2 and label:
                    candidates.append({"label": label, "latitude": coordinates[1], "longitude": coordinates[0]})
        for result in candidates:
            result_key = (round(float(result["latitude"]), 5), round(float(result["longitude"]), 5))
            if result_key not in seen:
                seen.add(result_key)
                results.append(result)
        if results:
            break
    if latitude is not None and longitude is not None:
        for result in results:
            result["distance_km"] = round(_distance_km(latitude, longitude, result["latitude"], result["longitude"]), 1)
        results = [result for result in results if result["distance_km"] <= settings.GEOCODING_NEARBY_RADIUS_KM]
        results.sort(key=lambda result: result.get("distance_km", float("inf")))
    results = results[:8]
    cache.set(key, results, timeout=86400)
    return results
