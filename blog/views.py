from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from rest_framework.permissions import IsAuthenticated, AllowAny
from orders.permissions import IsAdminOrReadOnly
from django.utils import timezone
from datetime import timedelta
from django.db.models import Count, F, Q
from khaja.pagination import MenuInfiniteScrollPagination
from .models import Blog, Comments, HashTags
from .serializers import BlogSerializer, CommentSerializer, PostReactionSerializer


class BlogView(APIView):
    def get_permissions(self):
        if self.request.method == 'GET':
            permission_classes = [AllowAny]
        elif self.request.method == 'POST':
            permission_classes = [IsAuthenticated]
        else:
            permission_classes = [IsAdminOrReadOnly]
        return [permission() for permission in permission_classes]

    def get(self, request):
        blogs = Blog.objects.all()
        mine = request.query_params.get('self', None)
        if mine:
            blogs = blogs.filter(user=request.user)
        hashtags_param = request.query_params.get('hashtags', None)
        if hashtags_param:
            hashtag_names = [h.strip() for h in hashtags_param.split(',')]
            blogs = blogs.filter(hashtags__name__in=hashtag_names).distinct()

        latest_count = 2 
        latest_posts = blogs.order_by('-created_at')[:latest_count]
        latest_serializer = BlogSerializer(latest_posts, many=True)

        remaining_blogs = blogs.exclude(blog_id__in=latest_posts.values_list('blog_id', flat=True))
        remaining_blogs = remaining_blogs.annotate(
            likes_total=Count('postreaction', filter=Q(postreaction__reaction='like')),
            dislikes_total=Count('postreaction', filter=Q(postreaction__reaction='dislike')),
            ratio=(F('likes_total') + 1.0) / (F('dislikes_total') + 1.0),
        ).order_by('-ratio')

        paginator = MenuInfiniteScrollPagination()
        page = paginator.paginate_queryset(remaining_blogs, request)
        serializer = BlogSerializer(page, many=True)

        response_data = {
            'latest_posts': latest_serializer.data,
            'blogs': serializer.data
        }
 
        return paginator.get_paginated_response(response_data)

    def post(self, request):
        serializer = BlogSerializer(data=request.data, context={'request': request})
        serializer.is_valid(raise_exception=True)   
        serializer.save()
        return Response(serializer.data, status=status.HTTP_201_CREATED)


class BlogDetailView(APIView):
    def get_permissions(self):
        if self.request.method == 'GET':
            permission_classes = [AllowAny]
        elif self.request.method in ['POST', 'PUT', 'DELETE']:
            permission_classes = [IsAuthenticated]
        else:
            permission_classes = [IsAdminOrReadOnly]
        return [permission() for permission in permission_classes]

    def get(self, request, slug):
        blog = Blog.objects.filter(slug=slug).first()
        if not blog:
            return Response(f"Blog not found with slug {slug}")
        serializer = BlogSerializer(blog)
        return Response(serializer.data, status=status.HTTP_200_OK)

    def put(self, request, slug):
        blog = Blog.objects.filter(slug=slug, user=request.user).first()
        if not blog:
            return Response(f"Not authorized for the operation to be performed.")
        serializer = BlogSerializer(blog, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(serializer.data, status=status.HTTP_202_ACCEPTED)

    def delete(self, request, slug):
        blog = Blog.objects.filter(slug=slug, user=request.user).first()
        if not blog:
            return Response(f"Not authorized for the operation to be performed.")
        blog.delete()
        return Response("Blog successfully deleted", status=status.HTTP_204_NO_CONTENT)


class CommentView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, slug):
        blog = Blog.objects.filter(slug=slug).first()
        if not blog:
            return Response(f"Blog not found with slug {slug}")
        comments = Comments.objects.filter(blog=blog, parent=None)

        user_comment = next((c for c in comments if c.user == request.user), None)
        other_comments = [c for c in comments if c != user_comment]
        other_comments.sort(
            key=lambda c: (c.like_count() + 1) / (c.dislike_count() + 1),
            reverse=True
        )
        sorted_comments = [user_comment] + other_comments if user_comment else other_comments
        serializer = CommentSerializer(sorted_comments, many=True)
        return Response({'comments': serializer.data}, status=status.HTTP_200_OK)


    def post(self, request, slug):
        blog = Blog.objects.filter(slug=slug).first()
        if not blog:
            return Response(f"Blog not found with slug {slug}")
        parent_id = request.data.get('parent') 
        serializer = CommentSerializer(
            data=request.data,
            context={'request': request, "blog": blog}
        )
        serializer.is_valid(raise_exception=True)
        comment = serializer.save()
        if parent_id:
            parent_comment = Comments.objects.filter(comment_id=parent_id, blog=blog).first()
            if not parent_comment:
                return Response("Comment not of this blog cant add", status=status.HTTP_403_FORBIDDEN)
            comment.parent = parent_comment
            comment.save()
        return Response(serializer.data, status=status.HTTP_201_CREATED)

    def put(self, request,slug, cid):
        comment = Comments.objects.filter(comment_id=cid, user=request.user).first()
        if not comment:
            return Response("You are not authorized to edit this", status=status.HTTP_400_BAD_REQUEST)
        serializer = CommentSerializer(comment, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        serializer.save()   
        return Response(serializer.data, status=status.HTTP_202_ACCEPTED)
    
    def delete(self, request, slug, cid):
        comment = Comments.objects.filter(comment_id=cid, user=request.user).first()
        if not comment:
            return Response("You are not authorized to edit this", status=status.HTTP_400_BAD_REQUEST)
        
        comment.delete()
        return Response("Comment Successfully deleted", status=status.HTTP_204_NO_CONTENT)


class PostReactionView(APIView):
    permission_classes=[IsAuthenticated]

    def post(self, request, slug, reaction, cid=None):
        if slug:
            blog_id = Blog.objects.filter(slug=slug).first()
            if not blog_id:
                return Response(f"Blog not found with slus {slug}")
            comment_id=None
        if cid:
            comment_id = Comments.objects.filter(comment_id=cid, user=request.user).first()
            if not comment_id:
                return Response(f"Comment not found with id {cid}")
            blog_id=None

        seiralizer = PostReactionSerializer(data=request.data,
                                            context={'request':request,'blog_id':blog_id,'comment':comment_id,'reaction':reaction})
        seiralizer.is_valid(raise_exception=True)
        rea = seiralizer.save()

        if rea is None:
            return Response(f"{reaction} changed.", status=status.HTTP_200_OK)
        return Response(f"{reaction} sucessfullt added",status=status.HTTP_201_CREATED)


class TrendingHashtagsView(APIView):
    permission_classes=[IsAuthenticated]
    def get(self, request):
        one_week_ago = timezone.now() - timedelta(days=7)

        hashtags = (
                HashTags.objects.filter(posts__created_at__gte=one_week_ago)
                .annotate(usage_count=Count("posts"))
                .order_by("-usage_count")[:10]
            )

        total_count = sum(tag.usage_count for tag in hashtags)
        data = [
            {
                "hashtag": tag.name,
                "count": tag.usage_count,
                "percentage": round((tag.usage_count / total_count) * 100, 2) if total_count else 0
            }
            for tag in hashtags
        ]

        return Response(data)


class SlugView(APIView):
    permission_classes = [AllowAny]

    def get(self, request):
        blog = Blog.objects.all()
        serializer  = BlogSerializer(blog, many=True)
        slugs = [blogs['slug'] for blogs in serializer.data]
        return Response(slugs, status=status.HTTP_200_OK)