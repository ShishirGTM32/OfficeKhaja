import re, math, string
from rest_framework import serializers
from collections import Counter
from users.serializers import UserSerializer
from nltk.corpus import stopwords
from .models import Blog, Comments,  HashTags, BlogMetadata, Tag, PostReaction

class HashTagSerializer(serializers.ModelSerializer):
    class Meta:
        model = HashTags
        fields = ['id', 'name']

class CommentSerializer(serializers.ModelSerializer):
    likes = serializers.SerializerMethodField()
    dislikes = serializers.SerializerMethodField()
    replies = serializers.SerializerMethodField()

    class Meta:
        model = Comments
        fields = ['comment_id', 'comment', 'likes', 'dislikes', 'user', 'blog','created_at', 'parent', 'replies']
        read_only_fields = ['comment_id', 'likes', 'dislikes', 'user','blog', 'created_at', 'replies']

    def get_likes(self, obj):
        return obj.like_count()

    def get_dislikes(self, obj):
        return obj.dislike_count()

    def get_replies(self, obj):
        serializer = CommentSerializer(obj.replies.all(), many=True)
        return serializer.data

    def create(self, validated_data):
        validated_data['user'] = self.context['request'].user
        validated_data['blog'] = self.context['blog']
        return super().create(validated_data)

class TagSerializer(serializers.ModelSerializer):
    class Meta:
        model = Tag
        fields = ['id', 'name', 'created_at']
        read_only_fields = ['id', 'name', 'created_at']

class BlogMetadataSerializer(serializers.ModelSerializer):
    tags = serializers.SlugRelatedField(many=True,read_only=True,slug_field="name")

    class Meta:
        model = BlogMetadata
        fields = [
            'author','summary','reading_time','seo_keywords','published_at','updated_at','tags' 
        ]

class BlogSerializer(serializers.ModelSerializer):
    hashtags = HashTagSerializer(read_only=True, many=True)
    tags = TagSerializer(read_only=True, many=True)
    metadata = BlogMetadataSerializer(read_only=True)
    comments = CommentSerializer(read_only=True, many=True)
    likes = serializers.SerializerMethodField()
    dislikes = serializers.SerializerMethodField()

    class Meta:
        model = Blog
        fields = [
            'blog_id', 'blog_title', 'blog_description',
            'tags', 'hashtags', 'metadata', 'comments', 'likes', 'dislikes',
            'user', 'image', 'created_at', 'slug'

        ]
        read_only_fields = ['blog_id', 'created_at', 'likes', 'dislikes', 'user', 'slug', 'metadata']

    def get_likes(self, obj):
        return getattr(obj, 'likes_total', obj.like_count)

    def get_dislikes(self, obj):
        return getattr(obj, 'dislikes_total', obj.dislike_count)

    def extract_hashtags(self, description):
        if not isinstance(description, str):
            description = str(description)
        raw_tags = re.findall(r"#(\w+)", description or "")
        return list(set(tag.lower() for tag in raw_tags))

    def extract_tags(self, description, max_tags=5):
        if not isinstance(description, str):
            description = str(description)
        clean_text = re.sub(r"#\w+", "", description)
        words = re.findall(r"\b\w+\b", clean_text.lower())
        stopword = set(stopwords.words('english'))
        keywords = [w for w in words if w not in stopword]
        top_keywords = [w for w, _ in Counter(keywords).most_common(max_tags)]
        return top_keywords


    def create(self, validated_data):
        user = self.context['request'].user
        validated_data['user'] = user

        description = validated_data.get("blog_description", "")

        hashtags_list = self.extract_hashtags(description)
        tags_list = self.extract_tags(description)

        blog = super().create(validated_data)

        for tag in hashtags_list:
            hashtag_obj, _ = HashTags.objects.get_or_create(name=tag)
            blog.hashtags.add(hashtag_obj)

        for tag in tags_list:
            tag_obj, _ = Tag.objects.get_or_create(name=tag)
            blog.tags.add(tag_obj)

        word_count = len(description.split())
        reading_time = math.ceil(word_count / 200) if word_count else None
        summary = description[:150] if description else ""

        metadata = BlogMetadata.objects.create(
            blog=blog,
            author=user,
            summary=summary,
            reading_time=reading_time,
            published_at=blog.created_at
        )
        metadata.seo_keywords = ",".join(tags_list + hashtags_list)
        metadata.save() 
        metadata.tags.set(blog.tags.all())

        return blog

    def update(self, instance, validated_data):
        description = validated_data.get("blog_description", instance.blog_description)

        hashtags_list = self.extract_hashtags(description)
        tags_list = self.extract_tags(description)

        instance = super().update(instance, validated_data)

        instance.hashtags.clear()
        for tag in hashtags_list:
            hashtag_obj, _ = HashTags.objects.get_or_create(name=tag)
            instance.hashtags.add(hashtag_obj)

        instance.tags.clear()
        for tag in tags_list:
            tag_obj, _ = Tag.objects.get_or_create(name=tag)
            instance.tags.add(tag_obj)

        metadata, created = BlogMetadata.objects.get_or_create(blog=instance, defaults={
            'author': instance.user,
            'summary': description[:150] if description else "",
            'reading_time': math.ceil(len(description.split()) / 100) if description else None,
            'published_at': instance.created_at
        })

        if not created:
            metadata.summary = description[:150] if description else ""
            metadata.reading_time = math.ceil(len(description.split()) / 100) if description else None
            metadata.tags.set(instance.tags.all())
            metadata.seo_keywords = ",".join(tags_list + hashtags_list)
            metadata.save()

        return instance

    
class PostReactionSerializer(serializers.ModelSerializer):
    user = UserSerializer(read_only=True)
    blog = BlogSerializer(read_only=True)
    comment = CommentSerializer(read_only=True)

    class Meta:
        model = PostReaction
        fields = ['id', 'user', 'blog', 'comment', 'reaction', 'created_at']
        read_only_fields = ['id', 'user', 'blog', 'comment', 'created_at', 'reaction']

    def create(self, validated_data):
        user = self.context['request'].user
        blog_id = self.context.get('blog_id')
        comment_id = self.context.get('comment')
        reaction_type = self.context.get('reaction') 

        if blog_id and comment_id:
            raise serializers.ValidationError("You can react to either a blog or a comment, not both.")
        if not blog_id and not comment_id:
            raise serializers.ValidationError("You must provide either a blog_id or a comment_id.")
        if reaction_type not in ['like', 'dislike']:
            raise serializers.ValidationError("Reaction must be either 'like' or 'dislike'.")
        
        filter_kwargs = {'user': user}
        if blog_id:
            filter_kwargs['blog_id'] = blog_id.blog_id
            filter_kwargs['comment_id'] = None
        else:
            filter_kwargs['comment_id'] = comment_id.comment_id
            filter_kwargs['blog'] = None

        existing = PostReaction.objects.filter(**filter_kwargs).first()
        if existing:
            if existing.reaction == reaction_type:
                existing.delete()
                raise serializers.ValidationError(f"{reaction_type.capitalize()} removed (toggle off).")
            else:
                existing.reaction = reaction_type
                existing.save()
                return existing
            
        return PostReaction.objects.create(reaction=reaction_type, **filter_kwargs)     