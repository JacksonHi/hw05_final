from http import HTTPStatus

from django.contrib.auth import get_user_model
from django.test import Client, TestCase

from ..models import Group, Post, Comment

User = get_user_model()


class StaticURLTests(TestCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        # Устанавливаем данные для тестирования
        # Создаём экземпляр клиента. Он неавторизован.
        cls.guest_client = Client()
        # Создаем второй клиент
        cls.authorized_client = Client()
        cls.user = User.objects.create_user(username='TestUser')
        # Авторизуем пользователя
        cls.authorized_client.force_login(StaticURLTests.user)
        # Пользователь без постов
        cls.authorized_client_without_posts = Client()
        cls.user_without_posts = User.objects.create_user(username='TestUser2')
        cls.authorized_client_without_posts.force_login(
            StaticURLTests.user_without_posts)

        # Создадим запись в БД для проверки доступности адреса
        cls.group = Group.objects.create(
            title='test-title',
            slug='test-slug',
            description='test-descrp',
        )
        cls.post = Post.objects.create(
            text='Тестовый текст',
            group=cls.group,
            author=cls.user,
        )
        cls.comment = Comment.objects.create(
            post=cls.post,
            author=cls.user,
            text='Тестовый коментарий',
            created='23.12.2020',
        )
        cls.urls_list_unauthorized_user = {
            '/': 'index.html',
            f'/group/{cls.group.slug}/': 'group.html',
            f'/profile/{cls.user.username}/': 'profile.html',
            f'/posts/{cls.post.id}/': 'post_detail.html'
        }
        cls.urls_list_authorized_user = {
            '/create/': 'create_post.html',
            f'/posts/{cls.post.id}/edit/': 'create_post.html',
            '/follow/': 'follow.html'
        }

    def test_homepage(self):
        response = StaticURLTests.guest_client.get('/')
        self.assertEqual(response.status_code, HTTPStatus.OK)

    def test_author(self):
        response = StaticURLTests.guest_client.get('/about/author/')
        self.assertEqual(response.status_code, HTTPStatus.OK)

    def test_tech(self):
        response = StaticURLTests.guest_client.get('/about/tech/')
        self.assertEqual(response.status_code, HTTPStatus.OK)

    def test_urls_all_user(self):  # !
        """Доступность страниц для неавторизованных"""
        for adress in StaticURLTests.urls_list_unauthorized_user:
            with self.subTest(adress=adress):
                response = self.guest_client.get(adress)
                self.assertEqual(response.status_code, HTTPStatus.OK)

    def test_urls_authorized_user(self):
        """Страницы для авторизованных подьзователей"""
        for adress in StaticURLTests.urls_list_authorized_user:
            with self.subTest(adress=adress):
                response = StaticURLTests.authorized_client.get(adress)
                self.assertEqual(response.status_code, HTTPStatus.OK)

    def test_urls_redirect_unauthorizad(self):
        """Переадресация неавторизованных"""
        login = '/auth/login/'
        post_create = '/create/'
        response = self.guest_client.get(
            '/create/',
            follow=True
        )
        self.assertRedirects(response, f'{login}?next={post_create}')

    def test_urls_redirect_not_author(self):  # !
        """Переадресация не автора поста"""
        post_id = StaticURLTests.post.id
        post_detail = f'/posts/{post_id}/'
        response = self.authorized_client_without_posts.get(
            f'/posts/{post_id}/edit/',
            follow=True
        )
        self.assertRedirects(
            response, f'{post_detail}')
