from django.db import models
from users.models import CustomUser
from django.utils.text import slugify
from django.db.models import Q

class HashTags(models.Model):
    name = models.CharField(max_length=100, unique=True)

    def __str__(self):
        return self.name
class Tag(models.Model):
    name = models.CharField(max_length=50, unique=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.name


class Blog(models.Model):
    blog_id = models.AutoField(primary_key=True)
    blog_title = models.CharField(max_length=255)
    slug = models.SlugField(unique=True)
    blog_description = models.TextField()
    user = models.ForeignKey(CustomUser, on_delete=models.CASCADE)
    image = models.ImageField(upload_to="blog-images/", null=True, blank=True)
    hashtags = models.ManyToManyField('HashTags', related_name="posts", blank=True)
    tags = models.ManyToManyField(Tag, related_name='posts', blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return self.blog_title
    
    def save(self, *args, **kwargs):
        if not self.slug:
            super().save(*args, **kwargs)
            base_slug = slugify(self.blog_title)
            self.slug = f"{base_slug}-{self.blog_id}"
            kwargs['force_insert'] = False
            super().save(*args, **kwargs)
        else:
            super().save(*args, **kwargs)


    @property 
    def like_count(self):
        return PostReaction.objects.filter(blog=self, reaction='like').count()


    @property
    def dislike_count(self):
        return PostReaction.objects.filter(blog=self, reaction='dislike').count()



class Comments(models.Model):
    comment_id = models.AutoField(primary_key=True)
    comment = models.TextField()
    user = models.ForeignKey(CustomUser, on_delete=models.CASCADE)
    blog = models.ForeignKey(Blog, on_delete=models.CASCADE)
    created_at = models.DateTimeField(auto_now_add=True)
    parent = models.ForeignKey('self', on_delete=models.CASCADE, null=True, blank=True, related_name='replies')

    def __str__(self):
        return self.comment
    
    def like_count(self):
        return PostReaction.objects.filter(comments=self, reaction='dislike').count()
    
    def dislike_count(self):
        return PostReaction.objects.filter(comments=self, reaction='dislike').count()

class PostReaction(models.Model):
    user = models.ForeignKey(CustomUser, on_delete=models.CASCADE)
    blog = models.ForeignKey(Blog, on_delete=models.CASCADE, blank=True, null=True)
    comment = models.ForeignKey(Comments, on_delete=models.CASCADE, blank=True, null=True)
    reaction = models.CharField(max_length=10, choices=[('like','Like'), ('dislike','Dislike')])
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=['user', 'blog'], condition=Q(blog__isnull=False), name='unique_user_blog'),
            models.UniqueConstraint(fields=['user', 'comment'], condition=Q(comment__isnull=False), name='unique_user_comment'),
        ]


class BlogMetadata(models.Model):
    blog = models.OneToOneField(Blog, on_delete=models.CASCADE, related_name='metadata')
    author = models.ForeignKey(CustomUser, on_delete=models.CASCADE)
    summary = models.CharField(max_length=255, blank=True, null=True)
    reading_time = models.IntegerField(blank=True, null=True)
    seo_keywords = models.CharField(max_length=255, blank=True, null=True)
    published_at = models.DateTimeField(blank=True, null=True)
    updated_at = models.DateTimeField(auto_now=True)
    tags = models.ManyToManyField(Tag, related_name='metadata_blogs', blank=True)

    def __str__(self):
        return f"Metadata for {self.blog.blog_title}"

    def save(self, *args, **kwargs):
        if not self.summary and self.blog.blog_description:
            self.summary = self.blog.blog_description[:150] 
        if not self.reading_time and self.blog.blog_description:
            import math
            word_count = len(self.blog.blog_description.split())
            self.reading_time = math.ceil(word_count / 100)

        if not self.published_at:
            self.published_at = self.blog.created_at

        super().save(*args, **kwargs)


