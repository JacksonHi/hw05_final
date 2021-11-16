import tempfile
from time import sleep

from django import forms
from django.conf import settings
from django.contrib.auth import get_user_model
from django.core.cache import cache
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import Client, TestCase, override_settings
from django.urls import reverse

from ..models import Follow, Group, Post

User = get_user_model()
# Создаем временную папку для медиа-файлов;
# на момент теста медиа папка будет переопределена
TEMP_MEDIA_ROOT = tempfile.mkdtemp(dir=settings.BASE_DIR)


# Для сохранения media-файлов в тестах будет использоваться
# временная папка TEMP_MEDIA_ROOT, а потом мы ее удалим
@override_settings(MEDIA_ROOT=TEMP_MEDIA_ROOT)
class TaskPagesTests(TestCase):
    """Протестируйте шаблоны, словарь контекста, паджинатор и
    отображение поста на различных страницах проекта"""
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.user = User.objects.create_user(username='TestUser')
        cls.user_2 = User.objects.create_user(username='TestUser_2')
        cls.authorized_client = Client()
        cls.authorized_client.force_login(cls.user)
        cls.unauthorized_client = Client()
        cls.group_2 = Group.objects.create(
            title='Заглавие_2',
            slug='test_slug_2',
            description='описание_2'
        )
        cls.post_2 = Post.objects.create(
            author=cls.user,
            pub_date='20.12.2021',
            text='Текст_2',
            group=cls.group_2
        )
        # без него записи в рандомном порядке каждый раз появляются
        sleep(0.1)

        small_gif = (
            b'\x47\x49\x46\x38\x39\x61\x02\x00'
            b'\x01\x00\x80\x00\x00\x00\x00\x00'
            b'\xFF\xFF\xFF\x21\xF9\x04\x00\x00'
            b'\x00\x00\x00\x2C\x00\x00\x00\x00'
            b'\x02\x00\x01\x00\x00\x02\x02\x0C'
            b'\x0A\x00\x3B'
        )
        uploaded = SimpleUploadedFile(
            name='small.gif',
            content=small_gif,
            content_type='image/gif'
        )

        cls.group = Group.objects.create(
            title='Заглавие',
            slug='test_slug',
            description='описание'
        )
        cls.post = Post.objects.create(
            author=cls.user,
            pub_date='21.12.2021',
            text='Текст',
            group=cls.group,
            image=uploaded
        )

    # Проверка namespace:name
    def test_pages_user_correct_template(self):
        """Адрес использует соответствующий шаблон"""
        temlates_pages_names = {
            reverse('posts:index'): 'posts/index.html',
            reverse('posts:post_create'): 'posts/create_post.html',
            reverse('posts:group_post', args=[self.group.slug]):
                'posts/group_list.html',
            reverse('posts:profile', args=[self.user.username]):
                'posts/profile.html',
            reverse('posts:post_detail', args=[self.post.id]):
                'posts/post_detail.html',
            reverse('posts:post_edit', args=[self.post.id]):
                'posts/create_post.html',
            reverse('posts:follow_index'): 'posts/follow.html'
        }
        for reverse_name, template in temlates_pages_names.items():
            with self.subTest(reverse_name=reverse_name):
                response = self.authorized_client.get(reverse_name)
                self.assertTemplateUsed(response, template)

    # Проверка контекста
    def test_create_post_context(self):
        """Шаблон сформирован с правильным контекстом."""
        response = self.authorized_client.get(reverse('posts:post_create'))
        # Словарь ожидаемых типов полей формы:
        # указываем, объектами какого класса должны быть поля формы
        form_fields = {
            # При создании формы поля модели типа TextField
            # преобразуются в CharField с виджетом forms.Textarea
            'text': forms.fields.CharField,
            'group': forms.models.ModelChoiceField
        }

        # Проверяем, что типы полей формы в словаре context
        # соответствуют ожиданиям
        for value, expected in form_fields.items():
            with self.subTest(value=value):
                form_field = response.context['form'].fields[value]
                # Проверяет, что поле формы является экземпляром
                # указанного класса
                self.assertIsInstance(form_field, expected)

    # проверка сохранения поста в нужных местах
    def test_post_appeared(self):
        """Шаблон появился на главной, в группе и профайле"""
        response_add_index = self.authorized_client.get(reverse('posts:index'))
        post_index = response_add_index.context['page_obj'][0]
        self.assertEqual(post_index.text, self.post.text)

        response_add_group_post = self.authorized_client.get(
            reverse('posts:group_post', args=[self.group.slug]))
        post_group_post = response_add_group_post.context['page_obj'][0]
        self.assertEqual(post_group_post.text, self.post.text)

        response_add_profile = self.authorized_client.get(
            reverse('posts:profile', args=[self.user.username]))
        post_profile = response_add_profile.context['page_obj'][0]
        self.assertEqual(post_profile.text, self.post.text)

    # post не появляется на не соответствующей группе
    def test_post_not_appeared(self):
        """Пост не появляется вне соответствующей группе"""
        response_add_group_post = self.authorized_client.get(
            reverse('posts:group_post', args=[self.group_2.slug]))
        post_group_post = response_add_group_post.context['page_obj'][0]
        self.assertNotEqual(post_group_post.text, self.post.text)

    # test post edit context
    def test_post_edit_context(self):
        """Шаблон post_edit формируется с правильным контекстом"""
        response = self.authorized_client.get(
            reverse('posts:post_edit', args=[self.post.id]))
        response_edit = response.context['is_edit']
        self.assertEqual(response_edit, True)
        form_fields = {
            'text': forms.fields.CharField,
            'group': forms.models.ModelChoiceField
        }
        for value, expected in form_fields.items():
            with self.subTest(value=value):
                form_field = response.context['form'].fields[value]
                self.assertIsInstance(form_field, expected)

    # test index + paginator
    def test_index_context(self):
        """Шаблон index сформирован с правильным контекстом."""
        response = self.authorized_client.get(reverse('posts:index'))
        # Взяли первый элемент из списка и проверили, что его содержание
        # совпадает с ожидаемым
        post = self.post
        response_post = response.context['page_obj'][0]
        post_author = response_post.author
        post_group = response_post.group
        post_text = response_post.text
        post_pub_date = response_post.pub_date
        post_image = response_post.image
        self.assertEqual(post_author, post.author)
        self.assertEqual(post_group, post.group)
        self.assertEqual(post_text, post.text)
        self.assertEqual(post_pub_date, post.pub_date)
        self.assertEqual(post_image, post.image)

    # Проверяем, что словарь context страницы task/test-slug
    # содержит ожидаемые значения
    def test_post_detail_context(self):
        """Шаблон post_detail сформирован с правильным контекстом."""
        response = self.authorized_client.get(reverse(
            'posts:post_detail', args=[self.post.id]))
        self.assertEqual(response.context.get('post').author, self.user)
        self.assertEqual(response.context.get('post').text, self.post.text)
        self.assertEqual(response.context.get('post').group, self.group)
        self.assertEqual(
            response.context.get('post').pub_date, self.post.pub_date)
        self.assertEqual(response.context.get('post').image, self.post.image)

    # group_posts + paginator
    def test_group_posts_context(self):
        """Шаблон group_posts сформирован с правильным контекстом."""
        response = self.authorized_client.get(
            reverse('posts:group_post', args=[self.group.slug]))
        response_post = response.context['page_obj'][0]
        post = self.post
        post_author = response_post.author
        post_group_title = response_post.group.title
        post_text = response_post.text
        post_pub_date = response_post.pub_date
        post_image = response_post.image
        self.assertEqual(post_author, post.author)
        self.assertEqual(post_group_title, post.group.title)
        self.assertEqual(post_text, post.text)
        self.assertEqual(post_pub_date, post.pub_date)
        self.assertEqual(post_image, post.image)

    # profile + paginator
    def test_profile_context(self):
        """Шаблон profile сформирован с правильным контекстом."""
        response = self.authorized_client.get(
            reverse('posts:profile', args=[self.user.username]))
        response_page_obj = response.context['page_obj'][0]
        response_author = response.context['author']
        post = self.post
        author = self.user
        post_author = response_author.username
        post_count = response_author.posts.count()
        post_group_title = response_page_obj.group.title
        post_text = response_page_obj.text
        post_pub_date = response_page_obj.pub_date
        post_image = response_page_obj.image
        self.assertEqual(post_author, author.username)
        self.assertEqual(post_count, author.posts.count())
        self.assertEqual(post_group_title, post.group.title)
        self.assertEqual(post_text, post.text)
        self.assertEqual(post_pub_date, post.pub_date)
        self.assertEqual(post_image, post.image)

    def test_cache_index(self):
        """Проверка работы кэша на index"""
        response = self.authorized_client.get(reverse('posts:index'))
        Post.objects.create(
            text='перед сбросом кэша',
            author=self.user,
            group=self.group,
        )
        response_before_dropping_cache = self.authorized_client.get(
            reverse('posts:index'))
        self.assertEqual(
            response.content, response_before_dropping_cache.content)
        cache.clear()
        response_after_dropping_cache = self.authorized_client.get(
            reverse('posts:index'))
        self.assertNotEqual(
            response.content, response_after_dropping_cache.content)

    def test_authorized_user_follow(self):
        """Авторизованный пользователь может подписаться и отписаться"""
        # не авторизованный не может подписаться
        self.unauthorized_client.get(
            reverse('posts:profile_follow', args=[self.user.username]))
        response = Follow.objects.filter(user=self.user).count()
        self.assertEqual(response, 0)
        # нельзя подписаться на себя
        self.authorized_client.get(
            reverse('posts:profile_follow', args=[self.user.username]))
        response = Follow.objects.filter(user=self.user).count()
        self.assertEqual(response, 0)
        # подписка работает, пост появляется у подписанного
        self.authorized_client.get(
            reverse('posts:profile_follow', args=[self.user_2.username]))
        response = Follow.objects.filter(user=self.user).count()
        self.assertEqual(response, 1)
        # не может подписаться второй раз
        self.authorized_client.get(
            reverse('posts:profile_follow', args=[self.user_2.username]))
        response = Follow.objects.filter(user=self.user).count()
        self.assertEqual(response, 1)

    def test_unfollowing_no_post(self):
        """Новая запись пользователя не появляется в ленте тех,
        кто не подписан на него."""
        response = self.authorized_client.get(reverse('posts:follow_index'))
        self.assertEqual(len(response.context['page_obj']), 0)


class PaginatorTests(TestCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.author = User.objects.create_user(username='test_user')
        cls.authorized_client = Client()
        cls.authorized_client.force_login(cls.author)
        cls.group = Group.objects.create(
            slug='test-slug'
        )
        # Почему так будет лучше? Ведь редыдущий вариант выглядит проще
        number_post = 13
        posts = [
            Post(
                text=f'Пост {i}',
                group=cls.group,
                author=cls.author
            ) for i in range(number_post)
        ]
        Post.objects.bulk_create(posts, number_post)

        cls.templates = [
            reverse('posts:index'),
            reverse('posts:group_post', args=[cls.group.slug]),
            reverse('posts:profile', args=[cls.author.username])
        ]
        posts_all = Post.objects.count()
        cls.pages = {
            1: 10,
            2: posts_all - 10
        }

    def test_first_page(self):
        """Paginator"""
        for template in self.templates:
            for page, count_post in self.pages.items():
                with self.subTest(page=page):
                    response = self.authorized_client.get(
                        f'{template}?page={page}')
                    count_objects = len(response.context['page_obj'])
                    self.assertEqual(count_objects, count_post)
