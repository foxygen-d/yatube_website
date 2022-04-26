import shutil
import tempfile

from django import forms
from django.conf import settings
from django.contrib.auth import get_user_model
from django.test import Client, TestCase, override_settings
from django.urls import reverse

from ..models import Group, Post


User = get_user_model()
TEMP_MEDIA_ROOT = tempfile.mkdtemp(dir=settings.BASE_DIR)


@override_settings(MEDIA_ROOT=TEMP_MEDIA_ROOT)
class PostsPagesTests(TestCase):
    POST_COUNT = settings.PAGE_COUNT + 1

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.author = User.objects.create_user(username='HasNoName')
        cls.group = Group.objects.create(
            title='Тестовая группа',
            slug='test-slug',
            description='Тестовое описание',
        )
        for i in range(cls.POST_COUNT):
            cls.post = Post.objects.create(
                author=cls.author,
                text=f'Тестовый пост {i}',
                group=cls.group,
            )
        cls.image = (
            b'\x47\x49\x46\x38\x39\x61\x02\x00'
            b'\x01\x00\x80\x00\x00\x00\x00\x00'
            b'\xFF\xFF\xFF\x21\xF9\x04\x00\x00'
            b'\x00\x00\x00\x2C\x00\x00\x00\x00'
            b'\x02\x00\x01\x00\x00\x02\x02\x0C'
            b'\x0A\x00\x3B'
        )

    @classmethod
    def tearDownClass(cls):
        super().tearDownClass()
        shutil.rmtree(TEMP_MEDIA_ROOT, ignore_errors=True)

    def setUp(self):
        self.authorized_client = Client()
        self.authorized_client.force_login(self.author)

    def test_pages_uses_correct_template(self):
        """URL-адрес использует соответствующий шаблон."""
        templates_page_names = {
            reverse('all_posts:index'): 'posts/index.html',
            reverse('all_posts:group_list',
                    kwargs={'slug': self.group.slug}): 'posts/group_list.html',
            reverse('all_posts:profile',
                    kwargs={'username': self.author}): 'posts/profile.html',
            reverse(
                'all_posts:post_detail',
                kwargs={'post_id': self.post.pk}): 'posts/post_detail.html',

            reverse('all_posts:post_create'): 'posts/create_post.html',
            reverse(
                'all_posts:post_edit',
                kwargs={'post_id': self.post.pk}): 'posts/create_post.html',
            reverse('all_posts:follow_index'): 'posts/follow.html',
        }
        for reverse_name, template in templates_page_names.items():
            with self.subTest(reverse_name=reverse_name):
                response = self.authorized_client.get(reverse_name)
                self.assertTemplateUsed(response, template)

    def test_show_correct_context(self):
        """Шаблоны index, group_list, profile
        сформированы с правильным контекстом."""
        templates_pages_names = [
            reverse('all_posts:index'),
            reverse('all_posts:group_list', kwargs={'slug': self.group.slug}),
            reverse('all_posts:profile', kwargs={'username': self.author}),
        ]
        for reverse_name in templates_pages_names:
            with self.subTest(reverse_name=reverse_name):
                response = self.authorized_client.get(reverse_name)
                object = response.context['page_obj'][0]
                self.assertEqual(object.id, self.post.pk)
                self.assertEqual(object.text,
                                 self.post.text)
                self.assertEqual(object.author.id, self.author.id)
                self.assertEqual(object.author.username, self.author.username)
                self.assertEqual(object.group.id, self.group.id)
                self.assertEqual(object.group.title, self.group.title)
                self.assertTrue(
                    Post.objects.filter(
                        text=object.text,
                        image=object.image
                    ).exists()
                )

    def test_post_detail_show_correct_context(self):
        """Шаблон post_detail сформирован с правильным контекстом."""
        response = self.authorized_client.get(
            reverse('all_posts:post_detail', kwargs={'post_id': self.post.pk}))
        object = response.context['post_item']
        self.assertEqual(object.id, self.post.pk)
        self.assertEqual(object.text,
                         self.post.text[:30])
        self.assertEqual(response.context['post_count'], self.POST_COUNT)

    def test_post_create_show_correct_context(self):
        """Шаблон post_create сформирован с правильным контекстом."""
        response = self.authorized_client.get(reverse('all_posts:post_create'))
        form_fields = {
            'group': forms.fields.ChoiceField,
        }
        for value, expected in form_fields.items():
            with self.subTest(value=value):
                form_field = response.context['form'].fields[value]
                self.assertIsInstance(form_field, expected)


class PaginatorViewsTest(TestCase):
    POST_COUNT = settings.PAGE_COUNT + 1

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.author = User.objects.create_user(username='HasNoName')
        cls.group = Group.objects.create(
            title='Тестовая группа',
            slug='test-slug',
            description='Тестовое описание',
        )
        for i in range(cls.POST_COUNT):
            Post.objects.create(
                author=cls.author,
                text=f'Тестовый пост {i}',
                group=cls.group,
            )

    def test_paginator(self):
        page_names = [
            reverse('all_posts:index'),
            reverse('all_posts:group_list', kwargs={'slug': self.group.slug}),
            reverse('all_posts:profile', kwargs={'username': self.author}),
        ]
        for page in page_names:
            with self.subTest(page=page):
                response = self.client.get(page)
                self.assertEqual(len(response.context['page_obj']),
                                 settings.PAGE_COUNT)

        for page in page_names:
            with self.subTest(page=page):
                response = self.client.get(page + '?page=2')
                self.assertEqual(
                    len(response.context['page_obj']),
                    self.author.posts.count() - settings.PAGE_COUNT)
