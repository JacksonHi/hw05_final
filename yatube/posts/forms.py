from django.db.models.base import Model
from django.forms import ModelForm

from .models import Comment, Post


class PostForm(ModelForm):
    class Meta:
        model = Post
        fields = ('text', 'group', 'image',)
        # fields = ('text', 'group')
        labels = {
            'text': 'Текст',
            'group': 'Группа'
        }
        help_text = {
            'text': 'Вспомогательный текст...',
            'group': 'Вспомогательный текст,,,'
        }


class CommentForm(ModelForm):
    class Meta:
        model = Comment
        fields = ('text',)
