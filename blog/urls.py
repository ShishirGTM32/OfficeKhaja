from django.urls import path
from .views import BlogView, BlogDetailView, CommentView, TrendingHashtagsView, SlugView, PostReactionView

urlpatterns = [
    path("blog/", BlogView.as_view(), name="blog-lists"),
    path("blog/<slug:slug>/", BlogDetailView.as_view(), name="blog_detail"),
    path("blog/<slug:slug>/comments/", CommentView.as_view(), name="comments"),
    path("blog/<slug:slug>/comments/<int:cid>/", CommentView.as_view(), name="comment-view"),
    path("blog/<slug:slug>/<str:reaction>/", PostReactionView.as_view(), name="blog-like"),
    path("blog/<slug:slug>/comments/<int:comment_id>/<str:reaction>/", PostReactionView.as_view(), name="comment-like"),
    path("trending/", TrendingHashtagsView.as_view(), name="trending-hastags"),
    path('slugs/', SlugView.as_view(), name="slugs"),
]