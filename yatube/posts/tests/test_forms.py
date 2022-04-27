import shutil
import tempfile

from django.conf import settings
from django.contrib.auth import get_user_model
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import Client, TestCase, override_settings
from django.urls import reverse

from ..models import Group, Post


User = get_user_model()
TEMP_MEDIA_ROOT = tempfile.mkdtemp(dir=settings.BASE_DIR)


@override_settings(MEDIA_ROOT=TEMP_MEDIA_ROOT)
class PostsFormTests(TestCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.author = User.objects.create_user(username='HasNoName')
        cls.group = Group.objects.create(
            title='Тестовая группа',
            slug='test-slug',
            description='Тестовое описание',
        )
        cls.post = Post.objects.create(
            author=cls.author,
            group=cls.group,
            text='Тестовый пост',
        )

    @classmethod
    def tearDownClass(cls):
        super().tearDownClass()
        shutil.rmtree(TEMP_MEDIA_ROOT, ignore_errors=True)

    def setUp(self):
        self.user = User.objects.create_user(username='auth')
        self.authorized_client = Client()
        self.authorized_client.force_login(self.user)

        self.author_client = Client()
        self.author_client.force_login(self.author)

    def test_post_create(self):
        """Валидная форма создает запись в Post."""
        posts_count = Post.objects.count()
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
        form_data = {
            'text': self.post.text,
            'group': self.group.id,
            'image': uploaded,
        }
        response = self.authorized_client.post(
            reverse('all_posts:post_create'),
            data=form_data,
            follow=True
        )
        post_1 = Post.objects.latest('pub_date')
        post_1.image = uploaded
        self.assertRedirects(response,
                             reverse('all_posts:profile',
                                     kwargs={'username': self.user}))
        self.assertEqual(Post.objects.count(), posts_count + 1)
        self.assertEqual(post_1.text, form_data['text'])
        self.assertEqual(post_1.author, self.user)
        self.assertEqual(post_1.group.title, self.group.title)
        self.assertEqual(post_1.image, form_data['image'])

    def test_author_post_edit(self):
        """Валидная форма редактирует запись в Post."""
        form_data = {
            'text': 'Измененный текст',
            'group': self.group.id,
        }
        response_edit = self.author_client.post(
            reverse('all_posts:post_edit', kwargs={'post_id': self.post.pk}),
            data=form_data,
            follow=True,
        )
        self.assertRedirects(response_edit,
                             reverse('all_posts:post_detail',
                                     kwargs={'post_id': self.post.pk}))

        post_2 = Post.objects.get(id=self.post.pk)
        self.assertEqual(post_2.text, form_data['text'])
        self.assertEqual(post_2.author, self.author)
        self.assertEqual(post_2.group.title, self.group.title)
