from accounts.models import UserProfile
from django.db.models import Q


KARMA_POINTS_PER_RETURN = 50


def award_karma_points(user, points=KARMA_POINTS_PER_RETURN):
    profile, created = UserProfile.objects.get_or_create(user=user)
    profile.karma_points += points
    profile.total_items_returned += 1
    profile.save()
    return profile


def get_leaderboard(limit=100):
    return UserProfile.objects.all().order_by('-karma_points')[:limit]


def get_user_karma(user):
    try:
        profile = UserProfile.objects.get(user=user)
        return profile.karma_points
    except UserProfile.DoesNotExist:
        return 0


def get_user_rank(user):
    try:
        user_profile = UserProfile.objects.get(user=user)
        rank = UserProfile.objects.filter(karma_points__gt=user_profile.karma_points).count() + 1
        return rank
    except UserProfile.DoesNotExist:
        # User has no profile yet, create one and return their rank
        profile = UserProfile.objects.create(user=user)
        rank = UserProfile.objects.filter(karma_points__gt=profile.karma_points).count() + 1
        return rank
