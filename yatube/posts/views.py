from xml.etree.ElementTree import Comment
from django.contrib.auth.decorators import login_required
from django.http import HttpResponse
from django.shortcuts import get_object_or_404, redirect, render

from .forms import PostForm, CommentForm
from .models import Group, Post, Comment, User
from .utils import get_page_context


def index(request):
    context = get_page_context(Post.objects.all(), request)
    return render(request, 'posts/index.html', context)


def group_posts(request, slug):
    """Посты, отфильтрованные по группам."""
    group = get_object_or_404(Group, slug=slug)
    context = {
        'group': group,
        'title': group.title,
    }
    context.update(get_page_context(group.posts.all(), request))
    return render(request, 'posts/group_list.html', context)


def profile(request, username):
    author = get_object_or_404(User, username=username)
    context = {
        'author': author,
    }
    context.update(get_page_context(Post.objects.filter(author=author),
                                    request))
    return render(request, 'posts/profile.html', context)


def post_detail(request, post_id):
    post_item = get_object_or_404(Post, id=post_id)
    comments = get_object_or_404(Comment, id=post_id)
    comment_form = CommentForm(request.POST or None)
    context = {
        'post_item': post_item,
        'text': post_item.text[:30],
        'post_count': Post.objects.filter(author=post_item.author).count(),
        'comment_form': comment_form,
        'comments': comments,
    }
    return render(request, 'posts/post_detail.html', context)


@login_required
def post_create(request):
    form = PostForm(request.POST or None)
    if form.is_valid():
        post = form.save(commit=False)
        post.author = request.user
        post.save()
        return redirect('all_posts:profile', username=post.author)
    return render(request, 'posts/create_post.html', {'form': form})


@login_required
def post_edit(request, post_id):
    post = get_object_or_404(Post, pk=post_id)
    if request.user != post.author:
        return HttpResponse('Вы не можете редактировать этот пост')

    is_edit = True
    form = PostForm(
        request.POST or None,
        files=request.FILES or None,
        instance=post
    )
    if form.is_valid():
        form.save()
        return redirect('all_posts:post_detail', post_id=post.pk)
    context = {
        'form': form,
        'is_edit': is_edit,
        'post': post,
    }
    return render(request, 'posts/create_post.html', context)

@login_required
def add_comment(request, post_id):
    form = CommentForm(request.POST or None)
    if form.is_valid():
        comment = form.save(commit=False)
        comment.author = request.user
        comment.save()
    return redirect('posts:post_detail', post_id=post_id) 
