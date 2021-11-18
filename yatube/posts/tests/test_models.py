from django.contrib.auth import get_user_model
from django.test import TestCase

from ..models import Group, Post, Comment

User = get_user_model()


class PostModelTest(TestCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.user = User.objects.create_user(username='auth')
        cls.user_2 = User.objects.create_user(username='auth_2')
        cls.group = Group.objects.create(
            title='Тестовая группа',
            slug='Тестовый слаг',
            description='Тестовое описание',
        )
        cls.post = Post.objects.create(
            author=cls.user,
            text='Тестовая группа',
        )
        cls.comment = Comment.objects.create(
            post=cls.post,
            author=cls.user_2,
            text='Тестовый коментарий',
            created='23.12.2020',
        )

    def test_models_have_correct_object_names(self):
        """Проверяем, что у моделей корректно работает __str__."""
        post = self.post
        group = self.group
        models_fields = {
            group: group.title,
            post: post.text[:15]
        }
        for value, expected in models_fields.items():
            with self.subTest(value=value):
                self.assertEqual(str(value), expected)

    def test_verbos_name(self):
        """Проверяет соответствие verbos_name"""
        verbos_name_post = {
            'text': 'Текст',
            'author': 'Автор',
            'pub_date': 'дата публикации',
            'group': 'Группа',
            'image': 'Картинка'
        }
        verbos_name_group = {
            'title': 'Заглавие',
            'slug': 'Слаг',
            'description': 'описание'
        }
        verbos_name_comment = {
            'post': 'Коментарий к посту',
            'author': 'Автор комментария',
            'text': 'Текст',
            'created': 'дата публикации'
        }
        verbos_name = {
            self.post: verbos_name_post,
            self.group: verbos_name_group,
            self.comment: verbos_name_comment
        }
        for model, verbos in verbos_name.items():
            for value, expected in verbos.items():
                with self.subTest(value=value):
                    self.assertEqual(
                        model._meta.get_field(value).verbose_name, expected)

    def test_help_text(self):
        """Проверяет соответствие help_text"""
        help_text = {
            'text': 'Введите текст поста',
            'group': 'Выбурите группу'
        }
        for value, expected in help_text.items():
            with self.subTest(value=value):
                self.assertEqual(
                    self.post._meta.get_field(value).help_text, expected)
