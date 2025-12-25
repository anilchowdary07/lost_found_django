from math import radians, sin, cos, sqrt, atan2
from django.db.models import F, FloatField
from django.db.models.functions import ACos, Cos, Radians, Sin


def haversine_distance(lat1, lon1, lat2, lon2):
    R = 6371
    
    lat1_rad = radians(lat1)
    lat2_rad = radians(lat2)
    delta_lat = radians(lat2 - lat1)
    delta_lon = radians(lon2 - lon1)
    
    a = sin(delta_lat / 2) ** 2 + cos(lat1_rad) * cos(lat2_rad) * sin(delta_lon / 2) ** 2
    c = 2 * atan2(sqrt(a), sqrt(1 - a))
    distance = R * c
    
    return distance


def get_nearby_items(latitude, longitude, radius_km=5):
    from .models import Item
    
    items_with_distance = []
    all_items = Item.objects.filter(
        latitude__isnull=False,
        longitude__isnull=False
    ).exclude(status='returned')
    
    for item in all_items:
        distance = haversine_distance(latitude, longitude, item.latitude, item.longitude)
        if distance <= radius_km:
            items_with_distance.append({
                'item': item,
                'distance': round(distance, 2)
            })
    
    items_with_distance.sort(key=lambda x: x['distance'])
    return items_with_distance
