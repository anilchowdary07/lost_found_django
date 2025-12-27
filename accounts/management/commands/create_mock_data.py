from django.core.management.base import BaseCommand
from django.contrib.auth.models import User
from items.models import Item, CATEGORY_CHOICES, ITEM_TYPE_CHOICES
from accounts.models import UserProfile
import random

class Command(BaseCommand):
    help = 'Create mock users and items for testing.'

    def handle(self, *args, **kwargs):
        # Create 10 users
        for i in range(10):
            username = f"mockuser{i+1}"
            email = f"mockuser{i+1}@example.com"
            user, created = User.objects.get_or_create(username=username, defaults={
                'email': email,
                'first_name': f"Mock{i+1}",
                'last_name': f"User{i+1}",
            })
            if created:
                user.set_password('testpassword')
                user.save()
                self.stdout.write(self.style.SUCCESS(f"Created user: {username}"))
            # Create or update profile
            profile, _ = UserProfile.objects.get_or_create(user=user)
            profile.karma_points = random.randint(0, 100)
            profile.total_items_returned = random.randint(0, 10)
            profile.save()
            # Create 3-5 items per user
            for j in range(random.randint(3, 5)):
                item = Item.objects.create(
                    user=user,
                    title=f"Item {j+1} of {username}",
                    category=random.choice([c[0] for c in CATEGORY_CHOICES]),
                    description=f"Description for item {j+1} of {username}",
                    image_url="https://via.placeholder.com/150",
                    location=f"Location {random.randint(1, 20)}",
                    status='reported',
                    item_type=random.choice([c[0] for c in ITEM_TYPE_CHOICES]),
                )
                self.stdout.write(self.style.SUCCESS(f"  Added item: {item.title}"))
        self.stdout.write(self.style.SUCCESS('Mock data creation complete.'))
