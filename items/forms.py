from django import forms
from .models import Item, CATEGORY_CHOICES, STATUS_CHOICES, ITEM_TYPE_CHOICES


class ItemForm(forms.ModelForm):
    image = forms.ImageField(
        label='Item Image',
        required=True,
        widget=forms.FileInput(attrs={
            'class': 'form-control',
            'accept': 'image/*',
            'id': 'id_image'
        })
    )
    
    item_type = forms.ChoiceField(
        choices=ITEM_TYPE_CHOICES,
        required=True,
        widget=forms.RadioSelect(attrs={
            'class': 'form-check-input',
        }),
        label='Item Type',
        initial='found'
    )
    
    category = forms.ChoiceField(
        choices=CATEGORY_CHOICES,
        required=False,
        widget=forms.Select(attrs={
            'class': 'form-select',
        }),
        label='Category'
    )
    
    manual_tags = forms.CharField(
        required=False,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'Enter tags separated by commas (optional)',
            'id': 'manualTags'
        }),
        label='Additional Tags',
        help_text='Separate multiple tags with commas'
    )
    
    ai_tags = forms.CharField(
        required=False,
        widget=forms.HiddenInput(),
        label='AI Tags'
    )

    class Meta:
        model = Item
        fields = ['title', 'location', 'description']
        widgets = {
            'title': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'e.g., Red Backpack',
            }),
            'location': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Where was the item found/lost?',
            }),
            'description': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 4,
                'placeholder': 'Describe any other details about the item...'
            }),
        }

    def clean_title(self):
        title = self.cleaned_data.get('title')
        if not title:
            raise forms.ValidationError('Title is required.')
        if len(title.strip()) < 3:
            raise forms.ValidationError('Title must be at least 3 characters.')
        if len(title) > 200:
            raise forms.ValidationError('Title cannot exceed 200 characters.')
        return title.strip()

    def clean_location(self):
        location = self.cleaned_data.get('location')
        if not location:
            raise forms.ValidationError('Location is required.')
        if len(location.strip()) < 3:
            raise forms.ValidationError('Location must be at least 3 characters.')
        if len(location) > 300:
            raise forms.ValidationError('Location cannot exceed 300 characters.')
        return location.strip()

    def clean_description(self):
        description = self.cleaned_data.get('description')
        if description and len(description) > 2000:
            raise forms.ValidationError('Description cannot exceed 2000 characters.')
        return description

    def clean_image(self):
        image = self.cleaned_data.get('image')
        if not image:
            raise forms.ValidationError('Please upload an image.')
        
        if image.size > 5 * 1024 * 1024:
            raise forms.ValidationError('Image size must be less than 5MB.')
        
        allowed_types = ['image/jpeg', 'image/png', 'image/gif', 'image/webp']
        if image.content_type not in allowed_types:
            raise forms.ValidationError('Please upload a valid image file (JPG, PNG, GIF, or WebP).')
        
        allowed_extensions = ['.jpg', '.jpeg', '.png', '.gif', '.webp']
        import os
        file_ext = os.path.splitext(image.name)[1].lower()
        if file_ext not in allowed_extensions:
            raise forms.ValidationError('File extension not allowed. Use JPG, PNG, GIF, or WebP.')
        
        return image
    
    def clean_manual_tags(self):
        tags = self.cleaned_data.get('manual_tags')
        if tags:
            tags_list = [tag.strip() for tag in tags.split(',') if tag.strip()]
            if len(tags_list) > 10:
                raise forms.ValidationError('Maximum 10 tags allowed.')
            
            for tag in tags_list:
                if len(tag) > 50:
                    raise forms.ValidationError(f'Tag "{tag}" exceeds 50 characters.')
                if not tag.replace(' ', '').replace('-', '').isalnum():
                    raise forms.ValidationError(f'Tag "{tag}" contains invalid characters. Use only letters, numbers, spaces, and hyphens.')
        
        return tags
