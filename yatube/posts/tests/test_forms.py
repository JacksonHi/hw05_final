
from http import HTTPStatus

from django.contrib.auth import get_user_model
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import Client, TestCase
from django.urls import reverse

from ..models import Comment, Group, Post

User = get_user_model()


# при отправке валидной формы со страницы создания поста
# reverse('posts:create_post') создаётся новая запись в базе данных
class PostCreateFormTests(TestCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.user = User.objects.create_user(username='TestUser')
        cls.unauthorized_user = Client()
        cls.authorized_client = Client()
        cls.authorized_client.force_login(cls.user)
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
        # Создаем запись в базе данных для проверки сушествующего slug
        cls.group = Group.objects.create(
            title='Тестовый заголовок',
            slug='first',
            description='Описание'
        )
        cls.post = Post.objects.create(
            author=cls.user,
            pub_date='21.01.2021',
            text='Тестовый текст',
            group=cls.group,
            image=uploaded
        )

    def test_create_post(self):
        """Валидная форма создает запись в Post."""
        post_count = Post.objects.count()
        form_data = {
            'text': 'Тестовый текст',
            'group': self.group.id,
            'image': self.post.image
        }
        response = self.authorized_client.post(
            reverse('posts:post_create'),
            data=form_data,
            follow=True
        )
        self.assertEqual(response.status_code, HTTPStatus.OK)
        # Проверяем, сработал ли редирект
        self.assertRedirects(
            response,
            reverse('posts:profile', args=[self.user.username])
        )
        # Проверяем, увеличилось ли число постов
        self.assertEqual(Post.objects.count(), post_count + 1)
        # Проверяем, что создалась запись с заданным слагом
        self.assertTrue(
            Post.objects.filter(
                text=form_data['text'],
                group=form_data['group'],
                author=self.user,
                image=form_data['image']
            ).exists()
        )

    def test_post_edit(self):
        """Проверка post_id после изменения поста"""
        post_count = Post.objects.count()
        form_data = {
            'text': 'Тестовый текст',
            'group': self.group.id
        }
        response = self.authorized_client.post(
            reverse('posts:post_edit',
                    args=[self.post.id]),
            data=form_data,
            follow=True
        )
        self.assertEqual(response.status_code, HTTPStatus.OK)
        # Редирект
        self.assertRedirects(
            response,
            reverse('posts:post_detail', args=[self.post.id])
        )
        # Проверка количества записей
        self.assertEqual(Post.objects.count(), post_count)
        # Проверяем, что создалась запись с заданным слагом
        self.assertTrue(
            Post.objects.filter(
                text=form_data['text'],
                group=form_data['group'],
                author=self.user
            ).exists()
        )

    def test_not_create_post(self):
        """Пост не создан не авторизованным пользователем"""
        post_count = Post.objects.count()
        create = reverse('posts:post_create')
        login_form = reverse('users:login')
        form_data = {
            'text': 'Тестовый текст',
            'group': self.group.id
        }
        response = self.unauthorized_user.post(
            create,
            data=form_data,
            follow=True
        )
        self.assertRedirects(response, f'{login_form}?next={create}')
        self.assertEqual(response.status_code, HTTPStatus.OK)
        self.assertNotEqual(Post.objects.count(), post_count + 1)

    def test_comment_post(self):
        """После успешной отправки комментарий появляется на странице поста"""
        comments_count = Comment.objects.count()
        data_comment = {
            'post': self.post,
            'author': self.user,
            'text': 'text'
        }
        response = self.authorized_client.post(
            reverse('posts:add_comment', args=[self.post.id]),
            data=data_comment,
            follow=True
        )
        after_comment = Comment.objects.count()
        self.assertEqual(after_comment, comments_count + 1)
        self.assertRedirects(
            response,
            reverse('posts:post_detail', args=[self.post.id]))
        comment = Comment.objects.first()
        self.assertEqual(comment.post, data_comment['post'])
        self.assertEqual(comment.author, data_comment['author'])
        self.assertEqual(comment.text, data_comment['text'])

    def test_not_comment_post(self):
        """Коментировать посты может только авторизованный пользователь"""
        comments_count = Comment.objects.count()
        comment = reverse('posts:add_comment', args=[self.post.id])
        login_form = reverse('users:login')
        data_comment = {
            'post': self.post,
            'author': self.user,
            'text': 'text'
        }
        response = self.unauthorized_user.post(
            comment,
            data=data_comment,
            follow=True
        )
        self.assertEqual(comments_count, Comment.objects.count())
        self.assertRedirects(
            response,
            f'{login_form}?next={comment}')
